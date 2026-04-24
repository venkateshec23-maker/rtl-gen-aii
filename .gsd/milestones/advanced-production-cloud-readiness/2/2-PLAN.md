---
phase: 2
plan: 1
wave: 1
---

# Plan 2.1: Implement Asynchronous Job Queue

## Objective
Implement a background task queue to handle OpenLane physical design runs. This prevents the Streamlit UI from blocking during the 90+ second synthesis/routing flow, and allows multiple designs to run in parallel without exceeding memory limits.

## Context
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- python/task_queue.py
- app.py

## Tasks

<task type="auto">
  <name>Integrate TaskQueue into Streamlit UI</name>
  <files>app.py</files>
  <action>
    - Modify the "Generate Verilog & Build Silicon" button action in `app.py`.
    - Instead of calling `RTLtoGDSIIFlow.run_full_flow()` directly (which blocks), call `st.session_state["queue"].add_task(...)`.
    - Remove the blocking UI updates for pipeline execution from the generation loop.
  </action>
  <verify>python -m py_compile app.py</verify>
  <done>app.py no longer blocks during pipeline execution and successfully delegates to `task_queue.py`.</done>
</task>

<task type="auto">
  <name>Create Queue Status UI</name>
  <files>app.py</files>
  <action>
    - Add a new "Queue Status" section in the Streamlit UI (either in a sidebar or the Design History page).
    - Call `st.session_state["queue"].list_tasks()` to get current background tasks.
    - Display the status (QUEUED, RUNNING, COMPLETED, FAILED) and progress for each task.
  </action>
  <verify>python -m py_compile app.py</verify>
  <done>Users can visibly monitor background tasks in the Streamlit UI.</done>
</task>

## Success Criteria
- [ ] Users can submit multiple AI generation requests without the UI hanging.
- [ ] The background thread correctly executes `full_flow.py` and saves metrics to the database.
- [ ] The UI displays a live view of all queued and running designs.
