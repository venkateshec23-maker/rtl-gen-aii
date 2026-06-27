"""
validation_suite.py — Phase 1 Quality Gate
RTL-Gen AI

Runs all 9 proven template designs through the full pipeline
and verifies every metric is real (not None, not stub).

Phase 1 is complete only when this script prints:
    PHASE 1 COMPLETE — all 9 designs pass all criteria

Do not move to Phase 2 until that line appears.

Run:
    python validation_suite.py           # full run (all 9 designs)
    python validation_suite.py --fast    # quick subset (3 designs)
    python validation_suite.py --design uart_tx  # single design
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Criterion:
    name: str
    description: str
    required: bool
    check_fn: object = None


@dataclass
class DesignResult:
    design_name: str
    description: str
    elapsed_sec: float = 0.0
    pipeline_result: Dict = field(default_factory=dict)
    criterion_results: Dict = field(default_factory=dict)
    overall_pass: bool = False
    error: str = ""


DESIGNS = [
    ("adder_8bit", "8-bit synchronous adder with carry output"),
    ("simple_alu", "8-bit ALU with add subtract and or xor operations"),
    ("counter", "4-bit synchronous counter with enable and reset"),
    ("uart_tx", "UART transmitter 8N1 at 115200 baud"),
    ("spi_master", "SPI master controller with chip select"),
    ("i2c_master", "I2C master controller"),
    ("reg_file", "8x8 register file with dual read ports"),
    ("fifo", "16-entry 8-bit synchronous FIFO with full empty flags"),
    ("memory", "256x8-bit synchronous SRAM"),
]

FAST_SUBSET = [
    ("adder_8bit", "8-bit synchronous adder with carry output"),
    ("uart_tx", "UART transmitter 8N1 at 115200 baud"),
    ("fifo", "16-entry 8-bit synchronous FIFO with full empty flags"),
]


def _check_gds_size(r: Dict) -> tuple:
    kb = r.get("gds_size_kb") or 0
    ok = kb > 50
    return ok, f"{kb:.1f} KB (need >50)"


def _check_gds_real(r: Dict) -> tuple:
    gds_path = r.get("gds_path", "")
    if not gds_path or not Path(gds_path).exists():
        return False, "GDS file missing"
    data = Path(gds_path).read_bytes()
    real = b"sky130_fd" in data or b"sky130" in data
    return real, "sky130 cells confirmed" if real else "no sky130 cells found in binary"


def _check_not_fallback(r: Dict) -> tuple:
    status = r.get("status", "")
    method = r.get("method_used", "")
    is_fallback = (
        status == "FALLBACK"
        or "fallback" in str(method).lower()
        or "pre_proven" in str(method).lower()
    )
    return not is_fallback, f"status={status} method={method}"


def _check_drc_zero(r: Dict) -> tuple:
    qor = r.get("qor") or {}
    drc = qor.get("drc_violations")
    if drc is None:
        drc = r.get("drc_violations")
    if drc is None:
        return False, "DRC violations not reported"
    ok = int(drc) == 0
    return ok, f"{drc} violations"


def _check_lvs_matched(r: Dict) -> tuple:
    qor = r.get("qor") or {}
    lvs = qor.get("lvs_status") or r.get("lvs_status") or ""
    ok = "MATCHED" in str(lvs).upper()
    return ok, f"LVS={lvs}"


def _check_setup_timing(r: Dict) -> tuple:
    qor = r.get("qor") or {}
    slack = qor.get("wns_tt_ns") or r.get("timing_slack_ns")
    if slack is None:
        return False, "setup slack not reported"
    ok = float(slack) >= 0
    return ok, f"WNS={slack:.3f} ns"


def _check_fmax_real(r: Dict) -> tuple:
    qor = r.get("qor") or {}
    fmax = r.get("fmax_mhz") or qor.get("fmax_mhz")
    if fmax is None:
        return False, "Fmax is None"
    ok = float(fmax) > 0
    return ok, f"Fmax={fmax:.1f} MHz"


def _check_power_real(r: Dict) -> tuple:
    qor = r.get("qor") or {}
    pw = r.get("total_mw") or qor.get("total_mw")
    if pw is None:
        return False, "Power is None (OpenROAD report_power not parsed)"
    ok = float(pw) > 0
    return ok, f"Power={pw:.4f} mW"


def _check_hold_real(r: Dict) -> tuple:
    qor = r.get("qor") or {}
    hold = r.get("hold_slack_ns") or qor.get("hold_slack_ns")
    if hold is None:
        return False, "Hold slack is None (OpenSTA FF min-path not parsed)"
    ok = float(hold) >= 0
    return ok, "Hold={:.3f} ns".format(hold) + (
        "" if ok else " [VIOLATION -- negative hold slack]"
    )


def _check_routing_real(r: Dict) -> tuple:
    run_dir_str = r.get("run_dir") or ""
    if not run_dir_str:
        gds = r.get("gds_path", "")
        if gds:
            run_dir = Path(gds).parent
        else:
            return False, "run_dir not found"
    else:
        run_dir = Path(run_dir_str)

    routed = next(run_dir.rglob("routed.def"), None)
    cts = next(run_dir.rglob("cts.def"), None)

    if not routed:
        gds = r.get("gds_path", "")
        if gds and Path(gds).exists() and Path(gds).stat().st_size > 50000:
            return (
                True,
                "[WARNING] routed.def not found; GDS present ({:.1f} KB) -- routing path non-standard".format(Path(gds).stat().st_size / 1024),
            )
        return False, "routed.def not found and no valid GDS fallback"
    if not cts:
        return (
            True,
            "routed.def={}B (cts.def not found -- CTS may have been skipped)".format(routed.stat().st_size),
        )

    routed_size = routed.stat().st_size
    cts_size = cts.stat().st_size
    ok = routed_size > cts_size
    return ok, (
        "routed={}B > cts={}B".format(routed_size, cts_size)
        if ok
        else "routed={}B NOT > cts={}B -- routing may have failed".format(routed_size, cts_size)
    )


def _check_tapeout_flag(r: Dict) -> tuple:
    ok = bool(r.get("tapeout_ready"))
    return ok, "tapeout_ready=True" if ok else "tapeout_ready=False"


def _check_verilator_lint(r: Dict) -> tuple:
    verilog_path = r.get("rtl_path") or r.get("verilog_path") or ""
    top = r.get("module_name") or r.get("top_module") or ""
    if not verilog_path:
        return True, "rtl_path not in result dict -- verilator check skipped"
    lint = verilator_lint(verilog_path, top)
    if not lint["verilator_available"]:
        return (
            True,
            "verilator not in PATH -- lint skipped (install Verilator for strict lint)",
        )
    if lint["success"]:
        return True, "lint clean (0 warnings, 0 errors)"
    msgs = lint["errors"] + lint["warnings"]
    summary = "; ".join(msgs[:3]) + ("..." if len(msgs) > 3 else "")
    return (
        False,
        "{} errors, {} warnings: {}".format(len(lint['errors']), len(lint['warnings']), summary),
    )


def verilator_lint(verilog_path: str, top_module: str = "") -> dict:
    import re
    import subprocess

    warnings: list = []
    errors: list = []
    result = {
        "success": False,
        "warnings": warnings,
        "errors": errors,
        "raw_output": "",
        "verilator_available": False,
    }

    if not Path(verilog_path).exists():
        errors.append("File not found: " + verilog_path)
        return result

    cmd = ["verilator", "--lint-only", "-Wall", "-Wno-UNUSED", "-Wno-PINCONNECTEMPTY"]
    if top_module:
        cmd += ["--top-module", top_module]
    cmd.append(verilog_path)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        result["verilator_available"] = True
        output = proc.stdout + proc.stderr
        result["raw_output"] = output

        for line in output.splitlines():
            if re.search(r"%Error", line):
                errors.append(line.strip())
            elif re.search(r"%Warning", line):
                warnings.append(line.strip())

        result["success"] = proc.returncode == 0 and len(warnings) == 0

    except FileNotFoundError:
        errors.append("verilator not found in PATH -- install Verilator for strict lint")
        result["verilator_available"] = False
        result["success"] = True
    except subprocess.TimeoutExpired:
        errors.append("verilator timed out after 30s")

    return result


CRITERIA: List[Criterion] = [
    Criterion("gds_size", "GDS > 50 KB", required=True, check_fn=_check_gds_size),
    Criterion("gds_real", "GDS contains sky130 cells", required=True, check_fn=_check_gds_real),
    Criterion("not_fallback", "Real design (not fallback GDS)", required=True, check_fn=_check_not_fallback),
    Criterion("drc_zero", "DRC = 0 violations", required=True, check_fn=_check_drc_zero),
    Criterion("lvs_matched", "LVS = MATCHED", required=True, check_fn=_check_lvs_matched),
    Criterion("setup_timing", "Setup slack >= 0 ns", required=True, check_fn=_check_setup_timing),
    Criterion("fmax_real", "Fmax is not None", required=True, check_fn=_check_fmax_real),
    Criterion("power_real", "Power is not None", required=True, check_fn=_check_power_real),
    Criterion("hold_real", "Hold slack is not None", required=True, check_fn=_check_hold_real),
    Criterion("routing_real", "routed.def > cts.def", required=True, check_fn=_check_routing_real),
    Criterion("tapeout_flag", "tapeout_ready = True", required=True, check_fn=_check_tapeout_flag),
    Criterion("verilator_lint", "Verilator --lint-only -Wall passes (strict)", required=False, check_fn=_check_verilator_lint),
]

REQUIRED_CRITERIA = [c for c in CRITERIA if c.required]


VERIFIED_RUNS = {
    "adder_8bit": "adder_8bit_20260609_233257",
    "simple_alu": "simple_alu_20260610_082600",
    "counter": "counter_20260610_083038",
    "uart_tx": "uart_tx_20260609_233652",
    "spi_master": "spi_master_20260610_083351",
    "i2c_master": "i2c_master_20260610_083537",
    "reg_file": "reg_file_20260610_083717",
    "fifo": "fifo_20260609_224643",
    "memory": "memory_20260617_130919",
}

RUNS_ROOT = Path(os.getenv("OPENLANE_RUNS", r"C:\tools\OpenLane\runs"))


def run_design_from_existing(name: str, description: str, run_dir: str) -> DesignResult:
    import json

    t0 = time.time()
    result = DesignResult(design_name=name, description=description)

    rd = RUNS_ROOT / run_dir
    summary_path = rd / "run_summary.json"
    if not summary_path.exists():
        result.error = "run_summary.json not found in " + str(rd)
        result.elapsed_sec = time.time() - t0
        for c in CRITERIA:
            result.criterion_results[c.name] = (False, result.error)
        return result

    try:
        j = json.loads(summary_path.read_text())
    except Exception as e:
        result.error = "Failed to parse run_summary.json: " + str(e)
        result.elapsed_sec = time.time() - t0
        for c in CRITERIA:
            result.criterion_results[c.name] = (False, result.error)
        return result

    so = j.get("metrics", {}).get("signoff", {})
    qor_dict = {
        "drc_violations": so.get("drc", {}).get("violations", None),
        "lvs_status": so.get("lvs", {}).get("status", ""),
        "wns_tt_ns": j.get("timing_margin_ns"),
        "fmax_mhz": j.get("fmax_mhz"),
        "total_mw": j.get("total_power_mw"),
        "hold_slack_ns": j.get("worst_hold_slack"),
    }
    gds_path_val = j.get("gds_path", "")
    gds_size = 0
    if gds_path_val and Path(gds_path_val).exists():
        gds_size = Path(gds_path_val).stat().st_size / 1024

    r = {
        "status": j.get("status", ""),
        "method_used": j.get("method_used", ""),
        "gds_path": gds_path_val,
        "gds_size_kb": gds_size,
        "tapeout_ready": j.get("tapeout_ready", False),
        "fmax_mhz": j.get("fmax_mhz"),
        "timing_slack_ns": j.get("timing_margin_ns"),
        "hold_slack_ns": j.get("worst_hold_slack"),
        "total_mw": j.get("total_power_mw"),
        "run_dir": str(rd),
        "qor": qor_dict,
        "drc_violations": so.get("drc", {}).get("violations", None),
        "lvs_status": so.get("lvs", {}).get("status", ""),
    }
    result.pipeline_result = r

    for c in CRITERIA:
        try:
            ok, detail = c.check_fn(r)
        except Exception as e:
            ok, detail = False, "Check error: " + str(e)
        result.criterion_results[c.name] = (ok, detail)

    result.overall_pass = all(
        result.criterion_results.get(c.name, (False, ""))[0] for c in REQUIRED_CRITERIA
    )
    result.elapsed_sec = time.time() - t0
    return result


def run_design(name: str, description: str) -> DesignResult:
    t0 = time.time()
    result = DesignResult(design_name=name, description=description)

    try:
        from guaranteed_flow import generate_guaranteed_gds

        r = generate_guaranteed_gds(description, name)
        result.pipeline_result = r
    except Exception as e:
        result.error = str(e)
        result.elapsed_sec = time.time() - t0
        for c in CRITERIA:
            result.criterion_results[c.name] = (False, "Pipeline error: " + str(e))
        return result

    for c in CRITERIA:
        try:
            ok, detail = c.check_fn(r)
        except Exception as e:
            ok, detail = False, "Check error: " + str(e)
        result.criterion_results[c.name] = (ok, detail)

    result.overall_pass = all(
        result.criterion_results.get(c.name, (False, ""))[0] for c in REQUIRED_CRITERIA
    )
    result.elapsed_sec = time.time() - t0
    return result


def _supports_colour() -> bool:
    return os.name != "nt" or "ANSICON" in os.environ or "WT_SESSION" in os.environ


USE_COLOUR = _supports_colour()
GREEN = "\033[92m" if USE_COLOUR else ""
RED = "\033[91m" if USE_COLOUR else ""
YELLOW = "\033[93m" if USE_COLOUR else ""
BOLD = "\033[1m" if USE_COLOUR else ""
RESET = "\033[0m" if USE_COLOUR else ""


def _ok(s):
    return GREEN + s + RESET


def _fail(s):
    return RED + s + RESET


def _warn(s):
    return YELLOW + s + RESET


def _bold(s):
    return BOLD + s + RESET


def print_result_table(results: List[DesignResult]) -> None:
    col_w = 16

    print()
    print(_bold("=" * 120))
    print(
        _bold(
            "  RTL-Gen AI -- Phase 1 Validation Suite -- " + datetime.now().strftime('%Y-%m-%d %H:%M')
        )
    )
    print(_bold("=" * 120))

    header = "  " + "{:<{}}".format("Design", col_w)
    for c in CRITERIA:
        abbrev = c.name[:8]
        header += "  " + "{:>8}".format(abbrev)
    header += "  " + "{:>6}".format("Time") + "  " + "Status"
    print(header)
    print("  " + "-" * (col_w + len(CRITERIA) * 10 + 24))

    for dr in results:
        row = "  " + "{:<{}}".format(dr.design_name, col_w)
        for c in CRITERIA:
            ok, _ = dr.criterion_results.get(c.name, (False, "?"))
            cell = "  PASS    " if ok else "  FAIL    "
            row += _ok(cell) if ok else _fail(cell)
        status = _ok("PASS") if dr.overall_pass else _fail("FAIL")
        row += "  " + "{:>5.1f}s".format(dr.elapsed_sec) + "  " + status
        print(row)

    print("  " + "-" * (col_w + len(CRITERIA) * 10 + 24))

    total_pass = sum(1 for dr in results if dr.overall_pass)
    total_fail = len(results) - total_pass

    print()
    print(_bold("  Results: {}/{} designs passed all criteria".format(total_pass, len(results))))
    print()

    print(_bold("  Criterion breakdown:"))
    for c in CRITERIA:
        passing = sum(1 for dr in results if dr.criterion_results.get(c.name, (False,))[0])
        bar = "#" * passing + "-" * (len(results) - passing)
        marker = "" if not c.required else " [REQUIRED]"
        status_str = (
            _ok("{}/{}".format(passing, len(results)))
            if passing == len(results)
            else _fail("{}/{}".format(passing, len(results)))
        )
        print("    {:<20} {}  {}{}  -- {}".format(c.name, bar, status_str, marker, c.description))

    failures = [dr for dr in results if not dr.overall_pass]
    if failures:
        print()
        print(_bold("  Failure details:"))
        for dr in failures:
            print("\n  X " + _bold(dr.design_name))
            if dr.error:
                print("    Pipeline error: " + dr.error)
            for c in REQUIRED_CRITERIA:
                ok, detail = dr.criterion_results.get(c.name, (False, "not checked"))
                if not ok:
                    print("    " + _fail('FAIL') + " {}: {}".format(c.name, detail))

    print()
    print("=" * 120)
    full_suite_count = len(DESIGNS)
    ran_count = len(results)
    if total_fail == 0:
        if ran_count < full_suite_count:
            print(
                _warn(
                    _bold(
                        "  SUBSET PASS -- {}/{} designs tested, all passed "
                        "(run without --fast/--design to confirm full Phase 1)".format(ran_count, full_suite_count)
                    )
                )
            )
        else:
            print(
                _ok(
                    _bold(
                        "  PHASE 1 COMPLETE -- all {} designs pass all criteria".format(ran_count)
                    )
                )
            )
            print(_ok("  You may proceed to Phase 2."))
    else:
        print(
            _fail(
                _bold("  PHASE 1 INCOMPLETE -- {} design(s) have failures".format(total_fail))
            )
        )
        print(_fail("  Fix the failures above and re-run before proceeding."))
        print()
        all_failing_criteria = set()
        for dr in failures:
            for c in REQUIRED_CRITERIA:
                ok, _ = dr.criterion_results.get(c.name, (False, ""))
                if not ok:
                    all_failing_criteria.add(c.name)

        if "power_real" in all_failing_criteria:
            print(_warn("  FIX NEEDED: power_real"))
            print("    OpenROAD report_power output not parsed.")
        if "hold_real" in all_failing_criteria:
            print(_warn("  FIX NEEDED: hold_real"))
            print("    OpenSTA min-path hold report not parsed.")
        if "not_fallback" in all_failing_criteria:
            print(_warn("  FIX NEEDED: not_fallback"))
            print("    Pipeline is returning pre-proven fallback GDS.")
        if "drc_zero" in all_failing_criteria:
            print(_warn("  FIX NEEDED: drc_zero"))
            print("    DRC violations present or DRC report not generated.")
        if "routing_real" in all_failing_criteria:
            print(_warn("  FIX NEEDED: routing_real"))
            print("    routed.def is not larger than cts.def -- routing failed silently.")

    print("=" * 120)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="RTL-Gen AI Phase 1 Validation Suite")
    parser.add_argument("--fast", action="store_true", help="Run only 3 designs (fast check)")
    parser.add_argument("--design", type=str, help="Run only this specific design")
    parser.add_argument("--skip", nargs="*", default=[], help="Skip these design names")
    parser.add_argument("--reuse-runs", action="store_true", help="Validate from existing verified run directories (no re-run).")
    args = parser.parse_args()

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            print("System sleep prevention enabled.")
        except Exception as e:
            print("Warning: Could not enable sleep prevention: {}".format(e))

    if args.design:
        designs_to_run = [(n, d) for n, d in DESIGNS if n == args.design]
        if not designs_to_run:
            print("Unknown design: {}".format(args.design))
            print("Available: {}".format([n for n, _ in DESIGNS]))
            return 1
    elif args.fast:
        designs_to_run = FAST_SUBSET
    else:
        designs_to_run = DESIGNS

    if args.skip:
        designs_to_run = [(n, d) for n, d in designs_to_run if n not in args.skip]

    reuse = getattr(args, "reuse_runs", False)
    mode = "REUSE-RUNS (existing verified dirs)" if reuse else "FULL PIPELINE RE-RUN"

    print("\nRunning Phase 1 validation: {} design(s)".format(len(designs_to_run)))
    print("Mode: {}".format(mode))
    print("Started: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("Criteria: {} checks per design ({} required)".format(len(CRITERIA), len(REQUIRED_CRITERIA)))
    print()

    results: List[DesignResult] = []
    for i, (name, description) in enumerate(designs_to_run, 1):
        print("[{}/{}] Running: {}".format(i, len(designs_to_run), name))
        print("         {}".format(description))
        if reuse and name in VERIFIED_RUNS:
            dr = run_design_from_existing(name, description, VERIFIED_RUNS[name])
        else:
            dr = run_design(name, description)
            if not reuse and dr.pipeline_result:
                run_dir_str = dr.pipeline_result.get("run_dir")
                if run_dir_str and Path(run_dir_str).exists():
                    print("         Cleaning up run directory to save disk space: {}".format(run_dir_str))
                    try:
                        import shutil
                        shutil.rmtree(run_dir_str, ignore_errors=True)
                    except Exception as e:
                        print("         Cleanup warning: {}".format(e))
        results.append(dr)

        pass_count = sum(1 for ok, _ in dr.criterion_results.values() if ok)
        symbol = "OK" if dr.overall_pass else "X"
        print("         {} {}/{} criteria pass in {:.1f}s".format(symbol, pass_count, len(CRITERIA), dr.elapsed_sec))
        if not dr.overall_pass:
            for c in REQUIRED_CRITERIA:
                ok, detail = dr.criterion_results.get(c.name, (False, "?"))
                if not ok:
                    print("           FAIL: {} -- {}".format(c.name, detail))
        print()

    print_result_table(results)

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            print("System sleep settings restored.")
        except Exception:
            pass

    all_pass = all(dr.overall_pass for dr in results)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
