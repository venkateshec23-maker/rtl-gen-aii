import os, sys, json, httpx, time
os.environ["PYTHONUTF8"] = "1"
sys.path.insert(0, ".")

from verilog_generator import _acp_create_session, ACP_BASE, ACP_MODEL, VERILOG_SYSTEM_PROMPT

base  = ACP_BASE
model = ACP_MODEL

# Create session
sid = _acp_create_session(base, model)
print("Session:", sid)

# Send verilog prompt
prompt = (
    f"{VERILOG_SYSTEM_PROMPT}\n\n"
    "Design name: cnt4\n"
    "Description: simple 4-bit counter with reset_n\n\n"
    "Use ```rtl and ```testbench blocks."
)

payload = {"parts": [{"type": "text", "text": prompt}], "modelID": model}
post_r  = httpx.post(f"{base}/session/{sid}/message", json=payload, timeout=120)
time.sleep(0.5)

msgs = httpx.get(f"{base}/session/{sid}/message", timeout=10).json()
print(f"Total messages: {len(msgs)}")
for i, m in enumerate(msgs):
    info = m.get("info", {})
    role = info.get("role", "NO_ROLE_IN_INFO")
    print(f"\nMsg {i}: info.role={role}")
    for j, p in enumerate(m.get("parts", [])):
        ptype = p.get("type","?")
        txt   = p.get("text","")
        print(f"  part[{j}] type={ptype} len={len(txt)} preview={repr(txt.strip()[:80])}")
