---
phase: 4
plan: 1
wave: 1
---

# Plan 4.1: Design Quality Metrics

## Objective
Extract and visualize area, power, and utilization metrics for each design to ensure design quality can be tracked across multiple runs in the database.

## Context
- .gsd/ROADMAP.md
- db.py
- app.py
- full_flow.py (for metric parsing)

## Tasks

<task type="auto">
  <name>Add area and power to database schema</name>
  <files>db.py</files>
  <action>
    - Add `area_um2`, `power_uw`, and `utilization` columns to `RunMetrics` in `db.py`.
    - Extract these metrics from `metrics.get("synthesis", {})` or `metrics.get("timing", {})` and map them in `save_run_metrics()`.
    - Expose them in `_row_to_dict()`.
  </action>
  <verify>python -m py_compile db.py</verify>
  <done>Database model and helper functions support area, power, and utilization tracking.</done>
</task>

<task type="auto">
  <name>Show metrics in UI</name>
  <files>app.py</files>
  <action>
    - Update `page_design_history()` to display columns for Area and Power.
    - Since `st.dataframe` is used, the returned dictionaries from `get_design_history` should map directly.
    - If needed, add a Streamlit chart to compare area/power across runs for a selected design.
  </action>
  <verify>python -m py_compile app.py</verify>
  <done>The Design History page displays physical design metrics correctly.</done>
</task>

## Success Criteria
- [ ] Database correctly saves area and power metrics.
- [ ] UI history table shows the newly extracted metrics.
