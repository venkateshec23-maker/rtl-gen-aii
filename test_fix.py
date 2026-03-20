"""
Test script to verify Grok integration fix
Run with: python test_fix.py
"""

import sys
import re
import os

# Add to path
sys.path.append('.')

from python.llm_client import LLMClient

# Get API key from environment or use provided value
API_KEY = os.getenv("GROK_API_KEY", "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")

def test_grok():
    """Test Grok integration"""
    print("="*70)
    print("TESTING GROK INTEGRATION FIX")
    print("="*70)
    
    # Check API key
    if not API_KEY or API_KEY == "":
        print("❌ ERROR: No GROK_API_KEY set!")
        print("   Set it with: $env:GROK_API_KEY = 'your-key-here'")
        return False
    
    print(f"\n✅ Using API key: {API_KEY[:20]}...")
    
    # Initialize client
    try:
        print("\n🔧 Initializing Grok client...")
        client = LLMClient(provider='grok', api_key=API_KEY, model='mixtral-8x7b-32768')
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ FAILED to initialize client: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test prompt
    prompt = "Create an 8-bit adder with carry in and carry out. Output in code block."
    print(f"\n📝 Test Prompt: {prompt}")
    
    # Generate
    print("\n⏳ Generating via Grok API...")
    try:
        result = client.generate(prompt)
    except Exception as e:
        print(f"❌ FAILED to generate: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Detailed result analysis
    print("\n" + "="*70)
    print("RESPONSE ANALYSIS")
    print("="*70)
    
    print(f"\nResponse keys: {list(result.keys())}")
    print(f"Success: {result.get('success', 'N/A')}")
    print(f"Provider: {result.get('provider', 'N/A')}")
    print(f"Model: {result.get('model', 'N/A')}")
    print(f"Error: {result.get('error', 'None')}")
    
    content_length = len(result.get('content', ''))
    print(f"Content length: {content_length} chars")
    
    if content_length > 0:
        print(f"\nFirst 300 chars of content:")
        print("-"*70)
        print(result.get('content', '')[:300])
        print("-"*70)
        
        # Check for code blocks in content
        has_markdown_blocks = bool(re.search(r'```', result.get('content', '')))
        print(f"\nHas markdown code blocks: {has_markdown_blocks}")
    
    # Extract code
    print("\n🔍 Extracting code blocks...")
    code_blocks = client.extract_code(result)
    
    print(f"\n✅ Code blocks extracted: {len(code_blocks)}")
    
    if code_blocks:
        print("\n" + "="*70)
        print("EXTRACTED CODE BLOCKS")
        print("="*70)
        
        for i, block in enumerate(code_blocks, 1):
            lines = block.split('\n')
            print(f"\n📦 Block {i}:")
            print(f"   Lines: {len(lines)}")
            print(f"   Size: {len(block)} chars")
            
            # Show first few lines
            print("   Preview:")
            for line in lines[:5]:
                if line.strip():
                    print(f"      {line[:60]}")
            
            if len(lines) > 5:
                print(f"      ... ({len(lines)-5} more lines)")
            
            # Check if it looks like valid Verilog
            has_module = 'module' in block.lower()
            has_endmodule = 'endmodule' in block.lower()
            print(f"   Looks like Verilog: {has_module and has_endmodule}")
        
        # Summary
        print("\n" + "="*70)
        print("✅ TEST PASSED!")
        print("="*70)
        print(f"\nSuccessfully extracted {len(code_blocks)} code block(s)")
        print("Grok integration is working correctly! 🎉")
        return True
    else:
        print("\n" + "="*70)
        print("❌ TEST FAILED!")
        print("="*70)
        print("\nNo code blocks were extracted.")
        
        if result.get('success'):
            print("\nThe response was marked as successful, but code extraction failed.")
            print("This might indicate:")
            print("  - Grok returned code in an unexpected format")
            print("  - The extraction patterns don't match the response")
            print("  - The response doesn't contain code at all")
            
            print("\nRaw content for debugging:")
            print("-"*70)
            content = result.get('content', '')
            if content:
                print(content[:1000])
                if len(content) > 1000:
                    print(f"\n... (truncated, total {len(content)} chars)")
            else:
                print("(empty content)")
            print("-"*70)
        else:
            print(f"\nGeneration failed with error: {result.get('error')}")
        
        return False

if __name__ == "__main__":
    try:
        success = test_grok()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
