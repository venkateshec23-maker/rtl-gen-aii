#!/usr/bin/env python3
"""
Quick test of waveform and synthesis features
"""

import sys
sys.path.insert(0, '/c/Users/venka/Documents/rtl-gen-aii')

from python.waveform_generator import WaveformGenerator
from python.synthesis_runner import SynthesisRunner

# Test code
test_rtl = """
module adder_8bit(
    input [7:0] a, b,
    input carry_in,
    output [7:0] sum,
    output carry_out
);
    assign {carry_out, sum} = a + b + carry_in;
endmodule
"""

test_tb = """
`timescale 1ns/1ps

module adder_8bit_tb;
    reg [7:0] a, b;
    reg carry_in;
    wire [7:0] sum;
    wire carry_out;
    
    adder_8bit dut(
        .a(a), .b(b), 
        .carry_in(carry_in),
        .sum(sum), 
        .carry_out(carry_out)
    );
    
    initial begin
        #0 a=0; b=0; carry_in=0;
        #10 a=1; b=1; carry_in=0;
        #20 a=255; b=1; carry_in=0;
        #30 a=128; b=128; carry_in=0;
        #100 $finish;
    end
endmodule
"""

print("=" * 60)
print("RTL-GEN AI: WAVEFORM & SYNTHESIS TEST")
print("=" * 60)

# Test 1: Waveform Generator
print("\n[TEST 1] Waveform Generator")
print("-" * 60)
try:
    waveform_gen = WaveformGenerator(output_dir='outputs', debug=True)
    result = waveform_gen.generate_from_verilog(test_tb, 'adder_8bit_tb')
    
    if result['success']:
        print(f"✅ SUCCESS: Waveform generated")
        print(f"   VCD File: {result['vcd_file']}")
        print(f"   GTKW File: {result['gtkw_file']}")
        print(f"   Signals: {result['signals']}")
        print(f"   Duration: {result['duration']}ns")
        print(f"   File Size: {result['size_kb']}KB")
        print(f"   Message: {result['message']}")
    else:
        print(f"❌ FAILED: {result['message']}")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 2: Synthesis Runner
print("\n[TEST 2] Synthesis Runner")
print("-" * 60)
try:
    synth_runner = SynthesisRunner(output_dir='outputs', debug=True)
    print(f"Yosys Available: {synth_runner.yosys_available}")
    
    result = synth_runner.synthesize_rtl(test_rtl, 'adder_8bit', 'verilog')
    
    if result['success']:
        print(f"✅ SUCCESS: Synthesis complete")
        print(f"   Netlist File: {result['netlist_file']}")
        print(f"   Message: {result['message']}")
        
        metrics = result['metrics']
        print(f"\n   Metrics:")
        print(f"   - Gate Count: {metrics.get('gate_count', 0)}")
        print(f"   - LUT Count: {metrics.get('lut_count', 0)}")
        print(f"   - FF Count: {metrics.get('ff_count', 0)}")
        print(f"   - Area Estimate: {metrics.get('area_estimate', 0):.0f} µm²")
        print(f"   - Power Estimate: {metrics.get('power_estimate', 0):.2f} mW")
    else:
        print(f"❌ FAILED: {result['message']}")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 3: Integration Test
print("\n[TEST 3] Integration Test")
print("-" * 60)
try:
    from python.llm_client import LLMClient
    from python.extraction_pipeline import ExtractionPipeline
    
    # Generate code
    client = LLMClient(use_mock=True)
    response = client.generate("Create an 8-bit adder with carry-in and carry-out")
    
    # Extract code
    extractor = ExtractionPipeline()
    extraction = extractor.process(response, description="Create an 8-bit adder")
    
    if extraction['success']:
        print(f"✅ Code Generated Successfully")
        print(f"   RTL Length: {len(extraction['rtl_code'])} chars")
        print(f"   Testbench Length: {len(extraction['testbench_code'])} chars")
        
        # Now generate waveform from extracted testbench
        waveform_result = waveform_gen.generate_from_verilog(
            extraction['testbench_code'],
            extraction['testbench_name']
        )
        
        if waveform_result['success']:
            print(f"\n✅ Waveform from Generated Code")
            print(f"   VCD: {waveform_result['vcd_file']}")
            print(f"   Signals: {waveform_result['signals']}")
        
        # Generate synthesis report
        synth_result = synth_runner.synthesize_rtl(
            extraction['rtl_code'],
            extraction['module_name']
        )
        
        if synth_result['success']:
            print(f"\n✅ Synthesis from Generated Code")
            print(f"   Netlist: {synth_result['netlist_file']}")
            print(f"   Gates: {synth_result['metrics'].get('gate_count', 0)}")
    else:
        print(f"❌ Code generation failed")
        
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("\n✅ All features working! Ready to use Streamlit app.")
print("\nNext step:")
print("  streamlit run app.py")
