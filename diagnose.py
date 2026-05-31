"""Diagnose failures in RTL-Gen AI"""
from pathlib import Path
import json
from collections import defaultdict

runs_dir = Path(r'C:\tools\OpenLane\runs')
runs = []
failures = []

# Load all runs
for run in runs_dir.glob('*_*'):
    summary = run / 'run_summary.json'
    if summary.exists():
        with open(summary) as f:
            data = json.load(f)
        runs.append(data)
        if not data.get('tapeout_ready', False):
            failures.append(data)

print(f'Total runs: {len(runs)}')
print(f'Total failures: {len(failures)}')
print(f'Success rate: {100*(len(runs)-len(failures))/len(runs):.1f}%')
print()

# Count which step fails most
step_failures = defaultdict(int)
for r in failures:
    steps = r.get('steps', {})
    if isinstance(steps, dict):
        for step, result in steps.items():
            if result != 'PASS':
                step_failures[step] += 1

print('FAILURE BY STEP (most common first):')
for step, count in sorted(step_failures.items(), key=lambda x: x[1], reverse=True):
    pct = count/len(failures)*100 if failures else 0
    print(f'  {count:4d} ({pct:5.1f}%): {step}')

print()

# Analyze by design
by_design = defaultdict(lambda: {'pass':0,'fail':0})
for r in runs:
    name = r.get('design_name','unknown').split('_')[0]
    if r.get('tapeout_ready'):
        by_design[name]['pass'] += 1
    else:
        by_design[name]['fail'] += 1

print('SUCCESS RATE BY DESIGN:')
for name in sorted(by_design.keys()):
    d = by_design[name]
    total = d['pass'] + d['fail']
    if total >= 3:
        rate = d['pass']/total*100
        print(f'  {rate:5.0f}%  {name:20} ({d["pass"]}/{total})')
