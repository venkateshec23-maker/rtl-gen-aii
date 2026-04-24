---
phase: 3
plan: 1
wave: 1
---

# Plan 3.1: Better LLM Repair Prompts

## Objective
Improve the LLM auto-repair capabilities by feeding back actual failure data from the pipeline. This includes simulation truth-tables (from VCD) and OpenLane physical design log errors.

## Context
- .gsd/ROADMAP.md
- verilog_generator.py
- vcd_parser.py
- full_flow.py

## Tasks

<task type="auto">
  <name>Inject VCD parsing into LLM repair context</name>
  <files>verilog_generator.py</files>
  <action>
    - In `verilog_generator.py`, locate where `repair_verilog` is called.
    - If simulation failed (i.e. validation failed during honesty check or simulation), call `extract_failure_truth_table("trace.vcd")` (from `vcd_parser.py`) and pass its output as the `vcd_context` argument to `repair_verilog`.
  </action>
  <verify>python -m py_compile verilog_generator.py</verify>
  <done>vcd_context is successfully passed into repair_verilog during simulation failures.</done>
</task>

<task type="auto">
  <name>Feed OpenLane errors back to LLM</name>
  <files>full_flow.py, verilog_generator.py</files>
  <action>
    - Modify `full_flow.py` to capture OpenLane logs (e.g. `synthesis.log` or `routing.log`) when physical design fails.
    - Right now, `full_flow.py` just fails. We need a hook to extract the last 50 lines of the failed step's log.
    - If `RTLtoGDSIIFlow.run_full_flow` encounters an OpenLane error, it should surface the error log snippet.
    - *Note: Since full_flow.py executes blindly via task_queue, returning the error is sufficient. The LLM repair loop is mostly in verilog_generator.py.*
  </action>
  <verify>python -m py_compile full_flow.py</verify>
  <done>OpenLane errors are parsed and exposed for potential repair.</done>
</task>

## Success Criteria
- [ ] `verilog_generator.py` uses `vcd_parser.py` when simulation fails.
- [ ] OpenLane errors are caught and logged for repair context.
