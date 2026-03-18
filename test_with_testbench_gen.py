"""
End-to-End Test with Automatic Testbench Generation
Tests the complete workflow including fallback testbench generation.

Usage: python test_with_testbench_gen.py
"""

from python.llm_client import LLMClient
from python.extraction_pipeline import ExtractionPipeline
from python.verification_engine import VerificationEngine


def test_with_testbench_generation():
    """Test complete workflow with testbench generation."""
    print("=" * 70)
    print("E2E TEST: WORKFLOW WITH TESTBENCH GENERATION")
    print("=" * 70)
    
    test_cases = [
        {
            'description': '4-bit multiplexer',
            'expected_type': 'combinational',
        },
        {
            'description': '8-bit register with enable',
            'expected_type': 'sequential',
        },
    ]
    
    # Initialize components
    client = LLMClient(use_mock=True)
    extractor = ExtractionPipeline(debug=True)  # Debug on for extraction
    verifier = VerificationEngine(debug=True)   # Debug on for verification
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST CASE {i}: {test_case['description']}")
        print('='*70)
        
        description = test_case['description']
        
        try:
            # Build prompt
            print("\n[2/5] Building prompt...")
            prompt = f"Write a Verilog module for a {description}."
            print("[PASS] Prompt ready")
            
            # Generate (MockLLM might not include testbench)
            print("\n[3/5] Generating with LLM...")
            response = client.generate(prompt)
            print("[PASS] Generated")
            
            # Extract (with testbench generation fallback)
            print("\n[4/5] Extracting & generating testbench...")
            extraction = extractor.process(response['content'], description=description)
            
            if not extraction['success']:
                print(f"[FAIL] Extraction failed: {extraction['errors']}")
                results.append(False)
                continue
            
            print(f"[PASS] Module: {extraction['module_name']}")
            print(f"  RTL: {len(extraction['rtl_code'])} chars")
            print(f"  TB: {len(extraction['testbench_code'])} chars")
            
            if extraction['warnings']:
                print("  Warnings:")
                for warning in extraction['warnings']:
                    print(f"    [WARN] {warning}")
            
            # Verify
            print("\n[5/5] Verifying...")
            verification = verifier.verify(
                extraction['rtl_code'],
                extraction['testbench_code'],
                module_name=extraction['module_name']
            )
            
            print(f"\n{'='*70}")
            print("RESULTS:")
            print(f"{'='*70}")
            print(f"Overall: {'PASSED [PASS]' if verification['passed'] else 'FAILED [FAIL]'}")
            print(f"  Compilation: {'[PASS]' if verification['compilation_passed'] else '[FAIL]'}")
            print(f"  Simulation: {'[PASS]' if verification['simulation_passed'] else '[FAIL]'}")
            print(f"  Tests: {verification['tests_passed']}/{verification['total_tests']}")
            
            if verification['waveform_file']:
                print(f"  Waveform: {verification['waveform_file']}")
            
            results.append(verification['passed'])
        
        except Exception as e:
            print(f"\n[FAIL] Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} passed")
    
    for i, (test_case, result) in enumerate(zip(test_cases, results), 1):
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {test_case['description']}")
    
    if all(results):
        print(f"\n{'='*70}")
        print("[PASS] ALL TESTS PASSED!")
        print(f"{'='*70}")
        return True
    else:
        print(f"\n{'='*70}")
        print("[FAIL] SOME TESTS FAILED")
        print(f"{'='*70}")
        return False


if __name__ == "__main__":
    success = test_with_testbench_generation()
    exit(0 if success else 1)
