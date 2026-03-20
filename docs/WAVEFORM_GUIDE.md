# Waveform Generation Guide

## Overview
RTL-Gen AI can generate VCD (Value Change Dump) waveforms from your Verilog testbenches, allowing you to visualize signal behavior over time.

## Quick Start

### 1. Generate RTL Code
```bash
streamlit run app.py
# Enter: "Create 8-bit counter"
# Click Generate
```

### 2. Generate Waveform
- Navigate to "Waveforms" tab
- Click "Generate VCD Waveform"
- View metrics and download

### 3. View Waveform

#### Option A: GTKWave (Recommended)
```bash
# Install GTKWave
sudo apt-get install gtkwave  # Linux
brew install gtkwave           # Mac
# Download from gtkwave.sourceforge.net (Windows)

# View waveform
gtkwave outputs/design_tb.gtkw
```

#### Option B: Online Viewer
1. Go to https://wavedrom.com/
2. Upload your .vcd file
3. View immediately

#### Option C: Python Viewer
```python
from python.waveform_generator import WaveformGenerator

gen = WaveformGenerator()
gen.view_waveform('outputs/design_tb.vcd')
```

## Understanding VCD Files

### What's in a VCD?
```
$timescale 1ns/1ps $end    # Time unit
$scope module testbench $end # Scope
$var wire 1 ! clk $end       # Signal definition
#0                           # Time 0
b0 !                         # clk = 0
#50                          # Time 50ns
b1 !                         # clk = 1
```

### Reading Waveforms
- **X-axis**: Time (ns)
- **Y-axis**: Signal values (0/1)
- **Rising edges**: Signal transitions

## Troubleshooting

### No VCD Generated
- Check if testbench has `$finish`
- Ensure signals are declared
- Try mock mode if no simulator

### Can't Open with GTKWave
- Install GTKWave first
- Use .gtkw config file
- Try online viewer as fallback

### Waveform Too Short
- Modify testbench duration
- Look for `#<time> $finish`
- Increase in testbench code

## Advanced Usage

### Custom Testbenches
```verilog
`timescale 1ns/1ps
module custom_tb;
    reg clk;
    initial begin
        $dumpfile("custom.vcd");  // Specify output
        $dumpvars(0, custom_tb);   // Dump all vars
        #1000 $finish;              // Run longer
    end
endmodule
```

### Batch Generation
```python
from python.waveform_generator import WaveformGenerator
from pathlib import Path

gen = WaveformGenerator()
for tb_file in Path('testbenches').glob('*.v'):
    result = gen.generate_from_testbench(
        tb_file.read_text(),
        tb_file.stem
    )
    print(f"Generated: {result['vcd_file']}")
```

## Next Steps
- Try synthesis with Yosys
- Add timing analysis
- Generate testbenches automatically

For more help, check:
- `docs/API_REFERENCE.md`
- `tests/test_waveform_generator.py`
