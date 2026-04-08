# RTL-Gen AI - Agent Context File
# READ THIS FIRST BEFORE DOING ANYTHING
# Last Updated: 2026-04-06 23:00

CURRENT PIPELINE STATE:
Synthesis: REAL_SKY130 (34 cells)
Routing: REAL (50868 bytes)
GDS: REAL (152.4 KB)
LVS: MATCHED
Timing: MET (?)
Unit Tests: 1 PASS / 0 FAIL
Integration Tests: 1 PASS / 0 FAIL
TAPE-OUT READY: YES

CRITICAL FILES - DO NOT MODIFY:
- full_flow.py: Main Docker EDA orchestrator
- RealMetricsParser: Reads real tool outputs
- FILE_SIZE_THRESHOLDS: Minimum sizes for real files
- verify_everything.ps1: Complete verification
- tests/test_unit.py: Prevention enforcement

DO NOT REVERT THESE FIVE FIXES:
1. hilomap before opt_clean (prevents DRT-0305)
2. pdngen before global_route (prevents SIGSEGV)
3. make_tracks before placement (prevents PPL-0021)
4. synth_sky130 not synth (prevents generic cells)
5. Dynamic cell name extraction from SPICE (prevents LVS abort)

VERIFICATION COMMANDS:
  cd C:\tools\OpenLane
  powershell -ExecutionPolicy Bypass -File verify_everything.ps1

Expected result: PASS: 55+, FAIL: 0

