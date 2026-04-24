# Project Specification: RTL-Gen AI Production Hardening
STATUS: FINALIZED

## Overview
Complete the production-grade hardening of the RTL-Gen AI platform by finalizing the integration of real-time progress monitoring in the UI, ensuring rigorous test coverage with database-backed validation, supporting parallel design runs, and improving LLM repair prompts.

## Core Requirements
1. **Parallel Design Runs (Phase 2):** Allow multiple designs to be processed asynchronously without blocking the Streamlit UI, respecting memory limits (max 2 parallel runs).
2. **Better LLM Repair Prompts (Phase 3):** Utilize `trace.vcd` and physical design log errors to improve LLM auto-repair capabilities.
3. **Design Quality Metrics (Phase 4):** Track Area/Power estimates in the PostgreSQL schema and visualize them.
4. **Upload Custom Verilog (Phase 5):** Allow drag-and-drop Verilog files to bypass AI generation and go straight to physical design.
