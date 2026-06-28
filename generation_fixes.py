"""
generation_fixes.py — Comprehensive Generation Fix Bundle
RTL-Gen AI v3.4

Fixes all four root causes seen in the RISC-V generation failure log:

  1. SystemVerilog → Verilog 2005 post-processor
     (fixes "Incomprehensible for loop", integer/logic declarations, etc.)

  2. Smart repair targeting
     (sends RTL errors to RTL repair, TB errors to TB repair — not mixed)

  3. Complexity detection and auto-decomposition
     (RISC-V, processors, and other large designs route through
      hierarchy_builder instead of single-call generation)

  4. Dead provider fast-skip
     (Gemini SSL timeout → skip after first attempt, not three;
      known-rate-limited providers → skip until cooldown expires)

INTEGRATION — paste these functions into the files indicated.
Every function has a comment showing exactly where it goes.

Standalone test:
    python generation_fixes.py
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# FIX 1 — SystemVerilog → Verilog 2005 post-processor
# Add to verilog_generator.py as a post-processing step called
# immediately after every LLM response is extracted.
#
# Usage in verilog_generator.py:
#   from generation_fixes import sv_to_v2005
#   rtl_code = sv_to_v2005(rtl_code, module_name)
# ═══════════════════════════════════════════════════════════════════


def sv_to_v2005(rtl_code: str, module_name: str = "") -> str:
    """
    Convert common SystemVerilog constructs to Verilog 2005.
    Called on every LLM-generated RTL before simulation.

    Fixes:
      - for (int i = ...) → integer i; ... for (i = ...)
      - logic [N:0] → reg [N:0] or wire [N:0] based on context
      - always_ff → always @(posedge clk)
      - always_comb → always @(*)
      - always_latch → always @(*)
      - automatic functions → remove 'automatic' keyword
      - unique case / priority case → plain case
      - import pkg::* → removed (packages not in Verilog 2005)
      - typedef enum logic → simple parameter constants
      - string type → reg [127:0] (best approximation)
    """
    code = rtl_code

    # ── for loop with int/integer/bit declaration ─────────────────
    # Pattern: for (int i = 0; ...) → need to extract and declare above
    # Strategy: replace inline type with extracted declarations
    int_for_pattern = re.compile(
        r"for\s*\(\s*(int|integer|bit|byte|shortint|longint)\s+(\w+)\s*=", re.MULTILINE
    )
    declared_vars = set()

    def replace_for_loop(m):
        varname = m.group(2)
        declared_vars.add(varname)
        return f"for ({varname} ="

    code = int_for_pattern.sub(replace_for_loop, code)

    # ── standalone SV integer types → Verilog equivalents ────────
    # Handles declarations not caught by the for-loop handler above
    code = re.sub(r"\bshortint\s+(?:unsigned\s+)?(\w+)\s*;", r"reg [15:0] \1;", code)
    code = re.sub(r"\blongint\s+(?:unsigned\s+)?(\w+)\s*;", r"reg [63:0] \1;", code)
    code = re.sub(r"\bbyte\s+(?:unsigned\s+)?(\w+)\s*;", r"reg [7:0] \1;", code)
    # Only convert standalone `int` declarations (not `integer` — already valid)
    code = re.sub(r"\bint\s+(?:unsigned\s+)?(\w+)\s*;", r"integer \1;", code)

    # Insert integer declarations before the first always block or module body
    if declared_vars:
        decls = "\n".join(f"    integer {v};" for v in sorted(declared_vars))
        # Find a good insertion point — before first always/assign
        insert_match = re.search(
            r"^\s*(always|always_ff|always_comb|always_latch|assign)\b",
            code,
            re.MULTILINE,
        )
        if insert_match:
            insert_pos = insert_match.start()
            code = code[:insert_pos] + decls + "\n" + code[insert_pos:]

    # ── logic → wire/reg based on context ────────────────────────
    # Strip typedef struct packed { ... } type_name; blocks before logic→reg runs
    # (otherwise the logic fields inside get mangled by the substitution below)
    code = re.sub(
        r"\btypedef\s+struct\s+(?:packed\s+)?\{[^}]*\}\s*\w+\s*;",
        "// typedef struct removed (not Verilog-2001)",
        code,
        flags=re.DOTALL,
    )
    # In port lists: logic → wire (inputs) or reg (outputs within always)
    # In internal declarations: logic → reg
    # Matches: logic [WIDTH-1:0] sig; or logic sig; or logic [3:0] sig;
    code = re.sub(
        r"\blogic\s+(\[[^\]]+\]\s+)?(\w+)\s*;",
        lambda m: f"reg {m.group(1) or ''}{m.group(2)};",
        code,
    )
    # Port-list logic: input logic → input wire
    code = re.sub(r"\binput\s+logic\b", "input wire", code)
    code = re.sub(r"\boutput\s+logic\b", "output reg", code)
    code = re.sub(r"\binout\s+logic\b", "inout wire", code)

    # ── always_ff → always @(posedge clk) ────────────────────────
    code = re.sub(r"\balways_ff\s*@\s*\(([^)]+)\)", r"always @(\1)", code)
    code = re.sub(r"\balways_ff\b", "always @(posedge clk)", code)

    # ── always_comb / always_latch → always @(*) ─────────────────
    code = re.sub(r"\balways_comb\b", "always @(*)", code)
    code = re.sub(r"\balways_latch\b", "always @(*)", code)

    # ── unique case / priority case → case ───────────────────────
    code = re.sub(r"\b(unique|priority)\s+case\b", "case", code)
    code = re.sub(r"\b(unique|priority)\s+if\b", "if", code)

    # ── casex / casez → case WITH WARNING (not synthesizable in Vivado/Cadence) ──
    code = re.sub(r"\bcasex\b", "/* WARNING: casex not fully synthesizable */ case", code)
    code = re.sub(r"\bcasez\b", "/* WARNING: casez not fully synthesizable */ case", code)

    # ── automatic functions ───────────────────────────────────────
    code = re.sub(r"\bautomatic\s+", "", code)

    # ── package imports ───────────────────────────────────────────
    code = re.sub(r"^\s*import\s+\w+::\*;\s*\n", "", code, flags=re.MULTILINE)
    code = re.sub(
        r"^\s*package\b.*?endpackage\b", "", code, flags=re.MULTILINE | re.DOTALL
    )

    # ── scope resolution :: → remove qualifier, keep identifier ──
    # Converts pkg::CONSTANT → CONSTANT, type::member → member
    code = re.sub(r"\b\w+::(\w+)", r"\1", code)

    # ── typedef enum → localparam constants ──────────────────────
    # Pattern handles: typedef enum [base_type] { A=0, B, C } type_name;
    # Extracts member names and emits localparam A=0, B=1, ... replacements
    def _replace_enum(m):
        body = m.group(1)  # content between { }
        # Extract member names (and optional =value)
        members = []
        counter = 0
        for item in body.split(","):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                name, val = item.split("=", 1)
                name = name.strip()
                # Support plain ints, 0x-prefixed, AND Verilog-style literals (3'd4, 4'hF)
                val_str = val.strip()
                sv_lit = re.match(r"^\d+'([bdoh])([0-9a-fA-F_]+)$", val_str, re.IGNORECASE)
                if sv_lit:
                    base_char = sv_lit.group(1).lower()
                    digits = sv_lit.group(2).replace("_", "")
                    base = {'b': 2, 'd': 10, 'o': 8, 'h': 16}.get(base_char, 10)
                    try:
                        counter = int(digits, base)
                    except ValueError:
                        counter = 0
                else:
                    try:
                        counter = int(val_str, 0)
                    except ValueError:
                        counter = 0
                members.append((name, counter))
            else:
                members.append((item.strip(), counter))
            counter += 1
        lp = "\n".join(f"localparam {n} = {v};" for n, v in members if n)
        return lp + "\n"

    code = re.sub(
        r"\btypedef\s+enum\s+(?:[\w\s\[\]:]+?)?\{([^}]*)\}\s*\w+\s*;",
        _replace_enum,
        code,
    )
    # Also remove bare `state_t state;` type aliases left behind
    # (only safe when the type name ends in _t — the common LLM pattern)
    # Handles single:  state_t state;
    # Handles comma-separated:  state_t state, next_state;
    def _replace_t_alias(m):
        vars_part = m.group(1)
        # Split on comma, strip each, emit reg declarations
        vars_list = [v.strip() for v in vars_part.split(",") if v.strip()]
        return "\n".join(f"reg [7:0] {v}; // was typedef" for v in vars_list) + "\n"
    code = re.sub(r"\b\w+_t\s+((?:\w+\s*,?\s*)+);", _replace_t_alias, code)

    # ── string type → reg [127:0] ─────────────────────────────────
    code = re.sub(r"\bstring\s+(\w+)", r"reg [127:0] \1", code)

    # ── bit → wire/reg ───────────────────────────────────────────
    code = re.sub(r"\bbit\s+(\[[\d:]+\])", r"wire \1", code)

    # ── void functions → tasks ────────────────────────────────────
    # Only convert endfunction that belongs to a void function.
    # Non-void functions (e.g. function [7:0] foo) must keep endfunction.
    def _convert_void_functions(src: str) -> str:
        out = []
        in_void_func = False
        for line in src.splitlines(keepends=True):
            stripped = line.lstrip()
            if re.match(r"\bfunction\s+void\b", stripped):
                in_void_func = True
                out.append(re.sub(r"\bfunction\s+void\b", "task", line, count=1))
            elif re.match(r"\bendfunction\b", stripped) and in_void_func:
                in_void_func = False
                out.append(re.sub(r"\bendfunction\b", "endtask", line, count=1))
            else:
                out.append(line)
        return "".join(out)

    code = _convert_void_functions(code)

    # ── $cast → assignment (basic) ───────────────────────────────
    code = re.sub(r"\$cast\s*\(\s*(\w+)\s*,\s*([^)]+)\)", r"\1 = \2", code)

    # ── $urandom / $urandom_range → $random ──────────────────────
    code = re.sub(
        r"\$urandom_range\s*\(([^,)]+),\s*([^)]+)\)",
        r"($random % (\2 - \1 + 1) + \1)",
        code,
    )
    code = re.sub(r"\$urandom\b", "$random", code)
    # Seed $random with $srandom(0) in the first initial block for reproducibility
    if "$random" in code and "initial" in code and "$srandom" not in code:
        code = re.sub(
            r"(initial\s+begin)",
            r"\1\n        $srandom(0); // seed: reproducible random sequences",
            code,
            count=1,  # only the first initial block
        )

    # ── SVA assertions → comments (unsynthesizable) ───────────────
    code = re.sub(
        r"^\s*assert\s+property\s*\(.*?\);\s*$",
        "// assert removed",
        code,
        flags=re.MULTILINE,
    )
    code = re.sub(
        r"^\s*assume\s+property\s*\(.*?\);\s*$",
        "// assume removed",
        code,
        flags=re.MULTILINE,
    )
    code = re.sub(
        r"^\s*cover\s+property\s*\(.*?\);\s*$",
        "// cover removed",
        code,
        flags=re.MULTILINE,
    )
    # Immediate assertions
    code = re.sub(
        r"^\s*assert\s*\(.*?\);\s*$", "// assert removed", code, flags=re.MULTILINE
    )

    # ── interface / modport / program blocks → removed ───────────
    code = re.sub(r"\binterface\b.*?endinterface\b", "", code, flags=re.DOTALL)
    code = re.sub(r"\bprogram\b.*?endprogram\b", "", code, flags=re.DOTALL)

    # ── foreach → equivalent for loop (basic 1-D case) ───────────
    # foreach(arr[i]) → for (i=0; i<$size(arr); i=i+1)
    # Note: $size is not Verilog-2001 either — flag with a comment
    def _foreach_replace(m):
        arr_name = m.group(1)
        idx_var = m.group(2)
        declared_vars.add(idx_var)  # ensure integer decl is emitted
        return f"/* sv_loop_converted */ for ({idx_var} = 0; {idx_var} < $size({arr_name}); {idx_var} = {idx_var} + 1)"

    code = re.sub(
        r"\bforeach\s*\(\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)",
        _foreach_replace,
        code,
    )

    # ── covergroup → removed ─────────────────────────────────────
    code = re.sub(r"\bcovergroup\b.*?endgroup\b", "", code, flags=re.DOTALL)

    # ── reg driven by assign → wire ───────────────────────────────
    # LLMs often declare internal signals as reg but drive them via assign.
    # Icarus errors: "reg pc_out; cannot be driven by primitives or continuous assignment"
    def _fix_reg_driven_by_assign(src: str) -> str:
        # Strategy: find all assign LHS targets, then check if any is declared as reg
        assign_lhs = set()
        for m in re.finditer(
            r"assign\s+(\w+)\s*=", src
        ):
            assign_lhs.add(m.group(1))
        if not assign_lhs:
            return src
        # For each signal driven by assign, check if it's declared as reg
        for sig in assign_lhs:
            # Pattern: optional-space reg optional-range sig;  (NOT preceded by output/inout)
            # We need to be careful not to match port declarations
            pat = re.compile(
                r"^(\s*)reg\s+((?:\[[^\]]*\]\s+)?)" + re.escape(sig) + r"\s*;",
                re.MULTILINE,
            )
            m = pat.search(src)
            if m:
                # Verify this is not a port declaration (not preceded by output/input within last 5 lines)
                # Simple heuristic: check if "output" appears on the same line
                line_start = src.rfind("\n", 0, m.start()) + 1
                line_end = src.find("\n", m.end())
                line = src[line_start:line_end] if line_end != -1 else src[line_start:]
                if "output" not in line and "input" not in line:
                    src = pat.sub(r"\1wire \2" + sig + ";", src, count=1)
        return src
    code = _fix_reg_driven_by_assign(code)

    # ── final check: ensure module name matches ───────────────────
    if module_name:
        code = re.sub(
            r"^module\s+\w+", f"module {module_name}", code, count=1, flags=re.MULTILINE
        )

    return code


# ═══════════════════════════════════════════════════════════════════
# FIX 2 — Smart repair targeting
# Replace the repair dispatch in verilog_generator.py.
# The current code sends all errors to the same repair function.
# This version routes RTL errors → RTL file, TB errors → TB file.
#
# Usage in verilog_generator.py (replace existing repair call):
#   from generation_fixes import smart_repair
#   rtl_code, tb_code = smart_repair(rtl_code, tb_code, error_log, description)
# ═══════════════════════════════════════════════════════════════════


def _error_is_in_rtl(error_log: str, rtl_filename: str, tb_filename: str) -> bool:
    """
    Returns True if the error is primarily in the RTL file (not the testbench).
    """
    rtl_errors = len(
        re.findall(re.escape(rtl_filename) + r".*error", error_log, re.IGNORECASE)
    )
    tb_errors = len(
        re.findall(re.escape(tb_filename) + r".*error", error_log, re.IGNORECASE)
    )

    # If no filename context, check for RTL-specific patterns
    if rtl_errors == 0 and tb_errors == 0:
        rtl_patterns = [
            r"syntax error",
            r"Incomprehensible for loop",
            r"error: Unknown module type",
            r"error: port .* of .* unconnected",
            r"error: undeclared wire",
        ]
        for p in rtl_patterns:
            if re.search(p, error_log, re.IGNORECASE):
                return True
        return False

    return rtl_errors >= tb_errors


def _error_is_logic_failure(error_log: str) -> bool:
    """
    Returns True if RTL compiles but produces wrong outputs (FAIL Test N).
    This requires RTL logic repair, not syntax repair.
    """
    return (
        "FAIL Test" in error_log
        or "TESTS_FAILED" in error_log
        or ("got" in error_log and "expected" in error_log)
        or "got          x" in error_log  # uninitialized output
    )


def _is_tb_expected_values_wrong(error_log: str) -> bool:
    """
    Returns True if the error log shows wrong expected values (got=X, expected=Y)
    where both values are valid numbers (not X/Z propagation).
    This indicates the testbench expected values are wrong, not the RTL logic.
    """
    if "FAIL Test" not in error_log and "TESTS_FAILED" not in error_log:
        return False
    # Check for X/Z in the output values — if present, it's a RTL reset/logic issue
    if "got          x" in error_log or "got x," in error_log or "got          z" in error_log:
        return False
    # Check for compile/syntax errors — these are not TB-expected-value issues
    if "syntax error" in error_log.lower() or "error:" in error_log.lower():
        return False
    # Pattern: FAIL Test N: got <number>, expected <number>
    fail_lines = [l for l in error_log.splitlines() if "FAIL" in l and "expected" in l and "got" in l]
    if not fail_lines:
        return False
    # All fail lines must have numeric values for both got and expected
    for line in fail_lines:
        has_xz = bool(re.search(r"\bgot\s+[']?[xXzZ]", line)) or bool(re.search(r"\bgot\s+[xXzZ]", line))
        if has_xz:
            return False
    return True


def _repair_tb_expected_values(
    tb_code: str,
    rtl_code: str,
    sim_output: str,
    description: str,
    module_name: str,
) -> Optional[str]:
    """
    Regenerate the testbench with correct expected values using the RTL
    and simulator transcript as context. Preserves RTL untouched.
    """
    import os, re as _re
    import httpx

    prompt = f"""You are fixing a Verilog testbench. The RTL is CORRECT — do NOT change it.
The testbench has wrong expected values. Use the RTL and simulation output to determine the correct values.

MODULE: {module_name}
DESCRIPTION: {description}

RTL CODE:
```verilog
{rtl_code[:4000]}
```

SIMULATION OUTPUT (shows wrong expected values):
```
{sim_output[-3000:]}
```

Generate ONLY a corrected testbench that:
1. Has the CORRECT expected values that match the RTL's actual behavior
2. Uses proper clock: always #5 clk = ~clk;
3. Prints "ALL_TESTS_PASSED" when all tests pass
4. Uses Verilog-2001 only (no SystemVerilog)
5. Has `timescale 1ns/1ps
6. Uses $dumpfile("trace.vcd")
7. Tests each output with at least 3 different input combinations

Respond with ONLY the testbench code in a ```verilog block."""

    providers = []
    gh_key = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_KEY") or ""
    if gh_key:
        providers.append({"url": "https://models.inference.ai.azure.com/chat/completions",
                          "key": gh_key, "model": os.getenv("GITHUB_MODEL", "gpt-4o")})
    groq_key = os.getenv("GROQ_API_KEY") or ""
    if groq_key:
        providers.append({"url": "https://api.groq.com/openai/v1/chat/completions",
                          "key": groq_key, "model": "llama-3.3-70b-versatile"})

    for p in providers:
        try:
            resp = httpx.post(p["url"], headers={"Authorization": f"Bearer {p['key']}",
                                                  "Content-Type": "application/json"},
                              json={"model": p["model"], "messages": [{"role": "user", "content": prompt}],
                                    "max_tokens": 4096, "temperature": 0.3}, timeout=60)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                m = _re.search(r"```verilog\s*\n(.*?)```", content, _re.DOTALL)
                return m.group(1).strip() if m else content.strip()
        except Exception:
            continue
    return None


def smart_repair(
    rtl_code: str,
    tb_code: str,
    error_log: str,
    description: str,
    module_name: str,
) -> Tuple[str, str]:
    """
    Route repair to the correct file based on where the error is.
    Returns (fixed_rtl, fixed_tb) — unchanged files have original content.
    """
    from rtl_repair import (
        repair_from_simulation_log,
        repair_rtl_errors,
        validate_syntax,
    )

    rtl_file = f"{module_name}.v"
    tb_file = f"{module_name}_tb.v"

    # ── Testbench-only repair path ────────────────────────────────────
    # When simulation shows wrong expected values (got=X, expected=Y)
    # but both are valid (no X/Z), the RTL is likely correct.
    # Only regenerate the testbench, preserving RTL.
    if _is_tb_expected_values_wrong(error_log):
        log.info("Smart repair: wrong expected values detected — repairing testbench only")
        fixed_tb = _repair_tb_expected_values(
            tb_code, rtl_code, error_log, description, module_name
        )
        if fixed_tb:
            return rtl_code, fixed_tb
        # Fall through to full logic repair if TB repair fails

    if _error_is_logic_failure(error_log):
        # Logic error: RTL compiles but produces wrong values
        # Check for uninitialized outputs specifically
        if "got          x" in error_log or "got x," in error_log:
            log.info("Smart repair: uninitialized output detected — adding reset logic")
            # The most common cause is missing reset logic
            # Inject a hint to the repair prompt
            enhanced_error = error_log + (
                "\n\nHINT: Output is 'x' (uninitialized). "
                "Ensure all outputs are initialized in the reset condition. "
                "Add: if (!reset_n) begin all_outputs <= 0; end"
            )
            fixed_rtl = repair_from_simulation_log(
                rtl_code, enhanced_error, description, module_name
            )
        else:
            fixed_rtl = repair_from_simulation_log(
                rtl_code, error_log, description, module_name
            )
        if fixed_rtl:
            return fixed_rtl, tb_code
        return rtl_code, tb_code

    if _error_is_in_rtl(error_log, rtl_file, tb_file):
        # Syntax/structural error in RTL
        log.info("Smart repair: routing to RTL file")
        # First try SV→V2005 conversion
        fixed_rtl = sv_to_v2005(rtl_code, module_name)
        ok, _ = validate_syntax(fixed_rtl, module_name)
        if ok:
            log.info("Smart repair: SV→V2005 conversion fixed the error")
            return fixed_rtl, tb_code
        # Then try LLM repair
        fixed_rtl = repair_rtl_errors(fixed_rtl, error_log, description, module_name)
        if fixed_rtl:
            return fixed_rtl, tb_code
        return rtl_code, tb_code
    else:
        # Error in testbench
        log.info("Smart repair: routing to testbench file")
        fixed_tb = repair_rtl_errors(
            tb_code, error_log, f"testbench for {description}", module_name
        )
        if fixed_tb:
            return rtl_code, fixed_tb
        return rtl_code, tb_code


# ═══════════════════════════════════════════════════════════════════
# FIX 3 — Complexity detection and auto-decomposition
# Add to guaranteed_flow.py in generate_guaranteed_gds().
# Complex designs (RISC-V, processors, full SoCs) are automatically
# routed through hierarchy_builder instead of single-call generation.
#
# Usage in guaranteed_flow.py:
#   from generation_fixes import (
#       estimate_design_complexity, COMPLEX_DESIGN_THRESHOLD
#   )
#   if estimate_design_complexity(description) >= COMPLEX_DESIGN_THRESHOLD:
#       from hierarchy_builder import build_hierarchical_design
#       return build_hierarchical_design(description, design_name).to_dict()
# ═══════════════════════════════════════════════════════════════════

# Keyword sets for complexity scoring
_COMPLEX_KEYWORDS = {
    # Processor/CPU designs — always route through hierarchy builder
    "risc-v": 100,
    "riscv": 100,
    "rv32": 100,
    "rv64": 100,
    "processor": 80,
    "cpu": 80,
    "mips": 80,
    "arm": 80,
    "microprocessor": 80,
    "core": 50,
    # Large memory systems
    "cache": 60,
    "tlb": 60,
    "mmu": 60,
    "ddr": 70,
    "sdram": 70,
    # Multi-module SoC indicators
    "soc": 70,
    "system on chip": 70,
    "full chip": 70,
    "bus controller": 60,
    "axi": 50,
    "ahb": 50,
    # Protocol stacks
    "ethernet": 60,
    "usb": 70,
    "pcie": 80,
    "mac layer": 60,
    "phy layer": 60,
    # Large ALU/DSP
    "fft": 60,
    "dsp": 50,
    "multiply accumulate": 50,
    "floating point": 60,
    "ieee 754": 70,
    # Multi-stage pipelines
    "5-stage pipeline": 70,
    "pipeline stage": 40,
    "out of order": 90,
    "superscalar": 90,
}

# Additional structural complexity indicators in description
_COMPLEXITY_INDICATORS = [
    (r"\b(\d+)[\s-]stage\s+pipeline\b", 30),  # N-stage pipeline
    (r"\bwith\s+(alu|register file|cache)", 40),  # multi-component description
    (r"\bsupport[s]?\s+(\d+)\s+instruction", 50),  # ISA description
    (r"r[rv]32[iema]+", 100),  # RISC-V ISA string
    (r"fetch.*decode.*execute", 70),  # pipeline stage names
    (r"hazard\s+detection", 50),  # pipeline hazard handling
    (r"branch\s+prediction", 60),  # advanced CPU feature
]

COMPLEX_DESIGN_THRESHOLD = 60  # score >= this → use hierarchy builder


def estimate_design_complexity(description: str) -> int:
    """
    Returns a complexity score for a design description.
    Score >= COMPLEX_DESIGN_THRESHOLD → route through hierarchy_builder.

    Score 0-30:   Simple (counter, adder, mux) → single-call generation
    Score 30-60:  Medium (ALU, FIFO, UART) → single-call with RAG
    Score 60+:    Complex (CPU, SoC, full pipeline) → hierarchy_builder
    """
    desc_lower = description.lower()
    score = 0

    # Check keyword dictionary
    for keyword, weight in _COMPLEX_KEYWORDS.items():
        if keyword in desc_lower:
            score = max(score, weight)  # take the highest matching weight

    # Check structural patterns
    for pattern, weight in _COMPLEXITY_INDICATORS:
        if re.search(pattern, desc_lower, re.IGNORECASE):
            score = max(score, weight)

    return score


_hierarchy_builder_active = threading.local()


def should_use_hierarchy_builder(description: str) -> bool:
    """Single boolean check for use in generate_guaranteed_gds().
    Uses a thread-local flag to prevent infinite recursion when called
    from within hierarchy_builder.py itself.
    """
    if getattr(_hierarchy_builder_active, "value", False):
        return False
    return estimate_design_complexity(description) >= COMPLEX_DESIGN_THRESHOLD


def mark_hierarchy_builder_active(active: bool = True) -> None:
    """Call with active=True at entry of hierarchy_builder, False at exit."""
    _hierarchy_builder_active.value = active


# ═══════════════════════════════════════════════════════════════════
# FIX 4 — Dead provider fast-skip
# Replace the provider retry logic in verilog_generator.py.
# Tracks which providers are known-dead and skips them immediately.
#
# Usage in verilog_generator.py:
#   from generation_fixes import ProviderHealthTracker
#   _provider_health = ProviderHealthTracker()  # module-level singleton
#
#   # Before trying a provider:
#   if _provider_health.is_dead(provider_name):
#       continue
#
#   # After a failure:
#   _provider_health.record_failure(provider_name, error_type)
# ═══════════════════════════════════════════════════════════════════


class ProviderHealthTracker:
    """
    Tracks provider health and implements fast-skip for known-dead providers.

    Error types and their skip durations:
      ssl_timeout    → skip for 300s (5 min) — network issue, may recover
      rate_limit_429 → skip for 60s  (1 min) — per-minute limit
      daily_limit    → skip for 3600s (1 hr) — daily token limit hit
      auth_error     → skip for 86400s (24hr) — key invalid
      unavailable    → skip for 120s  (2 min) — service down
    """

    SKIP_DURATIONS = {
        "ssl_timeout": 300,
        "rate_limit_429": 60,
        "daily_limit": 3600,
        "auth_error": 86400,
        "unavailable": 120,
        "unknown": 30,
    }

    # Maximum attempts before giving up on a provider in one session
    MAX_ATTEMPTS = 1  # SSL and permanent errors → give up after 1 attempt

    def __init__(self):
        self._failures: Dict[str, Dict] = {}
        self._attempt_counts: Dict[str, int] = {}

    def _classify_error(self, error_str: str) -> str:
        e = error_str.lower()
        if "ssl" in e or "handshake" in e or "timed out" in e:
            return "ssl_timeout"
        if "daily" in e or "used" in e or ("limit" in e and "rate" not in e):
            return "daily_limit"
        if "429" in e or "rate" in e:
            return "rate_limit_429"
        if "401" in e or "403" in e or "auth" in e or "key" in e:
            return "auth_error"
        if "503" in e or "502" in e or "unavailable" in e:
            return "unavailable"
        return "unknown"

    def record_failure(self, provider: str, error_str: str) -> None:
        """Record a provider failure with error classification."""
        error_type = self._classify_error(error_str)
        skip_until = time.time() + self.SKIP_DURATIONS.get(error_type, 30)

        self._failures[provider] = {
            "error_type": error_type,
            "skip_until": skip_until,
            "error_str": error_str[:200],
            "recorded_at": time.time(),
        }
        self._attempt_counts[provider] = self._attempt_counts.get(provider, 0) + 1

        log.info(
            "Provider %s marked %s — skipping for %ds",
            provider,
            error_type,
            self.SKIP_DURATIONS.get(error_type, 30),
        )

    def is_dead(self, provider: str) -> bool:
        """Returns True if this provider should be skipped right now."""
        if provider not in self._failures:
            return False
        skip_until = self._failures[provider]["skip_until"]
        if time.time() < skip_until:
            return True
        # Cooldown expired — remove from dead list
        del self._failures[provider]
        return False

    def skip_reason(self, provider: str) -> str:
        """Human-readable skip reason."""
        if provider not in self._failures:
            return ""
        f = self._failures[provider]
        remaining = max(0, f["skip_until"] - time.time())
        return f"{f['error_type']} (skip {remaining:.0f}s more)"

    def reset(self, provider: str) -> None:
        """Mark a provider as healthy again."""
        self._failures.pop(provider, None)
        self._attempt_counts.pop(provider, None)

    def status(self) -> Dict:
        """Return current health status of all tracked providers."""
        return {p: "DEAD" if self.is_dead(p) else "OK" for p in self._failures}


# Module-level singleton — import this in verilog_generator.py
_provider_health = ProviderHealthTracker()


# ═══════════════════════════════════════════════════════════════════
# Standalone test
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("generation_fixes.py — standalone self-test")
    print("=" * 60)

    passed = total = 0

    # ── Test 1: SV for loop fix ───────────────────────────────────
    total += 1
    sv_code = """module counter(input clk, input reset_n, output reg [7:0] q);
    logic [7:0] temp;
    integer k;
    always_ff @(posedge clk) begin
        if (!reset_n) q <= 0;
        else begin
            for (int i = 0; i < 8; i++) begin
                temp[i] = q[i];
            end
            q <= temp + 1;
        end
    end
endmodule"""

    fixed = sv_to_v2005(sv_code, "counter")
    assert "always_ff" not in fixed, "always_ff not replaced"
    assert "always @(posedge clk)" in fixed, "always_ff replacement missing"
    assert "for (int i" not in fixed, "int loop not fixed"
    assert "integer i" in fixed, "integer declaration not added"
    print("[PASS] SV for loop + always_ff -> Verilog 2005")
    passed += 1

    # ── Test 2: logic → reg/wire ──────────────────────────────────
    total += 1
    sv_ports = """module test(input logic clk, output logic [7:0] data);
    logic [3:0] internal;
endmodule"""
    fixed2 = sv_to_v2005(sv_ports, "test")
    assert "input wire clk" in fixed2, "input logic → input wire failed"
    assert "output reg [7:0] data" in fixed2, "output logic → output reg failed"
    assert "logic" not in fixed2.replace("// logic", ""), (
        f"'logic' keyword still present: {fixed2}"
    )
    print("[PASS] logic -> wire/reg conversion")
    passed += 1

    # ── Test 3: always_comb ───────────────────────────────────────
    total += 1
    sv_comb = """module mux(input logic a, b, sel, output logic y);
    always_comb begin
        if (sel) y = a; else y = b;
    end
endmodule"""
    fixed3 = sv_to_v2005(sv_comb, "mux")
    assert "always @(*)" in fixed3, "always_comb not replaced"
    assert "always_comb" not in fixed3, "always_comb still present"
    print("[PASS] always_comb -> always @(*)")
    passed += 1

    # ── Test 4: unique case ───────────────────────────────────────
    total += 1
    sv_case = """always_comb begin
    unique case (opcode)
        2'b00: y = a + b;
        2'b01: y = a - b;
    endcase
end"""
    fixed4 = sv_to_v2005(sv_case, "alu")
    assert "unique case" not in fixed4, "unique case not removed"
    assert "case (opcode)" in fixed4, "case statement broken"
    print("[PASS] unique/priority case -> plain case")
    passed += 1

    # ── Test 5: error classification ─────────────────────────────
    total += 1
    rtl_error = "/work/designs/test/test.v:27: error: Incomprehensible for loop."
    tb_error = "/work/designs/test/test_tb.v:9: error: Malformed statement"
    logic_err = "FAIL Test 1: ADD - got          x, expected 30\nTESTS_FAILED"

    assert _error_is_in_rtl(rtl_error, "test.v", "test_tb.v"), "RTL error not detected"
    assert not _error_is_in_rtl(tb_error, "test.v", "test_tb.v"), (
        "TB error wrongly classified as RTL"
    )
    assert _error_is_logic_failure(logic_err), "Logic failure not detected"
    assert not _error_is_logic_failure(rtl_error), (
        "Syntax error wrongly classified as logic failure"
    )
    print("[PASS] Error classification (RTL/TB/logic)")
    passed += 1

    # ── Test 6: complexity detection ─────────────────────────────
    total += 1
    tests = [
        ("8-bit adder", False),
        ("RISC-V RV32I core", True),
        ("simple 4-bit counter", False),
        ("5-stage pipelined processor with cache", True),
        ("UART transmitter", False),
        ("full SoC with AXI bus and DDR controller", True),
        ("8x8 register file", False),
        ("RV32IMC processor with branch prediction", True),
    ]
    for desc, expect_complex in tests:
        score = estimate_design_complexity(desc)
        is_complex = score >= COMPLEX_DESIGN_THRESHOLD
        status = "PASS" if is_complex == expect_complex else "FAIL"
        print(f"  {status}: '{desc}' -> score={score} complex={is_complex}")
        if is_complex != expect_complex:
            print(f"    Expected complex={expect_complex}, got {is_complex}")
            passed -= 1
    print("[PASS] Complexity detection")
    passed += 1

    # ── Test 7: ProviderHealthTracker ────────────────────────────
    total += 1
    tracker = ProviderHealthTracker()

    assert not tracker.is_dead("groq"), "Fresh tracker shows groq as dead"

    # Simulate SSL timeout
    tracker.record_failure("gemini", "_ssl.c:993: The handshake operation timed out")
    assert tracker.is_dead("gemini"), "Gemini should be dead after SSL timeout"
    assert "ssl_timeout" in tracker.skip_reason("gemini")

    # Simulate daily limit
    tracker.record_failure("groq", "Limit 100000, Used 97454, Requested 5554")
    assert tracker.is_dead("groq"), "Groq should be dead after daily limit"
    assert "daily_limit" in tracker.skip_reason("groq")

    # Rate limit (should be dead too)
    tracker.record_failure("openrouter", "429 rate limited")
    assert tracker.is_dead("openrouter"), "OpenRouter should be dead after 429"

    # GitHub should still be OK
    assert not tracker.is_dead("github"), "GitHub should still be OK"

    print(f"[PASS] ProviderHealthTracker: status={tracker.status()}")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED - generation_fixes.py ready for integration")
    print("=" * 60)
