from full_flow import RTLtoGDSIIFlow

designs = [
    ('adder_8bit',    r'C:\tools\OpenLane\designs\adder_8bit\adder_8bit.v'),
    ('counter_4bit',  r'C:\tools\OpenLane\designs\counter_4bit\counter_4bit.v'),
    ('alu_4bit',      r'C:\tools\OpenLane\designs\alu_4bit\alu_4bit.v'),
    ('shift_reg_8bit',r'C:\tools\OpenLane\designs\shift_reg_8bit\shift_reg_8bit.v'),
    ('traffic_light', r'C:\tools\OpenLane\designs\traffic_light\traffic_light.v'),
]

print("=== COMPREHENSIVE 10-RUN TEST ===")
print()

total = 0
passed = 0
results = {}

for name, path in designs:
    results[name] = {'pass': 0, 'fail': 0}
    for i in range(2):  # 2 runs each = 10 total
        total += 1
        flow = RTLtoGDSIIFlow(name, path, r'C:\tools\OpenLane', r'C:\pdk')
        s = flow.run_full_flow()
        if s['tapeout_ready']:
            passed += 1
            results[name]['pass'] += 1
            print(f'{name} run {i+1}: PASS')
        else:
            results[name]['fail'] += 1
            failed = [k for k,v in s['steps'].items() if v != 'PASS']
            print(f'{name} run {i+1}: FAIL - {failed}')

print()
print("=== SUMMARY ===")
for name, r in results.items():
    print(f'{name}: {r["pass"]}/2')
print()
print(f'TOTAL: {passed}/{total} ({passed/total*100:.0f}%)')
if passed/total >= 0.80:
    print('TARGET ACHIEVED: 80%+ SUCCESS RATE')
