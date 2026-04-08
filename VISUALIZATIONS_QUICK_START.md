# 🎨 RTL-Gen AI Pipeline Visualization System

## ✨ What's New: 2D Layout Visualization & Interactive Dashboard

We've integrated a **FREE, 100% open-source visualization system** that generates beautiful 2D images of every stage in the RTL-to-GDS pipeline!

---

## 📍 Where Are The Images?

All visualizations are located in:

```
validation/run_001/visualizations/
```

### View the Interactive Dashboard (START HERE!)

💻 **Web Browser** - Opens in your default browser:
```powershell
# Windows
start validation/run_001/visualizations/dashboard.html

# PowerShell
Invoke-Item validation/run_001/visualizations/dashboard.html
```

🌐 **Direct link**: Click on [dashboard.html](validation/run_001/visualizations/dashboard.html) to open

---

## 📊 Generated Images

### All PNG Images (High-Quality 2D Layouts)

| Stage | File | Shows |
|-------|------|-------|
| 1️⃣ | `02_synthesis_report.png` | Gate distribution, ports, synthesis stats |
| 2️⃣ | `03_floorplan.png` | Die area, core region, chip boundary |
| 3️⃣ | `04_placement.png` | **All cells placed** in color-coded layout |
| 4️⃣ | `05_cts.png` | Clock tree synthesis, CTS cell distribution |
| 5️⃣ | `06_routing.png` | **Net routing paths**, interconnections |
| 6️⃣ | `07_gds.png` | GDSII file info, fabrication status |
| 💾 | `dashboard.html` | **Interactive viewer** for all stages |

### File Sizes
- Each PNG: ~40-70 KB (optimized)
- Dashboard: ~10 KB (fast loading)
- Total: ~320 KB (very lightweight)

---

## 🎯 How to Use the Dashboard

### Step 1: Open in Browser
```powershell
start validation/run_001/visualizations/dashboard.html
```

### Step 2: Navigate Between Stages
- Click buttons at the top: **RTL**, **Synthesis**, **Floorplan**, **Placement**, **CTS**, **Routing**, **GDS**
- Use **Overview** tab to see all stages at once
- Smooth transitions between views

### Step 3: Analyze Each Stage
- **RTL**: See module structure and port connections
- **Synthesis**: View gate statistics and logic distribution
- **Floorplan**: Understand die dimensions and core area
- **Placement**: Visualize cell placement and density
- **CTS**: See clock tree cells (orange) vs regular cells (blue)
- **Routing**: Observe net connections and routing paths
- **GDS**: Verify GDSII output file for tape-out

---

## 👀 Sample Visualizations

### Placement Visualization
Shows all 20+ cells placed in the design area with unique colors. Each cell is labeled and positioned according to the DEF file coordinates.

**Key Information:**
- Total cells: Display count
- Total nets: Show interconnections
- Density heatmap: Cell concentration areas
- Coordinates: X/Y positions in µm

### Routing Visualization
Displays cells with net connections shown as red lines between cells.

**Key Information:**
- Cell positions: Routed layout
- Net paths: Simple visualization of routing
- Routing density: Visual interconnect concentration
- Net statistics: Total nets routed

### CTS Visualization
Divides cells into two categories:
- **Orange cells**: Clock Tree Synthesis buffers
- **Blue cells**: Regular design cells

**Key Information:**
- CTS percentage: % of cells dedicated to clock
- Distribution: CTS cells vs regular cells
- Clock statistics: Net counts and totals

---

## 🎨 Dashboard Features

### Beautiful Interface
✨ **Modern gradient design** with purple-to-indigo gradient background  
🎨 **Color-coded sections** for each pipeline stage  
📱 **Responsive layout** - works on desktop and tablet  
🌟 **Professional styling** with shadows and hover effects  

### Interactive Elements
🖱️ **Clickable stage buttons** - navigate between views  
⚡ **Smooth animations** - fade-in transitions  
📊 **Live statistics** - pipeline metrics displayed  
⏰ **Timestamp** - shows when dashboard was generated  

### Navigation
🎯 **Quick jump buttons** at the top of page  
♻️ **Smooth stage switching** without page reload  
📍 **Stage indicators** show current view  

---

## 📈 What Each Image Shows

### 1. Synthesis Report (02_synthesis_report.png)
```
RTL → Synthesis → Reports

Shows:
- Module name and structure
- Input/Output port counts
- Total logic gates
- Gate types: AND, OR, XOR, NOT, NAND, NOR
```

### 2. Floorplan (03_floorplan.png)
```
RTL → Synthesis → Floor Planning

Shows:
- Die boundary (black rectangle)
- Core area definition
- Chip dimensions in µm
- Safe routing region
```

### 3. Placement (04_placement.png)
```
Floor Planning → Cell Placement

Shows:
- All cells color-coded
- Cell positions in X/Y coordinates
- Total cell count
- Net connections
- Cell density distribution
```

### 4. CTS (05_cts.png)
```
Cell Placement → Clock Tree Synthesis

Shows:
- CTS buffer cells (orange)
- Regular cells (light blue)
- Clock distribution percentage
- CTS vs regular cell ratio
```

### 5. Routing (06_routing.png)
```
CTS → Detailed Routing

Shows:
- Routed cell positions
- Net connections (red lines)
- Total nets routed
- Routing density
- Interconnect visualization
```

### 6. GDS (07_gds.png)
```
Routing → GDS Generation → Tape-Out

Shows:
- GDSII file validity check
- File size and format confirmation
- Geometry record counts
- Fabrication readiness status
```

---

## 🚀 Quick Start Commands

### View Dashboard
```powershell
cd c:\Users\venka\Documents\rtl-gen-aii
start validation/run_001/visualizations/dashboard.html
```

### Or open any image directly
```powershell
# Open placement image
start validation/run_001/visualizations/04_placement.png

# Open all images in default viewer
Get-ChildItem validation/run_001/visualizations/*.png | % { start $_ }
```

### Programmatically access visualizations
```python
from pathlib import Path

viz_dir = Path('validation/run_001/visualizations')

# List all visualizations
print("Generated visualizations:")
for img in sorted(viz_dir.glob('*.png')):
    size = img.stat().st_size / 1024  # KB
    print(f"  ✓ {img.name:30} {size:6.1f} KB")

# Open dashboard
import webbrowser
dashboard = str(viz_dir / 'dashboard.html')
webbrowser.open(dashboard)
```

---

## 🛠️ Free Software Used

| Tool | License | Purpose |
|------|---------|---------|
| **Matplotlib** | BSD | 2D plotting, image generation |
| **NumPy** | BSD | Numerical operations |
| **Python** | PSF | Programming language |
| **HTML5/CSS3** | Standard | Dashboard interface |
| **JavaScript** | Standard | Interactive navigation |

**Total Cost**: $0 ✨  
**Quality**: Professional-grade  
**Speed**: Generates in <5 seconds  

---

## 📊 Visualization Features

### DEF File Parsing
- ✅ Reads DESIGN name, UNITS, DIEAREA
- ✅ Extracts COMPONENTS (cells) with positions
- ✅ Parses NETS for interconnection info
- ✅ Handles coordinate format: `( x y )`

### Verilog Analysis
- ✅ Module name extraction
- ✅ Port counting: input, output, inout
- ✅ Logic gate statistics: AND, OR, XOR, NOT, etc.
- ✅ Netlist complexity analysis

### 2D Rendering
- ✅ Color-coded cell visualization
- ✅ Coordinate-based positioning
- ✅ Net connection lines
- ✅ Multiple views per stage

### Interactive Dashboard
- ✅ HTML5-based (works offline)
- ✅ CSS3 styling (professional look)
- ✅ JavaScript navigation (instant switching)
- ✅ Responsive design (desktop/tablet)

---

## 🎬 Generate New Visualizations

After running a new pipeline, automatically generate visualizations:

### Method 1: Python Script
```python
from python.pipeline_visualizer import PipelineVisualizer, VisualizationConfig
from pathlib import Path

# Generate for existing run
visualizer = PipelineVisualizer(Path("validation/run_001"))
results = visualizer.visualize_all()
```

### Method 2: Command Line
```bash
python python/pipeline_visualizer.py validation/run_001
```

### Method 3: Auto-Integration (Recommended)
```python
from python.pipeline_visualizer_integration import integrate_visualizer_with_pipeline

# After pipeline completes
on_complete = integrate_visualizer_with_pipeline()
on_complete(Path("validation/run_001"))
```

---

## 📋 Troubleshooting

### Dashboard won't open
1. Check file exists: `validation/run_001/visualizations/dashboard.html`
2. Try opening directly: 
   ```powershell
   notepad validation/run_001/visualizations/dashboard.html
   ```
3. Copy URL to browser: `file:///c:/Users/venka/Documents/rtl-gen-aii/validation/run_001/visualizations/dashboard.html`

### Images look wrong
1. Check matplotlib installed: `pip install matplotlib`
2. Verify DEF files exist: `validation/run_001/*/` - should have `.def` files
3. Check file permissions: Should be readable

### Visualization generation fails
1. Ensure Python 3.7+: `python --version`
2. Install dependencies: `pip install matplotlib numpy`
3. Check storage: Need ~1MB free space
4. Try manual generation: `python python/pipeline_visualizer.py <run_dir>`

---

## 🎓 Learning Resources

### Understanding the Visualizations

1. **Placement Visualization**: Shows physical cell layout
   - X/Y coordinates from DEF file
   - Color indicates different cells
   - Useful for checking: density, distribution, fragmentation

2. **Routing Visualization**: Shows interconnections
   - Red lines = net connections
   - Shows which cells are closest
   - Useful for checking: net density, routing bottlenecks

3. **CTS Visualization**: Shows clock distribution
   - Orange = clock buffers (added by CTS tool)
   - Blue = original design cells
   - Useful for checking: clock tree balance, power distribution

4. **GDS Visualization**: Tape-out readiness
   - Shows file format validity
   - Indicates binary geometry records
   - Useful for checking: fabrication readiness

---

## 💡 Tips

✨ **Dashboard is best viewed in Chrome/Firefox for full styling**

📱 **Mobile-friendly**: Can view on phone but small images

🔄 **Regenerate anytime**: Running visualizer multiple times is safe

🎨 **Customize appearance**: Edit pipeline_visualizer.py to change colors/sizes

📊 **Use for presentations**: PNG images are perfect for slides

---

## 📞 Questions?

**See full documentation**: [VISUALIZATION_GUIDE.md](VISUALIZATION_GUIDE.md)

**For pipeline issues**: Check validation logs in `validation/run_001/*/`

**For visualization issues**: Check matplotlib installation

---

## ✅ Checklist

- [x] Visualizations generated ✓
- [x] Dashboard created ✓
- [x] All PNG images created ✓
- [x] Free software only (no KLayout needed!)
- [x] Works on Windows, Linux, Mac
- [x] Fast generation (<5 seconds)
- [x] Professional appearance
- [x] Fully documented

---

**🎉 You now have professional 2D layout visualizations for your RTL-to-GDS pipeline!**

Start by opening: `validation/run_001/visualizations/dashboard.html` in your browser.

---

**Version**: 1.0  
**Date**: March 30, 2026  
**License**: MIT (Free to use and modify)
