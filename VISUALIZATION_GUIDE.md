# Pipeline Visualization Guide

## 📊 Where to Find Generated Images

All pipeline visualizations are automatically generated in:
```
validation/run_001/visualizations/
```

### Generated Files

| File | Description |
|------|-------------|
| **02_synthesis_report.png** | Logic gate distribution, port analysis, synthesis statistics |
| **03_floorplan.png** | Core area definition, die boundary, chip floorplan |
| **04_placement.png** | Cell placement visualization showing all placed cells (color-coded) |
| **05_cts.png** | Clock Tree Synthesis - CTS cells vs regular cells distribution |
| **06_routing.png** | Routing visualization showing nets and interconnections |
| **07_gds.png** | GDSII output file information and geometry statistics |
| **dashboard.html** | **⭐ Interactive HTML dashboard** - view all visualizations together |

---

## 🚀 How to View Visualizations

### Option 1: Interactive HTML Dashboard (Recommended)

🌐 **Open in browser:**
```bash
# Windows
start validation/run_001/visualizations/dashboard.html

# Linux/Mac
open validation/run_001/visualizations/dashboard.html
```

**Features:**
- 📱 Interactive stage navigation (buttons for each stage)
- 🎨 Beautiful gradient UI with professional styling
- 🔄 Click stage buttons to view detailed visualizations
- 📊 Pipeline overview with all stages
- 🎬 Smooth animations and transitions

### Option 2: Individual PNG Images

View PNG images directly with any image viewer:
- **Windows Explorer**: Navigate to folder and open images
- **Preview**: Double-click .png file
- **Python**: 
  ```python
  from PIL import Image
  img = Image.open('validation/run_001/visualizations/04_placement.png')
  img.show()
  ```

### Option 3: Programmatic Access

```python
from pathlib import Path

viz_dir = Path('validation/run_001/visualizations')

# List all visualizations
for image in sorted(viz_dir.glob('*.png')):
    print(f"✓ {image.name}")

# Access specific visualization
placement_img = viz_dir / '04_placement.png'
print(f"Placement image size: {placement_img.stat().st_size} bytes")
```

---

## 📈 What Each Visualization Shows

### 1. RTL Schematic (01_rtl_schematic.png)
- **Module ports diagram**: Input/Output connections
- **Logic gates distribution**: Types and counts
- **Shows**: Design entry point, module structure

### 2. Synthesis Report (02_synthesis_report.png)
- **Gate statistics**: AND, OR, XOR, NOT, etc. counts
- **Port summary**: Input/Output/Inout ports
- **Key metrics**: Total gates, module name

### 3. Floorplan (03_floorplan.png)
- **Die area**: Physical chip boundary
- **Core region**: Safe routing area
- **Aspect ratio**: X/Y dimensions

### 4. Cell Placement (04_placement.png)
- **Cell distribution**: Color-coded cells
- **Density visualization**: Cell concentration
- **Total cells**: Count and coordinates
- **Net count**: Interconnection information

### 5. Clock Tree Synthesis (05_cts.png)
- **CTS cells**: Highlighted in orange
- **Regular cells**: Shown in light blue
- **Distribution**: Percentage of each type
- **Clock statistics**: Net counts, cell ratios

### 6. Routing (06_routing.png)
- **Net connections**: Red lines showing routing
- **Cell positions**: All routed cells
- **Interconnect density**: Visual net distribution
- **Route complexity**: Net count and connections

### 7. GDS Output (07_gds.png)
- **GDSII validity**: Format verification
- **File size**: Final stream file size
- **Geometry**: Boundary, path, and text record counts
- **Fabrication ready**: Confirms tape-out preparation

### 8. Dashboard (dashboard.html)
- **All stages in one view**: Switch between visualizations
- **Navigation panel**: Stage selection buttons
- **Pipeline overview**: Summary of all stages
- **Modern UI**: Responsive, interactive, beautiful

---

## 🎯 Integration with Pipeline

Visualizations are automatically generated after each complete pipeline run:

```python
from python.full_flow import RTLGenAI
from python.pipeline_visualizer import PipelineVisualizer, VisualizationConfig
from pathlib import Path

# Run pipeline
client = RTLGenAI(config, output_dir)
result = client.run_flow()

# Auto-generate visualizations (integrated)
visualizer = PipelineVisualizer(
    run_dir=Path("outputs/runs/adder_8bit"),
    config=VisualizationConfig(
        output_dir=Path("outputs/runs/adder_8bit/visualizations"),
        dpi=150
    )
)
results = visualizer.visualize_all()
print(f"Dashboard: {results['dashboard']}")
```

---

## 🛠️ Manual Visualization Generation

Generate visualizations for existing runs:

```bash
cd c:\Users\venka\Documents\rtl-gen-aii

# Generate visualizations
python python/pipeline_visualizer.py validation/run_001

# Or programmatically:
python -c "
from python.pipeline_visualizer import PipelineVisualizer, VisualizationConfig
from pathlib import Path

viz = PipelineVisualizer(Path('validation/run_001'))
results = viz.visualize_all()
"
```

---

## 📊 Visualization Technologies Used

### Free, Open-Source Tools

| Tool | Purpose |
|------|---------|
| **Matplotlib** | Core 2D plotting, image generation (PNG, SVG) |
| **NumPy** | Numerical operations, color mapping |
| **HTML5 + CSS3** | Interactive dashboard, styling |
| **JavaScript** | Stage navigation, button interactions |

### Why These Tools?

✅ **100% Free**: No commercial licenses required  
✅ **Lightweight**: No heavy dependencies like KLayout  
✅ **Fast**: Generates images in seconds  
✅ **Cross-platform**: Windows, Linux, Mac support  
✅ **Beautiful**: Professional-grade visualizations  
✅ **Scalable**: Works with small and large designs  

---

## 🎨 Image Specifications

All images are generated with:
- **Resolution**: 150 DPI (print-quality)
- **Format**: PNG (lossless compression)
- **Size**: ~40-70 KB per image
- **Dimensions**: 1400×1000 pixels (14×10 pixels per inch)
- **Fonts**: High-contrast, readable at any size

---

## 📱 Dashboard Features

### Navigation
- **Stage buttons**: Quick jump to any stage
- **Overview tab**: Pipeline summary with all stages
- **Back navigation**: Click buttons to switch views

### Design Elements
- **Gradient background**: Purple to indigo gradient
- **Color-coded sections**: Different colors for different stages
- **Responsive layout**: Adapts to screen size
- **Modern styling**: Professional appearance with shadows and effects

### Interactive Elements
- **Hover effects**: Buttons highlight on mouseover
- **Click activation**: Smooth transitions between stages
- **Animated reveals**: Fade-in animations for content
- **Live timestamp**: Shows when dashboard was generated

---

## 🔍 Advanced Usage

### Custom Visualization Configuration

```python
from python.pipeline_visualizer import PipelineVisualizer, VisualizationConfig
from pathlib import Path

# Create custom config
config = VisualizationConfig(
    output_dir=Path("my_visualizations"),
    dpi=300,  # Higher resolution
    figure_size=(18, 12),  # Larger images
    show_grid=True,
    show_labels=True,
    generate_html=True,
    generate_png=True,
    interactive_mode=True
)

# Generate with custom config
visualizer = PipelineVisualizer(Path("validation/run_001"), config)
results = visualizer.visualize_all()
```

### Batch Processing Multiple Runs

```python
from pathlib import Path
from python.pipeline_visualizer import PipelineVisualizer, VisualizationConfig

# Process multiple runs
for run_dir in Path("validation").glob("run_*"):
    config = VisualizationConfig(output_dir=run_dir / "visualizations")
    visualizer = PipelineVisualizer(run_dir, config)
    visualizer.visualize_all()
    print(f"✓ Generated visualizations for {run_dir.name}")
```

### Extracting Specific Data

```python
from python.pipeline_visualizer import DEFParser, VerilogParser
from pathlib import Path

# Parse DEF files
placement_def = Path("validation/run_001/04_placement/placed.def")
parser = DEFParser(placement_def)

print(f"Design: {parser.design_name}")
print(f"Cells: {len(parser.components)}")
print(f"Nets: {len(parser.nets)}")
print(f"Die area: {parser.die_area}")

# Parse Verilog
rtl_file = Path("validation/run_001/01_rtl/design.v")
verilog = VerilogParser(rtl_file)
print(f"Inputs: {verilog.ports['input']}")
print(f"Outputs: {verilog.ports['output']}")
print(f"Gates: {verilog.logic_gates}")
```

---

## ✨ Tips & Tricks

### 1. Batch Open All Images
```powershell
# Windows - Open all PNG files at once
Get-ChildItem validation/run_001/visualizations/*.png | % { start $_ }
```

### 2. Convert to PDF
```powershell
# Using ImageMagick (if installed)
magick convert @(Get-ChildItem *.png) output.pdf
```

### 3. Create Slideshow
```python
import webbrowser
webbrowser.open('validation/run_001/visualizations/dashboard.html')
```

### 4. Export to Different Formats
```python
# Matplotlib supports: PNG, PDF, SVG, EPS, etc.
# Edit pipeline_visualizer.py line: 
# plt.savefig(output_path, format='pdf', dpi=300)
```

---

## 📞 Support

**Questions or issues with visualizations?**

1. Check that files exist in: `validation/run_001/visualizations/`
2. Verify Python version: `python --version` (3.8+)
3. Ensure dependencies: `pip install matplotlib numpy`
4. Check run completion: Look for successful pipeline completion logs

---

**Generated**: 2026-03-30  
**Visualization System**: RTL-Gen AI Pipeline Visualizer v1.0  
**Free Software**: 100% open-source, MIT licensed
