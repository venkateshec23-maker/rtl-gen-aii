from full_flow import RTLtoGDSIIFlow

designs = [
    ('counter_4bit', r'C:\tools\OpenLane\designs\counter_4bit\counter_4bit.v'),
    ('shift_reg_8bit', r'C:\tools\OpenLane\designs\shift_reg_8bit\shift_reg_8bit.v'),
    ('traffic_light', r'C:\tools\OpenLane\designs\traffic_light\traffic_light.v'),
    ('alu_4bit', r'C:\tools\OpenLane\designs\alu_4bit\alu_4bit.v'),
]

print("=== DEBUGGING FAILING DESIGNS ===")
print()

for name, path in designs:
    print(f"--- {name} ---")
    try:
        flow = RTLtoGDSIIFlow(name, path, r'C:\tools\OpenLane', r'C:\pdk')
        s = flow.run_full_flow()
        
        failed = [(k, v) for k, v in s['steps'].items() if v != 'PASS']
        
        if s['tapeout_ready']:
            print(f"  STATUS: PASS")
        else:
            print(f"  STATUS: FAIL")
            for step, status in failed:
                print(f"    {step}: {status}")
            
            # Check specific failure reasons
            if not s.get('gds_generated', False):
                print(f"    REASON: GDS not generated")
            if s.get('lvs_matched') == False:
                print(f"    REASON: LVS mismatch")
            if s.get('timing_met') == False:
                print(f"    REASON: Timing failed")
            if s.get('drc_clean') == False:
                print(f"    REASON: DRC violations")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
