from full_flow import RTLtoGDSIIFlow

designs = [
    ('adder_8bit',    r'C:\tools\OpenLane\designs\adder_8bit\adder_8bit.v'),
    ('counter_4bit',  r'C:\tools\OpenLane\designs\counter_4bit\counter_4bit.v'),
    ('alu_4bit',      r'C:\tools\OpenLane\designs\alu_4bit\alu_4bit.v'),
    ('shift_reg_8bit',r'C:\tools\OpenLane\designs\shift_reg_8bit\shift_reg_8bit.v'),
    ('traffic_light', r'C:\tools\OpenLane\designs\traffic_light\traffic_light.v'),
]

passed = 0
for name, path in designs:
    flow = RTLtoGDSIIFlow(name, path, r'C:\tools\OpenLane', r'C:\pdk')
    s = flow.run_full_flow()
    ok = s['tapeout_ready']
    if ok:
        passed += 1
    status = "PASS" if ok else "FAIL"
    print(f"  {status}: {name} - {s['status']}")

print(f"\nSUCCESS RATE: {passed}/{len(designs)} ({passed/len(designs)*100:.0f}%)")
print(f"BEFORE FIXES: 32% (21/65)")
print(f"IMPROVEMENT: {passed/len(designs)*100 - 32:.0f}% better")
