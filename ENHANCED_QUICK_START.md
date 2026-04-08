# Enhanced Visualization - Quick Start

## 🚀 Get Started in 2 Minutes

### Step 1: Generate Visualizations
```bash
python python/enhanced_visualizer.py your_design.v output_folder
```

### Step 2: Open in Browser
```bash
start output_folder/enhanced_viewer.html
```

That's it! You now have:
- ✅ RTL gate-level schematic
- ✅ Synthesis progression (RTL → Generic → Technology-mapped)
- ✅ Waveform timing diagrams
- ✅ Interactive HTML5 dashboard

---

## 📊 What Each Image Shows

| Image | Shows | What to Look For |
|-------|-------|-----------------|
| **RTL Schematic** | Gate-level netlist | Logic gates, connections, signal flow |
| **Synthesis Progression** | Design evolution through 3 stages | Gate count reduction, optimization |
| **Waveforms** | Signal behavior over time | Clock edges, reset timing, transitions |

---

## 💡 Example Usage

### Create Visualizations for Your Design
```bash
cd c:\Users\venka\Documents\rtl-gen-aii

# For the adder design
python python/enhanced_visualizer.py adder_8bit.v viz/adder_enhanced

# For counter design  
python python/enhanced_visualizer.py counter_4bit.v viz/counter_enhanced

# For traffic controller
python python/enhanced_visualizer.py traffic_controller.v viz/traffic_enhanced
```

### View Results
```bash
# Open main dashboard
start viz/adder_enhanced/enhanced_viewer.html

# Or view individual images
explorer viz/adder_enhanced\
```

---

## 🎯 What to Look For in Each Visualization

### RTL Schematic
- **Blue boxes left**: Input signals
- **Red boxes right**: Output signals  
- **Colored rectangles**: Logic gates
- **Lines**: Signal routing

**Good schematic signs:**
- Inputs logically flow to outputs
- No dead-end signals
- Reasonable gate count for design complexity

### Synthesis Progression
- **Bar 1**: Your original RTL + port list
- **Bar 2**: Generic gate count after synthesis
- **Bar 3**: Final cell library mapping

**Good progression signs:**
- Gate count decreases from bar 2→3 (optimization working)
- All three stages visible and labeled

### Waveforms
- Shows clock cycles on X-axis
- Signals on Y-axis
- Vertical lines = transitions
- Shows reset, clock, data timing

---

## 🛠️ Customization

### Generate for Different Paths
```python
from pathlib import Path
from python.enhanced_visualizer import EnhancedPipelineVisualizer

# With different output directory
viz = EnhancedPipelineVisualizer(output_dir="my_custom_path")
results = viz.visualize_design(Path("counter_4bit.v"))

# View generated files
for stage, filepath in results.items():
    print(f"{stage}: {filepath}")
```

### Batch Processing
```python
from pathlib import Path
from python.enhanced_visualizer import EnhancedPipelineVisualizer

viz = EnhancedPipelineVisualizer("batch_output")

verilog_files = Path(".").glob("*.v")
for verilog in verilog_files:
    print(f"Processing {verilog.name}...")
    results = viz.visualize_design(verilog)
    print(f"  ✓ Generated {len(results)} visualizations")
```

---

## 📂 Generated Files

```
output_folder/
├── 01_rtl_schematic.png          ← Gate-level schematic diagram
├── synthesis_progression.png       ← Evolution through 3 synthesis stages
├── waveform_diagram.png            ← Timing diagram from simulation
└── enhanced_viewer.html            ← Interactive HTML5 dashboard
```

**File Sizes:**
- PNG images: ~50-150 KB each (150 DPI quality)
- HTML viewer: ~15 KB (lightweight, no dependencies)
- **Total: ~200-300 KB** for complete suite

---

## 🎓 Understanding the Design Flow

```
┌─────────────────────────────┐
│  Your Verilog RTL Code      │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  RTL Schematic Extraction   │ → Visualize as 01_rtl_schematic.png
│  (Parse gates & nets)       │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  Synthesis Analysis         │ → Visualize as synthesis_progression.png
│  Stage 1: Behavioral RTL    │
│  Stage 2: Generic Gates     │
│  Stage 3: Technology Mapped │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  Behavioral Simulation      │ → Visualize as waveform_diagram.png
│  Apply test vectors         │
│  Generate timing diagram    │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  Interactive Dashboard      │ → Open enhanced_viewer.html in browser
│  All visualizations + guide │
└─────────────────────────────┘
```

---

## ✨ Features

| Feature | Included | Details |
|---------|----------|---------|
| Gate Extraction | ✅ | Parses Verilog for logic gates |
| Schematic Drawing | ✅ | Colored gates, connections, ports |
| Synthesis Analysis | ✅ | Shows 3-stage transformation |
| RTL Simulation | ✅ | Basic clock/reset vectors |
| Waveform Diagram | ✅ | Timing diagram format |
| HTML Dashboard | ✅ | Tab-based interactive viewer |
| Zoom/Pan | ✅ | Browser native zoom (Ctrl+scroll) |
| Export Quality | ✅ | 150 DPI professional images |

---

## 🐛 Troubleshooting

### "No gates found" in RTL Schematic
**Normal!** Most designs use behavioral description, not explicit gate instantiation. The synthesizer will create gates during synthesis (visible in progression stage 2).

### Schematic looks empty
**Check:** Is your Verilog file readable and contains valid module declarations?

```bash
# Verify file exists
dir adder_8bit.v

# Check it's parseable
python -c "from pathlib import Path; print(Path('adder_8bit.v').read_text()[:200])"
```

### HTML dashboard won't load images
**Check:** All PNG files in same directory as HTML file

```bash
dir viz/adder_enhanced/
# Should show: 01_rtl_schematic.png, synthesis_progression.png, etc.
```

---

## 🔗 Integration with Your Pipeline

### After Synthesis
```python
# After your synthesis completes
from python.enhanced_visualizer import EnhancedPipelineVisualizer

viz = EnhancedPipelineVisualizer(run_dir / "visualizations")
results = viz.visualize_design(Path("synthesized.v"))

print(f"Visualizations ready at: {results['viewer']}")
```

### In CI/CD
```bash
#!/bin/bash
# Generate visualizations for every design

for design in *.v; do
    outdir="visualizations/$(basename $design .v)"
    python python/enhanced_visualizer.py "$design" "$outdir"
    echo "Generated: $outdir/enhanced_viewer.html"
done
```

---

## 📖 Learn More

See **ENHANCED_VISUALIZATION_GUIDE.md** for:
- Detailed explanation of each visualization
- How to read gate schematics professionally
- Synthesis optimization details
- Advanced customization
- Comparison with commercial tools (Cadence Genus)

---

## 💬 Example: Understanding a Circuit

Let's say you see this RTL schematic:

```
        ┌──────┐
clk ────┤      ├──── q
        │  DFF │
d  ─────┤      ├─────
        └──────┘
```

This shows a D flip-flop:
- **clk input** (left): Clock signal
- **d input** (left): Data input
- **q output** (right): Data output
- **DFF** (center): D Flip-Flop gate

At each clock edge, the value on `d` is captured and appears on `q` next cycle.

Now in the **Synthesis Progression**, you'd see:
- **Stage 1**: Original `always @(posedge clk) q <= d;`
- **Stage 2**: Generic DFF gate 
- **Stage 3**: `sky130_fd_sc_hd__dfxtp_1` (actual library DFF cell)

And in **Waveforms**, you'd see:
```
clk:  ┌─┐ ┌─┐ ┌─┐ ┌─┐
      └─┘ └─┘ └─┘ └─┘

d:    ─┐ ┌───────┬──
      0│ │1      │0

q:    ───┤1      ├──   (delayed by one clock)
      0  └───────┘
```

---

## 🎉 You're Ready!

1. **Generate:** `python python/enhanced_visualizer.py your_design.v output`
2. **View:** `start output/enhanced_viewer.html`
3. **Explore:** Click tabs to see RTL, Synthesis, and Waveforms
4. **Share:** PNG images are presentation-ready!

**Questions?** Refer to ENHANCED_VISUALIZATION_GUIDE.md for detailed help.
