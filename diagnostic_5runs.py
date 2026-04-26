from full_flow import RTLtoGDSIIFlow

print("=== 5-RUN DIAGNOSTIC ===")
print()

for i in range(5):
    flow = RTLtoGDSIIFlow(
        'adder_8bit',
        r'C:\tools\OpenLane\designs\adder_8bit\adder_8bit.v',
        r'C:\tools\OpenLane', r'C:\pdk'
    )
    s = flow.run_full_flow()
    failed = [k for k,v in s['steps'].items() if v != 'PASS']
    status = s.get('status', 'UNKNOWN')
    print(f'Run {i+1}: {status}')
    if failed:
        print(f'  Failed steps: {failed}')
    else:
        print(f'  All steps passed')
    print()

print("=== DIAGNOSTIC COMPLETE ===")
