#!/usr/bin/env python3
"""
Test complex RTL design through the synthesis pipeline
Demonstrates full pipeline integration
"""

import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from synthesis_engine import SynthesisEngine

# Complex 8-bit ALU design
COMPLEX_DESIGN = """
module alu_8bit (
    input [7:0] operand_a,
    input [7:0] operand_b,
    input [3:0] opcode,
    input enable,
    output reg [7:0] result,
    output reg zero_flag,
    output reg carry_flag,
    output reg overflow_flag
);

    localparam ADD = 4'b0000;
    localparam SUB = 4'b0001;
    localparam AND = 4'b0010;
    localparam OR  = 4'b0011;
    localparam XOR = 4'b0100;
    localparam SHL = 4'b0101;
    localparam SHR = 4'b0110;
    localparam CMP = 4'b0111;

    wire [8:0] temp_result;
    
    always @(*) begin
        if (!enable) begin
            result = 8'b0;
            zero_flag = 1'b0;
            carry_flag = 1'b0;
            overflow_flag = 1'b0;
        end
        else begin
            case (opcode)
                ADD: begin
                    {carry_flag, result} = operand_a + operand_b;
                    overflow_flag = (operand_a[7] == operand_b[7]) && (operand_a[7] != result[7]);
                    zero_flag = (result == 8'b0);
                end
                SUB: begin
                    {carry_flag, result} = operand_a - operand_b;
                    overflow_flag = (operand_a[7] != operand_b[7]) && (operand_a[7] != result[7]);
                    zero_flag = (result == 8'b0);
                end
                AND: begin
                    result = operand_a & operand_b;
                    zero_flag = (result == 8'b0);
                    carry_flag = 1'b0;
                    overflow_flag = 1'b0;
                end
                OR: begin
                    result = operand_a | operand_b;
                    zero_flag = (result == 8'b0);
                    carry_flag = 1'b0;
                    overflow_flag = 1'b0;
                end
                XOR: begin
                    result = operand_a ^ operand_b;
                    zero_flag = (result == 8'b0);
                    carry_flag = 1'b0;
                    overflow_flag = 1'b0;
                end
                SHL: begin
                    {carry_flag, result} = {operand_a, 1'b0};
                    zero_flag = (result == 8'b0);
                    overflow_flag = 1'b0;
                end
                SHR: begin
                    result = operand_a >> operand_b[2:0];
                    carry_flag = operand_a[0];
                    zero_flag = (result == 8'b0);
                    overflow_flag = 1'b0;
                end
                CMP: begin
                    {carry_flag, result} = operand_a - operand_b;
                    overflow_flag = (operand_a[7] != operand_b[7]) && (operand_a[7] != result[7]);
                    zero_flag = (result == 8'b0);
                end
                default: begin
                    result = 8'b0;
                    zero_flag = 1'b0;
                    carry_flag = 1'b0;
                    overflow_flag = 1'b0;
                end
            endcase
        end
    end
endmodule
"""

if __name__ == "__main__":
    print("=" * 70)
    print("🏭 RTL-Gen AI - Pipeline Test: 8-bit ALU Synthesis")
    print("=" * 70)
    
    # Initialize synthesis engine
    print("\n📊 Initializing Synthesis Engine...")
    synthesis = SynthesisEngine(output_dir='outputs/test_synthesis', tech_library='asic')
    
    # Run synthesis
    print("\n⏳ Running synthesis on 8-bit ALU design...")
    print("-" * 70)
    result = synthesis.synthesize(COMPLEX_DESIGN, top_module='alu_8bit')
    print("-" * 70)
    
    # Display results
    if result['success']:
        print("\n✅ SYNTHESIS SUCCESSFUL!")
        print("\n📋 Design Summary:")
        print(f"   Module Name: {result['top_module']}")
        print(f"   Synthesis Time: {result['synthesis_time']}")
        print(f"   Technology: {result['tech_library']}")
        print(f"   Tool: {result['simulator']}")
        
        if result.get('stats'):
            print("\n📊 Synthesis Statistics:")
            stats = result['stats']
            print(f"   Gates: {stats.get('num_gates', 'N/A')}")
            print(f"   Logic Depth: {stats.get('logic_depth', 'N/A')}")
            print(f"   Estimated Area: {stats.get('estimated_area', 'N/A')} um²")
            print(f"   Estimated Power: {stats.get('estimated_power', 'N/A')} uW/MHz")
        
        print(f"\n📂 Output Directory: {result['work_dir']}")
        
        if result.get('netlist'):
            print("\n📄 Generated Netlist (first 40 lines):")
            print("-" * 70)
            netlist_lines = result['netlist'].split('\n')[:40]
            for line in netlist_lines:
                print(line)
            if len(result['netlist'].split('\n')) > 40:
                print(f"\n... and {len(result['netlist'].split('\n')) - 40} more lines")
            print("-" * 70)
        
        print("\n🎉 Pipeline test completed successfully!")
    
    else:
        print("\n❌ SYNTHESIS FAILED!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        print("\n⚠️ This is normal if Yosys/OpenLane is not installed.")
        print("   The system can still run in mock mode for UI testing.")
    
    print("\n" + "=" * 70)
