"""
Extraction Pipeline for RTL-Gen AII.
Complete pipeline: LLM response → clean, formatted Verilog files.

Combines CodeExtractor + CodeFormatter + file saving.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict

from python.code_extractor import CodeExtractor
from python.code_formatter import CodeFormatter
from python.config import RTL_OUTPUT_DIR


class ExtractionPipeline:
    """
    Complete extraction and formatting pipeline.

    Usage:
        pipeline = ExtractionPipeline()
        result = pipeline.process(llm_response, description="8-bit adder")
        if result['success']:
            pipeline.save_to_files(result, "outputs/my_design")
    """

    def __init__(self, indent_size=2, debug=False):
        self.debug = debug
        self.extractor = CodeExtractor(debug=debug)
        self.formatter = CodeFormatter(indent_size=indent_size, debug=debug)

    def process(self, llm_response, description=None):
        """
        Process LLM response into clean, formatted code.

        Returns dict with:
            success, rtl_code, testbench_code, module_name,
            testbench_name, rtl_filename, tb_filename, errors, warnings
        """
        result = self.extractor.extract(llm_response)

        if not result['success']:
            result['rtl_filename'] = ""
            result['tb_filename'] = ""
            return result

        # Format RTL
        rtl_formatted = self.formatter.format(
            result['rtl_code'],
            module_name=result['module_name'],
            description=description,
            add_header=True
        )

        # Format testbench
        tb_formatted = ""
        if result['testbench_code']:
            tb_formatted = self.formatter.format(
                result['testbench_code'],
                module_name=result['testbench_name'],
                description=f"Testbench for {result['module_name']}",
                add_header=True
            )

        rtl_filename = f"{result['module_name']}.v"
        tb_filename = f"{result['testbench_name']}.v" if result['testbench_name'] else ""

        return {
            'success': True,
            'rtl_code': rtl_formatted,
            'testbench_code': tb_formatted,
            'module_name': result['module_name'],
            'testbench_name': result['testbench_name'],
            'rtl_filename': rtl_filename,
            'tb_filename': tb_filename,
            'num_rtl_blocks': result['num_rtl_blocks'],
            'num_tb_blocks': result['num_tb_blocks'],
            'errors': result['errors'],
            'warnings': result['warnings'],
        }

    def save_to_files(self, result, output_dir=None):
        """Save extracted code to files. Returns dict of paths."""
        if not result['success']:
            raise ValueError("Cannot save failed extraction")

        if output_dir is None:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = RTL_OUTPUT_DIR / f"{result['module_name']}_{ts}"
        else:
            output_dir = Path(output_dir)

        rtl_dir = output_dir / 'rtl'
        tb_dir = output_dir / 'tb'
        rtl_dir.mkdir(parents=True, exist_ok=True)
        tb_dir.mkdir(parents=True, exist_ok=True)

        rtl_path = rtl_dir / result['rtl_filename']
        with open(rtl_path, 'w', encoding='utf-8') as f:
            f.write(result['rtl_code'])

        tb_path = None
        if result['testbench_code']:
            tb_path = tb_dir / result['tb_filename']
            with open(tb_path, 'w', encoding='utf-8') as f:
                f.write(result['testbench_code'])

        return {'rtl': rtl_path, 'testbench': tb_path, 'output_dir': output_dir}


def extract_and_save(llm_response, description=None, output_dir=None):
    """Convenience: extract + save in one call."""
    pipeline = ExtractionPipeline()
    result = pipeline.process(llm_response, description)
    if result['success']:
        result['files'] = pipeline.save_to_files(result, output_dir)
    return result


if __name__ == "__main__":
    print("Extraction Pipeline Self-Test\n" + "=" * 60)

    sample = """
Here's the Verilog implementation:

```verilog
module adder_8bit(
    input [7:0] a,
    input [7:0] b,
    output [7:0] sum,
    output carry
);
    assign {carry, sum} = a + b;
endmodule
```

And here's the testbench:

```verilog
module adder_8bit_tb;
    reg [7:0] a, b;
    wire [7:0] sum;
    wire carry;

    adder_8bit dut(.*);

    initial begin
        $display("Testing adder");
        a = 8'd5; b = 8'd3; #10;
        $display("5 + 3 = %d (carry=%b)", sum, carry);
        $finish;
    end
endmodule
```
"""

    pipeline = ExtractionPipeline(debug=True)
    result = pipeline.process(sample, description="8-bit adder with carry")

    print(f"\nSuccess: {result['success']}")
    print(f"Module: {result['module_name']}")
    print(f"Testbench: {result['testbench_name']}")
    print(f"RTL file: {result['rtl_filename']}")
    print(f"TB file: {result['tb_filename']}")
    print(f"\nFormatted RTL preview:")
    print(result['rtl_code'][:400])

    files = pipeline.save_to_files(result, "outputs/test_extraction")
    print(f"\nSaved RTL: {files['rtl']}")
    print(f"Saved TB:  {files['testbench']}")

    print("\n" + "=" * 60 + "\nSelf-test passed ✓")
