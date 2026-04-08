# Quick-Start: Complete Design Flow in 2 Hours with OpenLANE

## TL;DR - The Fastest Path

If you want results **TODAY** with minimal setup, use **OpenLANE**. It automates the entire flow (synthesis → placement → routing → DRC) in one command and produces professional outputs.

---

## What You'll Get

After running this, you'll have:
```
design_output/
├── final/gds/design.gds           ← Final layout file
├── final/reports/                  ← Timing, power, area reports
│   ├── timing.rpt                 ← Setup/hold slack analysis
│   ├── power.rpt                  ← Power consumption
│   └── area.rpt                   ← Cell area used
├── runs/                           ← Intermediate step outputs
│   ├── synthesis/                 ← Yosys netlist
│   ├── placement/                 ← Cell positions
│   ├── routing/                   ← Interconnect
│   └── ...
└── logs/                           ← Detailed execution logs
```

**Total outputs:** 50+ files with real metrics

---

## 5-Minute Installation

### Windows (Easiest)

#### Option A: Docker Desktop (Recommended)
```powershell
# 1. Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop
# Run installer, restart

# 2. Enable WSL2
wsl --install

# 3. Verify Docker works
docker run hello-world
```

#### Option B: WSL2 Native (10 minutes)
```bash
# In WSL2 Ubuntu terminal:
sudo apt-get update
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
# Log out and back in
docker run hello-world
```

### macOS / Linux
```bash
# Install Docker for your OS from docker.com
docker run hello-world  # Verify
```

---

## 10-Minute Setup (Clone OpenLANE)

```bash
# Clone OpenLANE
git clone https://github.com/The-OpenROAD-Project/OpenLane.git
cd OpenLane

# Download sky130 PDK (first time only, ~2GB)
make pull-openlane pull-pdk

# Done! You're ready to design
```

---

## Run Your First Design (30 minutes)

### Step 1: Create Design Directory

```bash
cd designs
mkdir my_adder_8bit
cd my_adder_8bit
```

### Step 2: Add Your Verilog

Create `src/design.v`:
```verilog
module adder_8bit(
    input [7:0] a,
    input [7:0] b,
    output [8:0] sum,
    input clk,
    input rst
);

    reg [8:0] sum_r;
    
    always @(posedge clk or posedge rst) begin
        if (rst)
            sum_r <= 9'b0;
        else
            sum_r <= a + b;
    end
    
    assign sum = sum_r;
    
endmodule
```

### Step 3: Create Configuration

Create `config.json`:
```json
{
    "DESIGN_NAME": "adder_8bit",
    "VERILOG_FILES": ["src/design.v"],
    "CLOCK_PORT": "clk",
    "CLOCK_PERIOD": 10,
    "pdk::sky130A": {
        "FP_CORE_UTIL": 30,
        "PL_TARGET_DENSITY_PCT": 40,
        "scl::sky130_fd_sc_hd": {
            "CLOCK_PERIOD": 10
        }
    }
}
```

**What it means:**
- `CLOCK_PERIOD`: Design must work at 100 MHz (10 ns period)
- `FP_CORE_UTIL`: Use 30% of die for logic (70% for routing/power)
- `PL_TARGET_DENSITY`: Place cells at ~40% density

### Step 4: Run the Flow

```bash
# Navigate to OpenLane root
cd ../..

# Run the entire flow (takes 20-30 minutes for small design)
python3 -m openlane designs/my_adder_8bit/config.json

# Watch stdout for progress...
# [INFO] Running step 01: verilator-lint
# [INFO] Running step 02: checker-linttimingconstructs
# ...
# [SUCCESS] Design run completed!
```

**The tool automatically runs:**
- Step 01-03: Linting and checks
- Step 04-08: Yosys synthesis
- Step 09-15: OpenROAD floorplanning & placement
- Step 16-29: Clock tree synthesis & global routing
- Step 30-35: Detailed routing
- Step 36-40: Design verification (DRC, LVS)

All **automatically**, no manual intervention needed.

---

## View Your Results (5 minutes)

### 1. Open Layout in KLayout

```bash
# View the final layout
klayout designs/my_adder_8bit/runs/*/final/results/design.gds

# In KLayout:
# - Right-click → Fit Window (see whole design)
# - Ctrl+Shift+M → Show/hide metal layers
# - Click layers in left panel to see routing, cells, etc.
```

**What you see:**
- Yellow boxes: Standard cells (AND, OR, NAND, flip-flops)
- Blue/red/green lines: Metal routing (6 layers)
- Black outline: Die boundary
- Power/ground meshes: White/gray grid

### 2. Read the Timing Report

```bash
cat designs/my_adder_8bit/runs/*/reports/routing/summary.rpt
```

**Example output:**
```
Design: adder_8bit
Area: 385 µm²
Timing WNS: +0.45 ns (PASS ✓)
Timing TNS: 0 ns
Power (estimated): 1.2 mW @ 100MHz
```

### 3. Check Synthesis Results

```bash
cat designs/my_adder_8bit/runs/*/reports/synthesis/synthesis_area.rpt
```

**Example output:**
```
Cell Count: 97 standard cells
Total Area: 385.2 µm²
  - NAND2: 28 cells
  - OR2: 15 cells
  - DFF: 8 cells
  - etc.
```

---

## Generate Documentation Images

### Screenshot the Layout

```bash
# In KLayout (GUI):
# File → Export → Export as PNG
# Settings: 150 DPI, full design area
# Save to: step10_final_layout.png
```

### Extract Timing Data

```bash
# All timing reports are here:
ls designs/my_adder_8bit/runs/*/reports/routing/

# Key files:
# - summary.rpt           ← Overall summary
# - timing.rpt            ← Detailed timing
# - slacks.rpt            ← Slack by path
```

### Generate Area Breakdown

```python
# Extract and tabulate results
import json

# Read the final config
with open("designs/my_adder_8bit/runs/latest/config.json") as f:
    config = json.load(f)

# Print summary
print("ADDER 8-BIT DESIGN SUMMARY")
print("=" * 50)
print(f"Design Name: {config['DESIGN_NAME']}")
print(f"Clock Period: {config['CLOCK_PERIOD']} ns")
print(f"Technology: sky130 (130nm)")
print("\nMetrics:")
# (read from reports)
```

---

## What Each Step Produces (For Documentation)

| Stage | Output File | What to Document |
|-------|-------------|---|
| **Synthesis** | `synthesis_area.rpt` | Cell count, total area, breakdown |
| **Placement** | `placement.rpt` | Utilization %, cell count |
| **CTS** | `cts.rpt` | Clock tree depth, skew |
| **Routing** | `routing.rpt` | Wire length, congestion |
| **Final** | `summary.rpt` | **Area (µm²), Timing (ns), Power (mW)** |

---

## Example: Complete Workflow (Copy-Paste Ready)

```bash
# 1. Clone and setup (first time)
git clone https://github.com/The-OpenROAD-Project/OpenLane.git
cd OpenLane
make pull-openlane pull-pdk

# 2. Create design
mkdir designs/adder_8bit/src
cat > designs/adder_8bit/src/design.v << 'EOF'
module adder_8bit(
    input [7:0] a, b,
    output [8:0] sum,
    input clk, rst
);
    reg [8:0] sum_r;
    always @(posedge clk)
        if (rst) sum_r <= 0;
        else sum_r <= a + b;
    assign sum = sum_r;
endmodule
EOF

# 3. Create config
cat > designs/adder_8bit/config.json << 'EOF'
{
    "DESIGN_NAME": "adder_8bit",
    "VERILOG_FILES": ["src/design.v"],
    "CLOCK_PORT": "clk",
    "CLOCK_PERIOD": 10,
    "pdk::sky130A": {
        "FP_CORE_UTIL": 30,
        "PL_TARGET_DENSITY_PCT": 40
    }
}
EOF

# 4. Run flow
python3 -m openlane designs/adder_8bit/config.json

# 5. View results
klayout designs/adder_8bit/runs/RUN_*/final/results/design.gds
cat designs/adder_8bit/runs/RUN_*/reports/routing/summary.rpt
```

That's it! **~1 hour from zero to complete layout.**

---

## Understanding the Output

### The Most Important Files

1. **`design.gds`** - Your final layout (can send to fab)
2. **`timing.rpt`** - Shows if design is fast enough
3. **`area.rpt`** - How much silicon area used
4. **`power.rpt`** - Power consumption estimate

### Reading the Timing Report

```
Worst Setup Slack (WNS): +0.45 ns
  ↑ Positive = good! Design meets timing.
  ↓ Negative = bad, need to optimize.

If positive:
  ✓ Design meets 100 MHz clock constraint
  ✓ Can safely increase clock speed
  ↓ Or reduce area/power

Typical values:
  Good:  +1.0 ns slack (safe margin)
  OK:    +0.3 ns slack (tight but OK)
  Fail:  -0.5 ns slack (too slow, redesign)
```

---

## Troubleshooting

### Problem: "Docker not found"
```bash
# Reinstall/restart Docker Desktop
# Or try: docker ps
# If fails, Docker isn't running
```

### Problem: "PDK not found"
```bash
# Download PDK (first time only)
make pull-pdk
# ~2GB download
```

### Problem: "Design doesn't close timing"
```bash
# Loosen clock constraint and retry
# In config.json, increase CLOCK_PERIOD:
"CLOCK_PERIOD": 15  # was 10, now 150 MHz → 66 MHz

python3 -m openlane designs/adder_8bit/config.json
```

---

## Next Steps

Once you have the basic flow working:

1. **Try more complex designs** (multiplier, FSM, counter)
2. **Analyze metrics** - Compare area/timing/power tradeoffs
3. **Optimize** - Trade area for speed or vice versa
4. **Create documentation** - Screenshot each stage for presentation

---

## Key Takeaway

**OpenLANE does in one command what would take hours with manual tool orchestration:**

```
Manual way:
Yosys synthesis (30 min)
  ↓ (copy netlist)
OpenROAD floorplan (20 min)
  ↓
OpenROAD placement (30 min)
  ↓
OpenROAD CTS (15 min)
  ↓
OpenROAD routing (45 min)
  ↓
Magic DRC (10 min)
  ↓
Extract & verify (20 min)
= ~3 hours total

OpenLANE way:
python3 -m openlane config.json
= ~30 minutes ✓ (automates all steps)
```

**Time savings: 5-6x faster**

Also produces professional-quality results that match commercial tools.

---

## Resources

- **OpenLANE Docs:** https://openlane2.readthedocs.io/
- **Sky130 PDK Info:** https://skywater-pdk.readthedocs.io/
- **OpenROAD Project:** https://github.com/The-OpenROAD-Project
- **Example flows:** https://github.com/The-OpenROAD-Project/OpenLane/tree/master/designs

---

**Ready to start? Run this ONE command and you'll have a complete professional IC layout in 30 minutes!**

```bash
git clone https://github.com/The-OpenROAD-Project/OpenLane.git && \
cd OpenLane && \
make pull-openlane pull-pdk && \
python3 -m openlane designs/my_design/config.json
```

✓ Professional grade
✓ Industry standard
✓ Ready for fabrication
✓ Free and open-source

**Let's go!**
