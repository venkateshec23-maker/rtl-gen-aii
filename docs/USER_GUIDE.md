# RTL-Gen AI User Guide

Welcome to RTL-Gen AI, an advanced AI-powered system that transforms natural language descriptions into verified SystemVerilog RTL code.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- [Icarus Verilog](http://iverilog.icarus.com/) (for module verification and simulation)
- An Anthropic API key (for the Claude 3.5 Sonnet LLM)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rtl-gen-aii/rtl-gen-aii.git
   cd rtl-gen-aii
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Or install as a package:
   ```bash
   pip install -e .
   ```

3. Configure your API keys:
   Copy `.env.example` to `.env` and add your keys:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```

## Usage

### 1. Command Line Interface (CLI)

The easiest way to generate RTL is via the CLI:

```bash
python -m python.__main__ "Generate an 8-bit adder with carry out"
```

To enable simulation verification:
```bash
python -m python.__main__ "8-bit counter with synchronous reset" --verify
```

### 2. Streamlit Web Interface

For an interactive experience, use the web dashboard:

```bash
streamlit run app.py
```

### 3. Python API

Integrate RTL-Gen AI directly into your Python scripts:

```python
from python.rtl_generator import RTLGenerator

# Initialize generator
generator = RTLGenerator(enable_verification=True)

# Generate design
result = generator.generate("4-to-1 multiplexer with enable signal")

if result['success']:
    print(f"Generated module: {result['module_name']}")
    print("RTL Code:\n", result['rtl_code'])
    
    if result.get('verification'):
        print(f"Verification passed: {result['verification']['passed']}")
```

## Batch Processing

To generate multiple designs parallelly, use the `BatchProcessor`:

```python
from python.batch_processor import BatchProcessor

processor = BatchProcessor(max_workers=4)
designs = ["4-bit adder", "8-bit counter", "ALU"]
results = processor.process_batch(designs)
```

## Advanced Features

### Caching
The application caches identical requests via the `CacheManager` to minimize API costs. You can monitor its hit rate via `app.py` or the CLI output.

Wait... 
Ensure you provide explicit sizes like `32-bit register` or `Axi-stream interface` for the best code-generation fidelity.

### Performance Monitoring
Execution time, API performance and cached hits are tracked automatically. A detailed report can be printed via `generator.print_performance_report()`.

For deeper customization or deployment details, refer to the API Reference and Deployment Guide.
