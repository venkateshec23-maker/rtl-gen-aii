"""
validate_pipeline.py — End-to-End RTL-Gen AI Validation Run
===========================================================
Run the complete pipeline on a real design through Docker.
This proves the system works on actual silicon before building UIs.

Usage:
    python validate_pipeline.py
    
Expected output:
    ✅ VALIDATION PASSED → GDS file generated
    ❌ VALIDATION FAILED → Specific stage and reason
"""

import logging
import sys
from pathlib import Path

# Fix encoding for Windows terminal (UTF-8)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(name)-30s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("validation_run.log"),
    ]
)

logger = logging.getLogger("validation")

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.full_flow import RTLGenAI, FlowConfig, FlowError


def progress_bar(d: dict) -> None:
    """Render progress as a visual bar."""
    pct = d["pct"] * 100
    filled = int(pct / 5)
    bar = "#" * filled + "." * (20 - filled)
    print(f"  [{bar}] {pct:5.1f}%  [{d['stage']:20}]  {d['msg']}")


def main():
    print("\n" + "=" * 70)
    print("  RTL-Gen AI - End-to-End Validation Run")
    print("  Design: adder_8bit (registered 8-bit adder)")
    print("  Target: 40 MHz, 0.5 utilization (relaxed for first run)")
    print("=" * 70 + "\n")

    # Verify prerequisites
    print("Step 1: Verifying prerequisites...")
    print("-" * 70)

    checks = {
        "Docker running": lambda: __import__("subprocess").run(
            ["docker", "ps"], capture_output=True, timeout=5
        ).returncode == 0,
        "OpenLane image": lambda: __import__("subprocess").run(
            ["docker", "images"], capture_output=True, timeout=5,
            text=True
        ).stdout.count("openlane") > 0,
    }

    for check_name, check_fn in checks.items():
        try:
            if check_fn():
                print(f"  [OK]  {check_name}")
            else:
                print(f"  [FAILED]  {check_name} NOT FOUND")
                print(f"\n  Fix: docker pull efabless/openlane:latest")
                return False
        except Exception as e:
            print(f"  ❌  {check_name}: {e}")
            return False

    # PDK check
    try:
        from python.pdk_manager import PDKManager
        pdk = PDKManager()
        result = pdk.validate()
        if result.is_valid:
            print(f"  [OK]  PDK valid ({len(result.found_libraries)} libraries)")
        else:
            print(f"  [FAILED]  PDK invalid: {result.errors}")
            return False
    except Exception as e:
        print(f"  ❌  PDK check failed: {e}")
        return False

    print("\n[OK]  All critical prerequisites verified.")
    print("      (Yosys check will happen during synthesis stage)")

    # Configure flow
    print("Step 2: Configuring flow...")
    print("-" * 70)

    cfg = FlowConfig(
        target_utilization=0.50,  # 50% — generous headroom
        clock_period_ns=25.0,     # 40 MHz — relaxed timing
        placement_density=0.45,   # spread cells generously
        routing_adjustment=0.40,  # more routing headroom
        routing_threads=4,
        run_lvs=False,            # skip LVS on first run
    )

    print(f"  Target utilization: {cfg.target_utilization * 100:.0f}%")
    print(f"  Clock period:       {cfg.clock_period_ns} ns (40 MHz)")
    print(f"  Placement density:  {cfg.placement_density * 100:.0f}%")
    print(f"  Routing headroom:   {cfg.routing_adjustment * 100:.0f}%")
    print(f"  Threads:            {cfg.routing_threads}")

    print("\n" + "=" * 70)
    print("  RUNNING PIPELINE")
    print("=" * 70 + "\n")

    # Run pipeline
    try:
        result = RTLGenAI.run_from_rtl(
            rtl_path=r"C:\Users\venka\Documents\rtl-gen-aii\validation\adder_8bit.v",
            top_module="adder_8bit",
            output_dir=r"C:\Users\venka\Documents\rtl-gen-aii\validation\run_001",
            config=cfg,
            progress=progress_bar,
        )
    except FlowError as e:
        print(f"\n[FAILED]  FLOW ERROR at '{e.stage}'")
        print(f"    Message: {e.message}")
        if e.output:
            print(f"\n    Raw output:\n{e.output}")
        print(f"\n    Logs: C:\\Users\\venka\\Documents\\rtl-gen-aii\\validation\\")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\n[FAILED]  UNEXPECTED ERROR: {e}")
        return False

    # Report results
    print("\n" + "=" * 70)
    print(result.summary())
    print("=" * 70)

    if result.is_tapeable:
        print("\n[PASSED]  VALIDATION PASSED - PIPELINE WORKS END-TO-END")
        print(f"\n    GDS file generated:")
        print(f"      {result.gds_path}")
        print(f"\n    Complete package at:")
        print(f"      {result.package_dir}")
        print(f"\n    Total time: {result.total_seconds:.1f}s")
        print(f"    DRC violations: {result.drc_violations}")
        print(f"    Slack: {result.worst_slack_ns:.3f}ns")
        return True
    else:
        print(f"\n[FAILED]  VALIDATION FAILED")
        print(f"\n    Failed at: {result.failed_stage}")
        print(f"    Reason: {result.error_message}")
        print(f"\n    Output directory for debugging:")
        print(f"      {result.output_dir}")
        print(f"\n    Suggested fix:")

        fixes = {
            "floorplan": "Netlist has no cells. Check Yosys synthesis output.",
            "placement": "Die too small. Reduce target_utilization to 0.40.",
            "global_routing": "Congestion. Reduce placement_density to 0.35.",
            "detailed_routing": "Unrouted nets. Reduce routing_adjustment to 0.30.",
            "gds": "Magic tech file missing. Check PDK installation.",
        }

        if result.failed_stage in fixes:
            print(f"      → {fixes[result.failed_stage]}")
        else:
            print(f"      → Check logs above for details.")

        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
