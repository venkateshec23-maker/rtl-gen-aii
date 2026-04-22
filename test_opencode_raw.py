import os, sys
os.environ["PYTHONUTF8"] = "1"
sys.path.insert(0, ".")

from verilog_generator import _acp_is_running, _acp_create_session, _acp_send_message, VERILOG_SYSTEM_PROMPT

# Get raw response to see what format the model uses
prompt = (
    f"{VERILOG_SYSTEM_PROMPT}\n\n"
    "Design name: uart_tx\n\n"
    "Description: Simple UART TX with state machine IDLE->START->DATA->STOP.\n"
    "Inputs: clk, reset_n, tx_start, data_in[7:0]. Outputs: tx_out, tx_busy.\n\n"
    "IMPORTANT: Use EXACTLY this format:\n"
    "```rtl\n"
    "<your verilog RTL here>\n"
    "```\n"
    "```testbench\n"
    "<your testbench here, must print ALL_TESTS_PASSED or TESTS_FAILED>\n"
    "```"
)

sid  = _acp_create_session()
text = _acp_send_message(sid, prompt)

print("RAW RESPONSE LENGTH:", len(text))
print()
print("=== FIRST 80 LINES ===")
for i, line in enumerate(text.splitlines()[:80]):
    print(f"{i+1:3d}: {line}")
