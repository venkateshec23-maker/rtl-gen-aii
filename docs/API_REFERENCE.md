# API Reference

The RTL-Gen AI system is built with a modular architecture in mind for performance and scalability. This document details the core classes and their respective public APIs.

## `RTLGenerator`

Provides the primary interface for generating, caching, and verifying RTL designs.

**Path:** `python.rtl_generator`

### `__init__(use_mock=False, api_key=None, enable_verification=True, debug=None, enable_monitoring=True)`
- `use_mock` *(bool)*: Bypass the LLM and use mock AI responses (useful for offline testing/low-cost development). Default: `False`.
- `api_key` *(str, optional)*: Override the Anthropic API Key defined in environment settings.
- `enable_verification` *(bool)*: Auto-run HDL testbenches for syntactical and logical verification after code generation. Default: `True`.
- `debug` *(bool, optional)*: Force debug logging.
- `enable_monitoring` *(bool)*: Enable timing and memory tracking.

### `generate(description: str, verify: bool = None) -> Dict`
Parses the user string, extracts module details, asks the LLM for SystemVerilog code, and runs the verification suite.
- **Returns:** Application-defined structure with the generated RTL code and verification success report.

---

## `BatchProcessor`

Facilitates concurrent RTL designs creation to maximize multi-threading performance.

**Path:** `python.batch_processor`

### `__init__(max_workers=4, use_mock=False, enable_verification=True)`

### `process_batch(descriptions: List[str]) -> List[Dict]`
Executes `RTLGenerator.generate()` on a threadpool for all inputs, returning results in correct sequence order.

---

## `QualityChecker`

Analyzes generated RTL code for style issues and syntax correctness to guarantee consistency.

**Path:** `scripts.qa_check`

### `check_code(rtl_code: str, module_name: str) -> Dict`
Runs all internal rules (indentation consistency, code ratio comments, port structure) and calculates a QA score out of 100.

---

## `PerformanceMonitor`

Internal tool tracking resource constraints and time execution profiles.

**Path:** `python.performance_monitor`

### `measure(operation_name: str)`
Yield context manager tracking time deltas and memory allocations dynamically.

### `get_report() -> Dict`
Returns the compiled statistics summary report of tracked metrics.
