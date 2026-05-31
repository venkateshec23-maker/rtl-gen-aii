"""Direct test of gap fixes"""
from full_flow import RTLtoGDSIIFlow
from pathlib import Path

work = Path(r'C:\tools\OpenLane')
pdk = Path(r'C:\pdk')

# Use existing successful run
runs = list(Path(r'C:\tools\OpenLane\runs').glob('adder_8bit_*'))
if runs:
    latest = sorted(runs, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    print(f"Using run: {latest.name}")
    
    flow = RTLtoGDSIIFlow('adder_8bit', str(work / 'designs/adder_8bit/adder_8bit.v'), str(work), str(pdk))
    flow.results_dir = latest
    
    print("\n=== Testing IR Drop Analysis ===")
    ok1 = flow.step5b_ir_drop_analysis()
    ir_file = latest / 'ir_drop_vdd.txt'
    if ir_file.exists():
        print(f"File: {ir_file.stat().st_size} bytes")
        print(ir_file.read_text()[:300])
    
    print("\n=== Testing ERC Check ===")
    ok2 = flow._run_erc_check()
    erc_file = latest / 'erc_report.txt'
    if erc_file.exists():
        print(f"File: {erc_file.stat().st_size} bytes")
        print(erc_file.read_text()[:200])
    
    print("\n=== Testing Antenna Check ===")
    ok3 = flow._run_antenna_check()
    ant_file = latest / 'antenna_report.txt'
    if ant_file.exists():
        print(f"File: {ant_file.stat().st_size} bytes")
        print(ant_file.read_text()[:200])
    
    print("\n=== Testing Coverage Report ===")
    ok4 = flow._generate_coverage_report(5, 0)
    cov_file = latest / 'coverage_report.txt'
    if cov_file.exists():
        print(f"File: {cov_file.stat().st_size} bytes")
        print(cov_file.read_text()[:400])
    
    print("\n=== SUMMARY ===")
    print(f"IR Drop:   {'PASS' if ok1 else 'FAIL'}")
    print(f"ERC:       {ok2}")
    print(f"Antenna:   {ok3}")
    print(f"Coverage:  {ok4}")
