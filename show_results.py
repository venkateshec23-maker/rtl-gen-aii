from full_flow import RTLtoGDSIIFlow
flow = RTLtoGDSIIFlow('test', r'C:\tools\OpenLane')
results = flow.run_full_flow()
print('\n' + '='*50)
print('FINAL PIPELINE RESULTS')
print('='*50)
for step, result in results.items():
    if isinstance(result, bool):
        status = 'PASS' if result else 'FAIL'
        print(f'  {step}: {status}')
    else:
        print(f'  {step}: {result}')
