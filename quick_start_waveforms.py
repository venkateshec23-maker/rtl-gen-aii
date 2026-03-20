#!/usr/bin/env python
"""Quick start script for waveform generation"""

import sys
from pathlib import Path

# Add to path
sys.path.append(str(Path(__file__).parent))

from python.waveform_generator import WaveformGenerator
from python.testbench_generator import TestbenchGenerator, SimpleTestbenchGenerator

def main():
    print("🎬 RTL-Gen AI Waveform Quick Start\n")
    
    # Example RTL
    rtl = """
module counter_8bit(
    input clk,
    input rst,
    output reg [7:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst) count <= 8'b0;
        else count <= count + 1;
    end
endmodule
"""
    
    print("1️⃣  Generating testbench...")
    tb_gen = SimpleTestbenchGenerator()
    testbench = tb_gen.generate(rtl)
    
    if testbench:
        print("   ✅ Testbench generated")
        print("\n" + "-"*40)
        print(testbench[:200] + "...")
        print("-"*40)
    else:
        print("   ❌ Failed to generate testbench")
        return
    
    print("\n2️⃣  Generating waveform...")
    wf_gen = WaveformGenerator(output_dir='outputs')
    result = wf_gen.generate_from_testbench(testbench, 'counter_tb')
    
    if result['success']:
        print(f"   ✅ Waveform generated!")
        print(f"   📁 VCD File: {result['vcd_file']}")
        print(f"   📊 Signals: {result['signal_count']}")
        print(f"   ⏱️  Duration: {result['duration']}ns")
        print(f"   💾 Size: {result['size_kb']}KB")
        print(f"   🎮 Simulator: {result['simulator']}")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
    
    print("\n3️⃣  Next steps:")
    print("   • View with: gtkwave outputs/counter_tb.gtkw")
    print("   • Or open in browser: https://wavedrom.com")
    print("   • Run: streamlit run app.py")

if __name__ == "__main__":
    main()
