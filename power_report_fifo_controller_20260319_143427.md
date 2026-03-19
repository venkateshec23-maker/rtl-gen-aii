# Power Analysis Report

**Module:** fifo_controller  
**Generated:** 2026-03-19 14:34:27

---

## Operating Conditions

- **Frequency:** 100.00 MHz
- **Activity Factor:** 0.25
- **Technology:** 45nm
- **Supply Voltage:** 1.10V

---

## Power Summary

| Component | Power (mW) | Percentage |
|-----------|------------|------------|
| Dynamic Power | 0.4290 | 100.0% |
| - Clock | 0.1815 | 42.3% |
| - Logic | 0.2100 | 48.9% |
| - Registers | 0.0375 | 8.7% |
| Leakage Power | 0.0001 | 0.0% |
| **TOTAL** | **0.4291** | **100%** |

---

## Design Statistics

- **Registers:** 3
- **Combinational Gates:** 4
- **Muxes:** 0
- **Adders:** 2
- **Multipliers:** 0
- **Bit Width:** 4

---

## Power Efficiency

- **Power per bit:** 0.1073 mW/bit
- **Energy per operation:** 0.0043 pJ

---

## Recommendations

- Clock power is dominant (>42.3%). Consider clock gating.
- Low power design achieved (<10 mW).

---

Note: These are estimated values. Actual power depends on technology library and layout.
