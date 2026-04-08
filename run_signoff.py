#!/usr/bin/env python
"""Run GDS generation and sign-off steps only"""

from full_flow import RTLtoGDSIIFlow
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)

# Create flow object
flow = RTLtoGDSIIFlow(
    design_name  = 'adder_8bit',
    verilog_file = r'C:\tools\OpenLane\designs\adder_8bit\adder_8bit.v',
    work_dir     = r'C:\tools\OpenLane',
    pdk_dir      = r'C:\pdk',
    clock_period = 10.0
)

print("\n" + "="*60)
print("RUNNING REMAINING SIGN-OFF STEPS")
print("="*60)

# Step 4: GDS Generation
print("\nStep 4: GDS Generation...")
gds_ok = flow.step4_gds_generation()
print(f"  Result: {'✅ PASS' if gds_ok else '❌ FAIL'}")

# Step 5: DRC
print("\nStep 5: DRC...")
drc_ok = flow.step5_drc()
print(f"  Result: {'✅ PASS' if drc_ok else '❌ FAIL'}")

# Step 6: LVS
print("\nStep 6: LVS...")
lvs_ok = flow.step6_lvs()
print(f"  Result: {'✅ PASS' if lvs_ok else '❌ FAIL'}")

# Step 7: STA
print("\nStep 7: Static Timing Analysis...")
sta_ok = flow.step7_sta()
print(f"  Result: {'✅ PASS' if sta_ok else '❌ FAIL'}")

print("\n" + "="*60)
print("SIGN-OFF COMPLETE")
print("="*60)
