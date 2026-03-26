# RTL-Gen AI: RTL to GDSII Chip Design Platform

**Version:** 1.0.0 | **Python:** 3.9+ | **License:** MIT

RTL-Gen AI is a complete hardware design automation platform that bridges the gap between Verilog RTL and fabrication-ready chip layouts. It combines AI-powered code generation with industry-standard EDA tools to create a seamless design-to-silicon workflow.

## Overview

RTL-Gen AI simplifies complex chip design by automating the entire physical design flow. Whether you're working with AI-generated code or custom Verilog, the system handles synthesis, placement, routing, and sign-off verification in a single automated pipeline. The web interface makes it accessible to engineers at all levels, while the production-grade backend ensures professional-quality outputs.

## Key Capabilities

The platform provides:

- **Flexible Input**: Write custom Verilog code directly in the editor, select from pre-built templates, or upload existing designs
- **One-Click Execution**: Run a complete 9-stage RTL-to-GDSII flow from anywhere in the UI
- **Real-time Feedback**: Monitor pipeline progress with detailed stage timings and status updates
- **Professional Outputs**: Generate GDSII files, DEF layouts, Verilog netlists, and sign-off reports
- **Design Validation**: Automated DRC and LVS verification using industry-standard tools (Magic, Netgen)
- **Results Dashboard**: Browse design history, compare metrics, and download all outputs

## Technology Stack

The system is built on proven open-source tools:

- **Synthesis**: Yosys (RTL → gate-level netlist)
- **Physical Design**: OpenROAD (floorplanning, placement, routing)
- **Verification**: Magic (DRC), Netgen (LVS)
- **Process Node**: Sky130A (130nm open-source PDK)
- **Containerization**: Docker (reproducible, portable execution)
- **Frontend**: Streamlit (web-based UI)
- **Backend**: Python 3.9+

## Getting Started

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/rtl-gen-aii/rtl-gen-aii.git
cd rtl-gen-aii
pip install -r requirements.txt
```

### Running the Platform

Start the Streamlit web application:

```bash
streamlit run app.py
```

This launches the platform at `http://localhost:8501`. From here, you can:

1. Select a template (Counter, Adder, Traffic Light) or edit custom Verilog
2. Click "Run Pipeline" to execute all 9 design stages
3. View results in the dashboard with metrics and downloadable files

### Example: Testing with a Template

The platform includes several working examples:

```
Simple Counter: 8-bit counter with reset and enable
8-bit Adder: Full adder with carry propagation
Traffic Light Controller: 4-state FSM with timing control
```

Select any template, optionally modify the code, and run the pipeline to see end-to-end chip generation in under 15 seconds.

## Project Structure

```
rtl-gen-aii/
├── app.py                          # Main Streamlit application
├── pages/                          # Streamlit pages
│   ├── 00_Home.py                  # Platform overview
│   ├── 01_Custom_Design.py         # Code editor and pipeline execution
│   ├── 04_Physical_Design_Flow.py  # Pre-configured design flows
│   ├── 05_Results.py               # Results dashboard
│   └── 06_Workflow.py              # Integration guide
├── python/
│   ├── full_flow.py                # Main orchestrator (RTLGenAI class)
│   ├── docker_manager.py           # Docker lifecycle management
│   ├── synthesis_engine.py         # Yosys integration
│   ├── floorplanner.py             # Floorplanning logic
│   ├── placer.py                   # Placement engine
│   ├── cts_engine.py               # Clock tree synthesis
│   ├── detail_router.py            # Routing engine
│   ├── gds_generator.py            # GDS file generation
│   ├── signoff_checker.py          # DRC/LVS verification
│   └── tapeout_packager.py         # Professional packaging
├── tests/                          # Test suite (533 tests, 100% passing)
├── runs/                           # Generated design outputs
├── Dockerfile                      # Container specification
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Pipeline Stages

The RTL-to-GDSII flow executes in 9 automated stages:

1. **Synthesis** - Converts Verilog RTL to gate-level netlist using Yosys
2. **Floorplanning** - Defines core area, placement boundaries, and I/O rings
3. **Placement** - Positions standard cells for optimal area and timing
4. **Clock Tree Synthesis** - Builds clock distribution network
5. **Global Routing** - Plans interconnect before detailed routing
6. **Detailed Routing** - Creates final metal and via routes
7. **GDS Generation** - Produces layout-to-manufacturing format
8. **Sign-off Verification** - Runs DRC (design rule checks) and LVS (netlist verification)
9. **Tape-out Packaging** - Creates professional deliverables (GDS, netlist, reports)

Each stage produces validated outputs and automatically feeds into the next stage. Total execution time: typically 12-15 seconds per design.

## Web Interface

The Streamlit-based user interface provides seven pages:

- **Home**: Platform overview and quick start guide
- **Custom Design Studio**: Write or edit Verilog, select templates, run pipeline
- **Design History**: Browse previous runs with metrics and timings
- **Documentation**: Guides, API reference, and troubleshooting
- **Physical Design Flow**: Access pre-configured design flows
- **Results Dashboard**: View detailed outputs, download files
- **Workflow Guide**: Integration instructions and best practices

## Command-Line Usage

For automated workflows, run designs programmatically:

```python
from python.full_flow import RTLGenAI, FlowConfig

# Configure the flow
config = FlowConfig(run_drc=True, run_lvs=False)

# Run end-to-end pipeline
result = RTLGenAI.run_from_rtl(
    rtl_path="designs/adder.v",
    top_module="adder_8bit",
    output_dir="runs/adder_run",
    config=config,
    progress=lambda d: print(f"[{d['stage']}] {d['msg']}")
)

# Check results
if result.gds_path:
    print(f"✅ GDS generated: {result.gds_path}")
else:
    print(f"❌ Design failed at: {result.failed_stage}")
```

## Design Examples

### Example 1: Simple Counter

The platform includes a pre-built 8-bit counter template that demonstrates a basic sequential design:

```verilog
module counter (
    input clk, reset, enable,
    output [7:0] count
);
    // Implements a simple 8-bit counter
    // Runs through all 9 pipeline stages in ~13 seconds
    // Generates a valid GDS file
endmodule
```

### Example 2: Traffic Light Controller

A more complex finite state machine example that cycles through red, green, and yellow states:

```verilog
module traffic_controller (
    input clk, reset,
    output reg red, green, yellow
);
    // 4-state FSM with timing control
    // 28-bit timer for realistic cycle times
    // Demonstrates registered outputs and sequential logic
endmodule
```

## System Requirements

Minimum specifications:

- **OS**: Windows, Linux, or macOS
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 20GB for PDK and tool installation
- **Docker**: Required (automatically managed by DockerManager)

The system auto-detects and launches Docker if not already running. All EDA tools execute inside containers for portability.

## Architecture Details

### RTLGenAI Orchestrator

The `RTLGenAI` class serves as the main orchestrator. It manages the entire 9-stage pipeline through the `run_from_rtl()` static method:

- Takes Verilog RTL path and design name as input
- Sequentially executes each stage with error handling
- Collects timing metrics and verification results
- Returns `FlowResult` with all outputs and status

### Docker Integration

The `DockerManager` class handles all Docker operations:

- Auto-starts Docker daemon if needed
- Mounts working directories for stage execution
- Sets up environment variables (PDK_ROOT, STD_CELL_LIBRARY)
- Handles Windows/Linux path translation
- Captures stage logs for debugging

### Verification Pipeline

The `SignoffChecker` class runs post-layout verification:

- Executes Magic for DRC (design rule checks)
- Runs Netgen for LVS (layout vs. schematic)
- Parses tool outputs for violation counts
- Generates professional sign-off reports

## API Reference

For detailed API documentation, see [API_REFERENCE.md](docs/API_REFERENCE.md).

For deployment guidelines, see [DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Testing

The project includes a comprehensive test suite:

```bash
pytest tests/
```

Current status: **533/533 tests passing (100%)**

Tests cover:
- Core pipeline execution
- Docker integration
- Synthesis and routing
- GDS generation
- Sign-off verification
- Integration between stages

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all tests pass
5. Submit a pull request

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

## Community

For questions, issues, or suggestions, please open an issue on GitHub or contact the development team.
