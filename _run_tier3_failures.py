"""Re-run 3 failing Tier 3 designs"""
from guaranteed_flow import generate_guaranteed_gds
from complex_test_suite import _check_result

designs = [
    ("sram_512", "512x8-bit synchronous SRAM with byte write enable and output register", 400),
    ("arb_roundrobin8", "8-way round-robin arbiter with grant hold and priority override", 180),
    ("pipeline_4stage", "4-stage pipelined 8-bit adder with hazard detection and forwarding", 350),
]

for name, desc, min_cells in designs:
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    r = generate_guaranteed_gds(description=desc, module_name=name)
    ok, issues = _check_result(r, min_cells)
    status = "PASS" if ok else "FAIL"
    gds_kb = r.get("gds_size_kb") or 0
    fmax = r.get("fmax_mhz")
    print(f"  Status  : {status}")
    print(f"  GDS KB  : {gds_kb:.1f}")
    print(f"  Fmax    : {fmax:.1f} MHz" if fmax else "  Fmax    : None")
    print(f"  Tapeout : {r.get('tapeout_ready')}")
    print(f"  Method  : {r.get('method_used')}")
    if not ok:
        for iss in issues:
            print(f"  ISSUE : {iss}")
