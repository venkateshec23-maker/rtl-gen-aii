"""
Final Integration Test
Comprehensive test covering the complete workflow, batch processing, and verification.
Usage: python test_final_integration.py
"""
import sys
import os
from python.rtl_generator import RTLGenerator

def main():
    print("=" * 60)
    print("FINAL SYSTEM INTEGRATION TEST")
    print("=" * 60)
    
    use_mock = True
    if os.getenv("ANTHROPIC_API_KEY"):
        use_mock = False
        print("Running with live Anthropic LLM.")
    else:
        print("Running with Mock LLM due to missing API key.")
        
    generator = RTLGenerator(use_mock=use_mock, enable_verification=True, enable_monitoring=True)
    
    design = "8-bit counter with synchronous reset"
    print(f"\nGenerating design: {design}")
    
    result = generator.generate(design)
    
    if result.get("success"):
        print("\n✅ Generation Strategy Passed!")
        print(f"Module: {result.get('module_name')}")
        
        verif = result.get("verification")
        if verif:
            if verif.get('passed'):
                print("✅ Icarus Verilog Simulation Verification Passed!")
            else:
                print("❌ Simulation Verification Failed!")
                return 1
                
        print("\n" + "="*40)
        print("PERFORMANCE REPORT:")
        generator.print_performance_report()
        return 0
    else:
        print("\n❌ Final Integration Test Failed")
        print(result.get("error") or result.get("message"))
        return 1

if __name__ == "__main__":
    sys.exit(main())
