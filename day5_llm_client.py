# day5_llm_client.py
import json
import time

# ============================================
# SIMULATED LLM CLIENT
# ============================================


class LLMClient:
    """Client for interacting with LLM APIs (SIMULATION)"""

    def __init__(self, api_key="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", provider="nvidia"):
        self.api_key = api_key
        self.provider = provider
        self.call_count = 0

    def generate_verilog(self, description, max_tokens=4000):
        """Request Verilog code generation (simulated)"""
        self.call_count += 1

        print(f"\n📤 Sending request to {self.provider}...")
        print(f"   Description: {description}")

        time.sleep(0.5)  # Simulate short delay

        desc_lower = description.lower()
        if "adder" in desc_lower:
            code = self._generate_adder(description)
        elif "counter" in desc_lower:
            code = self._generate_counter(description)
        elif "alu" in desc_lower:
            code = self._generate_alu(description)
        else:
            code = self._generate_generic(description)

        response = {
            "id": f"sim_{self.call_count}",
            "model": f"{self.provider}-simulated",
            "content": code,
            "usage": {
                "input_tokens": len(description) // 4,
                "output_tokens": len(code) // 4
            },
            "success": True
        }

        print(f"📥 Received response ({len(code)} chars)")
        return response

    def _generate_adder(self, description):
        width = 8
        for w in [64, 32, 16, 8, 4]:
            if f"{w}-bit" in description or f"{w} bit" in description:
                width = w
                break

        return f"""// {width}-bit Adder
module adder_{width}bit(
    input [{width-1}:0] a,
    input [{width-1}:0] b,
    output [{width-1}:0] sum,
    output carry
);
    assign {{carry, sum}} = a + b;
endmodule"""

    def _generate_counter(self, description):
        return """// 8-bit counter with reset
module counter_8bit(
    input clk, input reset, input enable,
    output reg [7:0] count
);
    always @(posedge clk) begin
        if (reset) count <= 8'b0;
        else if (enable) count <= count + 1'b1;
    end
endmodule"""

    def _generate_alu(self, description):
        return """// Simple 8-bit ALU
module alu_8bit(
    input [7:0] a, b,
    input [2:0] opcode,
    output reg [7:0] result,
    output reg zero
);
    always @(*) begin
        case(opcode)
            3'b000: result = a + b;
            3'b001: result = a - b;
            3'b010: result = a & b;
            3'b011: result = a | b;
            3'b100: result = a ^ b;
            default: result = 8'b0;
        endcase
        zero = (result == 8'b0);
    end
endmodule"""

    def _generate_generic(self, description):
        return f"""// Generic module for: {description}
module generic_module(
    input clk, input reset,
    input [7:0] data_in,
    output reg [7:0] data_out
);
    always @(posedge clk) begin
        if (reset) data_out <= 8'b0;
        else data_out <= data_in;
    end
endmodule"""


# ============================================
# USING THE SIMULATED CLIENT
# ============================================

print("=" * 50)
print("SIMULATED LLM CLIENT")
print("=" * 50)

client = LLMClient(provider="nvidia")

descriptions = [
    "Create an 8-bit adder with carry output",
    "Design a 16-bit counter with reset",
    "Build a 32-bit ALU with basic operations"
]

for desc in descriptions:
    response = client.generate_verilog(desc)
    print(f"\n✅ Generated ({response['usage']['output_tokens']} tokens)")
    print("-" * 40)
    print(response['content'][:200] + "...")
    print("-" * 40)

# ============================================
# REAL API STRUCTURE (for reference)
# ============================================

print("\n" + "=" * 50)
print("REAL API STRUCTURE (for future use)")
print("=" * 50)

nvidia_request = {
    "model": "deepseek-ai/deepseek-v3.2",
    "max_tokens": 4000,
    "messages": [{"role": "user", "content": "Generate an 8-bit adder in Verilog"}],
    "stream": False
}
print("NVIDIA API format:")
print(json.dumps(nvidia_request, indent=2))

openai_request = {
    "model": "gpt-4",
    "messages": [
        {"role": "system", "content": "You are an expert Verilog programmer."},
        {"role": "user", "content": "Generate an 8-bit adder in Verilog"}
    ],
    "temperature": 0.3,
    "max_tokens": 4000
}
print("\nOpenAI API format:")
print(json.dumps(openai_request, indent=2))
