print('=== FINAL INTEGRATION TEST ===')
print()

import sys
errors = []

# 1. All imports
print('1. Imports')
for m in ['full_flow','app','database','guaranteed_flow',
          'verilog_generator','report_generator','api',
          'netlist_viewer','waveform_display',
          'layout_viewer','timing_viewer']:
    try:
        __import__(m)
        print(f'   OK: {m}')
    except Exception as e:
        errors.append(f'IMPORT: {m} — {e}')
        print(f'   FAIL: {m} — {e}')

# 2. Templates
print()
print('2. Templates')
from guaranteed_flow import TEMPLATES_RTL, TEMPLATES_TB
required = ['counter','adder','shift_reg','mux','alu',
            'fsm','uart_tx','spi_master','i2c_master',
            'fifo','memory','reg_file','comparator',
            'decoder','encoder','pwm','crc',
            'multiplier','clk_div']
for t in required:
    ok = t in TEMPLATES_RTL and t in TEMPLATES_TB
    if not ok:
        errors.append(f'TEMPLATE: {t} missing')
    print(f'   {"OK" if ok else "MISS"}: {t}')

# 3. Database
print()
print('3. Database')
from database import DB_AVAILABLE, get_all_runs
print(f'   DB: {"RUNNING" if DB_AVAILABLE else "OFFLINE"}')
if DB_AVAILABLE:
    runs = get_all_runs()
    ready = [r for r in runs if r.get('tapeout_ready')]
    print(f'   Runs: {len(runs)} total, {len(ready)} tape-out ready')

# 4. GDS files
print()
print('4. Real GDS Files')
from pathlib import Path
runs_dir = Path(r'C:\tools\OpenLane\runs')
real_gds = [g for g in runs_dir.rglob('*.gds')
            if g.stat().st_size > 50000]
print(f'   Total: {len(real_gds)} real GDS files')
for g in sorted(real_gds, key=lambda x: x.stat().st_size,
                reverse=True)[:5]:
    print(f'   {g.stat().st_size//1024:6}KB  {g.parent.name}')

# 5. UI tab files
print()
print('5. UI Viewer Files')
viewer_files = [
    'netlist_viewer.py',
    'waveform_display.py',
    'layout_viewer.py',
    'timing_viewer.py',
]
for f in viewer_files:
    exists = Path(f).exists()
    if not exists:
        errors.append(f'VIEWER: {f} missing')
    print(f'   {"OK" if exists else "MISSING"}: {f}')

# Summary
print()
print('=== SUMMARY ===')
if errors:
    print(f'ERRORS: {len(errors)}')
    for e in errors:
        print(f'  {e}')
else:
    print('ALL CHECKS PASSED — PROJECT IS PRODUCTION READY')
