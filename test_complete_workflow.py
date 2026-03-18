"""
Complete Workflow Test: Prompt -> Verify

This tests the ENTIRE pipeline from prompt to verified Verilog.

Usage: python test_complete_workflow.py
"""

from python.llm_client import LLMClient
from python.extraction_pipeline import ExtractionPipeline
from python.verification_engine import VerificationEngine


def test_complete_workflow():
    """Test complete workflow with verification."""
    print("=" * 70)
    print("COMPLETE WORKFLOW TEST: PROMPT -> VERIFIED VERILOG")
    print("=" * 70)
    
    # Test cases
    test_cases = [
        "4-bit adder with carry",
        "8-bit counter with reset",
    ]
    
    # Initialize all components
    client = LLMClient(use_mock=True)
    extractor = ExtractionPipeline(debug=False)
    verifier = VerificationEngine(debug=True)
    
    results = []
    
    for i, description in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST CASE {i}: {description}")
        print('='*70)
        
        try:
            # Step 1: Prompt
            print("\n[1/4] Using prompt...")
            prompt = f"Write a Verilog module for a {description}."
            
            # Step 2: Generate
            print("\n[2/4] Generating with LLM...")
            response = client.generate(prompt)
            print(f"[PASS] Generated: {len(response)} chars")
            
            # Step 3: Extract
            print("\n[3/4] Extracting code...")
            extraction = extractor.process(response['content'], description=description)
            if not extraction['success']:
                print(f"[FAIL] Extraction failed: {extraction['errors']}")
                results.append(False)
                continue
            print(f"[PASS] Module: {extraction['module_name']}")
            print(f"  RTL: {len(extraction['rtl_code'])} chars")
            print(f"  TB: {len(extraction['testbench_code'])} chars")
            
            # Step 4: Verify
            print("\n[4/4] Verifying design...")
            verification = verifier.verify(
                extraction['rtl_code'],
                extraction['testbench_code'],
                module_name=extraction['module_name']
            )
            
            # Show results
            print("\n" + "-" * 70)
            print("VERIFICATION RESULTS:")
            print("-" * 70)
            print(f"Overall: {'[PASS]' if verification['passed'] else '[FAIL]'}")
            print(f"  Compilation: {'[PASS]' if verification['compilation_passed'] else '[FAIL]'}")
            print(f"  Simulation: {'[PASS]' if verification['simulation_passed'] else '[FAIL]'}")
            print(f"  Tests: {verification['tests_passed']}/{verification['total_tests']} passed")
            
            if verification['errors']:
                print(f"\nErrors ({len(verification['errors'])}):")
                for error in verification['errors'][:5]:
                    print(f"  [FAIL] {error}")
            
            if verification['warnings']:
                print(f"\nWarnings ({len(verification['warnings'])}):")
                for warning in verification['warnings'][:3]:
                    print(f"  [WARN]  {warning}")
            
            if verification['waveform_file']:
                print(f"\nWaveform: {verification['waveform_file']}")
            
            # Show simulation output
            if verification['simulation_output']:
                print("\nSimulation Output:")
                print("-" * 70)
                for line in verification['simulation_output'].split('\n')[:15]:
                    print(f"  {line}")
                if len(verification['simulation_output'].split('\n')) > 15:
                    print("  ...")
            
            results.append(verification['passed'])
            
            print(f"\n{'[PASS]' if verification['passed'] else '[FAIL]'}")
        
        except Exception as e:
            print(f"\n[FAIL] Exception: {type(e).__name__}: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} passed")
    
    for i, (desc, result) in enumerate(zip(test_cases, results), 1):
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {desc}")
    
    # Show statistics
    print("\n" + "=" * 70)
    print("STATISTICS")
    print("=" * 70)
    
    print("\nVerification Engine:")
    verifier.print_stats()
    
    # Final result
    if all(results):
        print("\n" + "=" * 70)
        print("[PASS] ALL TESTS PASSED!")
        print("=" * 70)
        return True
    else:
        print("\n" + "=" * 70)
        print("[FAIL] SOME TESTS FAILED")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = test_complete_workflow()
    exit(0 if success else 1)
