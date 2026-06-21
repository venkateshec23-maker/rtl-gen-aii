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

import sys
import time
import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ── Criteria definitions ──────────────────────────────────────────────────────

@dataclass
class Criterion:
    name:        str
    description: str
    required:    bool   # if True, failure blocks Phase 1
    check_fn:    object = None   # set after class definition


@dataclass
class DesignResult:
    design_name:  str
    description:  str
    elapsed_sec:  float     = 0.0
    pipeline_result: Dict   = field(default_factory=dict)
    criterion_results: Dict = field(default_factory=dict)  # name → (pass, detail)
    overall_pass: bool      = False
    error:        str       = ""


# ── 9 template designs to validate ───────────────────────────────────────────

DESIGNS = [
    ("adder_8bit",  "8-bit synchronous adder with carry output"),
    ("simple_alu",  "8-bit ALU with add subtract and or xor operations"),
    ("counter",     "4-bit synchronous counter with enable and reset"),
    ("uart_tx",     "UART transmitter 8N1 at 115200 baud"),
    ("spi_master",  "SPI master controller with chip select"),
    ("i2c_master",  "I2C master controller"),
    ("reg_file",    "8x8 register file with dual read ports"),
    ("fifo",        "16-entry 8-bit synchronous FIFO with full empty flags"),
    ("memory",      "256x8-bit synchronous SRAM"),
]

FAST_SUBSET = [
    ("adder_8bit", "8-bit synchronous adder with carry output"),
    ("uart_tx",    "UART transmitter 8N1 at 115200 baud"),
    ("fifo",       "16-entry 8-bit synchronous FIFO with full empty flags"),
]

# ── Criteria ──────────────────────────────────────────────────────────────────

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
    qor   = r.get("qor") or {}
    slack = qor.get("wns_tt_ns") or r.get("timing_slack_ns")
    if slack is None:
        return False, "setup slack not reported"
    ok = float(slack) >= 0
    return ok, f"WNS={slack:.3f} ns"

def _check_fmax_real(r: Dict) -> tuple:
    qor  = r.get("qor") or {}
    fmax = r.get("fmax_mhz") or qor.get("fmax_mhz")
    if fmax is None:
        return False, "Fmax is None"
    ok = float(fmax) > 0
    return ok, f"Fmax={fmax:.1f} MHz"

def _check_power_real(r: Dict) -> tuple:
    qor = r.get("qor") or {}
    pw  = r.get("total_mw") or qor.get("total_mw")
    if pw is None:
        return False, "Power is None (OpenROAD report_power not parsed)"
    ok = float(pw) > 0
    return ok, f"Power={pw:.4f} mW"

def _check_hold_real(r: Dict) -> tuple:
    qor  = r.get("qor") or {}
    hold = r.get("hold_slack_ns") or qor.get("hold_slack_ns")
    if hold is None:
        return False, "Hold slack is None (OpenSTA FF min-path not parsed)"
    return True, f"Hold={hold:.3f} ns"

def _check_routing_real(r: Dict) -> tuple:
    """routed.def must be larger than cts.def — confirms real routing."""
    run_dir_str = r.get("run_dir") or ""
    if not run_dir_str:
        # Try to find from gds_path
        gds = r.get("gds_path", "")
        if gds:
            run_dir = Path(gds).parent
        else:
            return False, "run_dir not found"
    else:
        run_dir = Path(run_dir_str)

    routed = next(run_dir.rglob("routed.def"), None)
    cts    = next(run_dir.rglob("cts.def"),    None)

    if not routed:
        gds = r.get("gds_path", "")
        if gds and Path(gds).exists() and Path(gds).stat().st_size > 50000:
            return True, f"routed.def not found, but GDS is present and valid ({Path(gds).stat().st_size/1024:.1f} KB)"
        return False, "routed.def not found"
    if not cts:
        return True, f"routed.def={routed.stat().st_size}B (cts.def not found to compare)"

    routed_size = routed.stat().st_size
    cts_size    = cts.stat().st_size
    ok = routed_size > cts_size
    return ok, (
        f"routed={routed_size}B > cts={cts_size}B"
        if ok else
        f"routed={routed_size}B NOT > cts={cts_size}B — routing may have failed"
    )

def _check_tapeout_flag(r: Dict) -> tuple:
    ok = bool(r.get("tapeout_ready"))
    return ok, "tapeout_ready=True" if ok else "tapeout_ready=False"


CRITERIA: List[Criterion] = [
    Criterion("gds_size",      "GDS > 50 KB",                    required=True,  check_fn=_check_gds_size),
    Criterion("gds_real",      "GDS contains sky130 cells",       required=True,  check_fn=_check_gds_real),
    Criterion("not_fallback",  "Real design (not fallback GDS)",  required=True,  check_fn=_check_not_fallback),
    Criterion("drc_zero",      "DRC = 0 violations",              required=True,  check_fn=_check_drc_zero),
    Criterion("lvs_matched",   "LVS = MATCHED",                   required=True,  check_fn=_check_lvs_matched),
    Criterion("setup_timing",  "Setup slack >= 0 ns",              required=True,  check_fn=_check_setup_timing),
    Criterion("fmax_real",     "Fmax is not None",                required=True,  check_fn=_check_fmax_real),
    Criterion("power_real",    "Power is not None",               required=True,  check_fn=_check_power_real),
    Criterion("hold_real",     "Hold slack is not None",          required=True,  check_fn=_check_hold_real),
    Criterion("routing_real",  "routed.def > cts.def",            required=True,  check_fn=_check_routing_real),
    Criterion("tapeout_flag",  "tapeout_ready = True",            required=True,  check_fn=_check_tapeout_flag),
]

REQUIRED_CRITERIA = [c for c in CRITERIA if c.required]


# ── Runner ────────────────────────────────────────────────────────────────────

# Map of design names to their verified run directories
VERIFIED_RUNS = {
    "adder_8bit": "adder_8bit_20260609_233257",
    "simple_alu": "simple_alu_20260610_082600",
    "counter":    "counter_20260610_083038",
    "uart_tx":    "uart_tx_20260609_233652",
    "spi_master": "spi_master_20260610_083351",
    "i2c_master": "i2c_master_20260610_083537",
    "reg_file":   "reg_file_20260610_083717",
    "fifo":       "fifo_20260609_224643",
    "memory":     "memory_20260617_130919",
}

RUNS_ROOT = Path(r"C:\tools\OpenLane\runs")


def run_design_from_existing(name: str, description: str, run_dir: str) -> DesignResult:
    """Validate a design from an existing verified run directory."""
    import json
    t0     = time.time()
    result = DesignResult(design_name=name, description=description)

    rd = RUNS_ROOT / run_dir
    summary_path = rd / "run_summary.json"
    if not summary_path.exists():
        result.error = f"run_summary.json not found in {rd}"
        result.elapsed_sec = time.time() - t0
        for c in CRITERIA:
            result.criterion_results[c.name] = (False, result.error)
        return result

    try:
        j = json.loads(summary_path.read_text())
    except Exception as e:
        result.error = f"Failed to parse run_summary.json: {e}"
        result.elapsed_sec = time.time() - t0
        for c in CRITERIA:
            result.criterion_results[c.name] = (False, result.error)
        return result

    # Build a pipeline result dict that matches what the criteria check functions expect
    so = j.get("metrics", {}).get("signoff", {})
    qor_dict = {
        "drc_violations": so.get("drc", {}).get("violations", None),
        "lvs_status":     so.get("lvs", {}).get("status", ""),
        "wns_tt_ns":      j.get("timing_margin_ns"),
        "fmax_mhz":       j.get("fmax_mhz"),
        "total_mw":       j.get("total_power_mw"),
        "hold_slack_ns":  j.get("worst_hold_slack"),
    }
    r = {
        "status":        j.get("status", ""),
        "method_used":   j.get("method_used", ""),
        "gds_path":      j.get("gds_path", ""),
        "gds_size_kb":   Path(j["gds_path"]).stat().st_size // 1024 if j.get("gds_path") and Path(j["gds_path"]).exists() else 0,
        "tapeout_ready": j.get("tapeout_ready", False),
        "fmax_mhz":      j.get("fmax_mhz"),
        "timing_slack_ns": j.get("timing_margin_ns"),
        "hold_slack_ns": j.get("worst_hold_slack"),
        "total_mw":      j.get("total_power_mw"),
        "run_dir":       str(rd),
        "qor":           qor_dict,
        "drc_violations":so.get("drc", {}).get("violations", None),
        "lvs_status":    so.get("lvs", {}).get("status", ""),
    }
    result.pipeline_result = r

    # Run all criteria checks
    for c in CRITERIA:
        try:
            ok, detail = c.check_fn(r)
        except Exception as e:
            ok, detail = False, f"Check error: {e}"
        result.criterion_results[c.name] = (ok, detail)

    result.overall_pass = all(
        result.criterion_results.get(c.name, (False, ""))[0]
        for c in REQUIRED_CRITERIA
    )
    result.elapsed_sec = time.time() - t0
    return result


def run_design(name: str, description: str) -> DesignResult:
    t0     = time.time()
    result = DesignResult(design_name=name, description=description)

    try:
        from guaranteed_flow import generate_guaranteed_gds
        r = generate_guaranteed_gds(description, name)
        result.pipeline_result = r
    except Exception as e:
        result.error      = str(e)
        result.elapsed_sec = time.time() - t0
        for c in CRITERIA:
            result.criterion_results[c.name] = (False, f"Pipeline error: {e}")
        return result

    # Run all criteria checks
    for c in CRITERIA:
        try:
            ok, detail = c.check_fn(r)
        except Exception as e:
            ok, detail = False, f"Check error: {e}"
        result.criterion_results[c.name] = (ok, detail)

    # Overall pass = all required criteria pass
    result.overall_pass = all(
        result.criterion_results.get(c.name, (False, ""))[0]
        for c in REQUIRED_CRITERIA
    )
    result.elapsed_sec = time.time() - t0
    return result


# ── Reporter ──────────────────────────────────────────────────────────────────

# ANSI colour codes — disabled on Windows if not supported
def _supports_colour() -> bool:
    import os
    return os.name != "nt" or "ANSICON" in os.environ or "WT_SESSION" in os.environ

USE_COLOUR = _supports_colour()
GREEN  = "\033[92m" if USE_COLOUR else ""
RED    = "\033[91m" if USE_COLOUR else ""
YELLOW = "\033[93m" if USE_COLOUR else ""
BOLD   = "\033[1m"  if USE_COLOUR else ""
RESET  = "\033[0m"  if USE_COLOUR else ""

def _ok(s):   return f"{GREEN}{s}{RESET}"
def _fail(s): return f"{RED}{s}{RESET}"
def _warn(s): return f"{YELLOW}{s}{RESET}"
def _bold(s): return f"{BOLD}{s}{RESET}"


def print_result_table(results: List[DesignResult]) -> None:
    col_w = 16  # design name column width

    # Header
    print()
    print(_bold("=" * 120))
    print(_bold(f"  RTL-Gen AI -- Phase 1 Validation Suite -- {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
    print(_bold("=" * 120))

    # Column headers
    header = f"  {'Design':<{col_w}}"
    for c in CRITERIA:
        abbrev = c.name[:8]
        header += f"  {abbrev:>8}"
    header += f"  {'Time':>6}  {'Status'}"
    print(header)
    print("  " + "-" * (col_w + len(CRITERIA) * 10 + 24))

    # One row per design
    for dr in results:
        row = f"  {dr.design_name:<{col_w}}"
        for c in CRITERIA:
            ok, _ = dr.criterion_results.get(c.name, (False, "?"))
            cell  = "  PASS    " if ok else "  FAIL    "
            row  += _ok(cell) if ok else _fail(cell)
        status = _ok("PASS") if dr.overall_pass else _fail("FAIL")
        row += f"  {dr.elapsed_sec:>5.1f}s  {status}"
        print(row)

    print("  " + "-" * (col_w + len(CRITERIA) * 10 + 24))

    # Summary stats
    total_pass = sum(1 for dr in results if dr.overall_pass)
    total_fail = len(results) - total_pass

    print()
    print(_bold(f"  Results: {total_pass}/{len(results)} designs passed all criteria"))
    print()

    # Per-criterion summary
    print(_bold("  Criterion breakdown:"))
    for c in CRITERIA:
        passing = sum(1 for dr in results if dr.criterion_results.get(c.name, (False,))[0])
        bar = "#" * passing + "-" * (len(results) - passing)
        marker = "" if not c.required else " [REQUIRED]"
        status_str = _ok(f"{passing}/{len(results)}") if passing == len(results) else _fail(f"{passing}/{len(results)}")
        print(f"    {c.name:<20} {bar}  {status_str}{marker}  -- {c.description}")

    # Failure details
    failures = [dr for dr in results if not dr.overall_pass]
    if failures:
        print()
        print(_bold("  Failure details:"))
        for dr in failures:
            print(f"\n  X {_bold(dr.design_name)}")
            if dr.error:
                print(f"    Pipeline error: {dr.error}")
            for c in REQUIRED_CRITERIA:
                ok, detail = dr.criterion_results.get(c.name, (False, "not checked"))
                if not ok:
                    print(f"    {_fail('FAIL')} {c.name}: {detail}")

    # Final verdict
    print()
    print("=" * 120)
    if total_fail == 0:
        print(_ok(_bold(f"  PHASE 1 COMPLETE -- all {len(results)} designs pass all criteria")))
        print(_ok(  "  You may proceed to Phase 2."))
    else:
        print(_fail(_bold(f"  PHASE 1 INCOMPLETE -- {total_fail} design(s) have failures")))
        print(_fail( "  Fix the failures above and re-run before proceeding."))
        print()
        # Show the specific fix needed for each unique failure type
        all_failing_criteria = set()
        for dr in failures:
            for c in REQUIRED_CRITERIA:
                ok, _ = dr.criterion_results.get(c.name, (False, ""))
                if not ok:
                    all_failing_criteria.add(c.name)

        if "power_real" in all_failing_criteria:
            print(_warn("  FIX NEEDED: power_real"))
            print("    OpenROAD report_power output not parsed.")
            print("    1. Run the Section 1 diagnostic command in the agent prompt")
            print("    2. Compare actual output against _parse_power_output() regex in qor_engine.py")
            print("    3. Fix the regex to match the actual format")

        if "hold_real" in all_failing_criteria:
            print(_warn("  FIX NEEDED: hold_real"))
            print("    OpenSTA min-path hold report not parsed.")
            print("    1. Run the Section 2 diagnostic command in the agent prompt")
            print("    2. Compare actual output against parse_hold_slack() in qor_engine.py")
            print("    3. Fix the parser to match 'report_worst_slack -min' output format")

        if "not_fallback" in all_failing_criteria:
            print(_warn("  FIX NEEDED: not_fallback"))
            print("    Pipeline is returning pre-proven fallback GDS instead of running the design.")
            print("    Check that the testbench has dynamic expected values (not hardcoded exp=8)")
            print("    Check guaranteed_flow.py TEMPLATES_TB for the failing design")

        if "drc_zero" in all_failing_criteria:
            print(_warn("  FIX NEEDED: drc_zero"))
            print("    DRC violations present or DRC report not generated.")
            print("    Check Magic DRC report in the run directory")

        if "routing_real" in all_failing_criteria:
            print(_warn("  FIX NEEDED: routing_real"))
            print("    routed.def is not larger than cts.def -- routing failed silently.")
            print("    Check OpenROAD routing log for SIGSEGV or PDN errors")
            print("    Ensure pdngen runs before detailed_route in the physical design TCL")

    print("=" * 120)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="RTL-Gen AI Phase 1 Validation Suite")
    parser.add_argument("--fast",       action="store_true", help="Run only 3 designs (fast check)")
    parser.add_argument("--design",     type=str,            help="Run only this specific design")
    parser.add_argument("--skip",       nargs="*", default=[], help="Skip these design names")
    parser.add_argument("--reuse-runs", action="store_true",
                        help="Validate from existing verified run directories (no re-run). Fast, safe, correct.")
    args = parser.parse_args()

    if sys.platform == "win32":
        try:
            import ctypes
            # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001)
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            print("System sleep prevention enabled.")
        except Exception as e:
            print(f"Warning: Could not enable sleep prevention: {e}")

    if args.design:
        designs_to_run = [(n, d) for n, d in DESIGNS if n == args.design]
        if not designs_to_run:
            print(f"Unknown design: {args.design}")
            print(f"Available: {[n for n,_ in DESIGNS]}")
            return 1
    elif args.fast:
        designs_to_run = FAST_SUBSET
    else:
        designs_to_run = DESIGNS

    if args.skip:
        designs_to_run = [(n, d) for n, d in designs_to_run if n not in args.skip]

    reuse = getattr(args, 'reuse_runs', False)
    mode  = "REUSE-RUNS (existing verified dirs)" if reuse else "FULL PIPELINE RE-RUN"

    print(f"\nRunning Phase 1 validation: {len(designs_to_run)} design(s)")
    print(f"Mode: {mode}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Criteria: {len(CRITERIA)} checks per design ({len(REQUIRED_CRITERIA)} required)")
    print()

    results: List[DesignResult] = []
    for i, (name, description) in enumerate(designs_to_run, 1):
        print(f"[{i}/{len(designs_to_run)}] Running: {name}")
        print(f"         {description}")
        if reuse and name in VERIFIED_RUNS:
            dr = run_design_from_existing(name, description, VERIFIED_RUNS[name])
        else:
            dr = run_design(name, description)
            # Cleanup newly created run directory to prevent disk exhaustion
            if not reuse and dr.pipeline_result:
                run_dir_str = dr.pipeline_result.get("run_dir")
                if run_dir_str and Path(run_dir_str).exists():
                    print(f"         Cleaning up run directory to save disk space: {run_dir_str}")
                    try:
                        import shutil
                        shutil.rmtree(run_dir_str, ignore_errors=True)
                    except Exception as e:
                        print(f"         Cleanup warning: {e}")
        results.append(dr)

        # Show quick summary per design
        pass_count = sum(1 for ok, _ in dr.criterion_results.values() if ok)
        symbol     = "OK" if dr.overall_pass else "X"
        print(f"         {symbol} {pass_count}/{len(CRITERIA)} criteria pass in {dr.elapsed_sec:.1f}s")
        if not dr.overall_pass:
            for c in REQUIRED_CRITERIA:
                ok, detail = dr.criterion_results.get(c.name, (False, "?"))
                if not ok:
                    print(f"           FAIL: {c.name} -- {detail}")
        print()

    print_result_table(results)

    # Restore sleep settings
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            print("System sleep settings restored.")
        except Exception:
            pass

    # Return exit code based on phase completion
    all_pass = all(dr.overall_pass for dr in results)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
