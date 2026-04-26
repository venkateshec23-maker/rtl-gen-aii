# ROADMAP.md

> **Current Milestone**: Production Hardening
> **Goal**: Complete the production-grade hardening of the RTL-Gen AI platform

## Must-Haves
- [ ] Parallel Design Runs (max 2)
- [ ] Better LLM Repair Prompts
- [ ] Design Quality Metrics (Area/Power)
- [ ] Upload Custom Verilog

## Phases

### Phase 2: Parallel Design Runs
**Status**: ⬜ Not Started
**Objective**: Allow multiple designs to be processed asynchronously without blocking the Streamlit UI, respecting memory limits (max 2 parallel runs).

### Phase 3: Better LLM Repair Prompts
**Status**: ⬜ Not Started
**Objective**: Utilize `trace.vcd` and physical design log errors to improve LLM auto-repair capabilities.

### Phase 4: Design Quality Metrics
**Status**: ⬜ Not Started
**Objective**: Track Area/Power estimates in the PostgreSQL schema and visualize them.

### Phase 5: Upload Custom Verilog
**Status**: ⬜ Not Started
**Objective**: Allow drag-and-drop Verilog files to bypass AI generation and go straight to physical design.
