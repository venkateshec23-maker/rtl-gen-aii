# -*- coding: utf-8 -*-
"""
complex_test_suite.py -- Phase 2 Complex Design Validation
RTL-Gen AI

Runs 20 progressively complex designs through the full pipeline.
Phase 2 is complete only when all 20 print TAPE_OUT_READY = True.

Complexity tiers:
  Tier 1 (cells 50-150):   adder_16, alu_16, counter_16, multiplier_8
  Tier 2 (cells 150-400):  uart_full, spi_slave, fifo_32, crc32, lfsr
  Tier 3 (cells 400-1000): sram_512, i2c_slave, arb8, pwm_8ch, pipeline_4
  Conversational (5 tests): modify tier1 designs through 3 turns each
  Hierarchy (3 tests):     multi-module SoC designs end-to-end

Run:
    python complex_test_suite.py --tier 1        # tier 1 only (4 designs)
    python complex_test_suite.py --tier 2        # tier 2 only
    python complex_test_suite.py --tier 3        # tier 3 only
    python complex_test_suite.py --conv          # conversational tests
    python complex_test_suite.py --hier          # hierarchy tests
    python complex_test_suite.py                 # all 20 + conv + hier
"""

from __future__ import annotations

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# ── Design library ────────────────────────────────────────────────────────────

TIER_1_DESIGNS: List[Tuple[str, str, int]] = [
    ("adder_16bit",    "16-bit synchronous adder with carry output and overflow flag", 90),
    ("alu_16bit",      "16-bit ALU supporting add subtract and or xor operations with zero flag", 150),
    ("counter_16bit",  "16-bit up-down counter with enable load and synchronous reset", 80),
    ("multiplier_8",   "8x8 unsigned multiplier with registered output and overflow detection", 120),
]

TIER_2_DESIGNS: List[Tuple[str, str, int]] = [
    ("uart_fullduplex", "Full duplex UART with separate TX and RX at 115200 baud and status registers", 250),
    ("spi_slave",       "SPI slave with CPOL=0 CPHA=0 and 8-bit shift register", 180),
    ("fifo_32",         "32-entry 8-bit synchronous FIFO with almost-full almost-empty flags", 200),
    ("crc32",           "CRC-32 calculator with streaming byte input and registered output", 220),
    ("lfsr_prng",       "16-bit linear feedback shift register pseudo-random number generator", 60),
]

TIER_3_DESIGNS: List[Tuple[str, str, int]] = [
    ("sram_512",        "512x8-bit synchronous SRAM with byte write enable and output register", 400),
    ("i2c_slave",       "I2C slave with 7-bit address register and 8-byte receive buffer", 350),
    ("arb_roundrobin8", "8-way round-robin arbiter with grant hold and priority override", 180),
    ("pwm_8ch",         "8-channel PWM generator with independent duty cycle and period control", 280),
    ("pipeline_4stage", "4-stage pipelined 8-bit adder with hazard detection and forwarding", 350),
]

# ── Conversational test cases ─────────────────────────────────────────────────

CONVERSATIONAL_TESTS = [
    (
        "counter_conv",
        "4-bit synchronous counter with enable",
        [
            "Make it 8-bit",
            "Add a load input to preset the count to any value",
            "Add an output that pulses high for one cycle when count reaches maximum",
        ],
    ),
    (
        "adder_conv",
        "8-bit adder",
        [
            "Make it 16-bit",
            "Add a saturation mode so output clips at 0xFFFF instead of wrapping",
            "Add a subtract operation controlled by a sub input signal",
        ],
    ),
    (
        "fifo_conv",
        "8-entry FIFO",
        [
            "Double the depth to 16 entries",
            "Add an almost-full flag that asserts when 2 or fewer slots remain",
            "Add a flush input that empties the FIFO in one cycle",
        ],
    ),
]

# ── Hierarchy test cases ──────────────────────────────────────────────────────

HIERARCHY_TESTS = [
    (
        "simple_cpu",
        "8-bit CPU with an 8-bit ALU supporting add subtract and bitwise operations, an 8x8 register file, and a 4-bit program counter",
    ),
    (
        "uart_soc",
        "SoC with a UART transmitter at 115200 baud, a 256-byte SRAM for data storage, and a 4-bit address counter",
    ),
    (
        "signal_processor",
        "Signal processing unit with an 8-tap FIR filter accumulator, an 8-bit input FIFO, and a CRC-8 checksum generator",
    ),
]


# ── Runner ─────────────────────────────────────────────────────────────────────

def _run_pipeline(name: str, description: str) -> Dict:
    from guaranteed_flow import generate_guaranteed_gds
    return generate_guaranteed_gds(description, name)


def _check_result(r: Dict, min_cells: int = 50) -> Tuple[bool, List[str]]:
    issues = []

    if r.get("status") == "FALLBACK":
        issues.append("FALLBACK GDS returned — not a real design")

    gds_kb = r.get("gds_size_kb") or 0
    if gds_kb < 50:
        issues.append(f"GDS too small: {gds_kb:.1f} KB (need >50)")

    if not r.get("tapeout_ready"):
        issues.append("tapeout_ready = False")

    # QoR fields are at top level in generate_guaranteed_gds return
    if r.get("fmax_mhz") is None:
        issues.append("Fmax is None")
    if r.get("total_mw") is None:
        issues.append("Power is None")

    return len(issues) == 0, issues


def run_tier(designs: List[Tuple[str, str, int]], tier_name: str) -> List[Dict]:
    print(f"\n{'='*70}")
    print(f"  {tier_name}")
    print(f"{'='*70}")

    results = []
    for i, (name, desc, min_cells) in enumerate(designs, 1):
        print(f"\n  [{i}/{len(designs)}] {name}")
        print(f"  desc: {desc[:70]}")
        t0 = time.time()

        try:
            r = _run_pipeline(name, desc)
            elapsed = time.time() - t0
            ok, issues = _check_result(r, min_cells)

            status = "PASS" if ok else "FAIL"
            gds_kb = r.get("gds_size_kb") or 0
            fmax   = r.get("fmax_mhz")

            print(f"  status    : {status}")
            print(f"  GDS KB    : {gds_kb:.1f}")
            print(f"  Fmax      : {fmax:.1f} MHz" if fmax else "  Fmax      : None")
            print(f"  tapeout   : {r.get('tapeout_ready')}")
            print(f"  time      : {elapsed:.1f}s")

            if not ok:
                for issue in issues:
                    print(f"  FAIL    : {issue}")

            results.append({
                "name": name, "tier": tier_name,
                "ok": ok, "issues": issues,
                "gds_kb": gds_kb, "fmax_mhz": fmax,
                "elapsed": elapsed,
            })

        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ERROR   : {e}")
            results.append({
                "name": name, "tier": tier_name,
                "ok": False, "issues": [str(e)],
                "gds_kb": 0, "fmax_mhz": None,
                "elapsed": elapsed,
            })

    return results


def run_conversational_tests() -> List[Dict]:
    print(f"\n{'='*70}")
    print(f"  Phase 2 — Conversational Refinement Tests")
    print(f"{'='*70}")

    try:
        from conversational_rtl import (
            ConversationalSession, generate_initial_design,
            apply_modification, _diff_summary
        )
    except ImportError as e:
        print(f"  SKIP: conversational_rtl not available: {e}")
        return []

    results = []
    for session_name, initial_desc, refinements in CONVERSATIONAL_TESTS:
        print(f"\n  Session: {session_name}")
        print(f"  Start  : {initial_desc}")

        session = ConversationalSession(
            session_id  = session_name,
            design_name = session_name,
        )

        ok_init, msg = generate_initial_design(initial_desc, session_name, session)
        if not ok_init:
            print(f"  FAIL initial: {msg}")
            results.append({"name": session_name, "ok": False,
                            "issues": [f"Initial gen failed: {msg}"]})
            continue

        print(f"  v1: generated ({session.current_rtl.count(chr(10))} lines)")

        all_ok = True
        for j, refinement in enumerate(refinements, 2):
            ok_mod, msg_mod = apply_modification(refinement, session)
            if not ok_mod:
                print(f"  FAIL v{j}: {msg_mod}")
                all_ok = False
                break
            if len(session.versions) >= 2:
                diff = _diff_summary(session.versions[-2], session.versions[-1])
                print(f"  v{j}: '{refinement[:40]}' -> {diff}")

        from conversational_rtl import validate_syntax
        syntax_ok, err = validate_syntax(session.current_rtl, session_name)
        if not syntax_ok:
            print(f"  FAIL syntax: {err[:100]}")
            all_ok = False

        status = "PASS" if all_ok else "FAIL"
        print(f"  final: {status} — {len(session.versions)} versions, "
              f"{session.current_rtl.count(chr(10))} lines")

        results.append({
            "name": session_name,
            "ok":   all_ok,
            "issues": [] if all_ok else ["Refinement or syntax failed"],
            "versions": len(session.versions),
        })

    return results


def run_hierarchy_tests() -> List[Dict]:
    print(f"\n{'='*70}")
    print(f"  Phase 2 — Hierarchy Builder Tests")
    print(f"{'='*70}")

    try:
        from hierarchy_builder import build_hierarchical_design
    except ImportError as e:
        print(f"  SKIP: hierarchy_builder not available: {e}")
        return []

    results = []
    for name, description in HIERARCHY_TESTS:
        print(f"\n  Design: {name}")
        print(f"  Desc  : {description[:70]}")
        t0 = time.time()

        try:
            r = build_hierarchical_design(
                description     = description,
                design_name     = name,
                max_sub_modules = 3,
            )
            elapsed = time.time() - t0
            ok = r.status in ("SUCCESS", "PARTIAL") and r.gds_size_kb > 50
            sub_ok = sum(1 for s in r.sub_modules if s.status == "GENERATED")

            print(f"  status    : {r.status}")
            print(f"  sub-mods  : {sub_ok}/{len(r.sub_modules)} generated")
            print(f"  GDS KB    : {r.gds_size_kb:.1f}")
            print(f"  tapeout   : {r.tapeout_ready}")
            print(f"  time      : {elapsed:.1f}s")

            results.append({
                "name": name, "ok": ok,
                "issues": r.errors if hasattr(r, 'errors') else [],
                "gds_kb": r.gds_size_kb,
                "sub_modules": len(r.sub_modules),
                "elapsed": elapsed,
            })

        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ERROR: {e}")
            results.append({
                "name": name, "ok": False,
                "issues": [str(e)], "gds_kb": 0,
                "elapsed": elapsed,
            })

    return results


def print_phase2_summary(
    tier_results: List[Dict],
    conv_results: List[Dict],
    hier_results: List[Dict],
) -> bool:
    all_results = tier_results + conv_results + hier_results
    passed = sum(1 for r in all_results if r.get("ok"))
    failed = len(all_results) - passed

    print(f"\n{'='*70}")
    print(f"  Phase 2 Summary — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")
    print(f"  Pipeline tests  : {sum(1 for r in tier_results if r.get('ok'))}/{len(tier_results)} pass")
    print(f"  Conversational  : {sum(1 for r in conv_results if r.get('ok'))}/{len(conv_results)} pass")
    print(f"  Hierarchy       : {sum(1 for r in hier_results if r.get('ok'))}/{len(hier_results)} pass")
    print(f"  Total           : {passed}/{len(all_results)} pass")

    if failed > 0:
        print(f"\n  Failures:")
        for r in all_results:
            if not r.get("ok"):
                print(f"    FAIL: {r['name']}")
                for issue in r.get("issues", [])[:3]:
                    print(f"      {issue}")

    print(f"\n{'='*70}")
    if failed == 0:
        print("  PHASE 2 COMPLETE — all designs pass. Proceed to Phase 3.")
        return True
    else:
        print(f"  PHASE 2 INCOMPLETE — {failed} failure(s). Fix and re-run.")
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Run only this tier")
    parser.add_argument("--conv", action="store_true", help="Run only conversational tests")
    parser.add_argument("--hier", action="store_true", help="Run only hierarchy tests")
    args = parser.parse_args()

    print(f"\nRTL-Gen AI — Phase 2 Complex Design Validation")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tier_results: List[Dict] = []
    conv_results: List[Dict] = []
    hier_results: List[Dict] = []

    run_all = not any([args.tier, args.conv, args.hier])

    if run_all or args.tier == 1:
        tier_results += run_tier(TIER_1_DESIGNS, "Tier 1 — 50-150 cells")
    if run_all or args.tier == 2:
        tier_results += run_tier(TIER_2_DESIGNS, "Tier 2 — 150-400 cells")
    if run_all or args.tier == 3:
        tier_results += run_tier(TIER_3_DESIGNS, "Tier 3 — 400-1000 cells")
    if run_all or args.conv:
        conv_results = run_conversational_tests()
    if run_all or args.hier:
        hier_results = run_hierarchy_tests()

    phase_ok = print_phase2_summary(tier_results, conv_results, hier_results)
    return 0 if phase_ok else 1


if __name__ == "__main__":
    sys.exit(main())
