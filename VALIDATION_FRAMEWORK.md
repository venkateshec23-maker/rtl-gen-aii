# Pipeline Validation Framework

## Overview

The **Pipeline Validation Framework** (`python/validate_pipeline.py`) provides comprehensive validation for the RTL → GDSII physical design flow. It validates each of the 9 pipeline stages independently, performs preflight checks, and generates detailed diagnostic reports.

## Features

✅ **9 Independent Stage Validators**
- RTL generation/input validation
- Yosys synthesis validation
- Floorplanning validation
- Placement validation
- Clock tree synthesis (CTS) validation
- Global routing validation
- Detailed routing validation
- GDS generation validation
- DRC/LVS signoff validation

✅ **Preflight Checks**
- Docker installation verification
- Docker daemon readiness check
- PDK (Process Design Kit) availability validation
- Required dependencies detection

✅ **Comprehensive Diagnostics**
- Detailed error messages with remediation hints
- Docker container exit codes and logs
- Intermediate file verification
- Performance profiling per stage
- Warning categorization (non-blocking vs. critical)

✅ **Report Generation**
- **JSON reports** for programmatic analysis
- **HTML reports** for human-friendly visualization
- Summary console output with status indicators
- Timestamped report files for archival

✅ **Configurable Strictness**
- Quick validation mode (skip optional checks)
- Full PDK requirement toggle
- Custom timeout per stage
- Selective check control

## Installation

No additional dependencies required beyond the main RTL-Gen-AII environment.

```bash
# Verify the module is importable
python -c "from python.validate_pipeline import PipelineValidator; print('✓ OK')"
```

## Quick Start

### CLI Usage

**Validate a design:**

```bash
python python/validate_pipeline.py adder_8bit.v adder_8bit \
  --output-dir ./validate_results
```

**Skip Docker/PDK checks (for quick validation):**

```bash
python python/validate_pipeline.py adder_8bit.v adder_8bit \
  --skip-docker-check --skip-pdk-check --quick
```

**Generate only JSON report (for CI/CD pipelines):**

```bash
python python/validate_pipeline.py design.v top_module \
  --json --skip-docker-check
```

### Python API

**Basic validation:**

```python
from python.validate_pipeline import PipelineValidator, ValidationConfig

validator = PipelineValidator()
report = validator.validate_full_pipeline(
    rtl_path="adder_8bit.v",
    top_module="adder_8bit",
    output_dir="./results",
)

print(report.summary())
if report.all_passed:
    print("✓ Pipeline ready for synthesis!")
else:
    print(f"Failures:\n{report.failure_summary()}")
```

**Custom configuration:**

```python
config = ValidationConfig(
    check_docker=True,
    check_pdk=True,
    require_pdk_full=True,          # Require complete sky130 PDK
    timeout_per_stage=600,          # 10 minutes per stage
    quick_mode=False,               # Run all checks
    generate_html_report=True,
    generate_json_report=True,
)

validator = PipelineValidator(config)
report = validator.validate_full_pipeline(...)
```

**Check specific conditions:**

```python
# Check if all stages passed
if report.all_passed:
    print("Ready for tape-out!")

# Check for critical failures
if report.any_critical:
    print("CRITICAL: Cannot proceed")
    sys.exit(2)

# Access individual stage results
for stage_name, stage_result in report.stages.items():
    print(f"{stage_name}: {stage_result.level.value}")
    print(f"  Message: {stage_result.message}")
    print(f"  Duration: {stage_result.duration_sec:.2f}s")
```

## CLI Reference

```
usage: validate_pipeline.py [-h] [--output-dir OUTPUT_DIR]
                            [--skip-docker-check] [--skip-pdk-check]
                            [--quick] [--html] [--json]
                            rtl_path top_module

Positional Arguments:
  rtl_path              Path to RTL .v file (required)
  top_module            Top module name (required)

Optional Arguments:
  --output-dir DIR      Working/output directory (default: current dir)
  --skip-docker-check   Skip Docker readiness validation
  --skip-pdk-check      Skip PDK validation (will warn if not found)
  --quick               Skip optional checks for faster validation
  --html                Generate HTML report (default: on)
  --json                Generate JSON report (default: on)
  -h, --help            Show this help message

Exit Codes:
  0   = All validations passed
  1   = One or more non-critical failures
  2   = Critical stage failure (cannot proceed)
  3   = Configuration/environment error
```

## Validation Levels

The framework uses a 4-level severity model:

| Level | Symbol | Meaning | Blocks Flow? |
|-------|--------|---------|--------------|
| **PASS** | ✓ | Validation succeeded | No |
| **WARNING** | ⚠ | Non-blocking issue (e.g., PDK not found) | No |
| **ERROR** | ✗ | Stage failed but flow can continue | No |
| **CRITICAL** | ⚠️ | Stage failed, pipeline must stop | **Yes** |

## Output Reports

### JSON Report

Saved as `validation_YYYYMMDD_HHMMSS.json`

```json
{
  "rtl": "adder_8bit.v",
  "module": "adder_8bit",
  "output_dir": "./results",
  "timestamp": "2026-03-29T20:20:38",
  "duration_seconds": 15.34,
  "all_passed": true,
  "stages": {
    "rtl_generation": {
      "level": "PASS",
      "message": "RTL file valid (2048 bytes)",
      "duration": 0.01
    },
    "synthesis": {
      "level": "PASS",
      "message": "Netlist generated successfully",
      "duration": 8.23
    }
  }
}
```

### HTML Report

Saved as `validation_YYYYMMDD_HHMMSS.html`

Human-friendly visualization with:
- Design metadata (RTL file, module name, timestamp)
- Color-coded stage results (green=pass, orange=warning, red=error)
- Duration per stage
- Summary pass/fail status
- Responsive design (mobile-friendly)

### Console Output

Example:

```
╔════════════════════════════════════════════════════════════╗
║  PIPELINE VALIDATION REPORT                               ║
╚════════════════════════════════════════════════════════════╝
RTL:           adder_8bit.v
Module:        adder_8bit
Output dir:    ./results
Timestamp:     2026-03-29T20:20:38.982568
Duration:      15.3s

Stage Results:
  [✓] rtl_generation                 RTL file valid (2048 bytes)
  [✓] synthesis                      Netlist generated (sky130 cells)
  [✓] floorplanning                  Floorplan dimension 500×500um
  [✓] placement                      Cell placement converged
  [✓] clock_tree_synthesis           CTS tree built (25ns slack)
  [✓] global_routing                 Routed with 0 shorts
  [✓] detailed_routing               Finished with 3 DRC violations
  [⚠] gds_generation                 GDS size 12.5MB (warning)
  [✓] signoff                        DRC/LVS passed

Status:        ✓ ALL VALIDATIONS PASSED
```

## Environment & Dependencies

### Required

- Python 3.8+
- Docker Desktop (for actual flow execution; validation can run without)

### Optional

- PDK installation in `$PDK_ROOT` (for full validation; not required for basic checks)
- Yosys (required only if running synthesis stage)
- OpenROAD/OpenLane (required only if running physical design stages)

### Configuration

Set environment variables to control validation:

```bash
# Docker configuration
export DOCKER_IMAGE=efabless/openlane:latest
export DOCKER_CONTAINER_TIMEOUT=300

# PDK paths (auto-detected, but can be overridden)
export PDK_ROOT=/path/to/pdk
export PDKPATH=/path/to/pdk
```

## Common Scenarios

### ✓ Scenario 1: Quick Validation Before Synthesis

Check RTL file is valid and Docker is ready:

```bash
python python/validate_pipeline.py input.v my_module \
  --skip-pdk-check --quick
```

### ✓ Scenario 2: Full Pipeline Validation

Run all checks before committing to physical design:

```bash
python python/validate_pipeline.py design.v top_module \
  --output-dir ./validate
# Check reports in ./validate/
```

### ✓ Scenario 3: CI/CD Integration

Generate JSON report for automated pipeline status:

```bash
python python/validate_pipeline.py design.v top_module \
  --skip-docker-check --json
# Check exit code: 0 = pass, 1 = warnings, 2 = critical failure
# Parse JSON for detailed results
```

### ✓ Scenario 4: Diagnostics / Troubleshooting

Run with all checks enabled to identify issues:

```bash
python python/validate_pipeline.py design.v top_module \
  --output-dir ./diagnostics
# Review generated HTML and JSON reports
```

## Architecture

The framework uses a modular design:

```
PipelineValidator (main class)
├── validate_full_pipeline()          ← Entry point
├── Preflight validators
│   ├── _validate_docker()
│   └── _validate_pdk()
├── Input validation
│   └── _validate_input_rtl()
├── Stage validators (9 stages)
│   ├── _validate_synthesis()
│   ├── _validate_floorplanning()
│   ├── _validate_placement()
│   ├── _validate_cts()
│   ├── _validate_global_routing()
│   ├── _validate_detailed_routing()
│   ├── _validate_gds_generation()
│   └── _validate_signoff()
└── Report generators
    ├── _save_json_report()
    └── _save_html_report()
```

## Extending the Framework

### Add a New Stage Validator

```python
def _validate_custom_stage(self, rtl_path, top_module, output_dir):
    """Validate custom stage."""
    # Your validation logic here
    
    if some_error:
        return StageResult(
            stage=StageName.PLACEMENT,  # Use existing enum
            level=ValidationLevel.ERROR,
            message="Error message",
            docker_exit_code=1,
        )
    
    return StageResult(
        stage=StageName.PLACEMENT,
        level=ValidationLevel.PASS,
        message="Validation passed",
    )
```

Then register in `validate_full_pipeline()`:

```python
stages_to_validate = [
    # ... existing stages ...
    (StageName.CUSTOM_STAGE, self._validate_custom_stage),
]
```

### Add Custom Configuration Option

```python
@dataclass
class ValidationConfig:
    # ... existing options ...
    my_new_option: bool = True  # Add new config

class PipelineValidator:
    def _validate_synthesis(self, ...):
        if self.config.my_new_option:
            # Use new config
            pass
```

## Troubleshooting

### "Docker not installed"
**Fix:** Install Docker Desktop for Windows from https://www.docker.com/products/docker-desktop

### "Docker daemon not running"
**Fix:** Start Docker Desktop — right-click system tray → "Start Docker Desktop"

### "PDK not found"
**Fix:** Either:
1. Install volare: `pip install volare && volare enable sky130`
2. Set `PDK_ROOT=C:\pdk` and restart
3. Run with `--skip-pdk-check` (reduced functionality)

### "RTL file contains no module"
**Fix:** Ensure input .v file is valid Verilog with `module` keyword

### "HTML report failed to save"
**Fix:** Ensure output directory has write permissions; use `--skip-html` if needed

## Performance Tips

- Use `--quick` mode for rapid validation (skips optional checks)
- Run `--skip-docker-check` if Docker readiness is already known
- Generate only JSON report for scripting: fewer I/O operations
- Increase `--timeout-per-stage` for resource-constrained systems

## Integration with Full Flow

Use validation in your workflows:

```python
from python.validate_pipeline import PipelineValidator
from python.full_flow import RTLGenAI

# Validate before running full flow
validator = PipelineValidator()
report = validator.validate_full_pipeline(..., output_dir=work_dir)

if report.any_critical:
    print("✗ Validation failed; aborting flow")
    sys.exit(1)

# Proceed with full flow
result = RTLGenAI.run_from_rtl(
    rtl_path=rtl_path,
    top_module=top_module,
    output_dir=work_dir,
)
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-29 | Initial release; 9 stage validators, JSON/HTML reporting, CLI interface |

## Support & Issues

For issues or feature requests:
1. Check the troubleshooting section above
2. Review generated JSON/HTML reports for detailed diagnostics
3. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
4. File an issue with the validation reports (JSON/HTML)

---

**Happy validating!** 🎯
