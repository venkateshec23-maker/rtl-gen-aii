import httpx, json, time

base = 'http://127.0.0.1:4096'

# Create fresh session
sess = httpx.post(f'{base}/session', json={'modelID': 'opencode/big-pickle'}, timeout=10).json()
sid  = sess['id']
print('Session:', sid)

# Send message
payload = {
    'parts': [{'type': 'text', 'text': 'Reply with only: OPENCODE_OK - nothing else'}],
    'modelID': 'opencode/big-pickle'
}
r = httpx.post(f'{base}/session/{sid}/message', json=payload, timeout=120).json()
print('Keys:', list(r.keys()))

# Read all messages back
msgs_r = httpx.get(f'{base}/session/{sid}/message', timeout=10)
msgs = msgs_r.json()
print('Total messages:', len(msgs))
for m in msgs:
    role = m.get('role', '?')
    for p in m.get('parts', []):
        if p.get('type') == 'text':
            txt = p['text']
            print(f'  [{role}]: {txt[:300]}')
