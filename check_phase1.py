"""Quick Phase 1 check - uses correct JSON paths."""
import sys, json
from pathlib import Path

RUNS = Path("C:/tools/OpenLane/runs")
LATEST = {
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

def check(design, dirname):
    rd = RUNS / dirname
    j = json.loads((rd / "run_summary.json").read_text())
    so = j["metrics"]["signoff"]
    
    gds_path = j.get("gds_path", "")
    gds_file = Path(gds_path) if gds_path else None
    gds_kb = gds_file.stat().st_size // 1024 if gds_file and gds_file.exists() else 0
    
    r = {}
    r["gds_size"] = (gds_kb > 50, f"{gds_kb}KB")
    
    has_sky130 = False
    if gds_file and gds_file.exists():
        raw = gds_file.read_bytes()
        has_sky130 = b"sky130" in raw[:2000]
    r["gds_real"] = (has_sky130, "sky130 OK" if has_sky130 else "no sky130")
    
    is_fb = j.get("status") == "FALLBACK" or ("fallback" in str(gds_file.name).lower() if gds_file else False)
    r["not_fallback"] = (not is_fb, f"status={j.get('status')}")
    
    drc_v = so["drc"].get("violations", -1)
    r["drc_zero"] = (drc_v == 0, f"DRC={drc_v}")
    
    lvs_s = so["lvs"].get("status", "")
    r["lvs_matched"] = ("MATCHED" in str(lvs_s).upper(), f"LVS={lvs_s}")
    
    slack = j.get("timing_margin_ns")
    r["setup_timing"] = (slack is not None and float(slack) >= 0, f"WNS={slack}")
    
    fmax = j.get("fmax_mhz")
    r["fmax_real"] = (fmax is not None and float(fmax) > 0, f"Fmax={fmax}")
    
    pw = j.get("total_power_mw")
    r["power_real"] = (pw is not None and float(pw) > 0, f"Power={pw}")
    
    hold = j.get("worst_hold_slack")
    r["hold_real"] = (hold is not None, f"Hold={hold}")
    
    routed = next(rd.rglob("routed.def"), None)
    cts = next(rd.rglob("cts.def"), None)
    rs = routed.stat().st_size if routed else 0
    cs = cts.stat().st_size if cts else 0
    r["routing_real"] = (rs > cs, f"routed={rs//1024}KB > cts={cs//1024}KB")
    
    to = j.get("tapeout_ready", False)
    r["tapeout_flag"] = (bool(to), f"tapeout={to}")
    
    all_pass = all(v[0] for v in r.values())
    
    row = f"{design:15s}"
    for k in ["gds_size","gds_real","not_fallback","drc_zero","lvs_matched","setup_timing","fmax_real","power_real","hold_real","routing_real","tapeout_flag"]:
        p, d = r[k]
        row += f" | {'PASS' if p else 'FAIL':>4s}"
    row += f" | {'PASS' if all_pass else 'FAIL':>4s}  (Fmax={j.get('fmax_mhz')}, P={j.get('total_power_mw')}, Hold={j.get('worst_hold_slack')})"
    return row, all_pass

print(f"{'Design':15s} | size | real | no_fb| drc  | lvs  | setup| fmax | power| hold | route| to   | PASS?  Details")
print("="*140)
passed = 0
for d, rn in LATEST.items():
    row, ok = check(d, rn)
    print(row)
    if ok:
        passed += 1
print(f"\n{passed}/{len(LATEST)} designs pass all 11 criteria")
