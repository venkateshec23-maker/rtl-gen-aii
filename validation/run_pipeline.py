#!/usr/bin/env python3
"""Run the full RTL-to-GDSII pipeline on the 8-bit adder."""
import logging
import sys
import os
import io

# Fix Windows console encoding for Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(name)s: %(message)s",
)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.full_flow import RTLGenAI, FlowConfig


def progress(d):
    stage = d["stage"]
    pct = d["pct"] * 100
    msg = d["msg"]
    try:
        print(f"[{stage:15}] {pct:5.1f}%  {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{stage:15}] {pct:5.1f}%  {msg.encode('ascii', 'replace').decode()}", flush=True)


def main():
    print("=" * 70)
    print("  RTL-Gen AI  -  End-to-End Pipeline Validation")
    print("=" * 70)
    print()

    try:
        result = RTLGenAI.run_from_rtl(
            rtl_path="validation/adder_8bit.v",
            top_module="adder_8bit",
            output_dir="validation/run_002",
            progress=progress,
        )
        # Print summary with encoding safety
        try:
            print(result.summary())
        except UnicodeEncodeError:
            print(result.summary().encode("ascii", "replace").decode())

        print(f"is_tapeable: {result.is_tapeable}")
        if result.gds_path and os.path.exists(result.gds_path):
            print(f"GDS: {result.gds_path} ({os.path.getsize(result.gds_path)} bytes)")
        if result.failed_stage:
            print(f"\nFailed at: {result.failed_stage}")
            print(f"Error: {result.error_message[:500]}")
            sys.exit(1)
        else:
            print("\nPipeline Complete!")
    except Exception as e:
        print(f"\nEXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
