# day5_practice.py

import json
import os
import time

# ============================================
# EXERCISE 1: Configuration Manager
# ============================================


class Config:
    def __init__(self, filename="app_config.json"):
        self.filename = filename
        self.config = self.load()

    def load(self):
        """Load config from file or create default"""
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        default = {
            "project": "RTL-Gen AII",
            "version": "1.0",
            "api": {
                "model": "claude-3-sonnet",
                "temperature": 0.3,
                "max_tokens": 4000
            },
            "defaults": {
                "bit_width": 8,
                "output_dir": "./outputs"
            }
        }
        self.config = default
        self.save()
        return default

    def save(self):
        """Save config to file"""
        with open(self.filename, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key, default=None):
        """Get config value (supports dot notation)"""
        parts = key.split('.')
        target = self.config
        for part in parts:
            if isinstance(target, dict) and part in target:
                target = target[part]
            else:
                return default
        return target

    def set(self, key, value):
        """Set config value (supports dot notation)"""
        parts = key.split('.')
        target = self.config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        self.save()


config = Config()
print(f"Model: {config.get('api.model', 'default')}")
config.set("api.temperature", 0.5)
print(f"Updated temperature: {config.get('api.temperature')}")

# ============================================
# EXERCISE 2: Design Specification Validator
# ============================================


def validate_design_spec(spec_data):
    """Validate design specification. Returns: (is_valid, list_of_errors)"""
    if isinstance(spec_data, str):
        try:
            spec_data = json.loads(spec_data)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e.msg}"]

    errors = []
    required = ["name", "bit_width", "type"]
    for field in required:
        if field not in spec_data:
            errors.append(f"Missing required field: {field}")

    if "bit_width" in spec_data:
        bw = spec_data["bit_width"]
        if bw not in [1, 2, 4, 8, 16, 32, 64]:
            errors.append(f"bit_width {bw} must be power of 2 (1-64)")

    if "type" in spec_data:
        valid_types = ["combinational", "sequential", "fsm"]
        if spec_data["type"] not in valid_types:
            errors.append(f"type must be one of: {valid_types}")

    return len(errors) == 0, errors


valid = {"name": "adder", "bit_width": 8, "type": "combinational"}
invalid = {"name": "bad", "bit_width": 3, "type": "wrong"}
print(f"\nValid spec: {validate_design_spec(valid)}")
print(f"Invalid spec: {validate_design_spec(invalid)}")

# ============================================
# EXERCISE 3: API Response Parser
# ============================================


def parse_api_response(response_json, provider="anthropic"):
    """Extract code from API response"""
    if provider == "anthropic":
        content_list = response_json.get("content", [])
        code = content_list[0].get("text", "") if content_list else ""
        metadata = {
            "model": response_json.get("model"),
            "tokens": response_json.get("usage", {})
        }
    elif provider == "openai":
        choices = response_json.get("choices", [])
        code = choices[0]["message"]["content"] if choices else ""
        metadata = {
            "model": response_json.get("model"),
            "tokens": response_json.get("usage", {})
        }
    else:
        code = ""
        metadata = {}
    return code, metadata


anthropic_response = {
    "content": [{"text": "module adder(); endmodule"}],
    "model": "claude-3",
    "usage": {"input_tokens": 10, "output_tokens": 20}
}

openai_response = {
    "choices": [{"message": {"content": "module adder(); endmodule"}}],
    "model": "gpt-4",
    "usage": {"prompt_tokens": 10, "completion_tokens": 20}
}

print(f"\nAnthropic: {parse_api_response(anthropic_response, 'anthropic')}")
print(f"OpenAI: {parse_api_response(openai_response, 'openai')}")

# ============================================
# EXERCISE 4: Simple API Tester
# ============================================


def test_api_connection(api_url, api_key=None):
    """Test if API is reachable. Returns: (success, message, response_time_ms)"""
    import requests
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        start = time.time()
        response = requests.get(api_url, headers=headers, timeout=10)
        elapsed_ms = (time.time() - start) * 1000

        return True, f"Status {response.status_code}", round(elapsed_ms, 1)
    except requests.exceptions.ConnectionError:
        return False, "Connection error", 0
    except requests.exceptions.Timeout:
        return False, "Timeout", 0
    except Exception as e:
        return False, str(e), 0


success, msg, ms = test_api_connection("https://api.github.com")
print(f"\nAPI test: {success}, {msg}, {ms}ms")

# ============================================
# EXERCISE 5: Batch Processor
# ============================================


def batch_process_designs(input_file, output_dir):
    """Process multiple designs from JSON file"""
    with open(input_file, 'r') as f:
        designs = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    from day5_llm_client import LLMClient
    client = LLMClient()

    for design in designs:
        did = design["id"]
        desc = design["description"]
        response = client.generate_verilog(desc)

        output_file = os.path.join(output_dir, f"design_{did}.v")
        with open(output_file, 'w') as f:
            f.write(response["content"])
        print(f"✓ Saved {output_file}")


test_designs = [
    {"id": 1, "description": "Create an 8-bit adder"},
    {"id": 2, "description": "Design a 16-bit counter with reset"},
    {"id": 3, "description": "Build a 32-bit ALU with ADD, SUB"}
]

with open("designs.json", "w") as f:
    json.dump(test_designs, f, indent=2)

batch_process_designs("designs.json", "generated")
