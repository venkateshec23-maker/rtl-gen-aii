#!/usr/bin/env python3
"""
Test Mock LLM Client
Verifies the mock generation pipeline is working
"""

import sys
from pathlib import Path

print("=" * 60)
print("🧪 TESTING MOCK LLM CLIENT")
print("=" * 60)

try:
    from python.llm_client import LLMClient
    from python.mock_llm import MockLLM
    print("✅ Modules imported successfully\n")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test 1: Create mock client
print("Test 1: Creating Mock LLM Client")
print("-" * 60)
try:
    client = LLMClient(use_mock=True)
    print("✅ Client created successfully")
except Exception as e:
    print(f"❌ Failed to create client: {e}")
    sys.exit(1)

# Test 2: Generate simple design
print("\nTest 2: Generating RTL Code")
print("-" * 60)
prompt = "Create an 8-bit adder with carry in and carry out"
print(f"Prompt: {prompt}\n")

try:
    response = client.generate(prompt)
    print(f"✅ Response received")
    print(f"   Content length: {len(response.get('content', ''))} characters")
    
    if 'content' in response and response['content']:
        print(f"   Response type: {type(response['content'])}")
        # Show first 300 chars
        preview = response['content'][:300]
        print(f"\n   Preview:\n   {preview}...\n")
    else:
        print("❌ No content in response")
        
except Exception as e:
    print(f"❌ Generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Extract code blocks
print("Test 3: Extracting Code Blocks")
print("-" * 60)
try:
    if hasattr(client, 'extract_code'):
        blocks = client.extract_code(response)
        print(f"✅ Extracted {len(blocks)} code block(s)")
        
        if blocks:
            print(f"\n   First block preview:")
            first_block = blocks[0]
            preview = first_block[:200] if len(first_block) > 200 else first_block
            print(f"   {preview}...")
    else:
        print("⚠️ extract_code method not available")
        
except Exception as e:
    print(f"❌ Code extraction failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Verify response structure
print("\nTest 4: Response Structure")
print("-" * 60)
print(f"Response type: {type(response)}")
print(f"Response keys: {list(response.keys())}")
if 'model' in response:
    print(f"Model: {response['model']}")
    print("✅ Response has expected structure\n")

print("=" * 60)
print("✅ MOCK LLM CLIENT TEST COMPLETE")
print("=" * 60)
print("\n✅ Ready to test Claude API integration")
print("Run: python test_claude.py\n")
