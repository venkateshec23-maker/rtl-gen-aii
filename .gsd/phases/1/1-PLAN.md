---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Fix Intermittent Pipeline Failures & Docker Health Hardening

## Objective
The RTL-to-GDSII pipeline currently has an intermittent success rate (33-44%) due to Docker daemon startup latency, OpenROAD timeouts, and out-of-memory (OOM) kills. This plan hardens the physical design pipeline by introducing robust daemon health checks and retry logic, ensuring an 80%+ success rate on consecutive runs.

## Context
- `.gsd/SPEC.md`
- `full_flow.py`
- `diagnose_runs.py` (diagnostic script)
- `validate_10runs.py` (validation script)

## Tasks

<task type="auto">
  <name>Diagnose Pipeline Flakiness</name>
  <files>diagnose_runs.py</files>
  <action>
    - Create a Python script (`diagnose_runs.py`) to run the `adder_8bit` design 5 times consecutively.
    - Track exactly which steps fail across the 5 runs to identify the bottleneck.
    - Identify if the failure is caused by OpenROAD timeouts (Case A), symlink races (Case B), Magic hangs (Case C), or Docker connection drops (Case D).
  </action>
  <verify>Run `python diagnose_runs.py` and analyze output logs to confirm failure mode.</verify>
  <done>Root cause of the intermittent failure is confirmed (e.g., Docker daemon unavailability).</done>
</task>

<task type="auto">
  <name>Implement Pipeline Hardening (Wait & Retry Logic)</name>
  <files>full_flow.py</files>
  <action>
    - In `full_flow.py`, add a shared `_wait_for_docker(max_wait=90)` helper function to gracefully poll `docker info` every 5 seconds instead of failing immediately.
    - Add a retry loop (up to 3 attempts with a 10s backoff) inside `step3_physical_design()` specifically wrapping the `self.docker.run_script(...)` call to handle transient OpenROAD failures.
    - Replace all existing inline `subprocess.run(["docker", "info"])` checks in `step1_rtl_simulation()`, `step3_physical_design()`, and `step4_gds_generation()` with the new `_wait_for_docker()` helper.
  </action>
  <verify>Review `git diff full_flow.py` to ensure all 3 fixes are applied correctly.</verify>
  <done>Docker calls are protected by a 90-second wait window and Physical Design has a 3-attempt retry loop.</done>
</task>

<task type="auto">
  <name>Verify 10-Run Stability Target</name>
  <files>validate_10runs.py</files>
  <action>
    - Create `validate_10runs.py` to run 10 consecutive end-to-end `RTLtoGDSIIFlow` executions for `adder_8bit`.
    - Run the script and monitor the success rate.
  </action>
  <verify>Run `python validate_10runs.py`.</verify>
  <done>The pipeline achieves an 80%+ (ideally 100%) success rate across 10 consecutive runs.</done>
</task>

<task type="auto">
  <name>Measure Final Week 1 Report</name>
  <files>week1_report.py</files>
  <action>
    - Create `week1_report.py` to query the PostgreSQL database (`get_all_runs`) and compute the aggregate success rate across all recorded benchmark designs (`adder_8bit`, `alu_4bit`, `counter_4bit`, etc.).
    - Note that this report includes historical failures prior to the fix, serving as a baseline metric.
  </action>
  <verify>Run `python week1_report.py` to measure historical tape-out readiness.</verify>
  <done>Final metrics script executes successfully, summarizing total passes and failures from the DB.</done>
</task>

## Success Criteria
- [x] Diagnostic tool reveals the root cause of intermittent failures.
- [x] Wait-and-retry logic is fully integrated into `full_flow.py` for all Docker calls.
- [x] A 10-consecutive-run test yields a 100% success rate (`TAPE_OUT_READY`).
- [x] `week1_report.py` accurately reads from the database and groups historical success rates by design.
