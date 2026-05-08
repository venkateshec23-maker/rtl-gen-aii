# RTL-Gen AI — Known Issues & User Feedback

## How to Report an Issue
1. Open GitHub Issues
2. Use template below
3. Include your OS, Docker version, design description

## Issue Template
```
**Design description tried:**
[what you typed]

**Expected:**
[what you expected]

**Actual:**
[what happened]

**Error message:**
[paste exact error]

**Environment:**
OS: Windows/Mac/Linux
Docker: version
Python: version
```

## Known Issues (Current)

### ISSUE-001: UDP Warnings in Gate-Level Simulation
**Status:** Known limitation  
**Cause:** iverilog cannot simulate Sky130 UDP primitives  
**Impact:** Gate-level simulation skips — RTL sim still runs  
**Fix:** Use commercial simulator (VCS/Xcelium) for gate-level  

### ISSUE-002: LVS Pin Ordering Warnings
**Status:** Cosmetic — does not affect correctness  
**Cause:** Bus bit ordering differs between extraction/schematic  
**Impact:** Warning in LVS report but "matched uniquely" still reported  
**Fix:** sky130A_setup.tcl permutation rules applied  

### ISSUE-003: PDF Report Minimal Data
**Status:** Fixed in v1.5  
**Cause:** Wrong results directory path  
**Fix:** find_results_dir() searches multiple locations  

### ISSUE-004: Complex Designs Use Fallback
**Status:** Expected behavior  
**Cause:** LLM generation for complex designs may timeout  
**Impact:** Template-based fallback used instead  
**Fix:** Use simpler description or template name (adder, counter, uart)

## User-Reported Issues
[Will be added as users report them]
