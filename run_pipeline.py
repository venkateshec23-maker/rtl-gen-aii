from full_flow import RTLtoGDSIIFlow
flow = RTLtoGDSIIFlow('test', r'C:\tools\OpenLane')
results = flow.run_full_flow()
print('\n=== PIPELINE RESULTS ===')
for step, passed in results.items():
    if isinstance(passed, bool):
        status = '✅ PASS' if passed else '❌ FAIL'
        print(f'{step}: {status}')
