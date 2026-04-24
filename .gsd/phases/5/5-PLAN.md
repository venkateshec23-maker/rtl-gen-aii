---
phase: 5
plan: 1
wave: 1
---

# Plan 5.1: Upload Custom Verilog

## Objective
Allow users to upload their own Verilog RTL and testbenches, bypass the AI generation step, and run the validation/OpenLane pipeline directly.

## Context
- .gsd/ROADMAP.md
- app.py
- verilog_generator.py

## Tasks

<task type="auto">
  <name>Add Custom Verilog UI</name>
  <files>app.py</files>
  <action>
    - Add a "File Uploader" tab or section in the sidebar/main page of `app.py`.
    - Allow uploading two files: `rtl.v` and `testbench.v` (or just one combined file).
    - Provide a "Run Pipeline" button that takes these uploaded files and bypasses the AI generation.
  </action>
  <verify>python -m py_compile app.py</verify>
  <done>UI component for uploading custom Verilog is added.</done>
</task>

<task type="auto">
  <name>Bypass AI and integrate with Pipeline</name>
  <files>app.py, verilog_generator.py</files>
  <action>
    - Ensure uploaded Verilog is passed through `validate_verilog_syntax` and `simulate_with_tool` before adding to `task_queue.py`.
    - If validation passes, enqueue the task in `DesignQueue`.
  </action>
  <verify>python -m py_compile app.py</verify>
  <done>Uploaded Verilog is validated and run through the existing pipeline.</done>
</task>

## Success Criteria
- [ ] Users can upload custom `.v` files.
- [ ] Uploaded files bypass generation and go straight to validation/simulation/synthesis.
