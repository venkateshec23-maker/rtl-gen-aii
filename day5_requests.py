# day5_requests.py
import requests
import json

# ============================================
# BASIC GET REQUEST
# ============================================

print("=" * 50)
print("BASIC GET REQUEST")
print("=" * 50)

url = "https://api.github.com"
try:
    response = requests.get(url, timeout=10)

    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")

    if 'application/json' in response.headers.get('content-type', ''):
        data = response.json()
        print(f"Parsed JSON keys: {list(data.keys())[:5]}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")

# ============================================
# GET WITH PARAMETERS
# ============================================

print("\n" + "=" * 50)
print("GET WITH PARAMETERS")
print("=" * 50)

params = {
    'q': 'verilog',
    'sort': 'stars',
    'order': 'desc',
    'per_page': 3
}

try:
    response = requests.get(
        'https://api.github.com/search/repositories',
        params=params,
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['total_count']} Verilog repositories")
        print("\nTop 3 by stars:")
        for i, repo in enumerate(data['items'], 1):
            desc = repo.get('description', 'No description')
            print(f"{i}. {repo['name']} - ⭐ {repo['stargazers_count']}")
            if desc:
                print(f"   {desc[:60]}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")

# ============================================
# POST REQUEST (SENDING DATA)
# ============================================

print("\n" + "=" * 50)
print("POST REQUEST")
print("=" * 50)

payload = {
    "description": "Create an 8-bit adder",
    "bit_width": 8,
    "options": {
        "testbench": True,
        "comments": True
    }
}

try:
    response = requests.post(
        "https://httpbin.org/post",
        json=payload,
        headers={'User-Agent': 'RTL-Gen-AII/1.0'},
        timeout=10
    )

    if response.status_code == 200:
        result = response.json()
        print("Server received:")
        print(f"  JSON sent: {result['json']}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")

# ============================================
# ERROR HANDLING
# ============================================

print("\n" + "=" * 50)
print("ERROR HANDLING")
print("=" * 50)


def safe_request(url, timeout=10):
    """Make request with comprehensive error handling"""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        try:
            data = response.json()
            return True, data, response.status_code
        except ValueError:
            return True, response.text, response.status_code
    except requests.exceptions.ConnectionError:
        return False, "Connection error - check internet", None
    except requests.exceptions.Timeout:
        return False, f"Request timed out after {timeout}s", None
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP error: {e}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


success, data, status = safe_request('https://api.github.com')
if success:
    print(f"✓ Success! Status {status}")
else:
    print(f"✗ {data}")

success, data, status = safe_request('https://nonexistent.url.xyz', timeout=3)
if success:
    print(f"✓ {data}")
else:
    print(f"✗ {data}")
