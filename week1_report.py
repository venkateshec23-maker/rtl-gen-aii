from database import get_all_runs
from collections import defaultdict

runs = get_all_runs()
by_design = defaultdict(list)
for r in runs:
    by_design[r['design_name']].append(r)

print('=== WEEK 1 FINAL REPORT ===')
print()
total = len(runs)
passed = sum(1 for r in runs if r['tapeout_ready'])

for name in sorted(by_design.keys()):
    dr = by_design[name]
    p = sum(1 for r in dr if r['tapeout_ready'])
    pct = p / len(dr) * 100 if dr else 0
    print(f'{name}: {p}/{len(dr)} ({pct:.0f}%)')

print()
print(f'TOTAL: {passed}/{total} ({passed/total*100:.0f}%)' if total else 'TOTAL: no runs')
print()
if total and passed / total >= 0.80:
    print('STATUS: WEEK 1 TARGET ACHIEVED (80%+)')
elif total and passed / total >= 0.65:
    print('STATUS: CLOSE — one more fix needed')
else:
    print('STATUS: Still needs work')
