"""
Learning Engine for RTL-Gen AI

Learns from errors and successes to improve future generations.

Usage:
    from python.learning_engine import LearningEngine
    
    engine = LearningEngine()
    improved_prompt = engine.improve_prompt(original_prompt, error_info)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import re
from datetime import datetime


class LearningEngine:
    """Learn from generation attempts to improve quality."""
    
    def __init__(self, base_dir: str = 'data'):
        """Initialize learning engine."""
        self.base_dir = Path(base_dir)
        self.learning_dir = self.base_dir / 'learning'
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        self.corrections_file = self.learning_dir / 'corrections.jsonl'
        self.insights_file = self.learning_dir / 'insights.json'
        
        # Load existing insights
        self.insights = self._load_insights()
    
    def _load_insights(self) -> Dict:
        """Load existing learning insights."""
        if self.insights_file.exists():
            with open(self.insights_file) as f:
                return json.load(f)
        
        return {
            'successful_patterns': [],
            'failure_patterns': [],
            'prompt_improvements': [],
            'constraint_additions': [],
        }
    
    def _save_insights(self):
        """Save learning insights."""
        with open(self.insights_file, 'w') as f:
            json.dump(self.insights, f, indent=2)
    
    def log_correction(
        self,
        original_description: str,
        original_code: str,
        corrected_code: str,
        correction_type: str,
        notes: str = ""
    ):
        """
        Log a correction made to generated code.
        
        Args:
            original_description: Original description
            original_code: Original generated code
            corrected_code: Corrected code
            correction_type: Type of correction
            notes: Additional notes
        """
        correction = {
            'timestamp': datetime.now().isoformat(),
            'description': original_description,
            'original_code': original_code,
            'corrected_code': corrected_code,
            'correction_type': correction_type,
            'notes': notes,
        }
        
        with open(self.corrections_file, 'a') as f:
            f.write(json.dumps(correction) + '\n')
    
    def analyze_corrections(self) -> Dict:
        """
        Analyze logged corrections to extract patterns.
        
        Returns:
            dict: Analysis results
        """
        if not self.corrections_file.exists():
            return {'total_corrections': 0, 'patterns': {}}
        
        corrections = []
        with open(self.corrections_file) as f:
            for line in f:
                if line.strip():
                    corrections.append(json.loads(line))
        
        patterns = {
            'common_corrections': defaultdict(int),
            'by_type': defaultdict(int),
            'examples': [],
        }
        
        for correction in corrections:
            correction_type = correction['correction_type']
            patterns['by_type'][correction_type] += 1
            
            # Analyze what changed
            original = correction['original_code']
            corrected = correction['corrected_code']
            
            # Simple diff analysis
            if 'always @(*)' in original and 'always @(posedge' in corrected:
                patterns['common_corrections']['combinational_to_sequential'] += 1
            
            if ' = ' in original and ' <= ' in corrected:
                patterns['common_corrections']['blocking_to_nonblocking'] += 1
            
            if 'reg ' in original and 'wire ' in corrected:
                patterns['common_corrections']['reg_to_wire'] += 1
            
            # Store examples
            if len(patterns['examples']) < 10:
                patterns['examples'].append({
                    'type': correction_type,
                    'description': correction['description'],
                    'notes': correction['notes']
                })
        
        return {
            'total_corrections': len(corrections),
            'patterns': dict(patterns['common_corrections']),
            'by_type': dict(patterns['by_type']),
            'examples': patterns['examples'],
        }
    
    def improve_prompt(
        self,
        base_prompt: str,
        error_info: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Improve prompt based on learning.
        
        Args:
            base_prompt: Original prompt
            error_info: Information about previous errors
            context: Generation context
            
        Returns:
            str: Improved prompt
        """
        improved = base_prompt
        
        # Add learned constraints
        constraints = []
        
        # If there were previous syntax errors, add explicit syntax guidance
        if error_info and error_info.get('error_type') == 'syntax_error':
            constraints.append(
                "CRITICAL: Double-check syntax. Ensure all statements end with semicolons, "
                "all blocks have matching begin/end, and all identifiers are properly declared."
            )
        
        # If there were verification failures, add verification guidance
        if error_info and error_info.get('error_type') == 'verification_failure':
            constraints.append(
                "IMPORTANT: Generate testbench that thoroughly tests all functionality. "
                "Include corner cases and edge conditions."
            )
        
        # Add design-specific guidance based on context
        if context:
            design_type = context.get('design_type', '')
            
            if design_type == 'sequential':
                constraints.append(
                    "For sequential logic: Use non-blocking assignments (<=) inside "
                    "always @(posedge clk) blocks. Ensure proper reset logic."
                )
            
            if design_type == 'fsm':
                constraints.append(
                    "For FSM: Use 3-block coding style (next-state logic, state registers, "
                    "output logic). Declare all states clearly."
                )
        
        # Apply learned insights
        if self.insights.get('constraint_additions'):
            for constraint in self.insights['constraint_additions'][:3]:
                if constraint not in improved:
                    constraints.append(constraint)
        
        # Add constraints to prompt
        if constraints:
            improved += "\n\nADDITIONAL CONSTRAINTS:\n"
            for i, constraint in enumerate(constraints, 1):
                improved += f"{i}. {constraint}\n"
        
        return improved
    
    def learn_from_success(
        self,
        description: str,
        code: str,
        quality_score: float,
        verification_results: Dict
    ):
        """
        Learn from successful generation.
        
        Args:
            description: Design description
            code: Generated code
            quality_score: Quality score
            verification_results: Verification results
        """
        if quality_score >= 8.5 and verification_results.get('passed', False):
            pattern = {
                'description_keywords': re.findall(r'\b\w+\b', description.lower()),
                'code_features': self._extract_code_features(code),
                'quality_score': quality_score,
            }
            
            self.insights['successful_patterns'].append(pattern)
            self._save_insights()
    
    def learn_from_failure(
        self,
        description: str,
        code: str,
        error_type: str,
        error_message: str
    ):
        """
        Learn from generation failure.
        
        Args:
            description: Design description
            code: Generated code
            error_type: Error type
            error_message: Error message
        """
        pattern = {
            'description_keywords': re.findall(r'\b\w+\b', description.lower()),
            'error_type': error_type,
            'error_summary': error_message[:200],  # Truncate
        }
        
        self.insights['failure_patterns'].append(pattern)
        self._save_insights()
    
    def _extract_code_features(self, code: str) -> Dict:
        """Extract features from code."""
        features = {
            'has_always_posedge': 'always @(posedge' in code,
            'has_always_comb': 'always @(*)' in code or 'always_comb' in code,
            'has_case': 'case ' in code,
            'has_parameters': 'parameter ' in code or 'localparam ' in code,
            'uses_nonblocking': '<=' in code,
            'line_count': len(code.split('\n')),
        }
        return features
    
    def suggest_improvements(self) -> List[str]:
        """
        Generate improvement suggestions based on learning.
        
        Returns:
            list: Suggestions
        """
        suggestions = []
        
        # Analyze corrections
        correction_analysis = self.analyze_corrections()
        
        if correction_analysis.get('total_corrections', 0) > 0:
            common = correction_analysis.get('patterns', {})
            
            if common.get('blocking_to_nonblocking', 0) > 3:
                suggestions.append(
                    "Add explicit guidance about non-blocking assignments in sequential logic"
                )
                if "Use non-blocking assignments (<=) in always @(posedge clk) blocks" not in self.insights['constraint_additions']:
                    self.insights['constraint_additions'].append(
                        "Use non-blocking assignments (<=) in always @(posedge clk) blocks"
                    )
            
            if common.get('combinational_to_sequential', 0) > 3:
                suggestions.append(
                    "Improve detection of sequential vs combinational logic from description"
                )
            
            if common.get('reg_to_wire', 0) > 3:
                suggestions.append(
                    "Add guidance about when to use reg vs wire"
                )
                if "Use 'reg' only for variables assigned in always blocks, 'wire' for continuous assignments" not in self.insights['constraint_additions']:
                    self.insights['constraint_additions'].append(
                        "Use 'reg' only for variables assigned in always blocks, 'wire' for continuous assignments"
                    )
        
        # Save updated insights
        self._save_insights()
        
        return suggestions
    
    def get_learning_report(self) -> Dict:
        """
        Generate learning progress report.
        
        Returns:
            dict: Report data
        """
        correction_analysis = self.analyze_corrections()
        suggestions = self.suggest_improvements()
        
        report = {
            'total_corrections': correction_analysis.get('total_corrections', 0),
            'correction_patterns': correction_analysis.get('patterns', {}),
            'successful_patterns_learned': len(self.insights.get('successful_patterns', [])),
            'failure_patterns_learned': len(self.insights.get('failure_patterns', [])),
            'active_constraints': len(self.insights.get('constraint_additions', [])),
            'improvement_suggestions': suggestions,
        }
        
        return report
    
    def print_learning_report(self):
        """Print formatted learning report."""
        report = self.get_learning_report()
        
        print("=" * 70)
        print("LEARNING ENGINE REPORT")
        print("=" * 70)
        
        print(f"\nTotal Corrections Analyzed: {report['total_corrections']}")
        
        print("\nCommon Correction Patterns:")
        for pattern, count in sorted(report.get('correction_patterns', {}).items(),
                                     key=lambda x: x[1], reverse=True):
            print(f"  {pattern:40s}: {count:3d}")
        
        print(f"\nPatterns Learned:")
        print(f"  Successful patterns: {report['successful_patterns_learned']}")
        print(f"  Failure patterns: {report['failure_patterns_learned']}")
        print(f"  Active constraints: {report['active_constraints']}")
        
        print("\nImprovement Suggestions:")
        for i, suggestion in enumerate(report['improvement_suggestions'], 1):
            print(f"  {i}. {suggestion}")
        
        print("=" * 70)


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    
    print("Learning Engine Self-Test\n")
    
    engine = LearningEngine()
    
    # Log a correction
    engine.log_correction(
        original_description="8-bit counter",
        original_code="always @(*) count = count + 1;",
        corrected_code="always @(posedge clk) count <= count + 1;",
        correction_type="blocking_to_nonblocking",
        notes="Changed to sequential logic with non-blocking assignment"
    )
    
    # Improve a prompt
    improved = engine.improve_prompt(
        "Generate an 8-bit counter",
        error_info={'error_type': 'syntax_error'},
        context={'design_type': 'sequential'}
    )
    
    print("Improved Prompt:")
    print(improved)
    print()
    
    # Print learning report
    engine.print_learning_report()
    
    print("\n✓ Self-test complete")
