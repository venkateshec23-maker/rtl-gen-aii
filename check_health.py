"""
check_health.py
===============
One command to verify everything is working.
Run: python check_health.py
"""

import sys
import subprocess
from pathlib import Path

def check(name, condition, fix_hint=""):
    status = "OK" if condition else "FAIL"
    print(f"  [{status}] {name}")
    if not condition and fix_hint:
        print(f"         FIX: {fix_hint}")
    return condition

def main():
    print("=" * 50)
    print("RTL-GEN AI HEALTH CHECK")
    print("=" * 50)
    print()

    all_ok = True

    # 1. Python imports
    print("PYTHON IMPORTS:")
    for module in ["full_flow", "app", "database",
                   "guaranteed_flow", "verilog_generator",
                   "report_generator", "api"]:
        try:
            __import__(module)
            ok = check(module, True)
        except Exception as e:
            ok = check(module, False,
                      f"Fix import error: {e}")
        all_ok = all_ok and ok

    print()

    # 2. Docker
    print("DOCKER:")
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=10
        )
        ok = check("Docker running",
                   r.returncode == 0,
                   "Start Docker Desktop")
        all_ok = all_ok and ok
    except Exception:
        ok = check("Docker running", False,
                  "Install/start Docker Desktop")
        all_ok = all_ok and ok

    print()

    # 3. API keys
    print("API KEYS:")
    import os
    from dotenv import load_dotenv
    load_dotenv()

    keys = {
        "OPENROUTER_API_KEY": "openrouter.ai/keys (free)",
        "GOOGLE_API_KEY":     "aistudio.google.com (free)",
        "GROQ_API_KEY":       "console.groq.com (free)",
    }
    has_any_key = False
    for key, source in keys.items():
        val = os.getenv(key, "")
        exists = bool(val and len(val) > 10)
        if exists:
            has_any_key = True
        check(key, exists,
              f"Get free key at {source}")

    ok = check("At least one AI key", has_any_key,
              "Add OPENROUTER_API_KEY to .env file")
    all_ok = all_ok and ok

    print()

    # 4. Database
    print("DATABASE:")
    try:
        from database import DB_AVAILABLE, get_all_runs
        ok = check("PostgreSQL", DB_AVAILABLE,
                  "docker start rtlgenai-postgres")
        if DB_AVAILABLE:
            runs = get_all_runs()
            check(f"Runs stored ({len(runs)})", True)
        all_ok = all_ok and ok
    except Exception as e:
        ok = check("PostgreSQL", False, str(e))
        all_ok = all_ok and ok

    print()

    # 5. Templates
    print("TEMPLATES:")
    try:
        from guaranteed_flow import TEMPLATES_RTL, TEMPLATES_TB
        required = [
            "counter", "adder", "shift_reg", "mux",
            "alu", "fsm", "uart_tx", "spi_master",
            "i2c_master", "fifo", "memory", "reg_file"
        ]
        for t in required:
            ok = check(
                f"Template: {t}",
                t in TEMPLATES_RTL and t in TEMPLATES_TB,
                f"Add {t} to guaranteed_flow.py"
            )
            all_ok = all_ok and ok
    except Exception as e:
        check("Templates", False, str(e))
        all_ok = False

    print()

    # 6. PDK
    print("PDK:")
    pdk = Path(r"C:\pdk\sky130A")
    lib = pdk / "libs.ref" / "sky130_fd_sc_hd" / \
          "lib" / "sky130_fd_sc_hd__tt_025C_1v80.lib"
    ok = check("Sky130A PDK", pdk.exists(),
              "Download Sky130A PDK")
    if pdk.exists():
        ok2 = check("Liberty file", lib.exists(),
                   "Liberty file missing in PDK")
        all_ok = all_ok and ok2
    all_ok = all_ok and ok

    print()

    # 7. Run quick test
    print("QUICK PIPELINE TEST:")
    adder = Path(r"C:\tools\OpenLane\designs\adder_8bit\adder_8bit.v")
    if adder.exists():
        try:
            from guaranteed_flow import generate_guaranteed_gds
            r = generate_guaranteed_gds(
                "8-bit adder", "health_check_adder"
            )
            real = r["gds_size_kb"] > 50
            ok = check(
                f"Pipeline test ({r['gds_size_kb']}KB GDS)",
                real,
                "Check Docker and PDK"
            )
            all_ok = all_ok and ok
        except Exception as e:
            check("Pipeline test", False, str(e))
            all_ok = False
    else:
        check("adder_8bit.v", False,
             "Missing design file")
        all_ok = False

    print()
    print("=" * 50)
    if all_ok:
        print("RESULT: ALL CHECKS PASSED")
        print("Tool is ready to use.")
    else:
        print("RESULT: SOME CHECKS FAILED")
        print("Fix the issues above and re-run.")
    print("=" * 50)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
