import logging
from pathlib import Path
from python.full_flow import RTLGenAI, FlowConfig

# 1. Provide a basic RTL file
rtl_code = """
module adder_8bit (
    input  clk,
    input  reset_n,
    input  [7:0] a, b,
    output reg [8:0] sum
);
  always @(posedge clk) begin
    if (!reset_n) sum <= 9'b0;
    else          sum <= a + b;
  end
endmodule
"""

Path("adder.v").write_text(rtl_code, encoding="utf-8")

print("Starting End-to-End physical design pipeline!")
print("=============================================")

# 2. Run the pipeline
try:
    result = RTLGenAI.run_from_rtl(
        rtl_path="adder.v",
        top_module="adder_8bit",
        output_dir="demo_run",
        config=FlowConfig(
            clock_period_ns=20.0,
        ),
        progress=lambda d: print(f"[{d['stage']:>14}] {d['pct']*100:3.0f}% {d['msg']}")
    )

    print("\n" + result.summary())

except Exception as e:
    print(f"\n[PIPELINE FAILURE] Caught exception: {e}")
