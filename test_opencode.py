#!/usr/bin/env python3
"""Debug OpenCode.ai API connectivity."""

import httpx
import json

print("=" * 60)
print("Testing OpenCode.ai Server")
print("=" * 60)

# Check available endpoints
paths = [
    ("GET", "http://localhost:8000/"),
    ("GET", "http://localhost:8000/api"),
    ("GET", "http://localhost:8000/v1/models"),
]

print("\n1. Checking endpoints:")
for method, url in paths:
    try:
        r = httpx.get(url, timeout=2)
        print(f"\n{method} {url}")
        print(f"  Status: {r.status_code}")
        print(f"  Type:   {r.headers.get('content-type', 'unknown')[:50]}")
        if "json" in r.headers.get("content-type", "").lower():
            preview = r.text[:150]
            print(f"  Data:   {preview}")
    except Exception as e:
        print(f"\n{method} {url}")
        print(f"  Error:  {e}")

# Try the chat endpoint
print("\n" + "=" * 60)
print("2. Testing Chat Endpoint:")
print("=" * 60)

payload = {
    "model": "opencode",
    "messages": [
        {"role": "user", "content": "Say 'hello'"}
    ],
    "max_tokens": 50
}

try:
    response = httpx.post(
        "http://localhost:8000/v1/chat/completions",
        json=payload,
        headers={
            "Authorization": "Bearer opencode",
            "Content-Type": "application/json"
        },
        timeout=10
    )
    print(f"\nStatus: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    # Try to parse as JSON
    try:
        data = response.json()
        print("\nJSON Response:")
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError as e:
        print(f"\nNot JSON: {e}")
        print(f"Response preview: {response.text[:500]}")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("3. OpenCode.ai Status:")
print("=" * 60)
print("If response is HTML instead of JSON:")
print("  -> OpenCode.ai server is running but API not responding")
print("  -> Try restarting: opencode serve --port 8000")
print("  -> Ensure opencode-ai is installed: pip install opencode-ai")
