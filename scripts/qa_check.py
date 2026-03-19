"""
Quality Assurance Script
Runs comprehensive checks on generated code.

Usage: python scripts/qa_check.py
"""

import re
from typing import Dict, List
from pathlib import Path

from python.rtl_generator import RTLGenerator


class QualityChecker:
    """Check code quality of generated Verilog."""
    
    def __init__(self):
        """Initialize QA checker."""
        self.checks = {
            'syntax': [],
            'style': [],
            'best_practices': [],
            'warnings': [],
        }
    
    def check_code(self, rtl_code: str, module_name: str) -> Dict:
        """
        Run all quality checks on code.
        
        Args:
            rtl_code: Verilog RTL code
            module_name: Module name
            
        Returns:
            dict: Check results
        """
        results = {
            'passed': True,
            'score': 100,
            'issues': [],
        }
        
        # Check 1: Module declaration
        if not self._check_module_declaration(rtl_code, module_name):
            results['issues'].append({
                'severity': 'error',
                'category': 'syntax',
                'message': 'Missing or malformed module declaration'
            })
            results['score'] -= 20
            results['passed'] = False
        
        # Check 2: Port declarations
        if not self._check_port_declarations(rtl_code):
            results['issues'].append({
                'severity': 'warning',
                'category': 'style',
                'message': 'Port declarations could be improved'
            })
            results['score'] -= 5
        
        # Check 3: Indentation consistency
        if not self._check_indentation(rtl_code):
            results['issues'].append({
                'severity': 'warning',
                'category': 'style',
                'message': 'Inconsistent indentation'
            })
            results['score'] -= 5
        
        # Check 4: Comments present
        if not self._check_comments(rtl_code):
            results['issues'].append({
                'severity': 'info',
                'category': 'best_practices',
                'message': 'Consider adding more comments'
            })
            results['score'] -= 5
        
        # Check 5: Signal naming
        if not self._check_signal_names(rtl_code):
            results['issues'].append({
                'severity': 'warning',
                'category': 'style',
                'message': 'Some signal names could be more descriptive'
            })
            results['score'] -= 5
        
        # Check 6: No blocking assignments in always @(posedge)
        if self._has_blocking_in_sequential(rtl_code):
            results['issues'].append({
                'severity': 'warning',
                'category': 'best_practices',
                'message': 'Using blocking assignment (=) in sequential logic - consider non-blocking (<=)'
            })
            results['score'] -= 10
        
        # Check 7: Sensitivity list complete
        if not self._check_sensitivity_lists(rtl_code):
            results['issues'].append({
                'severity': 'warning',
                'category': 'best_practices',
                'message': 'Incomplete sensitivity lists detected'
            })
            results['score'] -= 5
        
        return results
    
    def _check_module_declaration(self, code: str, expected_name: str) -> bool:
        """Check module declaration is present and correct."""
        pattern = rf'module\s+{expected_name}\s*\('
        return bool(re.search(pattern, code))
    
    def _check_port_declarations(self, code: str) -> bool:
        """Check port declarations follow style guide."""
        # Look for proper port declarations
        has_ports = bool(re.search(r'(input|output|inout)', code))
        return has_ports
    
    def _check_indentation(self, code: str) -> bool:
        """Check indentation consistency."""
        lines = code.split('\n')
        indents = []
        
        for line in lines:
            if line.strip():  # Non-empty line
                indent = len(line) - len(line.lstrip())
                indents.append(indent)
        
        if not indents:
            return True
        
        # Check if indentation is consistent (multiples of 2 or 4)
        indent_unit = min(i for i in indents if i > 0) if any(i > 0 for i in indents) else 2
        
        consistent = all(indent % indent_unit == 0 for indent in indents)
        return consistent
    
    def _check_comments(self, code: str) -> bool:
        """Check if code has sufficient comments."""
        lines = code.split('\n')
        comment_lines = sum(1 for line in lines if '//' in line or '/*' in line)
        code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith('//'))
        
        if code_lines == 0:
            return True
        
        comment_ratio = comment_lines / code_lines
        return comment_ratio >= 0.1  # At least 10% comments
    
    def _check_signal_names(self, code: str) -> bool:
        """Check signal naming conventions."""
        # Look for single-letter signals (except common ones like a, b, i)
        pattern = r'\b([cdefghjklmnopqrstuvwxyz])\b'
        matches = re.findall(pattern, code.lower())
        
        # Allow some single-letter names
        allowed_single = {'a', 'b', 'i', 'j', 'x', 'y'}
        bad_names = [m for m in matches if m not in allowed_single]
        
        return len(bad_names) < 3
    
    def _has_blocking_in_sequential(self, code: str) -> bool:
        """Check for blocking assignments in sequential blocks."""
        # Find always @(posedge...) blocks
        always_blocks = re.findall(r'always\s*@\s*\(posedge[^)]+\)(.*?)end', code, re.DOTALL)
        
        for block in always_blocks:
            # Check for blocking assignments (=) not in if conditions
            if '=' in block and not '<=' in block:
                # More sophisticated check needed, but this is a start
                return True
        
        return False
    
    def _check_sensitivity_lists(self, code: str) -> bool:
        """Check for complete sensitivity lists in combinational logic."""
        # Find always @(...) blocks
        always_blocks = re.findall(r'always\s*@\s*\(([^)]+)\)', code)
        
        for sensitivity_list in always_blocks:
            # If it's not posedge/negedge (i.e., combinational)
            if 'posedge' not in sensitivity_list and 'negedge' not in sensitivity_list:
                # Should use always @(*) or always_comb
                if '*' not in sensitivity_list and 'always_comb' not in code:
                    return False
        
        return True
    
    def print_report(self, results: Dict, module_name: str):
        """Print formatted QA report."""
        print("=" * 70)
        print(f"QUALITY ASSURANCE REPORT: {module_name}")
        print("=" * 70)
        
        print(f"\nOverall: {'PASSED ✓' if results['passed'] else 'FAILED ✗'}")
        print(f"Quality Score: {results['score']}/100")
        
        if results['issues']:
            print(f"\nIssues Found: {len(results['issues'])}")
            print("-" * 70)
            
            for issue in results['issues']:
                severity_icon = {
                    'error': '❌',
                    'warning': '⚠️',
                    'info': 'ℹ️'
                }
                
                icon = severity_icon.get(issue['severity'], '•')
                print(f"{icon} [{issue['category']}] {issue['message']}")
        else:
            print("\n✓ No issues found!")
        
        print("=" * 70)


def run_qa_suite():
    """Run QA checks on generated designs."""
    print("=" * 70)
    print("QUALITY ASSURANCE SUITE")
    print("=" * 70)
    
    checker = QualityChecker()
    generator = RTLGenerator(use_mock=True, enable_verification=False)
    
    test_designs = [
        "4-bit adder",
        "8-bit counter with reset",
        "4-to-1 multiplexer",
    ]
    
    results = []
    
    for design in test_designs:
        print(f"\n\nGenerating: {design}")
        print("-" * 70)
        
        result = generator.generate(design)
        
        if result['success']:
            qa_result = checker.check_code(
                result['rtl_code'],
                result['module_name']
            )
            
            checker.print_report(qa_result, result['module_name'])
            results.append(qa_result)
        else:
            print(f"❌ Generation failed: {result.get('message')}")
    
    # Summary
    print("\n\n" + "=" * 70)
    print("QA SUITE SUMMARY")
    print("=" * 70)
    
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        passed = sum(1 for r in results if r['passed'])
        
        print(f"Average Quality Score: {avg_score:.1f}/100")
        print(f"Passed: {passed}/{len(results)}")
    
    print("=" * 70)


if __name__ == "__main__":
    run_qa_suite()
