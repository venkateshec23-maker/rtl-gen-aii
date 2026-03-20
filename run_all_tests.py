"""
Comprehensive Test Runner Orchestration

Orchestrates and coordinates running all test suites across the project.
Provides comprehensive results reporting and analysis.

Usage: python run_all_tests.py [--verbose] [--suite <suite_name>]
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path


class TestRunner:
    """Orchestrates test execution across all test suites."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = {}
        self.start_time = None
        self.end_time = None
        self.workspace_root = Path(__file__).parent
        
    def print_header(self, text):
        """Print formatted header."""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80)
    
    def run_suite(self, suite_name, script_name):
        """Run a single test suite."""
        print(f"\n▶ Running {suite_name}...")
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.workspace_root / script_name)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if self.verbose:
                print(result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
            
            passed = result.returncode == 0
            
            self.results[suite_name] = {
                'passed': passed,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timestamp': datetime.now().isoformat()
            }
            
            return passed
            
        except subprocess.TimeoutExpired:
            print(f"✗ {suite_name} TIMEOUT")
            self.results[suite_name] = {
                'passed': False,
                'error': 'Timeout',
                'timestamp': datetime.now().isoformat()
            }
            return False
        except Exception as e:
            print(f"✗ {suite_name} ERROR: {e}")
            self.results[suite_name] = {
                'passed': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def run_unit_tests(self):
        """Run unit test suite."""
        return self.run_suite("Unit Tests", "test_unit_suite.py")
    
    def run_performance_tests(self):
        """Run performance test suite."""
        return self.run_suite("Performance Tests", "test_performance_suite.py")
    
    def run_integration_tests(self):
        """Run integration test suite."""
        return self.run_suite("Integration Tests", "test_integration_suite.py")
    
    def generate_summary(self):
        """Generate test summary report."""
        self.print_header("TEST EXECUTION SUMMARY")
        
        if not self.results:
            print("No tests were run.")
            return
        
        total_suites = len(self.results)
        passed_suites = sum(1 for r in self.results.values() if r['passed'])
        failed_suites = total_suites - passed_suites
        
        print(f"\nTotal Suites: {total_suites}")
        print(f"Passed:       {passed_suites}")
        print(f"Failed:       {failed_suites}")
        print(f"Success Rate: {(passed_suites/total_suites*100):.1f}%")
        
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            print(f"Duration:     {duration:.2f}s")
        
        print("\nDetailed Results:")
        print("-" * 80)
        
        for suite_name, result in self.results.items():
            status = "✓ PASS" if result['passed'] else "✗ FAIL"
            print(f"{status} - {suite_name}")
            
            if 'error' in result:
                print(f"       Error: {result['error']}")
    
    def generate_detailed_report(self):
        """Generate detailed test report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_suites': len(self.results),
            'passed_suites': sum(1 for r in self.results.values() if r['passed']),
            'failed_suites': sum(1 for r in self.results.values() if not r['passed']),
            'duration_seconds': self.end_time - self.start_time if self.start_time and self.end_time else None,
            'suites': self.results
        }
        
        return report
    
    def save_report(self, filename='test_report.json'):
        """Save detailed report to file."""
        report = self.generate_detailed_report()
        
        report_path = self.workspace_root / filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Report saved to {filename}")
        return report_path
    
    def print_recommendations(self):
        """Print recommendations based on results."""
        self.print_header("RECOMMENDATIONS")
        
        failed_suites = [name for name, r in self.results.items() if not r['passed']]
        
        if not failed_suites:
            print("\n✓ All tests passed! No issues to address.")
            print("\nNext steps:")
            print("  • Continue with feature development")
            print("  • Monitor performance metrics")
            print("  • Maintain test coverage")
        else:
            print(f"\n✗ {len(failed_suites)} test suite(s) failed:\n")
            
            for suite in failed_suites:
                print(f"  • {suite}")
                result = self.results[suite]
                if 'error' in result:
                    print(f"    - {result['error']}")
            
            print("\nRecommended actions:")
            print("  1. Run individual test suites with --verbose flag")
            print("  2. Check test output for specific failures")
            print("  3. Fix failing tests before committing")
            print("  4. Re-run tests after fixes")
    
    def run_all(self):
        """Run all test suites."""
        self.print_header("COMPREHENSIVE TEST RUNNER")
        
        self.start_time = time.time()
        
        print("\nTest Suites to Run:")
        print("  1. Unit Tests")
        print("  2. Performance Tests")
        print("  3. Integration Tests")
        
        print("\n" + "-" * 80)
        
        self.run_unit_tests()
        self.run_performance_tests()
        self.run_integration_tests()
        
        self.end_time = time.time()
        
        self.generate_summary()
        self.print_recommendations()
        
        self.save_report()
        
        self.print_header("TEST RUN COMPLETE")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run comprehensive test suite")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--suite', '-s', help='Run specific suite (unit, performance, integration)')
    parser.add_argument('--report', '-r', default='test_report.json', help='Report filename')
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    
    if args.suite:
        suite = args.suite.lower()
        if suite == 'unit':
            runner.run_unit_tests()
        elif suite == 'performance':
            runner.run_performance_tests()
        elif suite == 'integration':
            runner.run_integration_tests()
        else:
            print(f"Unknown suite: {suite}")
            sys.exit(1)
    else:
        runner.run_all()
    
    if runner.results:
        runner.generate_summary()
        runner.print_recommendations()
        runner.save_report(args.report)
        
        failed = sum(1 for r in runner.results.values() if not r['passed'])
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
