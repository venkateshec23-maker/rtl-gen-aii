# Pipeline Analysis Report: REAL vs FAKE by Stage

**Log**: `task-2119.log` (224,181 lines, ~3h runtime)
**Data**: 25 distinct designs through 13 pipeline stages
**Date**: 2026-06-17 22:33 - 01:38

---

## 1. PRE-FLOW: TOOL VERSION CHECK

| Claim | Verdict | Evidence |
|-------|---------|----------|
| 5 tools checked (yosys, openroad, magic, netgen, iverilog) | **REAL** | `Tool check yosys: OK` appears consistently at ~0.8-1.5s intervals per design |
| Manual Docker pulls implied | **FAKE** | No Docker pull logs. Tools are always "ready" in ~1s per design, suggesting they're pre-cached or the check is stubbed |

---

## 2. GENERATION / RTL CREATION PHASE

| Claim | Verdict | Evidence |
|-------|---------|----------|
| **"Attempt 2: Universal auto-generation"** via Groq/OpenRouter/Gemini | **FAKE** | Every design (25/25) exhausts 3 providers with errors (429 rate limit, SSL timeout) then falls to template |
| **Groq 429 errors** - token limits reached | **REAL** | Error format is genuine Groq API response with exact token counts: `Limit 100000, Used 97454, Requested 5554` |
| **OpenRouter 429 errors** | **REAL** | `meta-llama/llama-3.3-70b-instruct:free is temporarily rate-limited` is a real OpenRouter error format |
| **Gemini SSL timeout** | **REAL** | `_ssl.c:993: The handshake operation timed out` - genuine network issue |
| **GitHub simulation fallback** | **SUSPICIOUS** | GitHub always either "succeeds" (via Docker) or fails with `TESTS_FAILED` then `[REPAIR]` - never shows actual GitHub Actions logs |
| **"Attempt 3: Using proven template"** | **FAKE** | **100% of designs (25/25) end up here.** The template codes like `adder.v`, `counter.v`, `mux.v` are used, but often with mismatched mapping: |
| | | `crc8_b → template: i2c_master.v` (CRC-8 has nothing to do with I2C) |
| | | `encoder_8to3_b → template: decoder.v` (encoder → decoder = wrong direction) |
| | | `spi_master_b → template: uart_tx.v`, `mux.v` (completely different protocols) |
| | | Template is used ~38 times for 25 designs (some use multiple) |
| **Local model + opencode fallback** | **REAL** | `Local model not enabled. Run: python model_trainer.py --deploy` and `[WinError 2] The system cannot find the file specified` are genuine |
| **"counter_updown_b with PDK=sky13"** (typo) | **FAKE** | PDK should be `sky130A`. Typo is silently ignored; flow continues normally. Real pipeline would fail. |

---

## 3. STEP 0: ENVIRONMENT VERIFICATION

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Docker available for iverilog/yosys/openroad/magic/netgen | **REAL** | Docker commands spawn correctly (no credential errors, command-not-found errors) |
| `STEP 0 COMPLETE - Environment ready (Docker optional for code generation)` | **REAL** | Consistently completes in ~2s per design |

---

## 4. STEP 1: RTL SIMULATION

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Local iverilog unavailable | **REAL** | `[WinError 2] The system cannot find` - genuine Windows limitation |
| Docker iverilog simulation | **REAL** | Commands like `cd /work/runs/{design} && iverilog -o sim_out` are valid Docker invocations |
| `ALL_TESTS_PASSED` for every design | **SUSPICIOUS** | 25/25 designs pass first try. Real flows have occasional failures. Could be real if testbenches are trivial |
| Simulation duration ~1s | **SUSPICIOUS** | All designs complete in ~1s regardless of complexity (15 cells → 515 cells → 5549 cells). Should scale with size |

---

## 5. STEP 1a: NATIVE SYNTHESIS CHECK

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Native synthesis check runs | **REAL** | Step appears in log, step transitions occur |
| Step duration | **REAL** | ~10-15ms (just a flag check, no Docker command) |

---

## 6. STEP 2: SYNTHESIS (Yosys)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Yosys synthesis via Docker | **REAL** | `Docker: yosys -s /work/scripts/synth.ys 2>&1...` - valid command |
| Synthesis completed (25 runs) | **REAL** | Varying durations: 2-4s per design, larger designs take longer |
| **Cell counts across different designs are identical** | **FAKE** | counter_4bit_b & gray_cnt_4_b both = **15 cells** (different logic → same cells? impossible) |
| | | barrel_8_b & shift_reg_8_b both = **24 cells** |
| | | decoder_3to8_b & counter_8bit_b both = **30 cells** (combinational vs sequential = same? impossible) |
| | | adder_8bit_b & debounce_b both = **52 cells** |
| | | fifo_16_b & fifo_32_b both = **515 cells** (16-deep vs 32-deep same? impossible) |
| | | sram_256_b & sram_512_b both = **5549 cells** (256B vs 512B SRAM same? impossible) |

---

## 7. STEP 2b: FORMAL EQUIVALENCE CHECK

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Yosys equivalence check runs | **REAL** | `Docker: yosys -s /work/runs/{design}/equiv_check.ys` |
| **ABC warnings about multi-output gates** | **REAL** | `ABC: Warning: Detected 9 multi-output gates (for example, "sky130_fd_sc_hd__fa_1")` - legitimate Yosys/ABC output |
| **Formal equivalence errors reported as non-blocking** | **SUSPICIOUS** | `WARNING FORMAL EQUIV: ERROR found - cell library issue (non-blocking)` - ignoring formal errors defeats the purpose of formal verification |

---

## 8. STEP 2c: FORMAL PROPERTY VERIFICATION

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Runs formal property TCL script | **REAL** | `Docker: yosys -s /work/runs/{design}/{design}_formal.tcl...` |
| **"Formal verification: 0/5 pass, 0 fail"** | **FAKE / STUBBED** | Every design (25/25) shows exactly **0/5 pass, 0 fail** in ~0.8-1.0s regardless of complexity. This means either: |
| | | (a) No formal properties are defined (0/5 means 5 are expected but none pass = empty suite) |
| | | (b) The formal verification framework is a stub that just returns "0/5 pass, 0 fail" |
| Timing also suspicious: 15-cell design = 0.8s, 5549-cell design = 1.5s. Only 2x for 370x more logic |

---

## 9. STEP 3: PHYSICAL DESIGN (Floorplan → CTS → PDN → Route via OpenROAD)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| OpenROAD flow runs via Docker | **REAL** | `Docker: openroad -exit /work/scripts/openroad_flow.tcl` - valid command |
| OpenROAD script written locally | **REAL** | `OpenROAD script written: C:\tools\OpenLane\scripts\openroad_flow.tcl` |
| **Routing progress with varying violations** | **REAL** | `Completing 30% with 2 violations` → `Completing 40% with 0 violations` → `Number of violations = 0`. Violation counts vary per design (0, 1, 2, 6, 12, 20, 21, 32) → realistic |
| **Floorplan/Placement/CTS/Routing VERIFIED with file sizes** | **REAL** | File sizes vary by design complexity (7KB for simple → 733KB for fifo_16, ~6MB for sram_512). Suggests actual OpenROAD runs |
| **[WARNING RSZ-0021] no estimated parasitics** | **REAL** | Genuine OpenROAD STA warning when LEF files don't have QRC tech file |

---

## 10. STEP 1b: GATE-LEVEL SIMULATION

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Gate-level sim via Docker iverilog | **REAL** | `Docker: cd /work/runs/{design} && iverilog -o /tmp/gate_sim_gate` |
| **"118 UDP errors"** per design | **REAL** | Count varies per design (112-799). UDP models in Sky130 primitives.v are unsupported by iverilog. This is a genuine open-source limitation |
| "RTL simulation provides functional verification" | **REAL** | Correct assessment of the limitation |

---

## 11. STEP 4: GDS GENERATION (Magic)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Magic via Docker for GDS streaming | **REAL** | `Docker: magic -noconsole -dnull -rcfile /pdk/sky130A/libs.tech/magic/sky130A.magicrc <<` |
| GDS sizes vary by design | **REAL** | 157KB (barrel_8) → 280KB (pwm) → 432KB (lfsr_16) → 678KB (i2c) → 1.5MB (fifo_32) → 13.8MB (sram_256) → 14.1MB+ (sram_512). Realistic scaling |
| **Exact duplicate GDS sizes for different designs** | **FAKE** | `decoder_3to8_b` and `counter_8bit_b` both have GDS = **195,414 bytes** and both synthesize to **30 cells** |
| | | `fifo_16_b` and `fifo_32_b` both have GDS = **1,537,800 bytes** and both have **515 cells** |
| | | `barrel_8_b` GDS = 161,008 vs `shift_reg_8_b` GDS = 161,016 (very close but not exact) |
| Timing proportional to design size | **REAL** | Small designs: ~2.5s, medium: ~4s, sram_256: ~10min (~14MB GDS), sram_512: ~20min (~14MB+ GDS). This is the strongest evidence of real EDA execution |

---

## 12. STEP 5: DRC (Magic)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Magic DRC runs via Docker | **REAL** | `Docker: magic -noconsole -dnull -rcfile /pdk/sky130A/libs.tech/magic/sky130A.magicrc <<` |
| **DRC: 0 violations for ALL designs (25/25)** | **SUSPICIOUS** | No design ever has a single DRC violation. Real EDA flows with 25 different designs would have occasional DRC failures |
| DRC completeness | **SUSPICIOUS** | No detailed DRC output shown. Real Magic DRC produces detailed violation reports |

---

## 13. STEP 5a: ERC + ANTENNA

| Claim | Verdict | Evidence |
|-------|---------|----------|
| ERC Check via Magic | **REAL** | `ERC Check: PASSED (real Magic analysis)` |
| Antenna Check via Magic | **REAL** | `Antenna Check: PASSED (real Magic analysis)` |
| **"real Magic analysis" in parentheses** | **SUSPICIOUS** | The explicit "(real Magic analysis)" qualifier suggests there may be non-real analyses elsewhere |

---

## 14. STEP 5b: IR DROP ANALYSIS (OpenROAD)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| IR drop analysis runs | **REAL** | `Docker: openroad -exit /work/runs/{design}/ir_drop.tcl` |
| All PASSED (25/25) | **SUSPICIOUS** | No design shows any IR drop issues |

---

## 15. STEP 7: FINAL STA (OpenROAD)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| STA across 3 corners (tt, ss, ff) | **REAL** | `sta_tt.tcl`, `sta_ss.tcl`, `sta_ff.tcl` - proper multi-corner STA |
| **[ERROR STA-0562] analyze_power_grid -vdd** | **REAL** | Genuine OpenROAD script version incompatibility. The flag changed between OpenROAD versions |
| Timing slack varies by design | **REAL** | 2.66ns (296 cells) → 6.85ns (57 cells) → 14.11ns (167 cells) → 9.75ns (5549 cells). Realistic variation |
| **All designs have positive slack** | **SUSPICIOUS** | 25/25 designs pass timing. Given the 50MHz target, this is plausible for small designs but suspicious for the 5549-cell SRAM |

---

## 16. STEP 6: LVS (Magic + Netgen)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Magic extraction for LVS | **REAL** | Magic extraction sizes vary (24KB → 2582KB). Larger designs take longer |
| Netgen comparison runs | **REAL** | Full netgen output shown with `Cell pin lists are equivalent` for every cell type |
| **LVS: MATCHED (100%)** for every design | **SUSPICIOUS** | 25/25 designs pass LVS perfectly. In real flows, LVS failures occur occasionally |
| Netgen warnings | **REAL** | `Warning: netgen command 'format' use fully-qualified name` - genuine netgen deprecation warnings |
| Device/net counts match | **REAL** | E.g., pwm_8bit_b: 57 devices/67 nets, fifo_16_b: 515/399, sram_256_b: 5549/3519. Realistic |

---

## 17. STEP 8: POST-LAYOUT SIMULATION (SDF)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Post-layout sim attempted | **REAL** | `Docker: cd /work/runs/{design} && iverilog -o /tmp/post_sim -s {design}_tb` |
| **SKIPPED - UDP model limitation** | **REAL** | Consistent with iverilog's known limitation with Sky130 primitives |

---

## 18. HOLD + POWER ANALYSIS

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Hold analysis via OpenROAD | **REAL** | `Docker: openroad -exit /work/scripts/hold_analysis.tcl` |
| **Hold slack suspiciously clustered** | **SUSPICIOUS** | 7 designs at exact 0.160ns, 7 at exact 0.150ns, 3 at 0.140ns. Real hold analysis would show more distribution |
| Power analysis via OpenROAD | **REAL** | `Docker: openroad -exit /work/scripts/power_analysis.tcl` |
| **Area: None um2, Util: None%** for every design | **FAKE** | OpenROAD always reports area and utilization after floorplan. Either area is not extracted or these values are fabricated |
| Power values vary | **REAL** | 0.062mW (pwm_8bit) → 2.28mW (fifo_32) → 13.2mW (sram). Realistic range |

---

## 19. QoR SUMMARY

| Claim | Verdict | Evidence |
|-------|---------|----------|
| **Fmax=4000.0 MHz** for sram_256_b | **FAKE** | Physically impossible for Sky130 130nm process. Real maximum is ~300-400 MHz. Timing slack is 9.75ns which computes to ~102 MHz |
| Fmax values for other designs | **SUSPICIOUS** | Fmax=317.5 MHz for 57-cell PWM is plausible; Fmax=159.0 MHz for 118-cell LFSR is plausible. But Fmax=375.9 MHz for 515-cell FIFO is aggressive |
| All designs `Tapeout=True` | **SUSPICIOUS** | 25/25 designs marked tapeout-ready. Real-tapeout qualification would have some failures |

---

## STAGE-BY-STAGE AUTHENTICITY SCORECARD

| Stage | REAL | FAKE | SUSPICIOUS | Notes |
|-------|------|------|-----------|-------|
| Tool checks | ✅ | | | Consistent version checks |
| LLM API calls | ✅ rate limits | | | Genuine API errors |
| Template generation | | ✅ | | Every design uses template, never real LLM output |
| RTL simulation | ✅ Docker | | | Works correctly |
| Synthesis | ✅ Docker | | ✅ cell counts | Real Yosys, fake cell counts |
| Formal equivalence | ✅ Docker | | ✅ ignored errors | Real commands, fake assertions |
| Formal property | | ✅ | | 0/5 pass, 0 fail is an empty stub |
| Physical design | ✅ OpenROAD | | ✅ 0 violations | Real PnR, implausibly clean |
| Gate-level sim | ✅ | | ✅ skipped | Real iverilog UDP issue |
| GDS generation | ✅ Magic | | ✅ duplicate sizes | Real Magic, fake size outputs |
| DRC | ✅ Magic | | ✅ 0 violations | Real DRC engine, implausibly clean |
| ERC/Antenna | ✅ Magic | | | Real checks |
| IR Drop | ✅ OpenROAD | | | Real analysis |
| Final STA | ✅ OpenROAD | ✅ Fmax=4000 | ✅ all positive | Real engine, fake Fmax |
| LVS | ✅ Magic+Netgen | | ✅ 100% match | Real tools, implausibly perfect |
| Post-layout sim | ✅ | | ✅ skipped | Real limitation |
| Hold/Power analysis | ✅ OpenROAD | ✅ Area=None | ✅ clustered slacks | Real engine, fabricated metrics |
| QoR report | | ✅ | ✅ | Fake Fmax, fake Tapeout=True |

---

## OVERALL VERDICT

### ✅ Genuinely Real Parts
- Docker-based EDA tool invocations (Yosys, OpenROAD, Magic, Netgen, iverilog)
- API rate limit errors from Groq/OpenRouter
- SSL/network timeouts to Gemini
- iverilog UDP limitation with Sky130 primitives
- OpenROAD version incompatibility warnings
- SPICE file not found errors
- Netgen deprecation warnings
- **Magic GDS generation shows realistic size scaling and timing** - especially the sram_256 (10min) and sram_512 (20min) runs
- **LVS device/net matching is internally consistent** (57 devices/67 nets for a 57-cell design)

### ❌ Definitely Fabricated
- **LLM generation**: Never produces output; always falls through to template (100% fallback rate)
- **Cell counts**: Different designs magically produce identical counts (15, 24, 30, 52, 515, 5549)
- **GDS sizes**: Different designs magically produce identical GDS sizes
- **Fmax=4000.0 MHz**: Physically impossible for Sky130
- **Area=None, Util=None%**: Every design - OpenROAD always reports these
- **Formal property verification**: "0/5 pass, 0 fail" = empty/stubbed suite
- **Template-to-design mapping**: CRC-8 using I2C template, encoder using decoder template
- **PDK typo**: `sky13` doesn't exist; flow continues regardless

### ⚠️ Suspicious / Implausibly Clean
- **25/25 designs pass everything**: DRC=0, LVS=100%, timing positive, hold clean. Real flows don't work like this
- **Hold slack clustering**: 7 designs locked at exactly 0.160ns
- **Identical flow timing** for very different design sizes (formal verification)
- **Every simulation passes first try** regardless of RTL complexity

### Bottom Line
The pipeline **runs real EDA tools via Docker** (Yosys, OpenROAD, Magic, Netgen, iverilog) on **pre-existing template RTL files**. The LLM generation, cell count accuracy, area/utilization reporting, and formal property verification are **fabricated or stubbed out**. The GDS/LVS results may be from real tools but the **QoR metrics and design-specific claims are unreliable**.
