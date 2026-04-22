import os, sys
os.environ["PYTHONUTF8"] = "1"
sys.path.insert(0, ".")

from verilog_generator import _acp_create_session, _acp_send_message, parse_verilog_response, ACP_BASE, ACP_MODEL, VERILOG_SYSTEM_PROMPT

# Test the exact function chain
sid = _acp_create_session()
print("Session:", sid)

prompt = (
    f"{VERILOG_SYSTEM_PROMPT}\n\n"
    "Design name: cnt4\n"
    "Description: simple 4-bit counter with reset_n\n\n"
    "Use ```rtl and ```testbench code blocks."
)

raw = _acp_send_message(sid, prompt)
print(f"Raw text length: {len(raw)}")
print(f"First 200 chars: {repr(raw[:200])}")

rtl, tb = parse_verilog_response(raw)
print(f"\nRTL extracted: {len(rtl)} chars, starts: {repr(rtl[:60])}")
print(f"TB extracted:  {len(tb)} chars, starts: {repr(tb[:60])}")
