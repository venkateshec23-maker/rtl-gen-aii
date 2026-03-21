# Validation Quickstart

This is the critical moment: **First end-to-end run on real tools.**

## 🔧 Road Map

### Step 1: Verify Prerequisites (1 min)
Run from PowerShell in project root:
```powershell
.\prereq_check.ps1
```

**Expected output:**
```
Step 1: Docker... [OK]
Step 2: OpenLane image... [OK]
Step 3: PDK... [OK]

[OK] ALL CHECKS PASSED
```

**If any fail:** Fix the specific issue before proceeding (see error message).

---

### Step 2: Run Validation (15-30 min)
Once all prerequisites pass:
```powershell
python validate_pipeline.py
```

**What it will do:**
- Load 8-bit adder design from `validation\adder_8bit.v`
- Run full RTL → GDS pipeline:
  - Yosys synthesis → netlist
  - Floorplanning, placement, CTS
  - Global routing, detailed routing
  - GDS generation + sign-off checks
- Report result: ✅ or ❌

**Expected time:** 15-30 minutes depending on system speed

---

## 📊 Success vs Failure

### ✅ Success
```
Pipeline Complete: ✅
- is_tapeable: True
- GDS file: C:\...\validation\runs\adder_8bit\run_*\results\final\adder_8bit.gds
- Total time: X.XX seconds
```

**Next:** Foundation proven. Ready to build UI/API/Docker container.

---

### ❌ Failure
Script reports specific stage + error:
```
Pipeline Failed at: [stage_name]
Error: [specific reason]
Diagnostic: [fix suggestion]
```

**Common failures & fixes:**
| Stage | Cause | Fix |
|---|---|---|
| synthesis | Yosys not found | `winget install YosysHQ.yosys` |
| synthesis | RTL syntax error | Check `validation/adder_8bit.v` |
| floorplan | Design too small for utilization | Edit validate_pipeline.py: set `target_utilization = 0.40` |
| placement | Placement too dense | Edit validate_pipeline.py: set `placement_density = 0.40` |
| routing | Congestion/unrouted nets | Reduce placement density further |
| gds | Magic tech file missing | Verify PDK at `C:\pdk\sky130A` |
| timeout | Stage takes too long | May need to adjust clock frequency or utilization |

---

## 📝 Files Involved

- **Design:** `validation/adder_8bit.v` (8-bit registered adder)
- **Validator:** `validate_pipeline.py` (orchestrator runner + diagnostics)
- **Prerequisites:** `prereq_check.ps1` (quick system check)
- **Results:** `validation/runs/adder_8bit/` (generated files + logs)

---

## ⚡ TL;DR
```powershell
# Check everything is ready
.\prereq_check.ps1

# Run validation (wait 15-30 min)
python validate_pipeline.py

# Report back with output
```

That's it. This determines whether the whole system works.
