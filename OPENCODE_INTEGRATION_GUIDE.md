# 🤖 OpenCode AI Integration Guide

**Status:** ✅ Integration Complete and Committed

## Overview

OpenCode has been integrated into the RTL-Gen-AII project to enable **natural language to Verilog RTL code generation**. Instead of starting with templates or writing code manually, you can now describe your circuit in plain English and let AI generate the Verilog code.

---

## Installation

### Prerequisites
- Node.js 18+ installed
- npm or equivalent package manager

### Install OpenCode

**Option 1: Using NPM (Recommended)**
```bash
npm install -g opencode-ai@latest
```

**Option 2: Download Desktop App**
Visit [opencode.ai/download](https://opencode.ai/download) and download for your OS:
- Windows: `opencode-desktop-windows-x64.exe`
- macOS: `opencode-desktop-darwin-aarch64.dmg`
- Linux: `.deb`, `.rpm`, or AppImage

**Verify Installation:**
```bash
opencode --version
```

---

## What's New in Your Project

### 1. **New Streamlit Page: AI Code Generation** (Page 3)
- Dedicated UI for AI-powered design generation
- Describe circuits in natural language
- Options to analyze and optimize generated code
- Direct integration with pipeline

**Access:** Click on "🤖 AI Code Generation" in the Streamlit sidebar

### 2. **Enhanced Custom Design Page**
- Sidebar now has three code sources:
  - **Template:** Traditional pre-built designs
  - **AI Generation:** OpenCode natural language generation
  - **Upload File:** Load existing Verilog files

**Usage:** Select "AI Generation (OpenCode)" in the Custom Design sidebar

### 3. **Python Module: OpenCode Integration**
- File: `python/opencode_integration.py`
- Classes and functions for programmatic access:
  - `OpenCodeGenerator` - Main class for all operations
  - `generate_rtl_from_description()` - Quick generation
  - `extract_module_name_from_text()` - Auto-naming

---

## Usage Examples

### Example 1: Generate a 4-bit Counter

**Streamlit Method:**
1. Go to **Custom Design** page
2. Select **AI Generation (OpenCode)** in sidebar
3. Paste this description:
   ```
   Create a 4-bit binary counter with:
   - Clock input (clk)
   - Active-high reset (rst)
   - Enable signal (en)
   - 4-bit output (count)
   ```
4. Click **🚀 Generate Code**
5. Code appears in editor, click **🚀 Run Pipeline**

**Result:** Working RTL code → Synthesis → Physical Design → GDS file

### Example 2: AI Code Generation Page

1. Click **🤖 AI Code Generation** in sidebar
2. Enter description:
   ```
   8-bit shift register with parallel load and serial input
   ```
3. Configure:
   - Module name: `my_shift_reg`
   - Data width: 8 bits
   - Style: behavioral
4. Click **🚀 Generate Verilog**
5. Analyze and optimize if needed
6. Insert into Custom Design page

### Example 3: Direct Python API

```python
from python.opencode_integration import OpenCodeGenerator

# Create generator instance
gen = OpenCodeGenerator()

# Check if available
if not gen.opencode_available:
    print("OpenCode not installed!")
    exit(1)

# Generate RTL
success, code, message = gen.generate_verilog(
    description="8-bit ripple carry adder",
    module_name="adder_8bit",
    width=8,
    style="dataflow"
)

if success:
    print(code)
else:
    print(f"Error: {message}")
```

---

## Language Examples for Descriptions

### Good Descriptions (Specific & Clear)
```
- "Create an 8-bit binary counter with clock, reset, and enable signals"
- "4-to-1 multiplexer for 16-bit wide data inputs with select lines"
- "8-bit magnitude comparator with less-than, equal, and greater-than outputs"
- "16-bit shift register with parallel input, clock, and serial output"
- "3-bit binary to Gray code converter"
```

### Less Ideal (Too Vague)
```
- "Make a counter"  [How many bits? What signals?]
- "Design a processor" [Too complex, too vague]
- "Create logic" [What logic?]
```

---

## Integration with Pipeline

### Flow Diagram
```
Natural Language Description
         ↓
   OpenCode AI
         ↓
  Verilog Code
         ↓
  RTL→GDSII Pipeline
   (Your existing flow)
         ↓
GDS File + Sign-off Reports
```

### Validation Features

The generated code goes through:
1. **Verilog Parsing** - Checks module name extraction
2. **Empty Logic Detection** - Ensures actual implementation exists
3. **Synthesis** - Yosys converts to gate-level netlist
4. **Physical Design** - OpenROAD handles place & route
5. **Sign-off** - Magic DRC verification
6. **Packaging** - Professional tape-out delivery

---

## Available Operations

### Code Generation
```python
# Generate RTL from description
success, code, msg = gen.generate_verilog(
    description="Your circuit description",
    module_name="generated_module",
    width=8,  # Default data width
    style="behavioral"  # behavioral, dataflow, or structural
)
```

### Code Analysis
```python
# Analyze generated code for improvements
success, analysis = gen.analyze_verilog(verilog_code)
# Returns: suggestions, warnings, style improvements
```

### Code Optimization
```python
# Optimize for area and speed
success, optimized_code, msg = gen.optimize_design(verilog_code)
# Returns: improved Verilog code
```

### Template Generation
```python
# Get template for specific design type
template = gen.get_templates_from_ai("counter")
# Returns: ready-to-use template code
```

---

## Design Styles

### Behavioral
- Most intuitive for description
- Uses `always` blocks and assignments
- Best for synthesis
- **Recommended for AI generation**

```verilog
always @(posedge clk)
    counter <= counter + 1;
```

### Dataflow
- Combinational logic
- Uses `assign` statements
- Good for simple circuits

```verilog
assign y = a & b | c & d;
```

### Structural
- Component instantiation
- Uses submodules
- Good for hierarchical designs

```verilog
and_gate gate1 (.a(x), .b(y), .out(z));
```

---

## Troubleshooting

### OpenCode Not Available
**Problem:** "OpenCode not installed" message
**Solution:**
```bash
npm install -g opencode-ai@latest
```
Then restart Streamlit: `Ctrl+R` in browser

### Generation Takes Too Long
**Problem:** Generation hangs or times out
**Solution:**
1. Try simpler description
2. Reduce module size
3. Use specific style (behavioral is fastest)

### Code Won't Synthesize
**Problem:** Generated code causes synthesis errors
**Solution:**
1. Review code in editor for syntax
2. Use **Analyze** button to get suggestions
3. Try **Optimize** to fix issues
4. Modify description to be more specific

### Module Name Mismatch
**Problem:** Module name doesn't match description
**Solution:** Explicitly set module name in the form (Auto-filled from description)

---

## API Key Configuration (Optional)

For premium model access (Claude, GPT-4, etc.):

```bash
# Set your API key
export OPENCODE_API_KEY="your-api-key"

# Or configure in Python
gen = OpenCodeGenerator(api_key="your-api-key")
```

Currently works with:
- Claude (Anthropic)
- OpenAI (GPT-4)
- Google (Gemini)
- Local models (free tier)

---

## Next Steps

1. **Install OpenCode:** `npm install -g opencode-ai@latest`
2. **Test the integration:** Go to Custom Design → AI Generation
3. **Try a simple design:** "8-bit counter with reset"
4. **Run pipeline:** Click "🚀 Run Pipeline"
5. **Check results:** View GDS file and sign-off reports

---

## Features Roadmap

✅ **Implemented:**
- Basic RTL generation from descriptions
- Code analysis and optimization
- Integration with Custom Design page
- Dedicated AI Generation page
- Multi-style support

🔜 **Planned:**
- Batch generation (multiple designs)
- Design templates from OpenCode
- Performance benchmarking
- Constraint-based generation
- Formal verification integration

---

## Resources

- **OpenCode Docs:** https://opencode.ai/docs
- **OpenCode GitHub:** https://github.com/anomalyco/opencode
- **Verilog Guide:** https://www.verilog.com
- **RTL Design Best Practices:** https://www.systemverilog.com

---

## Support

If issues occur:

1. Check OpenCode is installed: `opencode --version`
2. Review Streamlit browser console for errors
3. Check server logs in terminal
4. Try regenerating with simpler description
5. Verify your circuit description is valid English

---

**Integration Complete!** 🎉

Start using OpenCode AI to generate RTL designs today!
