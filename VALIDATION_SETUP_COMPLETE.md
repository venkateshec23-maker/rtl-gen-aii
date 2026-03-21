# VALIDATION SETUP — COMPLETE ✅

**What has been prepared:**
- ✅ Prerequisite checker (`prereq_check.ps1`)
- ✅ Full orchestrator runner (`validate_pipeline.py`)
- ✅ Test design (`validation/adder_8bit.v`)
- ✅ Comprehensive guides (START_HERE.md, VALIDATION_GUIDE.md, others)

**Current status:**
- ✅ Docker running
- ✅ OpenLane image available
- ✅ PDK installed
- ✅ Yosys (via Docker - no local install needed!)

---

## Key Change: NO LOCAL TOOL INSTALLATION NEEDED

The pipeline now runs **all tools inside Docker**:
- Yosys synthesis → inside OpenLane container
- All other stages → already via Docker

This means you can run validation with just Docker + the files we have!

---

## NEXT: Verify and Run

```powershell
# Verify prerequisites are ready (1 min)
.\prereq_check.ps1

# Run full pipeline on real design (15-30 min)
python validate_pipeline.py
```

---

## ENTRY POINTS

**Quick start:** [START_HERE.md](START_HERE.md)

**Full guide:** [VALIDATION_GUIDE.md](VALIDATION_GUIDE.md)

**Troubleshooting:** [YOSYS_INSTALL.md](YOSYS_INSTALL.md)

---

## What Happens When You Run

1. **Now:** You run `python validate_pipeline.py`
2. **System:** Loads 8-bit adder from `validation/adder_8bit.v`
3. **Pipeline:** 
   - Synthesizes to netlist (Yosys)
   - Estimates die size
   - Plans placement
   - Places cells
   - Builds clock tree
   - Routes connections
   - Generates GDS file
4. **Result:**
   - **Success:** `is_tapeable: True` + GDS file path
   - **Failure:** Specific stage + error + fix suggestion

---

## 🎯 This Is The Critical Gate

- ✅ **Pass:** Foundation proven → Build UI/API/Docker (Days 1-4)
- ❌ **Fail:** Identify stage, debug, fix, retry

No point building UX on unvalidated integration.

---

## Ready?

1. **Install Yosys** (pick option A, B, or C above)
2. **Run:** `.\prereq_check.ps1`
3. **Then:** `python validate_pipeline.py`
4. **Report:** output (success or error)

**That's it.** We'll know in 30 minutes whether the 449-test codebase actually works on a real design.

---

Created: March 21, 2026
Location: `c:\Users\venka\Documents\rtl-gen-aii\`
Status: Ready to validate
