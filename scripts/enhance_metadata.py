"""
Metadata Enhancement Script

Adds rich metadata to training examples for better searchability.

Usage: python scripts/enhance_metadata.py
"""

import json
from pathlib import Path
from typing import Dict, List, Set
import re
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from python.dataset_manager import PathEncoder


class MetadataEnhancer:
    """Enhance design metadata."""
    
    # Comprehensive keyword taxonomy
    KEYWORDS = {
        'operations': [
            'add', 'subtract', 'multiply', 'divide', 'shift', 'rotate',
            'and', 'or', 'xor', 'not', 'nand', 'nor',
            'compare', 'equal', 'greater', 'less',
            'increment', 'decrement', 'count'
        ],
        'features': [
            'reset', 'enable', 'load', 'clear', 'preset',
            'carry', 'borrow', 'overflow', 'underflow',
            'valid', 'ready', 'acknowledge', 'strobe',
            'flag', 'status', 'control'
        ],
        'types': [
            'synchronous', 'asynchronous', 'combinational', 'sequential',
            'pipelined', 'parallel', 'serial', 'cascaded',
            'priority', 'round-robin', 'fifo', 'lifo'
        ],
        'components': [
            'adder', 'counter', 'register', 'shifter', 'multiplexer',
            'demux', 'encoder', 'decoder', 'comparator',
            'alu', 'fsm', 'controller', 'arbiter', 'buffer'
        ]
    }
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize enhancer."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.enhanced_count = 0
    
    def extract_keywords(self, text: str) -> Set[str]:
        """
        Extract relevant keywords from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            set: Extracted keywords
        """
        text_lower = text.lower()
        keywords = set()
        
        for category, terms in self.KEYWORDS.items():
            for term in terms:
                if term in text_lower:
                    keywords.add(term)
        
        return keywords
    
    def analyze_complexity_detailed(self, rtl_code: str) -> Dict:
        """
        Detailed complexity analysis.
        
        Args:
            rtl_code: RTL code
            
        Returns:
            dict: Complexity metrics
        """
        lines = [l.strip() for l in rtl_code.split('\n') if l.strip()]
        
        metrics = {
            'total_lines': len(lines),
            'code_lines': sum(1 for l in lines if l and not l.startswith('//')),
            'comment_lines': sum(1 for l in lines if l.startswith('//')),
            'module_count': rtl_code.count('module '),
            'always_blocks': rtl_code.count('always'),
            'assign_statements': rtl_code.count('assign'),
            'case_statements': rtl_code.count('case'),
            'if_statements': rtl_code.count(' if '),
            'for_loops': rtl_code.count('for '),
        }
        
        # Calculate cyclomatic complexity (simplified)
        metrics['cyclomatic_complexity'] = (
            metrics['if_statements'] +
            metrics['case_statements'] +
            metrics['for_loops'] + 1
        )
        
        return metrics
    
    def extract_io_ports(self, rtl_code: str) -> Dict:
        """
        Extract detailed I/O port information.
        
        Args:
            rtl_code: RTL code
            
        Returns:
            dict: Port information
        """
        ports = {
            'inputs': [],
            'outputs': [],
            'inouts': [],
        }
        
        # Find module ports
        module_match = re.search(
            r'module\s+\w+\s*\((.*?)\);',
            rtl_code,
            re.DOTALL
        )
        
        if not module_match:
            return ports
        
        port_list = module_match.group(1)
        
        # Parse inputs
        for match in re.finditer(r'input\s+(?:\[([^\]]+)\])?\s*(\w+)', port_list):
            width = match.group(1) if match.group(1) else '0:0'
            name = match.group(2)
            ports['inputs'].append({'name': name, 'width': width})
        
        # Parse outputs
        for match in re.finditer(r'output\s+(?:reg\s+)?(?:\[([^\]]+)\])?\s*(\w+)', port_list):
            width = match.group(1) if match.group(1) else '0:0'
            name = match.group(2)
            ports['outputs'].append({'name': name, 'width': width})
        
        return ports
    
    def infer_design_pattern(self, data: Dict) -> str:
        """
        Infer design pattern from code.
        
        Args:
            data: Design data
            
        Returns:
            str: Design pattern
        """
        rtl = data['code']['rtl'].lower()
        desc = data['description']['natural_language'].lower()
        
        # Pattern detection
        if 'parameter' in rtl:
            return 'parameterized'
        elif 'state' in rtl and 'case' in rtl:
            return 'fsm'
        elif 'always @(posedge' in rtl and 'counter' in desc:
            return 'sequential_counter'
        elif 'always @(posedge' in rtl:
            return 'sequential_register'
        elif 'assign' in rtl or 'always @(*)' in rtl:
            return 'combinational'
        else:
            return 'unknown'
    
    def enhance_design(self, filepath: Path) -> bool:
        """
        Enhance metadata for single design.
        
        Args:
            filepath: Path to design JSON
            
        Returns:
            bool: True if enhanced
        """
        with open(filepath) as f:
            data = json.load(f)
        
        # Skip if already enhanced
        if 'enhanced_metadata' in data:
            return False
        
        # Extract keywords
        text = data['description']['natural_language'] + ' ' + data['code']['rtl']
        keywords = self.extract_keywords(text)
        
        # Analyze complexity
        complexity_metrics = self.analyze_complexity_detailed(data['code']['rtl'])
        
        # Extract ports
        ports = self.extract_io_ports(data['code']['rtl'])
        
        # Infer pattern
        pattern = self.infer_design_pattern(data)
        
        # Create enhanced metadata
        enhanced = {
            'keywords': sorted(list(keywords)),
            'complexity_metrics': complexity_metrics,
            'ports': ports,
            'design_pattern': pattern,
            'searchable_text': ' '.join([
                data['description']['natural_language'],
                data['metadata']['name'],
                data['metadata']['category'],
                ' '.join(data['metadata'].get('tags', [])),
                ' '.join(keywords)
            ]).lower(),
        }
        
        # Add to data
        data['enhanced_metadata'] = enhanced
        
        # Update original tags with keywords
        existing_tags = set(data['metadata'].get('tags', []))
        new_tags = existing_tags.union(keywords)
        data['metadata']['tags'] = sorted(list(new_tags))
        
        # Save
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, cls=PathEncoder)
        
        self.enhanced_count += 1
        return True
    
    def enhance_all(self):
        """Enhance all designs in dataset."""
        print("=" * 70)
        print("ENHANCING METADATA")
        print("=" * 70)
        
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        for category in categories:
            category_dir = self.designs_dir / category
            if not category_dir.exists():
                continue
            
            print(f"\nEnhancing {category}...")
            
            design_files = list(category_dir.glob('*.json'))
            for filepath in design_files:
                if self.enhance_design(filepath):
                    print(f"  ✓ {filepath.name}")
        
        print("\n" + "=" * 70)
        print("ENHANCEMENT COMPLETE")
        print("=" * 70)
        print(f"Enhanced: {self.enhanced_count} designs")
        print("=" * 70)


def main():
    """Main entry point."""
    enhancer = MetadataEnhancer()
    enhancer.enhance_all()


if __name__ == "__main__":
    main()
