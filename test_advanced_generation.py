"""
Test Advanced Generation System

Tests all advanced features: RAG, multi-stage generation, context awareness.

Usage: python test_advanced_generation.py
"""

import time
from python.multi_stage_generator import MultiStageGenerator
from python.rag_system import RAGSystem
from python.advanced_prompt_builder import AdvancedPromptBuilder


def test_rag_system():
    """Test RAG system."""
    print("=" * 70)
    print("TEST 1: RAG SYSTEM")
    print("=" * 70)
    
    rag = RAGSystem()
    
    # Test queries
    queries = [
        "8-bit adder",
        "counter with reset",
        "FSM traffic light",
        "16-bit ALU",
    ]
    
    print("\nTesting retrieval for various queries:\n")
    
    for query in queries:
        print(f"Query: {query}")
        results = rag.retrieve_relevant_examples(query, top_k=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['name']} (similarity: {result['similarity']:.3f})")
        else:
            print("  No results found")
        print()
    
    # Get statistics
    stats = rag.get_index_statistics()
    print(f"RAG Index Statistics:")
    print(f"  Indexed designs: {stats['indexed_designs']}")
    print(f"  Vector dimension: {stats['vector_dimension']}")
    print(f"  Vocabulary size: {stats['vocabulary_size']}")
    
    print("\n[OK] RAG system test complete\n")


def test_advanced_prompt_builder():
    """Test advanced prompt builder."""
    print("=" * 70)
    print("TEST 2: ADVANCED PROMPT BUILDER")
    print("=" * 70)
    
    builder = AdvancedPromptBuilder()
    
    # Test 1: Context-aware prompt
    print("\nTest 2.1: Context-aware prompt generation")
    
    description = "8-bit counter with reset"
    prompt = builder.build_context_aware_prompt(
        description=description,
        design_type='sequential',
        include_examples=True,
        include_history=False
    )
    
    print(f"[OK] Generated prompt: {len(prompt)} characters")
    print(f"  Includes similar examples: {'Example:' in prompt}")
    
    # Test 2: Refinement prompt
    print("\nTest 2.2: Refinement prompt generation")
    
    refinement = builder.build_refinement_prompt(
        original_description="8-bit adder",
        original_code="module adder(...);",
        error_message="Syntax error",
        attempt_number=2
    )
    
    print(f"[OK] Generated refinement prompt: {len(refinement)} characters")
    
    # Test 3: Testbench prompt
    print("\nTest 2.3: Testbench prompt generation")
    
    tb_prompt = builder.build_testbench_prompt(
        rtl_code="module adder_8bit(input [7:0] a, b, output [7:0] sum); endmodule",
        module_name="adder_8bit",
        design_description="8-bit adder"
    )
    
    print(f"[OK] Generated testbench prompt: {len(tb_prompt)} characters")
    
    print("\n[OK] Advanced prompt builder test complete\n")


def test_multi_stage_generation():
    """Test multi-stage generation pipeline."""
    print("=" * 70)
    print("TEST 3: MULTI-STAGE GENERATION")
    print("=" * 70)
    
    generator = MultiStageGenerator(use_mock=True)
    
    # Test cases
    test_cases = [
        "4-bit adder with carry",
        "8-bit counter with reset and enable",
        "2-to-1 multiplexer 8-bit",
    ]
    
    results = []
    
    for i, description in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test Case {i}/{len(test_cases)}")
        print(f"{'='*70}")
        
        result = generator.generate_multi_stage(
            description=description,
            max_refinements=1
        )
        
        results.append(result)
        time.sleep(1)  # Rate limiting
    
    # Print summary
    print("\n" + "=" * 70)
    print("MULTI-STAGE GENERATION SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r['success'])
    
    print(f"\nTotal tests: {len(test_cases)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(test_cases) - success_count}")
    
    print("\nDetailed Results:")
    for i, (desc, result) in enumerate(zip(test_cases, results), 1):
        status = "[OK]" if result['success'] else "[FAIL]"
        duration = result.get('duration_seconds', 0)
        refinements = result.get('refinement_count', 0)
        
        print(f"{i}. {status} {desc}")
        print(f"   Duration: {duration:.1f}s, Refinements: {refinements}")
    
    print("\n[OK] Multi-stage generation test complete\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("ADVANCED GENERATION SYSTEM - COMPREHENSIVE TEST")
    print("=" * 70)
    
    start_time = time.time()
    
    # Test 1: RAG System
    test_rag_system()
    
    # Test 2: Advanced Prompt Builder
    test_advanced_prompt_builder()
    
    # Test 3: Multi-Stage Generation
    test_multi_stage_generation()
    
    # Final summary
    duration = time.time() - start_time
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print(f"Total duration: {duration:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
