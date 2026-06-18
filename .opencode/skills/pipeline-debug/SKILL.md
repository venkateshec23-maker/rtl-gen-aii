---
name: pipeline-debug
description: Use when debugging OpenLane EDA pipeline failures, log parsing, or distinguishing real from fabricated metrics in pipeline output. Especially useful for log forensics tasks and quality review of completed runs.
---

# Pipeline Debugging

## Where Logs Live

Pipeline logs are at the project root (`full_flow.log`) and under `.gemini/antigravity-ide/brain/*/.system_generated/tasks/task-*.log` for AI-generated tasks. These can be 200k+ lines.

## Extracting Relevant Sections

Use Python line-range extraction for large logs:

```python
from pathlib import Path
lines = Path("full_flow.log").read_text(encoding="utf-8", errors="ignore").splitlines()
# Filter by stage markers
for line in lines:
    if "STEP" in line or "QoR" in line or "VERIFIED" in line or "MATCHED" in line:
        print(line)
```

## File Size Thresholds (real tool execution)

From `full_flow.py:57-75` — minimum bytes proving real EDA execution:
| Artifact | Minimum |
|----------|---------|
| Netlist | 500 B |
| Placed DEF | 4 KB |
| CTS DEF | 6 KB |
| Route DEF | 8 KB |
| GDS | 15 KB |
| LVS extracted | 8 KB |
| STA report | 500 B |

If outputs are below these, the tool likely didn't actually run.

## Known Failure Modes

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| `Generation failed: Error code: 429` | LLM API rate limit | Wait and retry, or use different provider |
| `Generation failed: _ssl.c:993 handshake timeout` | Gemini API unavailable | Retry or skip to template fallback |
| `TESTS_FAILED` | Generated RTL doesn't match spec | Check testbench, try simpler description |
| `536 error(s) during elaboration` | Sky130 library parsing noise (expected) | Ignore — check critical errors separately |
| GDS < 15 KB | Magic GDS generation didn't actually run | Check Magic invocation in Docker |
| `Area: None` | Area extraction failed or not implemented | Metric unreliable |
| `Fmax > 500` on Sky130 | Fabricated metric | Cross-check with slack value |

## Template Fallback Detection

When the pipeline can't generate a design via LLM, it falls back to templates. Look for:
- `[TEMPLATE] Using proven template: <name>.v`
- `Attempt 3: Using proven template`
- `classify_design()` returned type with `matched: True`

The template mapping (`guaranteed_flow.py:1939-2060`) has quirks — some mappings are inaccurate (e.g., LFSR → counter template).

## Log Pattern Quick Reference

| Pattern | Meaning |
|---------|---------|
| `=== STEP N: ===` | Pipeline stage boundary |
| `Tool check <name>: OK` | Tool available in Docker |
| `Docker: <command>` | Docker command execution |
| `ALL_TESTS_PASSED` | RTL simulation passed |
| `Synthesis VERIFIED - N bytes` | Yosys netlist size |
| `N Sky130 cells synthesized` | Synthesized cell count |
| `Completing N% with M violations` | Routing progress |
| `Number of violations = 0` | Routing completed clean |
| `GDS Generation VERIFIED - N bytes` | GDS output size |
| `DRC: 0 violations` | DRC clean |
| `ERC Check: PASSED` | ERC clean |
| `Antenna Check: PASSED` | Antenna rule clean |
| `IR Drop Analysis: PASSED` | IR drop clean |
| `Timing: N.NNns slack` | STA slack |
| `LVS: MATCHED (100.0%)` | LVS passed |
| `QoR from DB: Fmax=...` | Final quality summary |
| `Hold analysis: CLEAN` | Hold timing clean |

## Commands

```bash
# Run specific test
pytest tests/test_unit.py -v -k test_name

# Check Docker available
docker info

# Count templates used in a log
Select-String -Path full_flow.log -Pattern "\[TEMPLATE\]"

# Extract QoR summaries
Select-String -Path full_flow.log -Pattern "QoR from DB"

# Check design count
Select-String -Path full_flow.log -Pattern "Starting guaranteed GDS2" | Measure-Object
```
