"""
Test Result Analysis Tool

Analyzes test results, generates insights, and provides quality metrics.

Usage: python analyze_test_results.py [--report test_report.json]
"""

import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict


class TestResultAnalyzer:
    """Analyzes test execution results."""
    
    def __init__(self, report_path='test_report.json'):
        self.report_path = Path(report_path)
        self.report = None
        self.load_report()
    
    def load_report(self):
        """Load report from file."""
        if not self.report_path.exists():
            print(f"Report file not found: {self.report_path}")
            return False
        
        try:
            with open(self.report_path, 'r') as f:
                self.report = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading report: {e}")
            return False
    
    def print_header(self, text):
        """Print formatted header."""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80)
    
    def analyze_overall_metrics(self):
        """Analyze overall testing metrics."""
        self.print_header("OVERALL TEST METRICS")
        
        if not self.report:
            print("No report data available.")
            return
        
        total = self.report.get('total_suites', 0)
        passed = self.report.get('passed_suites', 0)
        failed = self.report.get('failed_suites', 0)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTotal Suites:     {total}")
        print(f"Passed Suites:    {passed}")
        print(f"Failed Suites:    {failed}")
        print(f"Success Rate:     {success_rate:.1f}%")
        
        if self.report.get('duration_seconds'):
            print(f"Duration:         {self.report['duration_seconds']:.2f}s")
        
        print("\nResult Distribution:")
        print(f"  ✓ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"  ✗ Failed: {failed} ({failed/total*100:.1f}%)")
    
    def analyze_suite_performance(self):
        """Analyze individual suite performance."""
        self.print_header("SUITE PERFORMANCE ANALYSIS")
        
        if not self.report or 'suites' not in self.report:
            print("No suite data available.")
            return
        
        suites = self.report['suites']
        
        print("\nSuite Status:")
        print("-" * 80)
        
        for suite_name, result in suites.items():
            status = "✓ PASS" if result['passed'] else "✗ FAIL"
            print(f"{status} - {suite_name}")
            
            if 'error' in result:
                print(f"       Error: {result['error']}")
            
            if 'timestamp' in result:
                print(f"       Time:  {result['timestamp']}")
    
    def analyze_failure_patterns(self):
        """Identify failure patterns."""
        self.print_header("FAILURE PATTERN ANALYSIS")
        
        if not self.report or 'suites' not in self.report:
            print("No failure data available.")
            return
        
        failed_suites = [name for name, r in self.report['suites'].items() if not r['passed']]
        
        if not failed_suites:
            print("\n✓ No failures detected.")
            return
        
        print(f"\nFailed Suites: {len(failed_suites)}")
        print("-" * 80)
        
        error_types = defaultdict(list)
        
        for suite_name in failed_suites:
            result = self.report['suites'][suite_name]
            error = result.get('error', 'Unknown error')
            error_types[error].append(suite_name)
            print(f"  • {suite_name}")
            print(f"    - {error}\n")
        
        print("\nError Type Summary:")
        for error_type, suites in error_types.items():
            print(f"  {error_type}: {len(suites)} suite(s)")
    
    def generate_quality_score(self):
        """Generate overall quality score."""
        self.print_header("QUALITY SCORE")
        
        if not self.report:
            print("No report data available.")
            return
        
        total = self.report.get('total_suites', 0)
        passed = self.report.get('passed_suites', 0)
        
        if total == 0:
            score = 0
        else:
            score = (passed / total) * 100
        
        # Determine quality grade
        if score >= 95:
            grade = "A+"
            status = "Excellent"
        elif score >= 90:
            grade = "A"
            status = "Very Good"
        elif score >= 80:
            grade = "B"
            status = "Good"
        elif score >= 70:
            grade = "C"
            status = "Fair"
        else:
            grade = "D"
            status = "Poor"
        
        print(f"\nQuality Score:  {score:.1f}/100")
        print(f"Grade:          {grade}")
        print(f"Status:         {status}")
        
        print(f"\nDetails:")
        print(f"  • Test Coverage: {total} suites")
        print(f"  • Pass Rate:     {score:.1f}%")
        print(f"  • Failures:      {total - passed} suites")
    
    def generate_recommendations(self):
        """Generate recommendations."""
        self.print_header("RECOMMENDATIONS")
        
        if not self.report:
            print("No report data available.")
            return
        
        total = self.report.get('total_suites', 0)
        passed = self.report.get('passed_suites', 0)
        failed = self.report.get('failed_suites', 0)
        
        score = (passed / total * 100) if total > 0 else 0
        
        print(f"\nCurrent Status: {score:.1f}% Pass Rate\n")
        
        if score >= 95:
            print("✓ Recommendations for Excellent Status:")
            print("  • Maintain high test coverage")
            print("  • Continue monitoring performance metrics")
            print("  • Document test procedures")
            print("  • Plan for future enhancements")
        
        elif score >= 90:
            print("✓ Recommendations for Very Good Status:")
            print("  • Address remaining failures")
            print("  • Increase test coverage")
            print("  • Review edge cases")
            print("  • Monitor performance")
        
        elif score >= 80:
            print("⚠ Recommendations for Good Status:")
            print("  • Fix failing test suites")
            print("  • Improve error handling")
            print("  • Add more comprehensive tests")
            print("  • Review test architecture")
        
        else:
            print("✗ Critical Recommendations:")
            print("  • Immediately address failures")
            print("  • Debug failing tests")
            print("  • Review error messages carefully")
            print("  • Fix root causes before deployment")
    
    def generate_timeline_analysis(self):
        """Analyze test execution timeline."""
        self.print_header("EXECUTION TIMELINE")
        
        if not self.report or 'suites' not in self.report:
            print("No timeline data available.")
            return
        
        print(f"\nReport Generated: {self.report.get('timestamp', 'N/A')}")
        
        if self.report.get('duration_seconds'):
            print(f"Total Duration:  {self.report['duration_seconds']:.2f} seconds")
        
        print("\nSuite Execution Order:")
        print("-" * 80)
        
        for i, (suite_name, result) in enumerate(self.report['suites'].items(), 1):
            timestamp = result.get('timestamp', 'N/A')
            status = "✓" if result['passed'] else "✗"
            print(f"{i}. {status} {suite_name:25} ({timestamp})")
    
    def generate_full_report(self):
        """Generate comprehensive analysis report."""
        self.print_header("COMPREHENSIVE TEST ANALYSIS REPORT")
        
        self.analyze_overall_metrics()
        self.analyze_suite_performance()
        self.analyze_failure_patterns()
        self.generate_quality_score()
        self.generate_timeline_analysis()
        self.generate_recommendations()
        
        self.print_header("ANALYSIS COMPLETE")
    
    def export_metrics(self, filename='test_metrics.json'):
        """Export metrics to JSON file."""
        if not self.report:
            print("No report data to export.")
            return False
        
        total = self.report.get('total_suites', 0)
        passed = self.report.get('passed_suites', 0)
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_suites': total,
            'passed_suites': passed,
            'failed_suites': total - passed,
            'success_rate': (passed / total * 100) if total > 0 else 0,
            'duration_seconds': self.report.get('duration_seconds'),
            'quality_grade': self._get_quality_grade(),
            'suites': self.report.get('suites', {})
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(metrics, f, indent=2)
            print(f"\n📊 Metrics exported to {filename}")
            return True
        except Exception as e:
            print(f"Error exporting metrics: {e}")
            return False
    
    def _get_quality_grade(self):
        """Get quality grade."""
        total = self.report.get('total_suites', 0)
        passed = self.report.get('passed_suites', 0)
        
        score = (passed / total * 100) if total > 0 else 0
        
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        else:
            return "D"


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze test results")
    parser.add_argument('--report', '-r', default='test_report.json', help='Report file path')
    parser.add_argument('--export', '-e', help='Export metrics to file')
    parser.add_argument('--metrics', '-m', action='store_true', help='Show quality metrics')
    parser.add_argument('--failures', '-f', action='store_true', help='Show failure analysis')
    
    args = parser.parse_args()
    
    analyzer = TestResultAnalyzer(args.report)
    
    if not analyzer.report:
        print("Failed to load report. Exiting.")
        return
    
    if args.metrics:
        analyzer.generate_quality_score()
    elif args.failures:
        analyzer.analyze_failure_patterns()
    else:
        analyzer.generate_full_report()
    
    if args.export:
        analyzer.export_metrics(args.export)


if __name__ == "__main__":
    main()
