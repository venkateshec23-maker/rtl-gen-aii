"""
Test Area Optimization System

Tests area analysis and resource optimization.

Usage: python test_area_optimization.py
"""

from python.area_analyzer import AreaAnalyzer
from python.resource_optimizer import ResourceOptimizer


def test_basic_area_analysis():
    """Test basic area analysis."""
    print("=" * 70)
    print("TEST 1: BASIC AREA ANALYSIS")
    print("=" * 70)
    
    analyzer = AreaAnalyzer(technology_nm=45)
    
    rtl_code = """
module simple_processor(
    input clk,
    input rst,
    input [31:0] instruction,
    output reg [31:0] result
);
    reg [31:0] registers [0:15];
    reg [31:0] pc;
    
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            pc <= 32'b0;
            result <= 32'b0;
        end else begin
            // Fetch
            pc <= pc + 4;
            
            // Execute (simplified)
            result <= registers[instruction[19:16]] + registers[instruction[15:12]];
        end
    end
endmodule
"""
    
    result = analyzer.analyze_area(rtl_code, 'simple_processor')
    
    print(f"\n✓ Area analysis complete")
    print(f"  Area: {result['final_area']['total_area_um2']:.2f} µm²")
    
    return result['final_area']['total_area_um2'] > 0


def test_implementation_comparison():
    """Test implementation comparison."""
    print("\n" + "=" * 70)
    print("TEST 2: IMPLEMENTATION COMPARISON")
    print("=" * 70)
    
    analyzer = AreaAnalyzer(technology_nm=45)
    
    # Two implementations of the same function
    implementations = [
        ("Parallel Adders", """
module parallel_add(
    input [7:0] a, b, c, d,
    output [7:0] sum1, sum2
);
    assign sum1 = a + b;
    assign sum2 = c + d;
endmodule
"""),
        ("Shared Adder", """
module shared_add(
    input clk,
    input sel,
    input [7:0] a, b, c, d,
    output reg [7:0] result
);
    wire [7:0] in1 = sel ? a : c;
    wire [7:0] in2 = sel ? b : d;
    
    always @(posedge clk)
        result <= in1 + in2;
endmodule
"""),
    ]
    
    comparison = analyzer.compare_implementations(implementations)
    
    smallest = comparison['smallest']
    largest = comparison['largest']
    
    print(f"\n✓ Comparison complete")
    print(f"  Smallest: {smallest['name']}")
    print(f"  Largest: {largest['name']}")
    
    return len(comparison['implementations']) == 2


def test_resource_optimization():
    """Test resource optimization."""
    print("\n" + "=" * 70)
    print("TEST 3: RESOURCE OPTIMIZATION")
    print("=" * 70)
    
    optimizer = ResourceOptimizer()
    
    # Mock area results
    area_results = {
        'final_area': {
            'total_area_um2': 10000.0,
            'breakdown': {
                'registers': 2000.0,
                'combinational_logic': 3000.0,
                'adders': 2000.0,
                'multipliers': 1500.0,
                'muxes': 1000.0,
                'routing_overhead': 500.0,
            },
        },
        'design_info': {
            'registers': 64,
            'adders': 8,
            'multipliers': 4,
            'muxes': 12,
            'memory_bits': 0,
        },
    }
    
    rtl_code = """
module complex_datapath(
    input clk,
    input [15:0] data_in,
    output reg [15:0] data_out
);
    reg [15:0] reg_file [0:15];
    
    always @(posedge clk) begin
        data_out <= reg_file[0] + reg_file[1] + reg_file[2] + reg_file[3];
    end
endmodule
"""
    
    suggestions = optimizer.analyze_and_optimize(rtl_code, area_results)
    
    print(f"\n✓ Optimization analysis complete")
    print(f"  Suggestions: {len(suggestions['suggestions'])}")
    
    return len(suggestions['suggestions']) > 0


def test_die_area_estimation():
    """Test die area estimation."""
    print("\n" + "=" * 70)
    print("TEST 4: DIE AREA ESTIMATION")
    print("=" * 70)
    
    analyzer = AreaAnalyzer(technology_nm=45)
    
    # Core area
    core_area_mm2 = 2.5
    
    # Estimate die with IO
    die_area = analyzer.estimate_die_area(
        core_area_mm2=core_area_mm2,
        io_pads=80,
        pad_pitch_um=50.0
    )
    
    print(f"\nDie Area Breakdown:")
    print(f"  Core: {die_area['core_area_mm2']:.3f} mm²")
    print(f"  IO: {die_area['io_area_mm2']:.3f} mm²")
    print(f"  Total: {die_area['total_die_area_mm2']:.3f} mm²")
    print(f"  Die side: {die_area['die_side_mm']:.3f} mm")
    
    print(f"\n✓ Die area estimation complete")
    
    return die_area['total_die_area_mm2'] > core_area_mm2


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("AREA OPTIMIZATION TEST SUITE")
    print("=" * 70)
    
    results = []
    
    # Test 1: Basic Area Analysis
    results.append(("Basic Area Analysis", test_basic_area_analysis()))
    
    # Test 2: Implementation Comparison
    results.append(("Implementation Comparison", test_implementation_comparison()))
    
    # Test 3: Resource Optimization
    results.append(("Resource Optimization", test_resource_optimization()))
    
    # Test 4: Die Area Estimation
    results.append(("Die Area Estimation", test_die_area_estimation()))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {passed_count}/{len(results)}")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
