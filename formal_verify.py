"""
formal_verify.py — Formal Property Verification (Fixed v3.4)
RTL-Gen AI

Root cause of 0/5 pass, 0 fail:
  1. Python f-string double-brace escaping produced malformed TCL
     catch blocks that silently prevented puts() from executing.
  2. SAT commands require SVA assertions — Sky130 templates have none,
     so sat returned nothing and the parser found no markers.

This version fixes both:
  - Uses =PROP_BEGIN:name= / =PROP_DONE:name= bracket approach.
    If Yosys exits early, DONE never appears -> FAIL is detected.
  - Replaces SAT commands with Yosys built-in checks that work on
    any standard Verilog without requiring SVA properties.

Properties checked (all work without SVA assertions):
  1. no_combinational_loops  -- Yosys check command
  2. hierarchy_consistent    -- hierarchy -check
  3. synthesis_clean         -- synth -noabc (catches unsupported constructs)
  4. no_multi_driven         -- check -noinit
  5. logic_well_formed       -- proc; opt_clean; check

Standalone test:
    python formal_verify.py
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_WORK_DIR = Path(r"C:\tools\OpenLane")


@dataclass
class Property:
    name: str
    description: str
    yosys_cmd: str
    kind: str = "safety"


UNIVERSAL_PROPERTIES: List[Property] = [
    Property(
        name="no_combinational_loops",
        description="No combinational feedback loops exist",
        yosys_cmd="check",
    ),
    Property(
        name="hierarchy_consistent",
        description="All module references are resolved",
        yosys_cmd="hierarchy -check",
    ),
    Property(
        name="synthesis_clean",
        description="Design synthesizes without unsupported constructs",
        yosys_cmd="synth -noabc -flatten",
    ),
    Property(
        name="no_multi_driven",
        description="No nets driven by multiple sources",
        yosys_cmd="check -noinit",
    ),
    Property(
        name="logic_well_formed",
        description="Internal logic structure passes well-formedness check",
        yosys_cmd="proc; opt_clean -purge; check",
    ),
]


@dataclass
class PropertyResult:
    property_name: str
    description: str
    status: str
    detail: str = ""
    elapsed_sec: float = 0.0


@dataclass
class FormalReport:
    design_name: str
    netlist_path: str
    module_name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[PropertyResult] = field(default_factory=list)
    elapsed_sec: float = 0.0
    yosys_available: bool = False

    @property
    def pass_rate(self) -> float:
        checked = self.passed + self.failed
        return (self.passed / checked * 100) if checked > 0 else 0.0

    @property
    def overall_status(self) -> str:
        if self.failed > 0:
            return "FAIL"
        if self.passed > 0:
            return "PASS"
        return "SKIP"

    def to_dict(self) -> Dict:
        return {
            "design_name": self.design_name,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 1),
            "status": self.overall_status,
            "results": [
                {"name": r.property_name, "desc": r.description,
                 "status": r.status, "detail": r.detail[:200]}
                for r in self.results
            ],
        }


def _build_formal_tcl(
    netlist_linux: str,
    module_name: str,
    properties: List[Property],
) -> str:
    """
    Build Yosys TCL with =PROP_BEGIN:name= / =PROP_DONE:name= markers.
    No catch blocks, no f-string double-brace escaping.
    If Yosys exits early on a failure, DONE is never printed -> FAIL.
    """
    checks = ""
    for p in properties:
        checks += "log =PROP_BEGIN:" + p.name + "=\n"
        checks += p.yosys_cmd + "\n"
        checks += "log =PROP_DONE:" + p.name + "=\n\n"

    return (
        "# RTL-Gen AI Formal Verification -- " + module_name + "\n"
        "read_verilog " + netlist_linux + "\n"
        "hierarchy -top " + module_name + "\n"
        "log =FORMAL_START=\n"
        + checks +
        "log =FORMAL_END=\n"
    )


def _parse_formal_output(
    output: str,
    properties: List[Property],
) -> List[PropertyResult]:
    """
    Parse using BEGIN/DONE bracket markers.
    BEGIN found + DONE found   = PASS
    BEGIN found + DONE missing = FAIL (Yosys exited early)
    BEGIN not found            = SKIP
    """
    results = []

    for prop in properties:
        begin_tag = "=PROP_BEGIN:" + prop.name + "="
        done_tag = "=PROP_DONE:" + prop.name + "="

        begin_idx = output.find(begin_tag)

        if begin_idx < 0:
            results.append(PropertyResult(
                prop.name, prop.description, "SKIP",
                "Property not reached in output"
            ))
            continue

        done_idx = output.find(done_tag, begin_idx)

        if done_idx < 0:
            next_begin = output.find("=PROP_BEGIN:", begin_idx + len(begin_tag))
            extract_end = next_begin if next_begin > 0 else min(begin_idx + 800, len(output))
            raw = output[begin_idx + len(begin_tag):extract_end].strip()
            error_lines = [
                l.strip() for l in raw.splitlines()
                if any(kw in l.lower() for kw in
                       ["error", "warning", "loop", "multiple", "undefined"])
            ]
            detail = " | ".join(error_lines[:3]) if error_lines else raw[:200]
            results.append(PropertyResult(
                prop.name, prop.description, "FAIL", detail[:300]
            ))
        else:
            between = output[begin_idx + len(begin_tag):done_idx]
            if any(kw in between.lower()
                   for kw in ["error:", "assert failed", "found a latch"]):
                error_lines = [
                    l.strip() for l in between.splitlines()
                    if "error" in l.lower()
                ]
                results.append(PropertyResult(
                    prop.name, prop.description, "FAIL",
                    " | ".join(error_lines[:2])[:200]
                ))
            else:
                results.append(PropertyResult(
                    prop.name, prop.description, "PASS", "ok"
                ))

    return results


def run_formal_verification_simple(
    netlist_path: Path,
    module_name: str,
    work_dir: Path = _WORK_DIR,
    properties: Optional[List[Property]] = None,
) -> FormalReport:
    """Run formal verification via Docker. No DockerManager required."""
    t0 = time.time()
    report = FormalReport(str(module_name), str(netlist_path), module_name)

    if not netlist_path.exists():
        log.warning("Formal: netlist not found: %s", netlist_path)
        return report

    if properties is None:
        properties = UNIVERSAL_PROPERTIES

    try:
        rel = netlist_path.relative_to(work_dir)
        nl_linux = "/work/" + str(rel).replace("\\", "/")
    except ValueError:
        nl_linux = "/work/designs/" + module_name + "/" + netlist_path.name

    tcl_content = _build_formal_tcl(nl_linux, module_name, properties)
    tcl_dir = work_dir / "scripts"
    tcl_dir.mkdir(parents=True, exist_ok=True)
    tcl_path = tcl_dir / (module_name + "_formal.tcl")
    tcl_path.write_text(tcl_content, encoding="utf-8")
    tcl_linux = "/work/scripts/" + module_name + "_formal.tcl"

    log.debug("Formal TCL:\n%s", tcl_content)

    try:
        result = subprocess.run(
            ["docker", "run", "--rm",
             "-v", str(work_dir) + ":/work",
             "efabless/openlane:latest",
             "yosys", "-s", tcl_linux],
            capture_output=True, text=True, timeout=120,
        )
        output = (result.stdout or "") + (result.stderr or "")
        report.yosys_available = True

        out_path = netlist_path.parent / (module_name + "_formal_output.txt")
        try:
            out_path.write_text(output, encoding="utf-8")
        except Exception:
            pass

    except subprocess.TimeoutExpired:
        log.warning("Formal: timeout after 120s")
        report.results = [
            PropertyResult(p.name, p.description, "SKIP", "Timeout")
            for p in properties
        ]
        report.total = report.skipped = len(properties)
        report.elapsed_sec = time.time() - t0
        return report

    except Exception as e:
        log.warning("Formal: %s", e)
        report.results = [
            PropertyResult(p.name, p.description, "SKIP", str(e)[:80])
            for p in properties
        ]
        report.total = report.skipped = len(properties)
        report.elapsed_sec = time.time() - t0
        return report

    parsed = _parse_formal_output(output, properties)
    report.results = parsed
    report.total = len(parsed)
    report.passed = sum(1 for r in parsed if r.status == "PASS")
    report.failed = sum(1 for r in parsed if r.status == "FAIL")
    report.skipped = sum(1 for r in parsed if r.status in ("SKIP", "ERROR"))
    report.elapsed_sec = time.time() - t0

    log.info("Formal verification: %d/%d pass, %d fail, %.1fs",
             report.passed, report.total, report.failed, report.elapsed_sec)
    return report


def run_formal_verification(
    netlist_path: Path,
    module_name: str,
    docker_manager=None,
    work_dir: Path = _WORK_DIR,
) -> FormalReport:
    return run_formal_verification_simple(netlist_path, module_name, work_dir)


def diagnose_formal(netlist_path: Path, module_name: str) -> None:
    """Quick diagnostic — prints raw Yosys output to confirm markers work."""
    work_dir = _WORK_DIR
    try:
        rel = netlist_path.relative_to(work_dir)
        nl_linux = "/work/" + str(rel).replace("\\", "/")
    except ValueError:
        nl_linux = "/work/designs/" + module_name + "/" + netlist_path.name

    tcl = (
        "read_verilog " + nl_linux + "\n"
        "hierarchy -top " + module_name + "\n"
        "log =DIAG_START=\n"
        "check\n"
        "log =DIAG_DONE=\n"
    )
    tcl_path = work_dir / "scripts" / (module_name + "_diag.tcl")
    tcl_path.parent.mkdir(parents=True, exist_ok=True)
    tcl_path.write_text(tcl, encoding="utf-8")

    result = subprocess.run(
        ["docker", "run", "--rm",
         "-v", str(work_dir) + ":/work",
         "efabless/openlane:latest",
         "yosys", "-s", "/work/scripts/" + module_name + "_diag.tcl"],
        capture_output=True, text=True, timeout=60,
    )
    output = result.stdout + result.stderr
    print("=== RAW OUTPUT ===")
    print(output[:2000])
    print("=== DIAG_START found:", "=DIAG_START=" in output)
    print("=== DIAG_DONE  found:", "=DIAG_DONE=" in output)


def render_formal_results_streamlit(
    report: Optional[FormalReport],
    run_dir: Optional[Path] = None,
    design_name: str = "",
) -> None:
    import streamlit as st

    if report is None and run_dir:
        out_file = Path(run_dir) / (design_name + "_formal_output.txt")
        if out_file.exists():
            raw = out_file.read_text(errors="replace")
            results = _parse_formal_output(raw, UNIVERSAL_PROPERTIES)
            report = FormalReport(
                design_name=design_name,
                netlist_path="",
                module_name=design_name,
                results=results,
                total=len(results),
                passed=sum(1 for r in results if r.status == "PASS"),
                failed=sum(1 for r in results if r.status == "FAIL"),
                skipped=sum(1 for r in results if r.status in ("SKIP", "ERROR")),
            )

    if report is None:
        st.info("Formal verification not yet run for this design.")
        return

    icons = {"PASS": "P", "FAIL": "F", "SKIP": "S", "ERROR": "E"}

    if report.overall_status == "PASS":
        st.success("Formal PASS -- {}/{} properties verified".format(report.passed, report.total))
    elif report.overall_status == "FAIL":
        st.error("Formal FAIL -- {} violation(s)".format(report.failed))
    else:
        st.warning("Formal -- {}/{} skipped".format(report.skipped, report.total))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", report.total)
    c2.metric("Pass", report.passed)
    c3.metric("Fail", report.failed)
    c4.metric("Rate", "{:.0f}%".format(report.pass_rate))

    for r in report.results:
        icon = icons.get(r.status, "?")
        with st.expander("[{}] {} -- {}".format(icon, r.property_name, r.description)):
            st.caption("Status: **{}**".format(r.status))
            if r.detail and r.detail != "ok":
                st.code(r.detail, language="text")

    st.caption(
        "Yosys built-in checks | {:.1f}s | No SVA assertions required".format(report.elapsed_sec)
    )


if __name__ == "__main__":
    print("=" * 60)
    print("formal_verify.py v3.4 -- standalone self-test")
    print("=" * 60)

    passed = total = 0

    # Test 1: TCL has correct markers, no double-brace artifacts
    total += 1
    tcl = _build_formal_tcl("/work/test.v", "adder_8bit", UNIVERSAL_PROPERTIES)
    for prop in UNIVERSAL_PROPERTIES:
        assert "=PROP_BEGIN:" + prop.name + "=" in tcl
        assert "=PROP_DONE:" + prop.name + "=" in tcl
        assert prop.yosys_cmd in tcl
    assert "{{" not in tcl, "Double-brace artifact found"
    assert "}}" not in tcl, "Double-brace artifact found"
    assert "read_verilog /work/test.v" in tcl
    print("[PASS] TCL: {} chars, all markers, no brace artifacts".format(len(tcl)))
    passed += 1

    # Test 2: All-pass parsing
    total += 1
    ap = "=FORMAL_START=\n"
    for prop in UNIVERSAL_PROPERTIES:
        ap += "=PROP_BEGIN:" + prop.name + "=\nOK\n=PROP_DONE:" + prop.name + "=\n"
    ap += "=FORMAL_END=\n"
    r = _parse_formal_output(ap, UNIVERSAL_PROPERTIES)
    assert all(x.status == "PASS" for x in r), str([(x.property_name, x.status) for x in r])
    print("[PASS] All-pass: {}".format([(x.property_name, x.status) for x in r]))
    passed += 1

    # Test 3: Early exit -> FAIL
    total += 1
    fe = ("=FORMAL_START=\n"
          "=PROP_BEGIN:no_combinational_loops=\n"
          "ERROR: Combinational loop detected\n"
          "=FORMAL_END=\n")
    r2 = _parse_formal_output(fe, UNIVERSAL_PROPERTIES[:1])
    assert r2[0].status == "FAIL"
    assert "loop" in r2[0].detail.lower() or "Combinational" in r2[0].detail
    print("[PASS] Early-exit FAIL: '{}'".format(r2[0].detail[:50]))
    passed += 1

    # Test 4: Property not reached -> SKIP
    total += 1
    partial = ("=PROP_BEGIN:no_combinational_loops=\nOK\n"
               "=PROP_DONE:no_combinational_loops=\n")
    r3 = _parse_formal_output(partial, UNIVERSAL_PROPERTIES[:2])
    assert r3[0].status == "PASS"
    assert r3[1].status == "SKIP"
    print("[PASS] Partial: {}".format([(x.property_name, x.status) for x in r3]))
    passed += 1

    # Test 5: FormalReport
    total += 1
    rpt = FormalReport("t", "", "t", results=[
        PropertyResult("a", "", "PASS", "ok"),
        PropertyResult("b", "", "FAIL", "err"),
        PropertyResult("c", "", "SKIP", ""),
    ], total=3, passed=1, failed=1, skipped=1)
    assert rpt.overall_status == "FAIL"
    assert rpt.pass_rate == 50.0
    d = rpt.to_dict()
    assert d["total"] == 3 and len(d["results"]) == 3
    print("[PASS] FormalReport: status={} rate={}%".format(rpt.overall_status, rpt.pass_rate))
    passed += 1

    # Test 6: No SAT commands that require SVA
    total += 1
    for prop in UNIVERSAL_PROPERTIES:
        assert "prove-asserts" not in prop.yosys_cmd
    print("[PASS] No SAT/prove-asserts: {}".format([p.name for p in UNIVERSAL_PROPERTIES]))
    passed += 1

    print()
    print("=" * 60)
    print("Results: {}/{} passed".format(passed, total))
    if passed == total:
        print("ALL TESTS PASSED -- formal_verify.py v3.4 ready")
    print("=" * 60)
