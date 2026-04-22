import os, sys
os.environ["PYTHONUTF8"] = "1"
sys.path.insert(0, ".")

from verilog_generator import generate_verilog_opencode, validate_verilog_syntax

print("Testing OpenCode ACP generation...")
print("Model: opencode/big-pickle")
print()

rtl, tb = generate_verilog_opencode(
    description=(
        "UART transmitter (uart_tx). "
        "Inputs: clk, reset_n, tx_start, data_in[7:0], baud_div[15:0]. "
        "Outputs: tx_out, tx_busy, tx_done. "
        "State machine: IDLE->START->DATA->STOP. "
        "Transmit 8-bit data serially: start bit (0), 8 data bits LSB first, stop bit (1). "
        "Baud rate = 1 bit per baud_div clocks. "
        "tx_busy high during tx. tx_done pulses 1 cycle when done. "
        "reset_n=0: tx_out=1, tx_busy=0, tx_done=0."
    ),
    module_name="uart_tx"
)

print("RTL length:", len(rtl), "chars")
print("TB length:", len(tb), "chars")
print()
print("=== FIRST 20 LINES OF RTL ===")
for i, line in enumerate(rtl.splitlines()[:20]):
    print(f"  {i+1:2d}: {line}")
print()

v = validate_verilog_syntax(rtl, tb, "uart_tx")
print("Syntax valid:", v["valid"])
if v["errors"]:
    print("Errors:", v["errors"][:3])

print()
print("STATUS:", "READY_FOR_PIPELINE" if v["valid"] else "NEEDS_RETRY")
