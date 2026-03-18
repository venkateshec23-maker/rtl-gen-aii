"""
Unit tests for Code Extraction Pipeline (Day 11).
Run with: pytest tests/test_extraction.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.code_extractor import CodeExtractor
from python.code_formatter import CodeFormatter
from python.extraction_pipeline import ExtractionPipeline


# ======== CodeExtractor Tests ========

class TestCodeExtractor:

    def setup_method(self):
        self.ext = CodeExtractor(debug=False)

    def test_extract_simple_markdown(self):
        r = self.ext.extract("""
```verilog
module test(input a, output b);
    assign b = a;
endmodule
```
""")
        assert r['success']
        assert r['module_name'] == 'test'
        assert 'module test' in r['rtl_code']

    def test_extract_rtl_and_testbench(self):
        r = self.ext.extract("""
```verilog
module counter(input clk, output reg [7:0] count);
    always @(posedge clk) count <= count + 1;
endmodule
```
```verilog
module counter_tb;
    reg clk;
    wire [7:0] count;
    counter dut(.*);
    initial begin $display("Test"); $finish; end
endmodule
```
""")
        assert r['success']
        assert r['module_name'] == 'counter'
        assert r['testbench_name'] == 'counter_tb'
        assert len(r['testbench_code']) > 0

    def test_extract_plain_code(self):
        r = self.ext.extract("""
Here's the code:
module adder(input a, b, output sum);
    assign sum = a ^ b;
endmodule
""")
        assert r['success']
        assert r['module_name'] == 'adder'

    def test_detect_testbench_by_name(self):
        assert self.ext._is_testbench("module my_tb; initial $finish; endmodule")
        assert not self.ext._is_testbench("module my_mod(input a, output b); assign b=a; endmodule")

    def test_detect_testbench_by_keywords(self):
        assert self.ext._is_testbench("module x; initial begin $display(\"hi\"); $finish; end endmodule")

    def test_missing_endmodule(self):
        r = self.ext.extract("""
```verilog
module broken(input a, output b);
    assign b = a;
```
""")
        assert not r['success']
        assert any('endmodule' in e.lower() for e in r['errors'])

    def test_mismatched_parens(self):
        r = self.ext.extract("""
```verilog
module bad(input a, output b);
    assign b = (a + 1;
endmodule
```
""")
        assert not r['success']
        assert any('parenthes' in e.lower() for e in r['errors'])

    def test_multiple_rtl_modules(self):
        r = self.ext.extract("""
```verilog
module mod1(input a, output b);
    assign b = a;
endmodule
```
```verilog
module mod2(input c, output d);
    assign d = c;
endmodule
```
""")
        assert r['success']
        assert 'mod1' in r['rtl_code']
        assert 'mod2' in r['rtl_code']

    def test_empty_response(self):
        r = self.ext.extract("")
        assert not r['success']

    def test_no_code_blocks(self):
        r = self.ext.extract("Just some text, no code.")
        assert not r['success']

    def test_systemverilog_block(self):
        r = self.ext.extract("""Here is code:
```systemverilog
module sv_test(
    input logic a,
    output logic b
);
    assign b = a;
endmodule
```
""")
        assert r['success']
        assert r['module_name'] == 'sv_test'

    def test_empty_module(self):
        r = self.ext.extract("""
```verilog
module empty;
endmodule
```
""")
        assert r['success']


# ======== CodeFormatter Tests ========

class TestCodeFormatter:

    def setup_method(self):
        self.fmt = CodeFormatter(indent_size=2, debug=False)

    def test_clean_whitespace(self):
        messy = "module test;  \n\n\n\nassign a = b;\n\n\nendmodule"
        clean = self.fmt._clean_whitespace(messy)
        assert '\n\n\n' not in clean

    def test_header_generation(self):
        code = "module test(input a); assign b = a; endmodule"
        out = self.fmt.format(code, module_name="test", description="Test mod")
        assert "RTL-Gen AII" in out
        assert "Test mod" in out
        assert "Module: test" in out

    def test_no_header(self):
        code = "module test; endmodule"
        out = self.fmt.format(code, add_header=False)
        assert "RTL-Gen AII" not in out

    def test_indent_2_spaces(self):
        code = "module test;\nassign a = b;\nendmodule"
        out = CodeFormatter(indent_size=2).format(code, add_header=False)
        assign_line = [l for l in out.split('\n') if 'assign' in l][0]
        assert assign_line.startswith('  ')

    def test_indent_4_spaces(self):
        code = "module test;\nassign a = b;\nendmodule"
        out = CodeFormatter(indent_size=4).format(code, add_header=False)
        assign_line = [l for l in out.split('\n') if 'assign' in l][0]
        assert assign_line.startswith('    ')

    def test_mixed_line_endings(self):
        code = "module test;\r\nassign a = b;\nendmodule\r\n"
        out = self.fmt.format(code, add_header=False)
        assert '\r\n' not in out

    def test_empty_code(self):
        assert self.fmt.format("") == ""
        assert self.fmt.format("   ") == ""


# ======== ExtractionPipeline Tests ========

class TestExtractionPipeline:

    def setup_method(self):
        self.pipe = ExtractionPipeline(debug=False)

    def test_complete_pipeline(self):
        r = self.pipe.process("""
```verilog
module adder(input [7:0] a, b, output [7:0] sum);
    assign sum = a + b;
endmodule
```
""", description="Simple adder")
        assert r['success']
        assert r['module_name'] == 'adder'
        assert 'RTL-Gen AII' in r['rtl_code']
        assert 'Simple adder' in r['rtl_code']

    def test_pipeline_with_testbench(self):
        r = self.pipe.process("""
```verilog
module counter(input clk, output reg [7:0] count);
    always @(posedge clk) count <= count + 1;
endmodule
```
```verilog
module counter_tb;
    reg clk;
    wire [7:0] count;
    counter dut(.*);
    initial $finish;
endmodule
```
""")
        assert r['success']
        assert r['rtl_filename'] == 'counter.v'
        assert r['tb_filename'] == 'counter_tb.v'
        assert len(r['testbench_code']) > 0

    def test_save_to_files(self, tmp_path):
        r = self.pipe.process("""Here is the code:
```verilog
module save_test(
    input a,
    output b
);
    assign b = a;
endmodule
```
""")
        assert r['success'], f"Extraction failed: {r['errors']}"
        files = self.pipe.save_to_files(r, str(tmp_path / "test_out"))
        assert files['rtl'].exists()
        content = files['rtl'].read_text()
        assert 'module save_test' in content

    def test_pipeline_error_propagation(self):
        r = self.pipe.process("No code here.")
        assert not r['success']
        assert len(r['errors']) > 0

    def test_pipeline_filenames(self):
        r = self.pipe.process("""
```verilog
module alu_32bit(input [31:0] a, b, input [1:0] op, output reg [31:0] result);
    always @(*) case(op)
        2'b00: result = a + b;
        2'b01: result = a - b;
        default: result = 0;
    endcase
endmodule
```
""")
        assert r['success']
        assert r['rtl_filename'] == 'alu_32bit.v'


# ======== Integration with LLM Client ========

class TestIntegrationWithLLM:

    def test_mock_llm_to_extraction(self):
        """Full flow: MockLLM → CodeExtractor → formatted files."""
        from python.llm_client import LLMClient

        client = LLMClient(use_mock=True)
        response = client.generate("Generate an 8-bit adder")
        assert response['success']

        pipeline = ExtractionPipeline(debug=False)
        result = pipeline.process(response['content'], description="8-bit adder")

        assert result['success']
        assert len(result['rtl_code']) > 0
        assert 'module' in result['rtl_code'].lower()

    def test_multiple_components(self):
        from python.llm_client import LLMClient

        client = LLMClient(use_mock=True)
        pipeline = ExtractionPipeline(debug=False)

        for desc in ["8-bit adder", "counter", "ALU"]:
            resp = client.generate(f"Generate a {desc}")
            result = pipeline.process(resp['content'])
            assert result['success'], f"Failed for: {desc}"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
