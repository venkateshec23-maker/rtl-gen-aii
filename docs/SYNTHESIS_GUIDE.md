# Synthesis Integration Guide

## Overview
RTL-Gen AI can synthesize your Verilog RTL code to gate-level netlists using Yosys open-source synthesis tool. This enables:

- **Area estimation** - Logic cell counts and utilization
- **Power estimation** - Dynamic power consumption
- **Frequency estimation** - Maximum clock frequency
- **Netlist generation** - Gate-level Verilog
- **Technology mapping** - ASIC or FPGA targets

## Quick Start

### 1. Install Yosys (Optional)

For full synthesis capabilities:
```bash
# Ubuntu/Debian
sudo apt-get install yosys

# MacOS
brew install yosys

# Windows
# Download from: https://github.com/YosysHQ/yosys/releases
```

### 2. Generate RTL
```bash
streamlit run app.py
# Enter design description
# Click Generate
```

### 3. Run Synthesis
- Navigate to "Synthesis" tab
- Select target technology (ASIC/FPGA)
- Click "Run Synthesis"
- View results and metrics

### 4. Analyze Results

The synthesis report includes:
- **Area** - Total cell area or LUT count
- **Power** - Estimated power consumption
- **Frequency** - Maximum clock frequency
- **Cell distribution** - Breakdown by cell type
- **Netlist** - Gate-level Verilog code

## Understanding Synthesis Results

### ASIC Technology
- **Cells**: AND, OR, NAND, NOR, XOR, DFF, etc.
- **Area unit**: µm² (micrometers squared)
- **Power unit**: µW/MHz (microwatts per MHz)

### FPGA Technology
- **Cells**: LUTs, FFs, DSPs, BRAMs, IOs
- **Area unit**: LUTs (Look-Up Tables)
- **Power unit**: mW (milliwatts)

### Key Metrics

| Metric | ASIC | FPGA | Interpretation |
|--------|------|------|----------------|
| Area | µm² | LUTs | Smaller is better |
| Power | µW/MHz | mW | Lower is better |
| Frequency | MHz | MHz | Higher is better |
| Cell Count | # | # | Design complexity |

## Mock Mode (No Yosys)

If Yosys is not installed, the system automatically falls back to **mock synthesis**:

- **Estimates** area/power/frequency based on RTL complexity
- **Generates** representative gate-level netlist
- **Provides** realistic metrics for evaluation
- **No installation required** - works out of the box

## Advanced Features

### Design Comparison
Compare multiple designs:
```python
from python.synthesis_engine import SynthesisEngine

synth = SynthesisEngine()
designs = [rtl1, rtl2, rtl3]
labels = ["Adder", "Counter", "ALU"]
comparison = synth.compare_synthesis(designs, labels)

print(f"Area: {comparison['area']}")
print(f"Power: {comparison['power']}")
print(f"Frequency: {comparison['frequency']}")
```

### Graph Visualization
Generate DOT graphs of design structure:
```python
dot_graph = synth.generate_dot_graph(rtl_code)
# Save to file and view with Graphviz
```

### Custom Technology Libraries
```python
synth = SynthesisEngine(tech_library='/path/to/my_cells.lib')
```

## Troubleshooting

### Yosys Not Found
- Install Yosys or use mock mode (automatic)
- Mock mode provides reasonable estimates

### Synthesis Takes Too Long
- Designs under 1000 lines synthesize in < 1 minute
- Use mock mode for very large designs

### Strange Area Numbers
- Mock mode estimates are approximations
- Install Yosys for accurate numbers

### Can't Open Netlist
- Check work directory permissions
- Output saved to `outputs/synthesis/`

## Next Steps
- Use netlist for place-and-route
- Run static timing analysis
- Generate layout (ASIC) or bitstream (FPGA)

For more help, see:
- `docs/API_REFERENCE.md`
- `tests/test_synthesis_engine.py`
