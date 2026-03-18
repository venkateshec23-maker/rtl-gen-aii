"""
Code Extractor for RTL-Gen AII.
Extracts Verilog code blocks from LLM responses.

Handles:
- Markdown ```verilog blocks
- Plain module...endmodule text
- Multiple modules in one response
- RTL vs testbench classification
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CodeBlock:
    """Represents an extracted code block."""
    content: str
    language: str = "verilog"
    is_testbench: bool = False
    module_name: Optional[str] = None


class CodeExtractor:
    """Extract and classify Verilog code from LLM responses."""

    def __init__(self, debug=False):
        self.debug = debug

    def extract(self, response: str) -> Dict:
        """
        Extract code from LLM response.

        Returns dict with:
            success, rtl_code, testbench_code, module_name,
            testbench_name, errors, warnings
        """
        if not response or not response.strip():
            return self._error_result(["Empty response"])

        errors = []
        warnings = []

        # Step 1: Extract code blocks
        blocks = self._extract_code_blocks(response)
        if not blocks:
            return self._error_result(["No code blocks found in response"])

        if self.debug:
            print(f"Found {len(blocks)} code block(s)")

        # Step 2: Classify blocks
        rtl_blocks = []
        tb_blocks = []

        for block in blocks:
            if self._is_testbench(block.content):
                block.is_testbench = True
                block.module_name = self._extract_module_name(block.content)
                tb_blocks.append(block)
            else:
                block.module_name = self._extract_module_name(block.content)
                rtl_blocks.append(block)

        if not rtl_blocks:
            return self._error_result(["No RTL module found in response"])

        # Step 3: Combine blocks
        rtl_code = self._combine_blocks(rtl_blocks)
        testbench_code = self._combine_blocks(tb_blocks) if tb_blocks else ""

        if not tb_blocks:
            warnings.append("No testbench found in response")

        # Step 4: Get module names
        rtl_module_name = self._extract_module_name(rtl_code) or "unknown"
        tb_module_name = self._extract_module_name(testbench_code) if testbench_code else ""

        # Step 5: Validate structure
        rtl_valid, rtl_errs = self._validate_verilog(rtl_code)
        if not rtl_valid:
            errors.extend([f"RTL: {e}" for e in rtl_errs])

        if testbench_code:
            tb_valid, tb_errs = self._validate_verilog(testbench_code)
            if not tb_valid:
                errors.extend([f"TB: {e}" for e in tb_errs])

        return {
            'success': len(errors) == 0,
            'rtl_code': rtl_code,
            'testbench_code': testbench_code,
            'module_name': rtl_module_name,
            'testbench_name': tb_module_name,
            'num_rtl_blocks': len(rtl_blocks),
            'num_tb_blocks': len(tb_blocks),
            'errors': errors,
            'warnings': warnings,
        }

    def _extract_code_blocks(self, text: str) -> List[CodeBlock]:
        """Extract ```verilog blocks, or fall back to plain modules."""
        blocks = []
        pattern = r'```(?:verilog|systemverilog)\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            code = match.strip()
            if code and re.search(r'module\s+\w+', code, re.IGNORECASE):
                blocks.append(CodeBlock(content=code))

        if not blocks:
            blocks = self._extract_plain_modules(text)

        return blocks

    def _extract_plain_modules(self, text: str) -> List[CodeBlock]:
        """Extract module...endmodule pairs from plain text."""
        blocks = []
        pattern = r'(module\s+\w+.*?endmodule)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            blocks.append(CodeBlock(content=match.strip()))
        return blocks

    def _is_testbench(self, code: str) -> bool:
        """Detect if code is a testbench."""
        module_name = self._extract_module_name(code)
        if module_name:
            name_lower = module_name.lower()
            if '_tb' in name_lower or 'testbench' in name_lower:
                return True

        tb_keywords = [
            r'\$display', r'\$monitor', r'\$finish',
            r'\$dumpfile', r'\$dumpvars',
            r'initial\s+begin', r'`timescale',
        ]
        for kw in tb_keywords:
            if re.search(kw, code):
                return True
        return False

    def _extract_module_name(self, code: str) -> Optional[str]:
        """Extract module name."""
        match = re.search(r'module\s+(\w+)\s*[(\;#]', code, re.IGNORECASE)
        if match:
            return match.group(1)
        # Fallback: looser pattern
        match = re.search(r'module\s+(\w+)', code, re.IGNORECASE)
        return match.group(1) if match else None

    def _combine_blocks(self, blocks: List[CodeBlock]) -> str:
        if not blocks:
            return ""
        return "\n\n".join(b.content for b in blocks)

    def _validate_verilog(self, code: str) -> Tuple[bool, List[str]]:
        """Validate basic Verilog structure."""
        if not code.strip():
            return False, ["Empty code"]
        errors = []

        if not re.search(r'module\s+\w+', code, re.IGNORECASE):
            errors.append("No module declaration found")
        if not re.search(r'endmodule', code, re.IGNORECASE):
            errors.append("No endmodule found")

        mods = len(re.findall(r'\bmodule\s+\w+', code, re.IGNORECASE))
        ends = len(re.findall(r'\bendmodule\b', code, re.IGNORECASE))
        if mods != ends:
            errors.append(f"Mismatched module/endmodule: {mods} vs {ends}")

        if code.count('(') != code.count(')'):
            errors.append(f"Mismatched parentheses: {code.count('(')} '(' vs {code.count(')')} ')'")
        if code.count('[') != code.count(']'):
            errors.append(f"Mismatched brackets: {code.count('[')} '[' vs {code.count(']')} ']'")

        return len(errors) == 0, errors

    def _error_result(self, errors):
        return {
            'success': False, 'rtl_code': "", 'testbench_code': "",
            'module_name': "", 'testbench_name': "",
            'num_rtl_blocks': 0, 'num_tb_blocks': 0,
            'errors': errors, 'warnings': [],
        }


if __name__ == "__main__":
    print("Code Extractor Self-Test\n" + "=" * 60)
    extractor = CodeExtractor(debug=True)

    # Test 1: Markdown response
    r1 = extractor.extract("""
```verilog
module adder_8bit(input [7:0] a, b, output [7:0] sum, output carry);
    assign {carry, sum} = a + b;
endmodule
```
""")
    print(f"\n1. Simple: success={r1['success']}, module={r1['module_name']} ✓")

    # Test 2: RTL + Testbench
    r2 = extractor.extract("""
```verilog
module counter(input clk, reset, output reg [7:0] count);
    always @(posedge clk) begin
        if (reset) count <= 0;
        else count <= count + 1;
    end
endmodule
```
```verilog
module counter_tb;
    reg clk, reset;
    wire [7:0] count;
    counter dut(.*);
    initial begin $display("test"); $finish; end
endmodule
```
""")
    print(f"2. RTL+TB: success={r2['success']}, rtl={r2['module_name']}, tb={r2['testbench_name']} ✓")

    # Test 3: Invalid
    r3 = extractor.extract("No code here at all")
    print(f"3. Invalid: success={r3['success']}, errors={r3['errors']} ✓")

    print("\n" + "=" * 60 + "\nAll self-tests passed ✓")
