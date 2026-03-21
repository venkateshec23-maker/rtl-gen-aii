# END-TO-END VALIDATION GUIDE

**Status:** All prerequisites ready. Docker ✅ OpenLane ✅ PDK ✅ — Only Yosys needed.

---

## 🎯 Objective

This is the **critical moment**: Execute the complete RTL→GDS pipeline end-to-end on a real design for the **first time** to prove the system works before building UI/API/Docker/publication.

**What will happen:**
- Load 8-bit adder from `validation/adder_8bit.v`
- Synthesize with Yosys → netlist
- Floorplan, place, CTS, global route, detailed route
- Generate GDS file + sign-off checks
- Report: ✅ **tapeable** or ❌ **failed at [stage]**

**Expected time:** 15-30 minutes

---

## ⚡ Quick Start (3 Steps)

### Step 1: Install Yosys (5 min - if not already present)

**If you have Conda/Miniconda** (recommended):

```powershell
conda install -c conda-forge yosys
```

Or use the installer script:
```powershell
.\install_yosys.ps1
```

**If you don't have Conda:**
- See [YOSYS_INSTALL.md](YOSYS_INSTALL.md) for alternatives

**Verify** (should see version):
```powershell
yosys -version
```

---

### Step 2: Verify Prerequisites (1 min)

```powershell
.\prereq_check.ps1
```

**Expected output:**
```
Step 1: Docker... [OK]
Step 2: OpenLane image... [OK]
Step 3: PDK... [OK]
Step 4: Yosys... [OK]

[OK] ALL CHECKS PASSED
Ready to run: python validate_pipeline.py
```

If anything fails, fix and re-run.

---

### Step 3: Run Validation (15-30 min)

```powershell
python validate_pipeline.py
```

This will:
- Start the pipeline
- Show progress bar + stage names in real-time
- Report success or specific failure point

---

## 📊 Expected Outcomes

### ✅ SUCCESS

```
Pipeline Complete: ✅
- is_tapeable: True
- GDS file: ...validation/runs/adder_8bit/run_*/results/final/adder_8bit.gds
- Total time: 18.5 seconds
```

**Next:** Foundation proven. Ready to build UI/API/Docker container.

---

### ❌ FAILURE

Script reports specific stage + error:

```
Pipeline Failed at: placement
Error: Insufficient area for placement
Diagnostic: Increase target_utilization from 0.50 to 0.40
```

**Fix:** Edit `validate_pipeline.py` line 75, rerun.

Common failure points:

| Stage | Cause | Fix |
|---|---|---|
| synthesis | Yosys not found | Ensure `yosys -version` works |
| synthesis | RTL syntax error | Check `validation/adder_8bit.v` |
| floorplan | Design too small for utilization goal | Reduce `target_utilization` to 0.40 |
| placement | Cells won't fit in allocated area | Reduce `placement_density` to 0.40 |
| routing | Unrouted nets / congestion | Reduce `placement_density` further (0.35) |
| gds | Magic issue | Verify PDK at `C:\pdk\sky130A` |
| timeout | Stage takes >5 min | Increase timeout in config |

---

## 📁 Files

| File | Purpose |
|---|---|
| `validate_pipeline.py` | Main orchestrator runner (280 lines) |
| `prereq_check.ps1` | System prerequisites checker |
| `VALIDATION_QUICKSTART.md` | This file |
| `YOSYS_INSTALL.md` | Yosys installation options |
| `install_yosys.ps1` / `.bat` | Automated Yosys installer |
| `validation/adder_8bit.v` | Test design (8-bit registered adder) |
| `validation/runs/` | Output directory (created during run) |

---

## 🔍 Understanding Results

### Success = is_tapeable: True

This means:
- ✅ Full pipeline works end-to-end
- ✅ Design successfully placed and routed
- ✅ GDS file generated and validated
- ✅ Ready for tapeout (theoretical)

**Implication:** Foundation is solid. All 5 phases (Floorplan→CTS→Routing→GDS) work in concert.

---

### Failure = specific stage

Each failure is a learning point:

1. **Synthesis**: RTL→netlist conversion
   - Usually means Yosys is missing
   - Or RTL has syntax errors

2. **Floorplanning**: Estimate die area
   - Usually means utilization target is too aggressive
   - Solution: reduce target_utilization

3. **Placement**: Place cells in die
   - Similar to floorplanning
   - Solution: reduce placement_density

4. **Routing**: Connect nets with metal layers
   - Most congestion-prone step
   - Solution: much more aggressive density reduction

5. **GDS**: Generate final layout file
   - Rare failure
   - Usually means Magic configuration or PDK issue

---

## 🛠️ Troubleshooting

### Yosys Not Found

```powershell
# Check if Yosys is in PATH
Get-Command yosys

# If not, install:
conda install -c conda-forge yosys
```

### Docker Not Running

```powershell
# Start Docker Desktop (GUI) or via CLI:
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

### OpenLane Image Missing

```powershell
docker pull efabless/openlane:latest
```

### PDK Invalid

Check that `C:\pdk\sky130A\` exists with subdirectories:
- `libs.tech/`
- `libs.ref/`

If not, verify your original PDK setup.

---

## 📝 Logs

Detailed logs written to:
- Terminal output (real-time)
- `validation_run.log` (current directory)
- `validation/runs/adder_8bit/run_*/logs/` (per-stage logs)

---

## ✨ What Happens Next

### If Validation Passes ✅

1. **Day 1**: Build Streamlit UI for parameter tuning + design upload
2. **Day 2**: Build Flask API for integration
3. **Days 3-4**: Package as Docker container
4. **Day 5**: Publication prep

### If Validation Fails ❌

1. Fix the identified stage
2. Re-run validation
3. Iterate until is_tapeable=True
4. Then proceed to UI/API/Docker

---

## 🚀 Run Now

```powershell
# One-liner to run everything:
.\prereq_check.ps1 -and python validate_pipeline.py
```

Or individually:
```powershell
.\prereq_check.ps1          # 1-2 min
python validate_pipeline.py  # 15-30 min
```

---

**Report back with the output** — success confirmation or specific error + line number.

This is the test that determines whether the entire project is ready for the next phase. 🎯
