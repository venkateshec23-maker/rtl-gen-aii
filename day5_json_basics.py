# day5_json_basics.py
import json
import os

# ============================================
# PYTHON TO JSON (SERIALIZATION)
# ============================================

print("=" * 50)
print("PYTHON -> JSON (Serialization)")
print("=" * 50)

design_spec = {
    "name": "adder_8bit",
    "bit_width": 8,
    "type": "combinational",
    "ports": {
        "inputs": ["a", "b"],
        "outputs": ["sum", "carry"]
    },
    "verified": False,
    "tags": ["arithmetic", "basic"],
    "version": 1.0
}

print("Python object:")
print(design_spec)

json_string = json.dumps(design_spec)
print(f"\nJSON string:\n{json_string}")

json_pretty = json.dumps(design_spec, indent=2)
print(f"\nPretty JSON:\n{json_pretty}")

# ============================================
# JSON TO PYTHON (DESERIALIZATION)
# ============================================

print("\n" + "=" * 50)
print("JSON -> PYTHON (Deserialization)")
print("=" * 50)

json_data = '{"name": "counter_16bit", "bit_width": 16, "type": "sequential"}'
python_obj = json.loads(json_data)
print(f"Python object: {python_obj}")
print(f"Access data: {python_obj['name']}")

# ============================================
# SAVING JSON TO FILE
# ============================================

print("\n" + "=" * 50)
print("SAVING JSON TO FILE")
print("=" * 50)

config = {
    "project_name": "RTL-Gen AII",
    "version": "1.0.0",
    "author": "Venka",
    "default_settings": {
        "bit_width": 8,
        "verify": True,
        "simulate": True,
        "output_dir": "./outputs"
    },
    "supported_components": ["adder", "counter", "alu", "mux"],
    "api_settings": {
        "provider": "nvidia",
        "model": "deepseek-ai/deepseek-v3.2",
        "temperature": 0.3,
        "max_tokens": 4000
    }
}

with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)
print("✓ Saved config.json")

# ============================================
# READING JSON FROM FILE
# ============================================

print("\n" + "=" * 50)
print("READING JSON FROM FILE")
print("=" * 50)

with open('config.json', 'r') as f:
    loaded_config = json.load(f)

print(f"Project: {loaded_config['project_name']}")
print(f"Version: {loaded_config['version']}")
print(f"Default bit width: {loaded_config['default_settings']['bit_width']}")
print(f"API provider: {loaded_config['api_settings']['provider']}")

# ============================================
# UPDATING JSON FILES
# ============================================

print("\n" + "=" * 50)
print("UPDATING JSON FILES")
print("=" * 50)


def update_config(key, value):
    """Update a value in config.json"""
    with open('config.json', 'r') as f:
        cfg = json.load(f)

    if '.' in key:
        parts = key.split('.')
        target = cfg
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    else:
        cfg[key] = value

    with open('config.json', 'w') as f:
        json.dump(cfg, f, indent=2)

    print(f"✓ Updated {key} = {value}")


update_config("default_settings.bit_width", 16)
update_config("api_settings.temperature", 0.5)

with open('config.json', 'r') as f:
    updated = json.load(f)
print(f"New bit width: {updated['default_settings']['bit_width']}")
print(f"New temperature: {updated['api_settings']['temperature']}")

# ============================================
# JSON ERROR HANDLING
# ============================================

print("\n" + "=" * 50)
print("JSON ERROR HANDLING")
print("=" * 50)


def safe_json_parse(json_string):
    """Safely parse JSON with error handling"""
    try:
        data = json.loads(json_string)
        return True, data
    except json.JSONDecodeError as e:
        return False, f"JSON error at position {e.pos}: {e.msg}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


valid_json = '{"name": "adder", "width": 8}'
success, result = safe_json_parse(valid_json)
print(f"Valid JSON: {success} -> {result}")

invalid_json = '{"name": "adder", "width": 8'
success, error = safe_json_parse(invalid_json)
print(f"Invalid JSON: {success} -> {error}")

# ============================================
# API REQUEST FORMAT
# ============================================

print("\n" + "=" * 50)
print("API REQUEST FORMAT")
print("=" * 50)


def create_llm_request(description, system_prompt=None):
    """Create a request in the format expected by LLM APIs"""
    request = {
        "model": "deepseek-ai/deepseek-v3.2",
        "max_tokens": 4000,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": description
            }
        ]
    }
    if system_prompt:
        request["system"] = system_prompt
    return request


system = "You are an expert Verilog programmer. Generate clean, synthesizable code."
request = create_llm_request("Generate an 8-bit adder with carry output", system)

print("LLM Request (JSON):")
print(json.dumps(request, indent=2))

with open('sample_request.json', 'w') as f:
    json.dump(request, f, indent=2)
