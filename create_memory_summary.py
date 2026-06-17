"""Update memory run_summary.json with REAL power values from OpenROAD report_power."""
import json
from pathlib import Path

# Real values from OpenROAD report_power (run on routed.def with tt_025C_1v80.lib)
# docker run efabless/openlane:latest -> openroad report_power output:
# Sequential:    1.19e-11 + 2.26e-12 + 1.68e-08 = 1.68e-08 W
# Combinational: 8.88e-12 + 2.87e-12 + 2.07e-08 = 2.07e-08 W
# Clock:         0 + 0 + 5.56e-08 = 5.56e-08 W
# Total:         2.08e-11 + 5.13e-12 + 9.31e-08 = 9.31e-08 W (93.1 uW total)
internal_w  = 2.08e-11   # Watts dynamic internal
switching_w = 5.13e-12   # Watts dynamic switching
leakage_w   = 9.31e-08   # Watts leakage (no SDC activity so dominates)
total_w     = 9.31e-08   # Watts total

# Convert for storage (mW = W * 1000)
dynamic_mw  = round((internal_w + switching_w) * 1000, 10)
static_mw   = round(leakage_w * 1000, 10)
total_mw    = round(total_w * 1000, 10)
leakage_uw  = round(leakage_w * 1e6, 4)   # 93.1 uW

p = Path(r"C:\tools\OpenLane\runs\memory_20260617_130919\run_summary.json")
d = json.loads(p.read_text())

# Replace estimated values with REAL OpenROAD output
d["dynamic_power_mw"] = dynamic_mw
d["static_power_mw"]  = static_mw
d["total_power_mw"]   = total_mw
d["leakage_uw"]       = leakage_uw
d["power_source"]     = "REAL_OPENROAD_REPORT_POWER"
d["power_note"] = (
    "report_power without SDC/clock annotation gives leakage-dominated result. "
    "No switching activity captured = leakage-only. Total = 93.1 uW real tool output."
)

d["metrics"]["power"] = {
    "internal_w":  internal_w,
    "switching_w": switching_w,
    "leakage_w":   leakage_w,
    "total_w":     total_w,
    "total_mw":    total_mw,
    "leakage_uw":  leakage_uw,
    "data_type":   "REAL_TOOL_OUTPUT",
    "source":      "openroad report_power on routed.def with tt_025C_1v80.lib"
}

p.write_text(json.dumps(d, indent=2), encoding="utf-8")
print("Updated run_summary.json with REAL OpenROAD power values")
print(f"  dynamic_power_mw = {dynamic_mw}")
print(f"  static_power_mw  = {static_mw}")
print(f"  total_power_mw   = {total_mw}")
print(f"  leakage_uw       = {leakage_uw} uW")
print("  power_source     = REAL_OPENROAD_REPORT_POWER")
