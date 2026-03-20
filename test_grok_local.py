"""
Test script for Grok API integration
Run with: python test_grok_local.py
"""

import os
import sys
from pathlib import Path

# Add python directory to path
sys.path.append(str(Path(__file__).parent))

from python.llm_client import LLMClient


def test_grok_api():
    """Test Grok API connection and generation"""
    
    # Get Grok API key from environment
    api_key = os.getenv("GROK_API_KEY")
    
    if not api_key:
        print("❌ GROK_API_KEY not set in environment")
        print("   Set it with: export GROK_API_KEY='your-key-here'")
        return False
    
    print("✅ Grok API key found")
    print(f"   Key: {api_key[:20]}...")
    
    try:
        print("\n🔧 Initializing Grok client...")
        client = LLMClient(
            provider='grok',
            api_key=api_key,
            model='mixtral-8x7b-32768'
        )
        print("✅ Client initialized successfully")
        
        print("\n📝 Generating RTL code for 8-bit adder...")
        prompt = "Create a simple 8-bit adder module in Verilog with carry in and carry out"
        
        response = client.generate(prompt)
        
        if response['success']:
            print("✅ Generation successful!")
            print(f"   Model: {response['model']}")
            print(f"   Tokens used: {response['usage']['total_tokens']}")
            
            print("\n" + "="*60)
            print("Generated RTL Code:")
            print("="*60)
            print(response['content'][:1000])
            if len(response['content']) > 1000:
                print(f"\n... (truncated, total: {len(response['content'])} chars)")
            
            # Try to extract code blocks
            print("\n" + "="*60)
            print("Extracting code blocks...")
            print("="*60)
            code_blocks = client.extract_code(response)
            print(f"Found {len(code_blocks)} code block(s)")
            
            for i, block in enumerate(code_blocks):
                print(f"\n--- Block {i+1} ---")
                print(block[:300])
                if len(block) > 300:
                    print(f"... (truncated)")
            
            return True
        else:
            print(f"❌ Generation failed: {response['error']}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Testing Grok API Integration")
    print("="*60)
    
    success = test_grok_api()
    
    print("\n" + "="*60)
    if success:
        print("✅ All tests passed! Grok is working correctly.")
        sys.exit(0)
    else:
        print("❌ Tests failed. Check your API key and try again.")
        sys.exit(1)
