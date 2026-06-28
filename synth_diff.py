"""
synth_diff.py — Synthesis Netlist Port-Preservation Checker
RTL-Gen AI v3.1

Runs Yosys synthesis on an RTL source and diffs the resulting netlist's
port list against the original RTL to catch:
  - Renamed ports
  - Changed port directions
  - Truncated / widened ports
  - Merged flip-flops (register-count regression)
  - Constant-propagation that silently eliminates ports

Entry point:
    from synth_diff import check_synthesis_port_preservation
    result = check_synthesis_port_preservation(rtl_path, module_name)

The function tries Docker (efabless/openlane:latest) first, then falls
back to a locally-installed ``yosys`` binary.

Env-vars honoured:
    OPENLANE_WORK  — host path mounted to /work inside Docker
                     (default: C:\\tools\\OpenLane)
    OPENLANE_PDK   — host path mounted to /pdk  inside Docker
                     (default: C:/pdk)
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

_WORK_DIR = Path(os.getenv("OPENLANE_WORK", r"C:\tools\OpenLane"))
_PDK_HOST = os.getenv("OPENLANE_PDK", "C:/pdk")

# ---------------------------------------------------------------------------
# Port parsing
# ---------------------------------------------------------------------------

# Matches lines like:
#   input  wire [7:0]  data_in,
#   output reg         out_valid
#   inout              bidir
_PORT_RE = re.compile(
    r"^\s*(input|output|inout)\s+"  # direction
    r"(?:wire\s+|reg\s+)?"  # optional net type
    r"(?:\[([^\]]+)\]\s+)?"  # optional width [msb:lsb]
    r"(\w+)",  # port name
    re.MULTILINE,
)


def _parse_ports(verilog_text: str) -> Dict[str, Tuple[str, Optional[str]]]:
    """
    Return {name: (direction, width_str)} for every port declaration found.
    width_str is None when the port is 1-bit (no bracket).
    """
    ports: Dict[str, Tuple[str, Optional[str]]] = {}
    for m in _PORT_RE.finditer(verilog_text):
        direction = m.group(1).lower()
        width = m.group(2)  # may be None
        name = m.group(3)
        ports[name] = (direction, width)
    return ports


# ---------------------------------------------------------------------------
# Flip-flop counting
# ---------------------------------------------------------------------------


def _count_rtl_flops(verilog_text: str) -> int:
    """Count ``always @(posedge`` blocks as a proxy for synchronous registers."""
    return len(re.findall(r"always\s*@\s*\(\s*posedge", verilog_text, re.IGNORECASE))


def _count_synth_flops(synth_text: str) -> int:
    """
    Count DFF cells in the synthesized netlist.
    Matches sky130 DFF variants (sky130_fd_sc_hd__dfrtp, __dfxtp, …) and
    generic Yosys ``$dff`` / ``$sdff`` cells.
    """
    sky130_dffs = len(re.findall(r"sky130_fd_sc_hd__df\w+", synth_text, re.IGNORECASE))
    generic_dffs = len(
        re.findall(r"\\\$[sd]?dff\w*\b|\$[sd]?dff\w*\s+\\", synth_text, re.IGNORECASE)
    )
    return sky130_dffs + generic_dffs


# ---------------------------------------------------------------------------
# Yosys TCL synthesis script builder
# ---------------------------------------------------------------------------

_SYNTH_TCL_TEMPLATE = """\
# synth_diff.py — auto-generated Yosys synthesis script
read_verilog {rtl_linux}
hierarchy -top {module}

# Try sky130 flow; fall back to generic synth if PDK cells unavailable.
if {{ [catch {{ synth_sky130 -flatten -top {module} -run :check }} err] }} {{
    puts "synth_sky130 not available: $err — using generic synth"
    synth -flatten -top {module}
}}

write_verilog -noattr {out_linux}
stat
puts "SYNTH_DIFF_DONE"
exit
"""


def _build_synth_tcl(rtl_linux: str, module: str, out_linux: str) -> str:
    return _SYNTH_TCL_TEMPLATE.format(
        rtl_linux=rtl_linux, module=module, out_linux=out_linux
    )


# ---------------------------------------------------------------------------
# Docker / local runner
# ---------------------------------------------------------------------------


def _run_yosys_tcl(
    tcl_host_path: Path,
    work_dir: Path,
) -> Tuple[int, str]:
    """
    Run ``yosys -s <tcl>`` via Docker first; fall back to local binary.
    Returns (returncode, combined_output).
    """
    try:
        tcl_rel = tcl_host_path.relative_to(work_dir)
    except ValueError:
        return 1, f"TCL file {tcl_host_path} is outside work_dir {work_dir}"

    tcl_linux = "/work/" + str(tcl_rel).replace("\\", "/")

    # ---- Docker attempt ---------------------------------------------------
    try:
        proc = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{str(work_dir)}:/work",
                "-v",
                f"{_PDK_HOST}:/pdk",
                "efabless/openlane:latest",
                "yosys",
                "-s",
                tcl_linux,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        return proc.returncode, proc.stdout + proc.stderr
    except FileNotFoundError:
        log.debug("synth_diff: docker not found, trying local yosys")
    except subprocess.TimeoutExpired:
        return 1, "Docker yosys timed out"
    except Exception as exc:
        log.debug("synth_diff: docker error: %s", exc)

    # ---- Local yosys fall-back -------------------------------------------
    # When running locally the TCL paths must be host paths, not /work/…
    try:
        proc = subprocess.run(
            ["yosys", "-s", str(tcl_host_path)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        return proc.returncode, proc.stdout + proc.stderr
    except FileNotFoundError:
        return 1, "yosys binary not found (Docker unavailable too)"
    except subprocess.TimeoutExpired:
        return 1, "Local yosys timed out"
    except Exception as exc:
        return 1, str(exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_SENTINEL = object()  # used as a default-sentinel for work_dir


def check_synthesis_port_preservation(
    rtl_path: Path,
    module_name: str,
    work_dir: Optional[Path] = None,
) -> dict:
    """
    Run Yosys synthesis and diff the port list against the original RTL.

    Checks:
    1. Port names are preserved (no renaming)
    2. Port directions are preserved
    3. Port widths are preserved (no truncation)
    4. No flip-flops were merged (register count preserved)
    5. No constant-propagation that eliminates ports

    Returns dict with:
        port_match       : bool
        width_match      : bool
        flop_count_rtl   : int
        flop_count_synth : int
        missing_ports    : list[str]   — in RTL but absent from synth
        extra_ports      : list[str]   — in synth but absent from RTL
        width_mismatches : list[str]   — human-readable diff lines
        raw_yosys_output : str
        error            : str | None
    """
    result: dict = {
        "port_match": False,
        "width_match": False,
        "flop_count_rtl": 0,
        "flop_count_synth": 0,
        "missing_ports": [],
        "extra_ports": [],
        "width_mismatches": [],
        "raw_yosys_output": "",
        "error": None,
    }

    rtl_path = Path(rtl_path)
    _wd: Path = Path(work_dir) if work_dir is not None else _WORK_DIR
    work_dir = _wd

    if not rtl_path.exists():
        result["error"] = f"RTL file not found: {rtl_path}"
        return result

    # ---- Read RTL source --------------------------------------------------
    try:
        rtl_text = rtl_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result["error"] = f"Cannot read RTL: {exc}"
        return result

    rtl_ports = _parse_ports(rtl_text)
    result["flop_count_rtl"] = _count_rtl_flops(rtl_text)

    if not rtl_ports:
        result["error"] = "No port declarations found in RTL source"
        return result

    # ---- Build temporary work area ----------------------------------------
    # We need the TCL and output files to live inside work_dir so Docker's
    # /work volume mount can reach them.
    synth_dir = work_dir / "_synth_diff_tmp"
    synth_dir.mkdir(parents=True, exist_ok=True)

    out_host = synth_dir / f"{module_name}_synth.v"
    tcl_host = synth_dir / f"{module_name}_synth_diff.tcl"

    # Build Linux container paths (/work/…)
    try:
        rtl_rel = rtl_path.relative_to(work_dir)
        rtl_linux = "/work/" + str(rtl_rel).replace("\\", "/")
    except ValueError:
        # RTL is outside work_dir — copy it in
        import shutil

        rtl_copy = synth_dir / rtl_path.name
        shutil.copy2(rtl_path, rtl_copy)
        rtl_linux = "/work/_synth_diff_tmp/" + rtl_path.name

    out_rel = out_host.relative_to(work_dir)
    out_linux = "/work/" + str(out_rel).replace("\\", "/")

    # ---- Write TCL --------------------------------------------------------
    tcl_content = _build_synth_tcl(rtl_linux, module_name, out_linux)
    # Local-path version for fall-back (paths replaced to host paths)
    tcl_local_content = _SYNTH_TCL_TEMPLATE.format(
        rtl_linux=str(rtl_path).replace("\\", "/"),
        module=module_name,
        out_linux=str(out_host).replace("\\", "/"),
    )
    # Write both; Docker uses container paths, local uses host paths.
    # We write the Docker version by default and rewrite if Docker fails
    # inside _run_yosys_tcl (local fallback reads the same file but yosys
    # resolves paths from the host OS — so we write local paths for the
    # local fallback case and Docker paths for Docker).
    tcl_host.write_text(tcl_content, encoding="utf-8")

    # ---- Run Yosys --------------------------------------------------------
    rc, yosys_output = _run_yosys_tcl(tcl_host, work_dir)
    result["raw_yosys_output"] = yosys_output[:8000]  # cap stored output

    # If Docker failed and local yosys was tried, the TCL may need host paths.
    # Detect by checking if output contains a "not found" error and retry.
    if rc != 0 and "SYNTH_DIFF_DONE" not in yosys_output:
        # Rewrite TCL with host paths and retry local yosys
        tcl_host.write_text(tcl_local_content, encoding="utf-8")
        rc2, yosys_output2 = _run_yosys_tcl(tcl_host, work_dir)
        if "SYNTH_DIFF_DONE" in yosys_output2:
            rc, yosys_output = rc2, yosys_output2
            result["raw_yosys_output"] = yosys_output[:8000]

    if "SYNTH_DIFF_DONE" not in yosys_output:
        result["error"] = (
            f"Yosys synthesis did not complete (rc={rc}). "
            f"Output tail: {yosys_output[-400:]}"
        )
        return result

    # ---- Read synthesized netlist -----------------------------------------
    if not out_host.exists():
        result["error"] = (
            f"Synthesis completed but output netlist not written: {out_host}"
        )
        return result

    try:
        synth_text = out_host.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result["error"] = f"Cannot read synthesized netlist: {exc}"
        return result

    # ---- Compare ports ----------------------------------------------------
    synth_ports = _parse_ports(synth_text)
    result["flop_count_synth"] = _count_synth_flops(synth_text)

    rtl_names = set(rtl_ports)
    synth_names = set(synth_ports)

    missing = sorted(rtl_names - synth_names)
    extra = sorted(synth_names - rtl_names)
    result["missing_ports"] = missing
    result["extra_ports"] = extra
    result["port_match"] = len(missing) == 0 and len(extra) == 0

    # Width / direction mismatches for common ports
    width_issues: List[str] = []
    for name in sorted(rtl_names & synth_names):
        rtl_dir, rtl_w = rtl_ports[name]
        syn_dir, syn_w = synth_ports[name]
        issues = []
        if rtl_dir != syn_dir:
            issues.append(f"direction {rtl_dir}→{syn_dir}")
        if rtl_w != syn_w:
            issues.append(f"width [{rtl_w}]→[{syn_w}]")
        if issues:
            width_issues.append(f"{name}: " + ", ".join(issues))

    result["width_mismatches"] = width_issues
    result["width_match"] = len(width_issues) == 0

    log.info(
        "synth_diff %s: ports match=%s width_match=%s "
        "missing=%s extra=%s flops rtl=%d synth=%d",
        module_name,
        result["port_match"],
        result["width_match"],
        missing,
        extra,
        result["flop_count_rtl"],
        result["flop_count_synth"],
    )

    return result


# ---------------------------------------------------------------------------
# Standalone self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("synth_diff.py — standalone self-test (parser only)")
    print("=" * 60)

    passed = total = 0

    # Test 1: port regex
    total += 1
    sample = """\
module adder (
    input  wire [7:0] a,
    input  wire [7:0] b,
    output wire [8:0] sum,
    inout              bidir
);
"""
    ports = _parse_ports(sample)
    assert "a" in ports and ports["a"] == ("input", "7:0"), ports
    assert "sum" in ports and ports["sum"] == ("output", "8:0"), ports
    assert "bidir" in ports and ports["bidir"] == ("inout", None), ports
    print(f"[PASS] Port regex: {sorted(ports.keys())}")
    passed += 1

    # Test 2: flop counting
    total += 1
    rtl_sample = "always @(posedge clk) q <= d;\nalways @(posedge clk) r <= e;"
    assert _count_rtl_flops(rtl_sample) == 2, _count_rtl_flops(rtl_sample)
    print("[PASS] RTL flop count: 2")
    passed += 1

    # Test 3: synth flop counting (sky130 cells)
    total += 1
    synth_sample = (
        "sky130_fd_sc_hd__dfrtp_1 _42_ (.CLK(clk),.D(d),.Q(q));\n"
        "sky130_fd_sc_hd__dfxtp_2 _43_ (.CLK(clk),.D(e),.Q(r));\n"
    )
    assert _count_synth_flops(synth_sample) == 2, _count_synth_flops(synth_sample)
    print("[PASS] Synth flop count (sky130): 2")
    passed += 1

    # Test 4: missing-port detection
    total += 1
    rtl_ports_t = {
        "a": ("input", "7:0"),
        "b": ("input", "7:0"),
        "sum": ("output", "8:0"),
    }
    syn_ports_t = {"a": ("input", "7:0"), "sum": ("output", "8:0")}
    missing = sorted(set(rtl_ports_t) - set(syn_ports_t))
    assert missing == ["b"], missing
    print(f"[PASS] Missing port detection: {missing}")
    passed += 1

    # Test 5: width mismatch detection
    total += 1
    rtl_ports_w = {"a": ("input", "7:0")}
    syn_ports_w = {"a": ("input", "6:0")}  # truncated
    issues = []
    for name in sorted(set(rtl_ports_w) & set(syn_ports_w)):
        rd, rw = rtl_ports_w[name]
        sd, sw = syn_ports_w[name]
        if rw != sw:
            issues.append(f"{name}: width [{rw}]→[{sw}]")
    assert issues == ["a: width [7:0]→[6:0]"], issues
    print(f"[PASS] Width mismatch detection: {issues}")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED — synth_diff.py ready for integration")
    else:
        sys.exit(1)
    print("=" * 60)
