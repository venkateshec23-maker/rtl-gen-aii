"""
Test Power Analysis System

Tests power estimation, optimization, and reporting.

Usage: python test_power_analysis.py
"""

from pathlib import Path

from python.power_analyzer import PowerAnalyzer
from python.power_optimizer import PowerOptimizer


def test_basic_power_analysis() -> bool:
    """Test basic power analysis."""
    print('=' * 70)
    print('TEST 1: BASIC POWER ANALYSIS')
    print('=' * 70)

    analyzer = PowerAnalyzer()

    rtl_code = """
module simple_alu(
    input clk,
    input [7:0] a,
    input [7:0] b,
    input [1:0] op,
    output reg [7:0] result
);
    always @(posedge clk) begin
        case (op)
            2'b00: result <= a + b;
            2'b01: result <= a - b;
            2'b10: result <= a & b;
            2'b11: result <= a | b;
        endcase
    end
endmodule
"""

    result = analyzer.analyze_power(rtl_code, 'simple_alu', 100.0, 0.25)

    print('\nPower analysis complete')
    print(f"  Total power: {result['total_power']['total_power_mw']:.4f} mW")

    return result['total_power']['total_power_mw'] > 0


def test_power_scenarios() -> bool:
    """Test power scenario comparison."""
    print('\n' + '=' * 70)
    print('TEST 2: POWER SCENARIO COMPARISON')
    print('=' * 70)

    analyzer = PowerAnalyzer()

    rtl_code = """
module counter_32bit(
    input clk,
    input rst,
    input enable,
    output reg [31:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 32'b0;
        else if (enable)
            count <= count + 1;
    end
endmodule
"""

    scenarios = [
        {'name': 'Idle', 'frequency_mhz': 10, 'activity_factor': 0.05},
        {'name': 'Normal', 'frequency_mhz': 100, 'activity_factor': 0.25},
        {'name': 'Turbo', 'frequency_mhz': 500, 'activity_factor': 0.5},
    ]

    comparison = analyzer.compare_power_scenarios(rtl_code, 'counter_32bit', scenarios)

    best = comparison['best_power']
    worst = comparison['worst_power']

    print('\nScenario comparison complete')
    print(f"  Best: {best['name']} at {best['power']['total_power']['total_power_mw']:.4f} mW")
    print(f"  Worst: {worst['name']} at {worst['power']['total_power']['total_power_mw']:.4f} mW")

    return len(comparison['scenarios']) == 3


def test_power_optimization() -> bool:
    """Test power optimization suggestions."""
    print('\n' + '=' * 70)
    print('TEST 3: POWER OPTIMIZATION')
    print('=' * 70)

    optimizer = PowerOptimizer()

    power_results = {
        'total_power': {'total_power_mw': 50.0},
        'breakdown': {
            'clock_percent': 40.0,
            'logic_percent': 30.0,
            'register_percent': 20.0,
            'leakage_percent': 10.0,
        },
        'design_info': {
            'registers': 128,
            'combinational_gates': 500,
            'adders': 8,
            'multipliers': 4,
        },
    }

    rtl_code = """
module datapath(
    input clk,
    input enable,
    input [31:0] data_in,
    output reg [31:0] data_out
);
    reg [31:0] reg_file [0:31];

    always @(posedge clk) begin
        if (enable) begin
            data_out <= reg_file[0] + data_in;
        end
    end
endmodule
"""

    suggestions = optimizer.analyze_and_suggest(
        rtl_code,
        power_results,
        target_power_mw=30.0,
    )

    print('\nOptimization analysis complete')
    print(f"  Suggestions: {len(suggestions['suggestions'])}")

    return len(suggestions['suggestions']) > 0


def test_power_report_generation() -> bool:
    """Test power report generation."""
    print('\n' + '=' * 70)
    print('TEST 4: POWER REPORT GENERATION')
    print('=' * 70)

    analyzer = PowerAnalyzer()

    rtl_code = """
module fifo_controller(
    input clk,
    input rst,
    input wr_en,
    input rd_en,
    output reg full,
    output reg empty,
    output reg [3:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            count <= 4'b0;
            full <= 1'b0;
            empty <= 1'b1;
        end else begin
            if (wr_en && !full)
                count <= count + 1;
            if (rd_en && !empty)
                count <= count - 1;

            full <= (count == 4'd15);
            empty <= (count == 4'd0);
        end
    end
endmodule
"""

    result = analyzer.analyze_power(rtl_code, 'fifo_controller', 100.0, 0.25)
    report_file = analyzer.generate_power_report(result)

    print('\nReport generation complete')
    print(f'  Report file: {report_file}')

    return Path(report_file).exists()


def main() -> None:
    """Run all tests."""
    print('\n' + '=' * 70)
    print('POWER ANALYSIS TEST SUITE')
    print('=' * 70)

    results = []

    results.append(('Basic Power Analysis', test_basic_power_analysis()))
    results.append(('Power Scenarios', test_power_scenarios()))
    results.append(('Power Optimization', test_power_optimization()))
    results.append(('Report Generation', test_power_report_generation()))

    print('\n' + '=' * 70)
    print('TEST SUMMARY')
    print('=' * 70)

    for name, passed in results:
        status = 'PASS' if passed else 'FAIL'
        print(f'{status} - {name}')

    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {passed_count}/{len(results)}")
    print('=' * 70)


if __name__ == '__main__':
    main()
