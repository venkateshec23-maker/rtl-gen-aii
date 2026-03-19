"""
Error Tracker for RTL-Gen AI

Tracks and analyzes generation errors to enable learning and improvement.

Usage:
    from python.error_tracker import ErrorTracker
    
    tracker = ErrorTracker()
    tracker.log_error(description, error_type, context)
    patterns = tracker.analyze_patterns()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
import hashlib


class ErrorTracker:
    """Track and analyze generation errors."""
    
    ERROR_CATEGORIES = [
        'syntax_error',
        'semantic_error',
        'verification_failure',
        'simulation_failure',
        'testbench_error',
        'incomplete_generation',
        'incorrect_logic',
        'port_mismatch',
        'timing_violation',
        'other'
    ]
    
    def __init__(self, base_dir: str = 'data'):
        """Initialize error tracker."""
        self.base_dir = Path(base_dir)
        self.errors_dir = self.base_dir / 'errors'
        self.errors_dir.mkdir(parents=True, exist_ok=True)
        
        self.errors_file = self.errors_dir / 'error_log.jsonl'
        self.patterns_file = self.errors_dir / 'error_patterns.json'
        
        # Statistics
        self.stats = {
            'total_errors': 0,
            'by_category': defaultdict(int),
            'by_design_type': defaultdict(int),
        }
    
    def generate_error_id(self, description: str, error_type: str) -> str:
        """
        Generate unique error ID.
        
        Args:
            description: Design description
            error_type: Error category
            
        Returns:
            str: Error ID
        """
        content = f"{description}{error_type}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:16]
    
    def log_error(
        self,
        description: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None,
        generated_code: Optional[str] = None,
        verification_results: Optional[Dict] = None
    ) -> str:
        """
        Log a generation error.
        
        Args:
            description: Original design description
            error_type: Error category
            error_message: Error message
            context: Additional context
            generated_code: Generated code (if any)
            verification_results: Verification results
            
        Returns:
            str: Error ID
        """
        if error_type not in self.ERROR_CATEGORIES:
            error_type = 'other'
        
        error_id = self.generate_error_id(description, error_type)
        
        error_record = {
            'id': error_id,
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {},
            'generated_code': generated_code,
            'verification_results': verification_results,
        }
        
        # Append to log
        with open(self.errors_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_record) + '\n')
        
        # Update statistics
        self.stats['total_errors'] += 1
        self.stats['by_category'][error_type] += 1
        
        if context and 'design_type' in context:
            self.stats['by_design_type'][context['design_type']] += 1
        
        return error_id
    
    def get_errors(
        self,
        error_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve errors from log.
        
        Args:
            error_type: Filter by error type
            limit: Maximum number of errors to return
            
        Returns:
            list: Error records
        """
        if not self.errors_file.exists():
            return []
        
        errors = []
        with open(self.errors_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                
                error = json.loads(line)
                
                # Filter by type if specified
                if error_type and error['error_type'] != error_type:
                    continue
                
                errors.append(error)
                
                # Limit results
                if limit and len(errors) >= limit:
                    break
        
        return errors
    
    def analyze_patterns(self) -> Dict:
        """
        Analyze error patterns to identify common issues.
        
        Returns:
            dict: Pattern analysis
        """
        errors = self.get_errors()
        
        if not errors:
            return {'patterns': [], 'total_analyzed': 0}
        
        patterns = {
            'common_syntax_errors': defaultdict(int),
            'common_keywords': defaultdict(int),
            'problematic_descriptions': [],
            'total_analyzed': len(errors),
        }
        
        for error in errors:
            error_type = error['error_type']
            error_msg = error['error_message'].lower()
            description = error['description'].lower()
            
            # Extract common syntax errors
            if error_type == 'syntax_error':
                # Extract error patterns
                if 'undefined' in error_msg:
                    patterns['common_syntax_errors']['undefined_identifier'] += 1
                if 'expected' in error_msg:
                    patterns['common_syntax_errors']['missing_token'] += 1
                if 'syntax error' in error_msg:
                    patterns['common_syntax_errors']['general_syntax'] += 1
            
            # Extract keywords from descriptions with errors
            words = description.split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    patterns['common_keywords'][word] += 1
            
            # Track problematic descriptions
            if error['context'].get('retry_count', 0) > 2:
                patterns['problematic_descriptions'].append({
                    'description': error['description'],
                    'error_type': error_type,
                    'retries': error['context'].get('retry_count', 0)
                })
        
        # Convert defaultdicts to regular dicts for JSON serialization
        patterns['common_syntax_errors'] = dict(
            sorted(patterns['common_syntax_errors'].items(), 
                   key=lambda x: x[1], reverse=True)[:10]
        )
        patterns['common_keywords'] = dict(
            sorted(patterns['common_keywords'].items(),
                   key=lambda x: x[1], reverse=True)[:20]
        )
        
        # Save patterns
        with open(self.patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)
        
        return patterns
    
    def get_statistics(self) -> Dict:
        """
        Get error statistics.
        
        Returns:
            dict: Statistics
        """
        errors = self.get_errors()
        
        stats = {
            'total_errors': len(errors),
            'by_category': defaultdict(int),
            'by_design_type': defaultdict(int),
            'recent_errors': [],
        }
        
        for error in errors:
            stats['by_category'][error['error_type']] += 1
            
            if error['context'] and 'design_type' in error['context']:
                stats['by_design_type'][error['context']['design_type']] += 1
        
        # Get recent errors (last 10)
        stats['recent_errors'] = errors[-10:]
        
        # Convert defaultdicts to regular dicts
        stats['by_category'] = dict(stats['by_category'])
        stats['by_design_type'] = dict(stats['by_design_type'])
        
        return stats
    
    def generate_improvement_suggestions(self) -> List[str]:
        """
        Generate suggestions for improvement based on error patterns.
        
        Returns:
            list: Improvement suggestions
        """
        patterns = self.analyze_patterns()
        suggestions = []
        
        # Syntax error suggestions
        syntax_errors = patterns.get('common_syntax_errors', {})
        if 'undefined_identifier' in syntax_errors:
            suggestions.append(
                "Add validation to ensure all identifiers are properly defined before use"
            )
        if 'missing_token' in syntax_errors:
            suggestions.append(
                "Improve syntax checking to catch missing tokens (semicolons, parentheses)"
            )
        
        # Keyword suggestions
        common_keywords = patterns.get('common_keywords', {})
        problematic_words = [w for w, count in common_keywords.items() if count > 5]
        if problematic_words:
            suggestions.append(
                f"Review prompt templates for these frequently problematic keywords: {', '.join(problematic_words[:5])}"
            )
        
        # Problematic descriptions
        problematic = patterns.get('problematic_descriptions', [])
        if len(problematic) > 5:
            suggestions.append(
                f"Add clarification prompts for ambiguous descriptions (found {len(problematic)} cases)"
            )
        
        return suggestions
    
    def print_report(self):
        """Print error analysis report."""
        stats = self.get_statistics()
        patterns = self.analyze_patterns()
        suggestions = self.generate_improvement_suggestions()
        
        print("=" * 70)
        print("ERROR ANALYSIS REPORT")
        print("=" * 70)
        
        print(f"\nTotal Errors Logged: {stats['total_errors']}")
        
        print("\nErrors by Category:")
        for category, count in sorted(stats['by_category'].items(), 
                                     key=lambda x: x[1], reverse=True):
            pct = count / max(stats['total_errors'], 1) * 100
            print(f"  {category:25s}: {count:3d} ({pct:5.1f}%)")
        
        print("\nErrors by Design Type:")
        for design_type, count in sorted(stats['by_design_type'].items(),
                                        key=lambda x: x[1], reverse=True):
            print(f"  {design_type:25s}: {count:3d}")
        
        print("\nCommon Syntax Errors:")
        for error, count in patterns.get('common_syntax_errors', {}).items():
            print(f"  {error:25s}: {count:3d}")
        
        print("\nImprovement Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
        
        print("\n" + "=" * 70)


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Error Tracker Self-Test\n")
    
    tracker = ErrorTracker()
    
    # Log some test errors
    tracker.log_error(
        description="8-bit adder",
        error_type="syntax_error",
        error_message="Syntax error: expected ';' at line 10",
        context={'design_type': 'combinational', 'retry_count': 1}
    )
    
    tracker.log_error(
        description="counter with reset",
        error_type="verification_failure",
        error_message="Simulation failed: output mismatch",
        context={'design_type': 'sequential', 'retry_count': 2}
    )
    
    # Print report
    tracker.print_report()
    
    print("\n✓ Self-test complete")
