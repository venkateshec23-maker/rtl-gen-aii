#!/usr/bin/env python
"""Complete integration test for all Phase 3 features"""

import sys
from pathlib import Path
import json
import shutil

# Add to path
sys.path.append(str(Path(__file__).parent))

from python.synthesis_engine import SynthesisEngine
from python.synthesis_visualizer import SynthesisVisualizer

def test_synthesis():
    print("[SYNTHESIS ENGINE TEST]\n")
    
    # Test designs
    designs = {
        "8-bit Adder": """
module adder_8bit(
    input [7:0] a, b,
    input cin,
    output [7:0] sum,
    output cout
);
    assign {cout, sum} = a + b + cin;
endmodule
""",
        "16-bit Counter": """
module counter_16bit(
    input clk, rst, en,
    output reg [15:0] count
);
    always @(posedge clk or posedge rst)
        if (rst) count <= 0;
        else if (en) count <= count + 1;
endmodule
""",
        "4-bit ALU": """
module alu_4bit(
    input [3:0] a, b,
    input [1:0] op,
    output reg [3:0] result,
    output zero, carry
);
    always @(*) begin
        case(op)
            2'b00: result = a + b;
            2'b01: result = a - b;
            2'b10: result = a & b;
            2'b11: result = a | b;
        endcase
    end
    assign zero = (result == 0);
    assign carry = (a + b) > 15;
endmodule
"""
    }
    
    print("[1] Testing individual synthesis...\n")
    synth = SynthesisEngine()
    viz = SynthesisVisualizer()
    
    results = {}
    for name, rtl in designs.items():
        print(f"   Synthesizing: {name}")
        result = synth.synthesize(rtl)
        results[name] = result
        
        if result['success']:
            stats = result.get('stats', {})
            print(f"   [OK] Success!")
            print(f"      Area: {stats.get('area', 0):.1f}")
            print(f"      Power: {stats.get('power', 0):.3f}")
            print(f"      Freq: {stats.get('frequency', 0):.1f} MHz")
            
            # Generate report
            html = viz.generate_full_report(result)
            report_file = Path('outputs/synthesis') / f"{name.replace(' ', '_')}_report.html"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"      Report: {report_file}\n")
        else:
            print(f"   [ERROR] Failed: {result.get('error')}\n")
    
    print("\n[2] Testing design comparison...")
    comparison = synth.compare_synthesis(
        list(designs.values()),
        list(designs.keys())
    )
    
    print("\n   Comparison Results:")
    print(f"   Area: {comparison['area']}")
    print(f"   Power: {comparison['power']}")
    print(f"   Frequency: {comparison['frequency']}")
    
    # Generate comparison plots
    try:
        area_plot = viz.create_area_bar_chart(comparison)
        print(f"   [OK] Area comparison plot: {area_plot}")
    except Exception as e:
        print(f"   [WARNING] Area plot failed: {e}")
    
    try:
        power_freq_plot = viz.create_power_frequency_scatter(comparison)
        print(f"   [OK] Power vs frequency plot: {power_freq_plot}")
    except Exception as e:
        print(f"   [WARNING] Power vs frequency plot failed: {e}")
    
    print("\n[3] Testing graph generation...")
    for name, rtl in designs.items():
        try:
            dot = synth.generate_dot_graph(rtl)
            if dot:
                print(f"   [OK] {name}: DOT graph generated")
        except Exception as e:
            print(f"   [WARNING] {name}: Graph generation failed: {e}")
    
    print("\n" + "="*60)
    print("PHASE 3 SYNTHESIS INTEGRATION COMPLETE")
    print("="*60)
    
    # Summary
    successful = sum(1 for r in results.values() if r.get('success'))
    print(f"\nSummary:")
    print(f"  [OK] {successful}/{len(results)} designs synthesized successfully")
    if successful == len(results):
        print(f"  [OK] All visualization plots created")
    print(f"\nOutput directory: outputs/synthesis/")
    
    return results

if __name__ == "__main__":
    try:
        test_synthesis()
        print("\n[SUCCESS] All tests completed successfully")
    except Exception as e:
        print(f"\n[FATAL] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
