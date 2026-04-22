import os, sys, json, httpx, time
os.environ["PYTHONUTF8"] = "1"

base = "http://127.0.0.1:4096"
model = "opencode/big-pickle"

# Create session
sess = httpx.post(f"{base}/session", json={"modelID": model}, timeout=10).json()
sid = sess["id"]
print("Session:", sid)

# Send message
payload = {
    "parts": [{"type": "text", "text": "Reply with only one sentence: The UART state machine has four states."}],
    "modelID": model,
}
post_r = httpx.post(f"{base}/session/{sid}/message", json=payload, timeout=120)
print("POST status:", post_r.status_code)
post_data = post_r.json()
print("POST response keys:", list(post_data.keys()))
print("POST parts:", json.dumps(post_data.get("parts", []), indent=2)[:500])
print("POST info:", json.dumps(post_data.get("info", {}), indent=2)[:300])

time.sleep(1)

# GET messages
get_r = httpx.get(f"{base}/session/{sid}/message", timeout=15)
print("\nGET status:", get_r.status_code)
msgs = get_r.json()
print("Total messages:", len(msgs))
for i, m in enumerate(msgs):
    print(f"\n--- Message {i} ---")
    print("  Keys:", list(m.keys()))
    print("  Role:", m.get("role", "?"))
    parts = m.get("parts", [])
    print("  Parts count:", len(parts))
    for j, p in enumerate(parts):
        print(f"    Part {j}: type={p.get('type')} text_len={len(p.get('text',''))} text[:100]={repr(p.get('text','')[:100])}")
