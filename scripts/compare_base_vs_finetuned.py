"""
Compare Base Model vs Fine-Tuned Model

Comprehensive comparison of base and fine-tuned model performance.

Usage: python scripts/compare_base_vs_finetuned.py
"""

import json
import argparse
from pathlib import Path

from python.model_evaluator import ModelEvaluator


def run_comparison(
    test_file: str = 'training_data/finetuning/test_set.jsonl',
    base_model: str = 'base',
    finetuned_model: str = 'finetuned',
    max_examples: int = 20,
    use_mock: bool = True
):
    """
    Run comparison between base and fine-tuned models.
    
    Args:
        test_file: Path to test set
        base_model: Base model identifier
        finetuned_model: Fine-tuned model identifier
        max_examples: Maximum test examples
        use_mock: Use mock LLM for testing
    """
    print("=" * 70)
    print("BASE VS FINE-TUNED MODEL COMPARISON")
    print("=" * 70)
    
    evaluator = ModelEvaluator()
    
    # Load test set
    print(f"\nLoading test set: {test_file}")
    test_set = evaluator.load_test_set(test_file)
    print(f"✓ Loaded {len(test_set)} test examples")
    
    if max_examples:
        test_set = test_set[:max_examples]
        print(f"✓ Using {len(test_set)} examples for comparison")
    
    # Evaluate base model
    print(f"\n{'='*70}")
    print("EVALUATING BASE MODEL")
    print(f"{'='*70}")
    
    base_results = evaluator.evaluate_model(
        model_name=base_model,
        test_set=test_set,
        use_mock=use_mock
    )
    
    evaluator.print_evaluation_report(base_results)
    
    # Evaluate fine-tuned model
    print(f"\n{'='*70}")
    print("EVALUATING FINE-TUNED MODEL")
    print(f"{'='*70}")
    
    finetuned_results = evaluator.evaluate_model(
        model_name=finetuned_model,
        test_set=test_set,
        use_mock=use_mock
    )
    
    evaluator.print_evaluation_report(finetuned_results)
    
    # Compare models
    comparison = evaluator.compare_models([base_results, finetuned_results])
    evaluator.print_comparison_report(comparison)
    
    # Calculate improvements
    print(f"\n{'='*70}")
    print("IMPROVEMENT ANALYSIS")
    print(f"{'='*70}")
    
    base_metrics = base_results['metrics']
    finetuned_metrics = finetuned_results['metrics']
    
    improvements = {
        'success_rate': finetuned_metrics['success_rate'] - base_metrics['success_rate'],
        'syntax_correctness': finetuned_metrics['syntax_correctness_rate'] - base_metrics['syntax_correctness_rate'],
        'simulation_success': finetuned_metrics['simulation_success_rate'] - base_metrics['simulation_success_rate'],
        'quality_score': finetuned_metrics['average_quality_score'] - base_metrics['average_quality_score'],
        'generation_time': base_metrics['average_generation_time'] - finetuned_metrics['average_generation_time'],
    }
    
    print("\nMetric Improvements (Fine-tuned vs Base):")
    for metric, improvement in improvements.items():
        direction = "↑" if improvement > 0 else "↓" if improvement < 0 else "→"
        sign = "+" if improvement > 0 else ""
        
        if 'rate' in metric or 'success' in metric:
            print(f"  {metric:<25}: {sign}{improvement:>6.1f}% {direction}")
        elif 'time' in metric:
            print(f"  {metric:<25}: {sign}{improvement:>6.1f}s {direction}")
        else:
            print(f"  {metric:<25}: {sign}{improvement:>6.2f} {direction}")
    
    # Save comparison
    comparison_file = Path('evaluation_results') / f'comparison_{base_model}_vs_{finetuned_model}.json'
    
    comparison_data = {
        'base_model': base_results,
        'finetuned_model': finetuned_results,
        'comparison': comparison,
        'improvements': improvements,
    }
    
    with open(comparison_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)
    
    print(f"\n✓ Comparison saved: {comparison_file}")
    
    # Recommendations
    print(f"\n{'='*70}")
    print("RECOMMENDATIONS")
    print(f"{'='*70}")
    
    if improvements['success_rate'] > 5:
        print("✓ Fine-tuned model shows significant improvement in success rate")
        print("  Recommendation: Deploy fine-tuned model")
    elif improvements['success_rate'] > 0:
        print("✓ Fine-tuned model shows modest improvement")
        print("  Recommendation: Consider deploying, monitor performance")
    else:
        print("⚠ Fine-tuned model does not show improvement")
        print("  Recommendation: Review training data and hyperparameters")
    
    if improvements['quality_score'] > 0.5:
        print("✓ Significant quality improvement detected")
    
    if improvements['generation_time'] > 2:
        print("✓ Notable speed improvement")
    
    print(f"\n{'='*70}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Compare base vs fine-tuned models')
    parser.add_argument('--test-file', type=str,
                       default='training_data/finetuning/test_set.jsonl',
                       help='Path to test set')
    parser.add_argument('--base-model', type=str, default='base',
                       help='Base model identifier')
    parser.add_argument('--finetuned-model', type=str, default='finetuned',
                       help='Fine-tuned model identifier')
    parser.add_argument('--max-examples', type=int, default=20,
                       help='Maximum test examples')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock LLM for testing')
    
    args = parser.parse_args()
    
    run_comparison(
        test_file=args.test_file,
        base_model=args.base_model,
        finetuned_model=args.finetuned_model,
        max_examples=args.max_examples,
        use_mock=args.mock
    )


if __name__ == "__main__":
    main()
