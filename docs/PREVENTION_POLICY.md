# RTL-Gen AI — Prevention Policy
## Eradicating Synthetic Metrics Permanently

**Version:** 1.0  
**Date:** April 2026  
**Status:** ENFORCED — violations fail CI

---

## Why This Document Exists

Between March 31 and April 2, 2026, three separate reports claimed
tape-out readiness. All three were wrong in different ways:

- Report 3: Simulation BLOCKED, synthesis unmapped — marked as ✅ COMPLETE
- Report 4: Matplotlib mock claiming TAPEOUT READY — completely fake
- Achievement Audit: 178-byte stub GDS, routing silently failed — marked ✅

The root cause in every case was the same:
**a step was marked PASS based on script exit codes or log output
rather than verified file system evidence.**

This policy prevents that from ever happening again.

---

## THE SINGLE RULE

> A pipeline step is ✅ PASS only when a specific output file exists,
> meets a minimum byte size threshold, and contains expected content
> patterns. Everything else is ❌ regardless of what any script printed.

---

## Mandatory File Size Thresholds

These thresholds are enforced in `full_flow.py::FILE_SIZE_THRESHOLDS`
and validated by `tests/test_unit.py::TestPreventionRules`.

| Output File | Minimum Size | Why |
|-------------|-------------|-----|
| Liberty file | 1,000,000 bytes | Real Sky130A lib = ~10-15 MB |
| Synthesized netlist | 500 bytes | Generic synth output = small |
| VCD waveform | 500 bytes | Empty VCD = simulation failed |
| placed.def | 5,000 bytes | Real placement has cell coords |
| cts.def | 5,000 bytes | CTS adds buffer cells |
| routed.def | 6,000 bytes | Must be LARGER than cts.def |
| GDS file | 50,000 bytes | Real 8-bit adder GDS = ~180KB |
| Extracted SPICE | 10,000 bytes | Real extraction = many lines |

---

## The Three Silent Failures — Must Test For Explicitly

### Silent Failure 1: Routing Copies CTS DEF

**Symptom:** `routed.def` size == `cts.def` size  
**Cause:** TritonRoute crashed (SIGSEGV) — PDN missing  
**Test:** `test_routing_not_silent_failure` in `test_real_integration.py`  
**Prevention:** `pdngen` must always precede `global_route`

### Silent Failure 2: DRC Passes on Empty GDS

**Symptom:** DRC = 0 violations on 178-byte stub GDS  
**Cause:** Magic found nothing to check in empty layout  
**Test:** `test_parse_signoff_invalidates_drc_on_stub` in `test_unit.py`  
**Prevention:** `parse_signoff()` cross-checks GDS size before reporting DRC

### Silent Failure 3: LVS Aborts Without Report

**Symptom:** LVS "UNMATCHED" because Netgen could not find cell name  
**Cause:** Magic exports `adder_8bit_flat`, Netgen told to find `adder_8bit`  
**Test:** `test_extracted_spice_has_correct_cell_name` in integration tests  
**Prevention:** Always extract cell name dynamically from SPICE subckt line

---

## Forbidden Patterns — Enforced by `test_unit.py::TestPreventionRules`

These patterns are prohibited in all non-test Python files:

```python
# FORBIDDEN — hardcoded metrics
"110 gates"
"2450"           # hardcoded area
"45 ps"          # hardcoded CTS skew
"1213"           # hardcoded wirelength
"status": "PASS" # hardcoded pass status in production code
```

If any of these appear in production code, `pytest -m unit` fails.

---

## Ownership Model

| Check | Owner | When |
|-------|-------|------|
| File size thresholds | `full_flow.py::FILE_SIZE_THRESHOLDS` | Every flow run |
| Silent failure detection | `RealMetricsParser` | Every metrics read |
| Unit test coverage | `tests/test_unit.py` | Every git commit |
| Integration test | `tests/test_real_integration.py` | Before every release |
| Full verification | `verify_integration.ps1` | After any infrastructure change |

---

## CI Gates — What Blocks a Merge

```
Every commit:
  pytest -m unit          must pass (< 30 seconds)
  
Before release:
  pytest -m integration   must pass (< 10 minutes)
  verify_integration.ps1  must show 23/23 PASS
```

---

## What "Production Ready" Means

A design is tape-out ready ONLY when ALL of these are true simultaneously:

```
1. GDS file > 50,000 bytes                    ← real layout
2. routed.def > cts.def (different sizes)     ← real routing
3. LVS report contains "equivalent"           ← circuit matches layout
4. STA report WNS >= 0.00                     ← timing met
5. DRC violations = 0 AND GDS > 50KB         ← real DRC on real layout
6. pytest -m integration → 0 failures         ← automated proof
```

Any single failure means NOT tape-out ready. No exceptions.

---

## What is NOT Evidence of Success

These outputs do NOT prove a step completed correctly:

- Script exit code 0
- Log file saying "DONE" or "COMPLETE"
- Dashboard showing green checkmark
- pytest passing with mocked Docker calls
- DRC showing 0 violations without checking GDS size
- LVS "equivalent" without checking transistor count > 0
