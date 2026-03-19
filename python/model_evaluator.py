"""
Model Evaluator

Comprehensive evaluation framework for comparing base and fine-tuned models.

Usage:
    from python.model_evaluator import ModelEvaluator
    
    evaluator = ModelEvaluator()
    results = evaluator.evaluate_model(model_name, test_set)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import time

from python.rtl_generator import RTLGenerator


class ModelEvaluator:
    """Evaluate and compare model performance."""
    
    def __init__(self, results_dir: str = 'evaluation_results'):
        """Initialize evaluator."""
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # Evaluation metrics
        self.metrics = [
            'syntax_correctness',
            'simulation_success',
            'quality_score',
            'generation_time',
            'code_length',
            'test_coverage',
        ]
    
    def load_test_set(self, test_file: str) -> List[Dict]:
        """
        Load test set.
        
        Args:
            test_file: Path to test set file
            
        Returns:
            list: Test examples
        """
        test_examples = []
        
        with open(test_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    test_examples.append(json.loads(line))
        
        return test_examples
    
    def evaluate_single_example(
        self,
        generator: RTLGenerator,
        example: Dict
    ) -> Dict:
        """
        Evaluate single example.
        
        Args:
            generator: RTL generator instance
            example: Test example
            
        Returns:
            dict: Evaluation results
        """
        # Extract description
        description = example['messages'][1]['content']
        
        # Generate
        start_time = time.time()
        result = generator.generate(description, verify=True)
        generation_time = time.time() - start_time
        
        # Evaluate
        evaluation = {
            'description': description,
            'success': result['success'],
            'generation_time': generation_time,
        }
        
        if result['success']:
            # Syntax correctness
            evaluation['syntax_correct'] = True
            
            # Simulation success
            if result.get('verification'):
                evaluation['simulation_passed'] = result['verification'].get('passed', False)
            else:
                evaluation['simulation_passed'] = False
            
            # Quality score
            evaluation['quality_score'] = result.get('metadata', {}).get('quality_score', 0)
            
            # Code length
            evaluation['code_length'] = len(result['rtl_code'].split('\n'))
            
            # Test coverage (if available)
            if result.get('verification', {}).get('simulation'):
                sim_results = result['verification']['simulation']
                if sim_results.get('tests_total'):
                    evaluation['test_coverage'] = (
                        sim_results.get('tests_passed', 0) / 
                        sim_results.get('tests_total', 1) * 100
                    )
                else:
                    evaluation['test_coverage'] = 0
            else:
                evaluation['test_coverage'] = 0
        else:
            # Failed generation
            evaluation['syntax_correct'] = False
            evaluation['simulation_passed'] = False
            evaluation['quality_score'] = 0
            evaluation['code_length'] = 0
            evaluation['test_coverage'] = 0
            evaluation['error_message'] = result.get('message', 'Unknown error')
        
        return evaluation
    
    def evaluate_model(
        self,
        model_name: str,
        test_set: List[Dict],
        max_examples: Optional[int] = None,
        use_mock: bool = False
    ) -> Dict:
        """
        Evaluate model on test set.
        
        Args:
            model_name: Model identifier
            test_set: Test examples
            max_examples: Maximum examples to test
            use_mock: Use mock LLM
            
        Returns:
            dict: Evaluation results
        """
        print(f"\n{'='*70}")
        print(f"EVALUATING MODEL: {model_name}")
        print(f"{'='*70}")
        
        # Initialize generator
        generator = RTLGenerator(
            use_mock=use_mock,
            enable_verification=True
        )
        
        # Limit examples if specified
        if max_examples:
            test_set = test_set[:max_examples]
        
        print(f"\nTest examples: {len(test_set)}")
        
        # Evaluate each example
        results = []
        
        for i, example in enumerate(test_set, 1):
            print(f"\n[{i}/{len(test_set)}] Testing...")
            
            evaluation = self.evaluate_single_example(generator, example)
            results.append(evaluation)
            
            # Show progress
            status = "✓" if evaluation['success'] else "✗"
            print(f"  {status} {evaluation['description'][:60]}...")
            print(f"     Time: {evaluation['generation_time']:.1f}s")
            
            # Rate limiting
            time.sleep(0.5)
        
        # Calculate aggregate metrics
        metrics = self._calculate_metrics(results)
        
        # Save results
        output_file = self.results_dir / f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'model_name': model_name,
            'evaluated_at': datetime.now().isoformat(),
            'test_examples': len(test_set),
            'metrics': metrics,
            'individual_results': results,
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Results saved: {output_file}")
        
        return report
    
    def _calculate_metrics(self, results: List[Dict]) -> Dict:
        """Calculate aggregate metrics."""
        total = len(results)
        
        if total == 0:
            return {}
        
        metrics = {
            'total_examples': total,
            'successful_generations': sum(1 for r in results if r['success']),
            'syntax_correct': sum(1 for r in results if r.get('syntax_correct', False)),
            'simulation_passed': sum(1 for r in results if r.get('simulation_passed', False)),
            'average_quality_score': sum(r.get('quality_score', 0) for r in results) / total,
            'average_generation_time': sum(r['generation_time'] for r in results) / total,
            'average_code_length': sum(r.get('code_length', 0) for r in results) / total,
            'average_test_coverage': sum(r.get('test_coverage', 0) for r in results) / total,
        }
        
        # Calculate percentages
        metrics['success_rate'] = metrics['successful_generations'] / total * 100
        metrics['syntax_correctness_rate'] = metrics['syntax_correct'] / total * 100
        metrics['simulation_success_rate'] = metrics['simulation_passed'] / total * 100
        
        return metrics
    
    def compare_models(
        self,
        model_results: List[Dict]
    ) -> Dict:
        """
        Compare multiple model results.
        
        Args:
            model_results: List of evaluation results from different models
            
        Returns:
            dict: Comparison report
        """
        print(f"\n{'='*70}")
        print("MODEL COMPARISON")
        print(f"{'='*70}")
        
        comparison = {
            'models': [],
            'metrics_comparison': {},
        }
        
        # Extract metrics for each model
        for result in model_results:
            model_info = {
                'name': result['model_name'],
                'metrics': result['metrics'],
            }
            comparison['models'].append(model_info)
        
        # Compare each metric
        for metric in ['success_rate', 'syntax_correctness_rate', 'simulation_success_rate',
                      'average_quality_score', 'average_generation_time']:
            
            comparison['metrics_comparison'][metric] = {}
            
            for model_info in comparison['models']:
                value = model_info['metrics'].get(metric, 0)
                comparison['metrics_comparison'][metric][model_info['name']] = value
        
        # Determine winner for each metric
        for metric, values in comparison['metrics_comparison'].items():
            if 'time' in metric:
                # Lower is better
                winner = min(values.items(), key=lambda x: x[1])
            else:
                # Higher is better
                winner = max(values.items(), key=lambda x: x[1])
            
            comparison['metrics_comparison'][metric]['winner'] = winner[0]
        
        return comparison
    
    def print_evaluation_report(self, report: Dict):
        """Print formatted evaluation report."""
        print(f"\n{'='*70}")
        print(f"EVALUATION REPORT: {report['model_name']}")
        print(f"{'='*70}")
        
        metrics = report['metrics']
        
        print(f"\nTest Examples: {metrics['total_examples']}")
        print(f"\nSuccess Metrics:")
        print(f"  Overall Success Rate:     {metrics['success_rate']:.1f}%")
        print(f"  Syntax Correctness:       {metrics['syntax_correctness_rate']:.1f}%")
        print(f"  Simulation Pass Rate:     {metrics['simulation_success_rate']:.1f}%")
        
        print(f"\nQuality Metrics:")
        print(f"  Average Quality Score:    {metrics['average_quality_score']:.2f}/10")
        print(f"  Average Code Length:      {metrics['average_code_length']:.0f} lines")
        print(f"  Average Test Coverage:    {metrics['average_test_coverage']:.1f}%")
        
        print(f"\nPerformance Metrics:")
        print(f"  Average Generation Time:  {metrics['average_generation_time']:.1f}s")
        
        print(f"\n{'='*70}")
    
    def print_comparison_report(self, comparison: Dict):
        """Print formatted comparison report."""
        print(f"\n{'='*70}")
        print("MODEL COMPARISON REPORT")
        print(f"{'='*70}")
        
        print(f"\nModels Compared: {len(comparison['models'])}")
        for model in comparison['models']:
            print(f"  - {model['name']}")
        
        print(f"\nMetric Comparison:")
        print(f"{'Metric':<30} | {'Winner':<20} | Values")
        print("-" * 70)
        
        for metric, data in comparison['metrics_comparison'].items():
            if metric == 'winner':
                continue
            
            winner = data.get('winner', 'N/A')
            values_str = " | ".join([f"{k}: {v:.2f}" for k, v in data.items() if k != 'winner'])
            
            print(f"{metric:<30} | {winner:<20} | {values_str}")
        
        print(f"\n{'='*70}")


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Model Evaluator Self-Test\n")
    
    evaluator = ModelEvaluator()
    
    # Create dummy test set
    test_set = [
        {
            'messages': [
                {'role': 'system', 'content': 'You are an expert.'},
                {'role': 'user', 'content': '4-bit adder'},
                {'role': 'assistant', 'content': 'module adder...'}
            ]
        },
        {
            'messages': [
                {'role': 'system', 'content': 'You are an expert.'},
                {'role': 'user', 'content': '8-bit counter'},
                {'role': 'assistant', 'content': 'module counter...'}
            ]
        },
    ]
    
    # Evaluate (with mock)
    report = evaluator.evaluate_model(
        model_name="test_model",
        test_set=test_set,
        use_mock=True
    )
    
    # Print report
    evaluator.print_evaluation_report(report)
    
    print("\n✓ Self-test complete")
