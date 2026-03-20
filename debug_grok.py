"""
Debug script for Grok API Response
Run with: python debug_grok.py
"""

import os
from groq import Groq

# Your API key
API_KEY = os.getenv("GROK_API_KEY", "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")

print("🔍 Debugging Grok API Response\n")
print("="*60)

# Initialize Groq client
client = Groq(api_key=API_KEY)

# Simple test prompt
prompt = "Create a simple 8-bit adder in Verilog"

print(f"Prompt: {prompt}\n")
print("Sending request...")

try:
    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {"role": "system", "content": "You are a Verilog expert. Generate only Verilog code."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    print("✅ Response received!\n")
    print("="*60)
    print("FULL RESPONSE OBJECT:")
    print("="*60)
    print(f"Type: {type(response)}")
    print(f"Response: {response}")
    print("\n" + "="*60)
    print("CONTENT:")
    print("="*60)
    
    # Check different ways to access content
    print(f"response.choices: {response.choices}")
    print(f"response.choices[0]: {response.choices[0]}")
    print(f"response.choices[0].message: {response.choices[0].message}")
    print(f"response.choices[0].message.content: {response.choices[0].message.content}")
    
    content = response.choices[0].message.content
    print("\n" + "="*60)
    print("ACTUAL CONTENT:")
    print("="*60)
    print(content)
    
    print("\n" + "="*60)
    print("CONTENT LENGTH:", len(content))
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
