"""
Test script for Gap Analysis fixes
Tests: IR Drop, Coverage, ERC, Antenna checks
"""

import json
from pathlib import Path
from full_flow import RTLtoGDSIIFlow

def test_gap_fixes():
    """Run a simple counter design through the enhanced pipeline."""
    
    print("=" * 70)
    print("TESTING GAP FIXES")
    print("=" * 70)
    print()
    print("Testing: IR Drop, Coverage, ERC, Antenna checks")
    print()
    
    # Create a simple test design
    rtl = """
module test_gap_fix (
    input clk,
    input reset_n,
    input enable,
    output reg [3:0] count
);
    always @(posedge clk) begin
        if (!reset_n)
            count <= 0;
        else if (enable)
            count <= count + 1;
    end
endmodule
"""
    
    tb = """
`timescale 1ns/1ps
module test_gap_fix_tb();
    reg clk, reset_n, enable;
    wire [3:0] count;
    integer fail_count = 0;
    integer pass_count = 0;
    
    test_gap_fix dut(.clk(clk), .reset_n(reset_n), .enable(enable), .count(count));
    
    initial clk = 0;
    always #5 clk = ~clk;
    
    initial begin
        $dumpfile("trace.vcd");
        $dumpvars(0, test_gap_fix_tb);
        
        reset_n = 0; enable = 0;
        repeat(4) @(posedge clk);
        reset_n = 1;
        
        enable = 1;
        repeat(20) @(posedge clk);
        
        if (count == 20) begin
            $display("PASS: Counter reached 20");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL: Counter = %d, expected 20", count);
            fail_count = fail_count + 1;
        end
        
        if (fail_count == 0)
            $display("ALL_TESTS_PASSED");
        
        $finish;
    end
endmodule
"""
    
    # Setup paths
    work_dir = Path(r"C:\tools\OpenLane")
    pdk_dir = Path(r"C:\pdk")
    designs_dir = work_dir / "designs" / "test_gap_fix"
    designs_dir.mkdir(parents=True, exist_ok=True)
    
    # Write RTL and TB
    rtl_path = designs_dir / "test_gap_fix.v"
    tb_path = designs_dir / "test_gap_fix_tb.v"
    rtl_path.write_text(rtl)
    tb_path.write_text(tb)
    
    print(f"RTL written to: {rtl_path}")
    print(f"TB written to:  {tb_path}")
    print()
    
    # Run flow
    print("Running RTLtoGDSII flow with gap fixes...")
    print()
    
    flow = RTLtoGDSIIFlow(
        "test_gap_fix",
        str(rtl_path),
        str(work_dir),
        str(pdk_dir),
        clock_period=10.0
    )
    
    summary = flow.run_full_flow()
    
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    
    steps = summary.get("steps", {})
    metrics = summary.get("metrics", {})
    
    print("Pipeline Steps:")
    for step, status in steps.items():
        icon = " OK " if status == "PASS" else "FAIL"
        print(f"  {icon} {step}")
    
    print()
    print("New Metrics:")
    
    # IR Drop
    ir_drop = metrics.get("ir_drop", {})
    print(f"  IR Drop:   {ir_drop.get('status', 'N/A')}")
    if ir_drop.get('max_mv'):
        print(f"             Max drop: {ir_drop['max_mv']} mV")
    
    # Coverage
    coverage = metrics.get("coverage", {})
    print(f"  Coverage:  {coverage.get('status', 'N/A')}")
    if coverage.get('toggle_coverage'):
        print(f"             Toggle: {coverage['toggle_coverage']:.1f}%")
    
    # Signoff (ERC/Antenna)
    signoff = metrics.get("signoff", {})
    if isinstance(signoff, dict):
        erc = signoff.get("erc", {})
        antenna = signoff.get("antenna", {})
        print(f"  ERC:       {erc.get('status', 'N/A')}")
        print(f"  Antenna:   {antenna.get('status', 'N/A')}")
    
    print()
    print("Status:", summary.get("status"))
    print("Tapeout Ready:", summary.get("tapeout_ready"))
    
    return summary


if __name__ == "__main__":
    result = test_gap_fixes()
    
    # Save result
    result_path = Path("test_gap_fixes_result.json")
    result_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nResult saved to: {result_path}")
