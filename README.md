# RTL-Gen AI: Natural Language to SystemVerilog

![GitHub version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python Support](https://img.shields.io/badge/python-3.9+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

An AI-driven system that accepts a simple, natural language prompt, converts it into structured SystemVerilog RTL, automatically writes and runs a testbench simulation using Icarus Verilog, and assures quality all in one step.

---

## What is RTL-Gen AI?
RTL-Gen AI serves as a powerful Copilot for hardware engineers. Powered by state-of-the-art LLMs (Anthropic Claude 3.5 Sonnet), it parses digital definitions ranging from standard FSMs to complex ALUs, and performs syntax-level verification ensuring immediate validity.

## Core Features
1. **Self-Correcting LLM Loop**: Writes code and testbenches simultaneously.
2. **Robust Verification Pipeline**: Evaluates and compiles output with Icarus Verilog (`iverilog`).
3. **Optimized Caching**: Tracks previously built structures instantly.
4. **Batch Generation**: Speedily runs generation across standard modules via Python ThreadPoolExecutors.
5. **Quality Assurance**: In-built tool parsing styling standards and naming rules.

## Documentation
- See [User Guide](docs/USER_GUIDE.md) for UI & CLI usage.
- See [API Reference](docs/API_REFERENCE.md) for deeper programmatic control.
- See [Deployment](docs/DEPLOYMENT.md) for deployment and distribution guidelines.
- See [Bugs & Known Issues](BUGS.md) for error reporting.

## Installation

```bash
git clone https://github.com/rtl-gen-aii/rtl-gen-aii
cd rtl-gen-aii
pip install -e .
```

## Quick Start
```bash
python -m python.__main__ "Generate an 8-bit D-Flipflop"
```

## Community & Licensing
This repository is open-source under the MIT License. Feel free to open issues or PRs!
