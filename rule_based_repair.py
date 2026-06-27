"""
rule_based_repair.py — Deterministic RTL/TB Repair Engine
RTL-Gen AI

Runs BEFORE any LLM repair call. If all validation errors are resolved
by rule-based fixes, the LLM repair step is skipped entirely.

Integration — in verilog_generator.py, replace Step 1 with:
    from rule_based_repair import RuleBasedRepairEngine, ErrorClassifier
    engine = RuleBasedRepairEngine()
    rtl, tb, applied = engine.apply(rtl, tb, validation["errors"], module_name)
    if applied and not validate_verilog_syntax(rtl, tb, module_name)["errors"]:
        # Skip LLM repair

Standalone test:
    python rule_based_repair.py
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


class ErrorClassifier:
    """
    Maps validation error messages to deterministic repair rule names.

    Each entry maps a substring of the validation error message
    (from validate_verilog_syntax) to the corresponding handler method
    on RuleBasedRepairEngine.
    """

    RULE_MAP: Dict[str, str] = {
        "Testbench missing ALL_TESTS_PASSED": "add_all_tests_passed",
        "No proper clock in testbench": "add_clock_gen",
        "No VCD dump": "add_vcd_dump",
        "Missing `timescale": "add_timescale",
        "Module name mismatch": "fix_module_name",
        "Missing $finish": "add_finish",
        "Missing reset sequence": "add_reset_sequence",
        "Missing default case": "add_default_case",
        "Missing newline at EOF": "add_newline_eof",
    }

    @classmethod
    def classify(cls, error_message: str) -> Optional[str]:
        """Return the rule name for a validation error, or None if no rule matches."""
        for pattern, rule in cls.RULE_MAP.items():
            if pattern in error_message:
                return rule
        return None


class RuleBasedRepairEngine:
    """
    Applies deterministic (zero-LLM) repair handlers to Verilog RTL and testbench code.

    Each handler is a static method that takes code and optional context
    and returns fixed code.  If no change is needed the handler returns the
    original string unchanged.

    Usage:
        engine = RuleBasedRepairEngine()
        fixed_rtl, fixed_tb, rules = engine.apply(rtl, tb, errors, module_name)
    """

    # ── Handlers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def add_all_tests_passed(tb_code: str, module_name: str) -> str:
        """Inject a conditional ALL_TESTS_PASSED / TESTS_FAILED block at the end of the testbench initial block."""
        if "ALL_TESTS_PASSED" in tb_code:
            return tb_code

        marker = (
            '\n        // Final report\n'
            '        $display("RESULTS: %0d PASS / %0d FAIL", pass_count, fail_count);\n'
            '        if (fail_count == 0)\n'
            '            $display("ALL_TESTS_PASSED");\n'
            '        else\n'
            '            $display("TESTS_FAILED");\n'
        )

        # Insert before $finish if present, otherwise before end of last initial block
        finish_pos = tb_code.rfind("$finish")
        if finish_pos != -1:
            return tb_code[:finish_pos] + marker + "        " + tb_code[finish_pos:]

        # Find the last end of initial block
        initial_ends = [m.end() for m in re.finditer(r"\bend\b", tb_code)]
        if initial_ends:
            pos = initial_ends[-1]
            # Find the corresponding `initial` that owns this end
            return tb_code[:pos] + marker + tb_code[pos:]

        return tb_code

    @staticmethod
    def add_finish(tb_code: str, module_name: str) -> str:
        """Add $finish before the end of the last initial block if missing."""
        if "$finish" in tb_code:
            return tb_code

        marker = '\n        #50;\n        $finish;\n'

        # Insert before the final end that closes an initial block
        initial_starts = [m.start() for m in re.finditer(r"\binitial\b", tb_code)]
        initial_ends = [m.end() for m in re.finditer(r"\bend\b", tb_code)]

        if initial_starts and initial_ends:
            # Find the end that belongs to the last initial block
            last_initial_start = initial_starts[-1]
            for pos in reversed(initial_ends):
                if pos > last_initial_start:
                    return tb_code[:pos] + marker + tb_code[pos:]

        # Fallback: before last endmodule
        endmodule_pos = tb_code.rfind("endmodule")
        if endmodule_pos != -1:
            return tb_code[:endmodule_pos] + marker + tb_code[endmodule_pos:]

        return tb_code

    @staticmethod
    def add_timescale(code: str) -> str:
        """Prepend `timescale 1ns/1ps if missing."""
        if "`timescale" in code:
            return code
        return "`timescale 1ns/1ps\n" + code

    @staticmethod
    def fix_module_name(code: str, expected_name: str) -> str:
        """Fix the module declaration to match the expected name."""
        m = re.search(r"module\s+(\w+)", code)
        if not m:
            return code
        actual = m.group(1)
        if actual == expected_name:
            return code
        return re.sub(
            rf"\bmodule\s+{re.escape(actual)}\b",
            f"module {expected_name}",
            code,
            count=1,
        )

    @staticmethod
    def add_clock_gen(tb_code: str, module_name: str) -> str:
        """Add 'always #5 clk = ~clk' if no clock generation pattern is found."""
        if re.search(r"always\s+#\d+\s+clk\s*=", tb_code):
            return tb_code

        # Ensure clk is initialized to 0 first
        if "initial clk = 0" not in tb_code and "clk = 0" not in tb_code.split("initial")[-1][:50]:
            tb_code = re.sub(
                r"(initial\s+begin)",
                r"\1\n        clk = 0;",
                tb_code,
                count=1,
            )

        # Add clock generation inside but before endmodule
        clock_block = "\n    // Clock generation\n    always #5 clk = ~clk;\n"
        endmodule_pos = tb_code.rfind("endmodule")
        if endmodule_pos != -1:
            return tb_code[:endmodule_pos] + clock_block + tb_code[endmodule_pos:]
        return tb_code + clock_block

    @staticmethod
    def add_reset_sequence(tb_code: str, module_name: str) -> str:
        """
        Add a proper active-low reset sequence (reset_n = 0, wait 2 cycles, release).
        Only inserts if 'reset_n' appears in the code but no drive pattern is found.
        """
        if "reset_n" not in tb_code:
            return tb_code
        if "reset_n = 0" in tb_code or "reset_n <= 0" in tb_code:
            return tb_code

        reset_seq = (
            "\n        // Reset sequence\n"
            "        reset_n = 0;\n"
            '        #10; #10;\n'
            "        reset_n = 1;\n"
        )

        # Insert after VCD dump or after initial begin
        dumpfile_pos = tb_code.rfind("$dumpvars")
        if dumpfile_pos != -1:
            line_end = tb_code.find("\n", dumpfile_pos)
            if line_end != -1:
                return tb_code[:line_end] + reset_seq + tb_code[line_end:]

        # Fallback: after first begin of an initial block
        m = re.search(r"(initial\s+begin\s*\n)", tb_code)
        if m:
            pos = m.end()
            return tb_code[:pos] + "    " + reset_seq.strip() + "\n" + tb_code[pos:]

        return tb_code

    @staticmethod
    def add_vcd_dump(tb_code: str, module_name: str) -> str:
        """Add $dumpfile and $dumpvars if missing."""
        if "dumpfile" in tb_code:
            return tb_code
        tb_name = f"{module_name}_tb"
        vcd_block = (
            '\n        $dumpfile("trace.vcd");\n'
            f'        $dumpvars(0, {tb_name});\n'
        )
        m = re.search(r"(initial\s+begin\s*\n)", tb_code)
        if m:
            pos = m.end()
            return tb_code[:pos] + vcd_block + tb_code[pos:]
        return tb_code

    @staticmethod
    def add_default_case(rtl_code: str) -> str:
        """
        Adds a 'default: ;' clause to every case/casex/casez statement
        that lacks one.  This prevents inferred latches in synthesis.
        """
        case_pattern = re.compile(
            r"(case[zx]?\s*\([^)]*\))(.*?)(endcase)",
            re.DOTALL,
        )

        def _ensure_default(m):
            header = m.group(1)
            body = m.group(2)
            closer = m.group(3)
            if "default" in body:
                return m.group(0)
            indent = "        "
            for line in body.splitlines(keepends=True):
                stripped = line.lstrip()
                if stripped.startswith("//") or stripped.startswith("/*"):
                    continue
                ws = line[: len(line) - len(line.lstrip())]
                if ws and ws.count(" ") >= 2:
                    indent = ws
                    break
            body += f"{indent}default: ;\n"
            return header + body + closer

        return case_pattern.sub(_ensure_default, rtl_code)

    @staticmethod
    def add_newline_eof(code: str) -> str:
        """Ensure the file ends with exactly one newline."""
        code = code.rstrip("\n")
        return code + "\n"

    # ── Dispatch ─────────────────────────────────────────────────────────────────

    def apply(
        self,
        rtl_code: str,
        tb_code: str,
        errors: List[str],
        module_name: str,
    ) -> Tuple[str, str, List[str]]:
        """
        Apply all matching repair rules.

        Args:
            rtl_code:    Verilog RTL source
            tb_code:     Verilog testbench source
            errors:      Validation error strings from validate_verilog_syntax()
            module_name: Expected module name

        Returns:
            (fixed_rtl, fixed_tb, list_of_applied_rule_names)
        """
        applied: List[str] = []

        # Rules that operate on testbench
        _TB_RULES = {"add_all_tests_passed", "add_finish", "add_clock_gen", "add_vcd_dump", "add_reset_sequence"}
        # Rules that operate on RTL
        _RTL_RULES = {"add_default_case"}

        for err in errors:
            rule_name = ErrorClassifier.classify(err)
            if rule_name is None:
                continue

            handler = getattr(self, rule_name, None)
            if handler is None:
                continue

            if rule_name in _TB_RULES:
                new_tb = handler(tb_code, module_name)
                if new_tb != tb_code:
                    log.info("Rule repair applied: %s (testbench)", rule_name)
                    print(f"  Rule repair applied: {rule_name} (testbench)")
                    tb_code = new_tb
                    applied.append(rule_name)
            elif rule_name in _RTL_RULES:
                new_rtl = handler(rtl_code)
                if new_rtl != rtl_code:
                    log.info("Rule repair applied: %s (RTL)", rule_name)
                    print(f"  Rule repair applied: {rule_name} (RTL)")
                    rtl_code = new_rtl
                    applied.append(rule_name)
            elif rule_name == "add_timescale":
                new_tb = handler(tb_code)
                if new_tb != tb_code:
                    log.info("Rule repair applied: add_timescale (testbench)")
                    print("  Rule repair applied: add_timescale (testbench)")
                    tb_code = new_tb
                    applied.append("add_timescale")
                new_rtl = handler(rtl_code)
                if new_rtl != rtl_code:
                    log.info("Rule repair applied: add_timescale (RTL)")
                    print("  Rule repair applied: add_timescale (RTL)")
                    rtl_code = new_rtl
                    if "add_timescale" not in applied:
                        applied.append("add_timescale")
            elif rule_name == "fix_module_name":
                new_rtl = handler(rtl_code, module_name)
                if new_rtl != rtl_code:
                    log.info("Rule repair applied: fix_module_name (RTL)")
                    print("  Rule repair applied: fix_module_name (RTL)")
                    rtl_code = new_rtl
                    applied.append("fix_module_name")
            elif rule_name == "add_newline_eof":
                new_rtl = handler(rtl_code)
                if new_rtl != rtl_code:
                    rtl_code = new_rtl
                    applied.append("add_newline_eof (RTL)")
                new_tb = handler(tb_code)
                if new_tb != tb_code:
                    tb_code = new_tb
                    applied.append("add_newline_eof (testbench)")

        return rtl_code, tb_code, applied


# ── Standalone self-test ─────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    print("=" * 60)
    print("rule_based_repair.py — standalone self-test")
    print("=" * 60)

    passed = total = 0
    engine = RuleBasedRepairEngine()

    # ── Test 1: ErrorClassifier ──
    total += 1
    assert ErrorClassifier.classify("Testbench missing ALL_TESTS_PASSED — pipeline requires it") == "add_all_tests_passed"
    assert ErrorClassifier.classify("No proper clock in testbench — add: always #5 clk = ~clk") == "add_clock_gen"
    assert ErrorClassifier.classify("No VCD dump — add $dumpfile for waveform viewing") == "add_vcd_dump"
    assert ErrorClassifier.classify("Module name mismatch — expected 'module foo'") == "fix_module_name"
    assert ErrorClassifier.classify("Some random error") is None
    print("[PASS] ErrorClassifier maps validation messages correctly")
    passed += 1

    # ── Test 2: add_all_tests_passed ──
    total += 1
    tb_no_pass = (
        "module foo_tb;\n"
        "initial begin\n"
        "    $display(\"test\");\n"
        "    $finish;\n"
        "end\n"
        "endmodule\n"
    )
    fixed = engine.add_all_tests_passed(tb_no_pass, "foo")
    assert "ALL_TESTS_PASSED" in fixed
    assert "TESTS_FAILED" in fixed
    assert "$finish" in fixed  # still there
    print("[PASS] add_all_tests_passed injects ALL_TESTS_PASSED/TESTS_FAILED")
    passed += 1

    # ── Test 3: add_finish ──
    total += 1
    tb_no_finish = (
        "module foo_tb;\n"
        "initial begin\n"
        "    $display(\"test\");\n"
        "end\n"
        "endmodule\n"
    )
    fixed = engine.add_finish(tb_no_finish, "foo")
    assert "$finish" in fixed
    print("[PASS] add_finish inserts $finish")
    passed += 1

    # ── Test 4: add_timescale ──
    total += 1
    code_no_ts = "module foo;\nendmodule\n"
    fixed = engine.add_timescale(code_no_ts)
    assert fixed.startswith("`timescale")
    assert "module foo" in fixed
    # Idempotent
    assert engine.add_timescale(fixed) == fixed
    print("[PASS] add_timescale prepends `timescale")
    passed += 1

    # ── Test 5: fix_module_name ──
    total += 1
    code_wrong = "module wrong_name(input clk);\nendmodule\n"
    fixed = engine.fix_module_name(code_wrong, "bar")
    assert "module bar" in fixed
    assert "wrong_name" not in fixed
    # Idempotent
    assert engine.fix_module_name(fixed, "bar") == fixed
    print("[PASS] fix_module_name corrects module name")
    passed += 1

    # ── Test 6: add_clock_gen ──
    total += 1
    tb_no_clk = (
        "module foo_tb;\n"
        "initial begin\n"
        "    $display(\"test\");\n"
        "    $finish;\n"
        "end\n"
        "endmodule\n"
    )
    fixed = engine.add_clock_gen(tb_no_clk, "foo")
    assert "always #5 clk = ~clk" in fixed
    assert "clk = 0" in fixed
    print("[PASS] add_clock_gen inserts clock generation")
    passed += 1

    # ── Test 7: add_reset_sequence ──
    total += 1
    tb_no_rst = (
        "module foo_tb;\n"
        "reg clk, reset_n;\n"
        "initial begin\n"
        "    $dumpfile(\"trace.vcd\");\n"
        "    $dumpvars(0, foo_tb);\n"
        "    $finish;\n"
        "end\n"
        "endmodule\n"
    )
    fixed = engine.add_reset_sequence(tb_no_rst, "foo")
    assert "reset_n = 0" in fixed
    assert "reset_n = 1" in fixed
    print("[PASS] add_reset_sequence injects reset drive")
    passed += 1

    # ── Test 8: add_vcd_dump ──
    total += 1
    tb_no_vcd = (
        "module foo_tb;\n"
        "initial begin\n"
        "    $display(\"test\");\n"
        "    $finish;\n"
        "end\n"
        "endmodule\n"
    )
    fixed = engine.add_vcd_dump(tb_no_vcd, "foo")
    assert "dumpfile" in fixed
    assert "dumpvars" in fixed
    print("[PASS] add_vcd_dump injects VCD dump")
    passed += 1

    # ── Test 9: add_default_case ──
    total += 1
    rtl_no_default = (
        "module foo(input [1:0] sel, output reg y);\n"
        "always @(*) begin\n"
        "    case (sel)\n"
        "        2'b00: y = 0;\n"
        "        2'b01: y = 1;\n"
        "    endcase\n"
        "end\n"
        "endmodule\n"
    )
    fixed = engine.add_default_case(rtl_no_default)
    assert "default: ;" in fixed
    print("[PASS] add_default_case adds default clause")
    passed += 1

    # ── Test 10: add_newline_eof ──
    total += 1
    code_no_nl = "module foo;\nendmodule"
    fixed = engine.add_newline_eof(code_no_nl)
    assert fixed.endswith("\n")
    assert fixed.count("\n") == code_no_nl.count("\n") + 1
    # Idempotent
    assert engine.add_newline_eof(fixed) == fixed
    print("[PASS] add_newline_eof ensures trailing newline")
    passed += 1

    # ── Test 11: Integration — apply() with matching errors ──
    total += 1
    rtl = "module wrong_name;\nendmodule"
    tb = (
        "module wrong_name_tb;\n"
        "initial begin\n"
        "    $display(\"test\");\n"
        "    $finish;\n"
        "end\n"
        "endmodule"
    )
    errors = [
        "Module name mismatch — expected 'module correct_name'",
    ]
    fixed_rtl, fixed_tb, applied = engine.apply(rtl, tb, errors, "correct_name")
    assert "module correct_name" in fixed_rtl
    assert "fix_module_name" in applied
    print("[PASS] Engine.apply() fixes module name and returns applied rules")
    passed += 1

    # ── Test 12: Integration — no LLM call triggered (no matching errors) ──
    total += 1
    rtl_ok = "module ok(input clk);\nendmodule\n"
    tb_ok = (
        "module ok_tb;\n"
        "initial begin\n"
        "    $display(\"test\");\n"
        "    $finish;\n"
        "end\n"
        "endmodule\n"
    )
    errors_no_match = ["RTL code has syntax error"]
    fixed_rtl, fixed_tb, applied = engine.apply(rtl_ok, tb_ok, errors_no_match, "ok")
    assert applied == []
    assert fixed_rtl == rtl_ok
    assert fixed_tb == tb_ok
    print("[PASS] Engine.apply() returns empty when no rules match")
    passed += 1

    # ── Test 13: add_default_case — idempotent ──
    total += 1
    rtl_with_default = (
        "module foo(input [1:0] sel, output reg y);\n"
        "always @(*) begin\n"
        "    case (sel)\n"
        "        2'b00: y = 0;\n"
        "        2'b01: y = 1;\n"
        "        default: y = 0;\n"
        "    endcase\n"
        "end\n"
        "endmodule\n"
    )
    fixed = engine.add_default_case(rtl_with_default)
    assert fixed == rtl_with_default
    print("[PASS] add_default_case is idempotent")
    passed += 1

    # ── Test 14: add_clock_gen — idempotent ──
    total += 1
    tb_with_clk = (
        "module foo_tb;\n"
        "initial clk = 0;\n"
        "always #5 clk = ~clk;\n"
        "initial begin\n"
        "    $finish;\n"
        "end\n"
        "endmodule\n"
    )
    fixed = engine.add_clock_gen(tb_with_clk, "foo")
    assert fixed == tb_with_clk
    print("[PASS] add_clock_gen is idempotent")
    passed += 1

    # ── Test 15: add_newline_eof — also works on testbench ──
    total += 1
    tb_no_nl = "module t;\ninitial $finish;\nendmodule"
    fixed = engine.add_newline_eof(tb_no_nl)
    assert fixed.endswith("\n")
    print("[PASS] add_newline_eof works on testbench")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED — rule_based_repair.py ready for integration")
    print("=" * 60)
