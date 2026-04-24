import subprocess
from pathlib import Path

RESULTS = Path(r'C:\tools\OpenLane\results')
RUNS    = Path(r'C:\tools\OpenLane\runs')

print('='*60)
print('RTL-GEN AI — REAL STATUS REPORT')
print('='*60)

# Count real GDS files
real_gds = []
if RUNS.exists():
    for run_dir in RUNS.iterdir():
        if run_dir.is_dir():
            for gds in run_dir.glob('**/*.gds'):
                if gds.stat().st_size > 50000:
                    real_gds.append({
                        'design': run_dir.name,
                        'kb': round(gds.stat().st_size/1024,1)
                    })

print(f'Real GDS files (>50KB): {len(real_gds)}')
for g in real_gds:
    print(f"  {g['design']}: {g['kb']} KB")

# Check exhaustive simulation exists
exhaustive_log = RESULTS / 'exhaustive_simulation.log'
if exhaustive_log.exists():
    content = exhaustive_log.read_text(errors='ignore')
    print(f'Exhaustive simulation: EXISTS')
    if 'ALL_TESTS_PASSED' in content:
        print('  Result: ALL_TESTS_PASSED')
    else:
        print('  Result: NOT PASSING')
else:
    print('Exhaustive simulation: NEVER RUN')

# Check KLayout full DRC
drc_full = RESULTS / 'drc_full.xml'
if drc_full.exists():
    print(f'Full KLayout DRC: EXISTS ({drc_full.stat().st_size} bytes)')
else:
    print('Full KLayout DRC: NEVER RUN')

# Check post-layout simulation
post_sim = RESULTS / 'post_layout_simulation.log'
if post_sim.exists():
    print('Post-layout simulation: EXISTS')
else:
    print('Post-layout simulation: NEVER RUN')

print()
print('DESIGNS PROVEN END-TO-END:')
designs_proven = len(real_gds)
print(f'  {designs_proven} designs have real GDS')
print(f'  0 designs have exhaustive simulation')
print(f'  0 designs have full KLayout DRC')
print(f'  0 designs have post-layout simulation')
print()
print('HONEST STATUS:')
if designs_proven >= 5:
    print('  Pipeline: PROVEN FOR MULTIPLE DESIGNS')
elif designs_proven >= 2:
    print('  Pipeline: PARTIALLY PROVEN (2 designs)')
else:
    print('  Pipeline: SINGLE DESIGN PROOF ONLY')
print('  Simulation depth: SHALLOW (6 vectors)')
print('  DRC completeness: PARTIAL (not full rule deck)')
print('  Post-layout sim: NOT DONE')
print()
print('WHAT WOULD MAKE THIS COMPLETE:')
print('  1. Exhaustive simulation (65536 vectors for adder)')
print('  2. 5 different designs proven')
print('  3. Full KLayout DRC rule deck')
print('  4. Post-layout extraction + simulation')
print('  5. Cloud deployment tested by real user')
