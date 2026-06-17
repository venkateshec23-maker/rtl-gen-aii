# API Reference

## Core Modules

### `guaranteed_flow.generate_guaranteed_gds(description, design_name)`

Main entry point for RTL generation and synthesis pipeline.

**Parameters:**
- `description` (str): Natural language design description
- `design_name` (str): Module name for the generated Verilog

**Returns:**
```python
{
    "status": "SUCCESS",
    "gds_size_kb": 241.8,
    "tapeout_ready": True,
    "steps": {
        "qor": {
            "fmax_mhz": 259.1,
            "total_mw": 0.5,
            "hold_slack_ns": 0.78,
            "utilization_pct": 45.0
        }
    }
}
```

### `conversational_rtl.generate_initial_design(description, module_name, session)`

Generate the first version of a design in a conversational session.

**Parameters:**
- `description` (str): Design description
- `module_name` (str): Verilog module name
- `session` (ConversationalSession): Session object

**Returns:**
- `(bool, str)`: (success, message)

### `conversational_rtl.apply_modification(user_request, session)`

Apply a natural language modification to the current design.

**Parameters:**
- `user_request` (str): Modification request
- `session` (ConversationalSession): Session object

**Returns:**
- `(bool, str)`: (success, message with diff)

### `rag_engine.retrieve(description, top_k=3)`

Retrieve relevant example designs from the built-in library.

**Parameters:**
- `description` (str): Query description
- `top_k` (int): Number of examples to return

**Returns:**
- `List[Dict]`: List of example dictionaries with `id`, `keywords`, `desc`, `verilog`

### `rag_engine.build_rag_prompt(description, base_prompt)`

Enhance a prompt with retrieved examples.

**Parameters:**
- `description` (str): User's design request
- `base_prompt` (str): Original LLM prompt

**Returns:**
- `str`: Enhanced prompt with reference examples

### `qor_engine.build_qor_report(design_name, run_dir, work_dir, metrics, docker, period_ns)`

Build a complete Quality-of-Results report.

**Parameters:**
- `design_name` (str): Design name
- `run_dir` (Path): Path to the run directory
- `work_dir` (Path): Path to OpenLane workspace
- `metrics` (dict): Existing metrics from full_flow
- `docker` (DockerManager): Docker manager instance
- `period_ns` (float): Clock period in nanoseconds

**Returns:**
- `QoRReport`: QoR report object with timing, power, area, DRC, LVS

## Data Classes

### `ConversationalSession`

```python
@dataclass
class ConversationalSession:
    session_id: str
    design_name: str
    versions: List[DesignVersion]
    messages: List[Dict]
```

### `DesignVersion`

```python
@dataclass
class DesignVersion:
    version: int
    timestamp: str
    user_request: str
    rtl_code: str
    cell_count: Optional[int]
    area_um2: Optional[float]
    fmax_mhz: Optional[float]
    syntax_ok: bool
    synth_ok: bool
```

## Streamlit Components

### `render_conversational_rtl_streamlit()`

Renders the conversational designer UI in Streamlit.

### `render_qor_table(results_dir, design_name)`

Renders the QoR summary table in Streamlit.

### `show_signoff()`

Renders the full sign-off dashboard with DRC, LVS, timing, power.
