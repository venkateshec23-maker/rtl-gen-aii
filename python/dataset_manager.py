"""
Dataset Manager for RTL-Gen AI Training Data

Manages collection, organization, and validation of training examples.

Usage:
    from python.dataset_manager import DatasetManager
    
    manager = DatasetManager()
    manager.add_design(description, rtl_code, testbench, metadata)
    dataset = manager.export_for_training()
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re

class PathEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)

class DatasetManager:
    """Manage training dataset for RTL-Gen AI."""
    
    CATEGORIES = [
        'combinational',
        'sequential', 
        'fsm',
        'memory',
        'arithmetic',
        'control'
    ]
    
    COMPLEXITY_LEVELS = ['simple', 'medium', 'complex']
    
    def __init__(self, base_dir: str = 'training_data'):
        """
        Initialize dataset manager.
        
        Args:
            base_dir: Base directory for training data
        """
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.metadata_dir = self.base_dir / 'metadata'
        self.validation_dir = self.base_dir / 'validation'
        self.processed_dir = self.base_dir / 'processed'
        
        # Create directories
        for category in self.CATEGORIES:
            (self.designs_dir / category).mkdir(parents=True, exist_ok=True)
        
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.validation_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'total_designs': 0,
            'by_category': {cat: 0 for cat in self.CATEGORIES},
            'by_complexity': {level: 0 for level in self.COMPLEXITY_LEVELS},
            'verified': 0,
            'synthesizable': 0,
        }
    
    def generate_id(self, description: str, rtl_code: str) -> str:
        """
        Generate unique ID for design.
        
        Args:
            description: Design description
            rtl_code: RTL code
            
        Returns:
            str: Unique ID (SHA-256 hash)
        """
        content = f"{description}{rtl_code}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:16]
    
    def categorize_design(self, description: str, rtl_code: str) -> str:
        """
        Auto-categorize design based on description and code.
        
        Args:
            description: Design description
            rtl_code: RTL code
            
        Returns:
            str: Category name
        """
        desc_lower = description.lower()
        code_lower = rtl_code.lower()
        
        # FSM detection
        if any(word in desc_lower for word in ['fsm', 'state machine', 'state']):
            return 'fsm'
        
        # Memory detection
        if any(word in desc_lower for word in ['memory', 'ram', 'rom', 'fifo', 'buffer']):
            return 'memory'
        
        # Arithmetic detection
        if any(word in desc_lower for word in ['alu', 'adder', 'multiplier', 'divider', 'arithmetic']):
            return 'arithmetic'
        
        # Control detection
        if any(word in desc_lower for word in ['controller', 'decoder', 'encoder', 'control']):
            return 'control'
        
        # Sequential detection
        if 'always @(posedge' in code_lower or 'always_ff' in code_lower:
            return 'sequential'
        
        # Default: combinational
        return 'combinational'
    
    def estimate_complexity(self, rtl_code: str, testbench: str = "") -> str:
        """
        Estimate design complexity.
        
        Args:
            rtl_code: RTL code
            testbench: Testbench code
            
        Returns:
            str: Complexity level (simple/medium/complex)
        """
        # Count lines of code (excluding comments and whitespace)
        lines = [
            line.strip() 
            for line in rtl_code.split('\n')
            if line.strip() and not line.strip().startswith('//')
        ]
        
        loc = len(lines)
        
        # Count modules
        module_count = rtl_code.count('module ')
        
        # Count always blocks
        always_count = rtl_code.count('always')
        
        # Calculate complexity score
        score = loc + (module_count * 20) + (always_count * 10)
        
        if score < 50:
            return 'simple'
        elif score < 150:
            return 'medium'
        else:
            return 'complex'
    
    def extract_bit_width(self, description: str, rtl_code: str) -> int:
        """
        Extract bit width from description or code.
        
        Args:
            description: Design description
            rtl_code: RTL code
            
        Returns:
            int: Bit width (default 8 if not found)
        """
        # Try description first
        match = re.search(r'(\d+)-bit', description.lower())
        if match:
            return int(match.group(1))
        
        # Try code (look for port declarations)
        match = re.search(r'\[(\d+):0\]', rtl_code)
        if match:
            return int(match.group(1)) + 1
        
        return 8  # Default
    
    def add_design(
        self,
        description: str,
        rtl_code: str,
        testbench: str,
        verification_results: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add design to training dataset.
        
        Args:
            description: Natural language description
            rtl_code: RTL code
            testbench: Testbench code
            verification_results: Verification results from testing
            metadata: Additional metadata
            
        Returns:
            str: Design ID
        """
        # Generate ID
        design_id = self.generate_id(description, rtl_code)
        
        # Auto-categorize
        category = self.categorize_design(description, rtl_code)
        
        # Estimate complexity
        complexity = self.estimate_complexity(rtl_code, testbench)
        
        # Extract bit width
        bit_width = self.extract_bit_width(description, rtl_code)
        
        # Extract module name
        match = re.search(r'module\s+(\w+)', rtl_code)
        module_name = match.group(1) if match else 'unknown'
        
        # Create design record
        design_record = {
            'metadata': {
                'id': design_id,
                'category': category,
                'name': module_name,
                'bit_width': bit_width,
                'complexity': complexity,
                'verified': verification_results is not None and verification_results.get('passed', False),
                'quality_score': self._calculate_quality_score(rtl_code, verification_results),
                'created_date': datetime.now().isoformat(),
                'tags': self._extract_tags(description, rtl_code),
            },
            'description': {
                'natural_language': description,
                'detailed_spec': metadata.get('detailed_spec', '') if metadata else '',
                'requirements': metadata.get('requirements', []) if metadata else [],
            },
            'code': {
                'rtl': rtl_code,
                'testbench': testbench,
                'language': 'verilog',
                'style': 'ieee_standard',
            },
            'verification': verification_results or {},
            'learning_notes': {
                'common_errors': [],
                'best_practices': [],
                'optimization_tips': [],
            }
        }
        
        # Save to file
        filename = f"{category}_{module_name}_{bit_width}bit_{design_id[:8]}.json"
        filepath = self.designs_dir / category / filename
        
        with open(filepath, 'w') as f:
            json.dump(design_record, f, indent=2, cls=PathEncoder)
        
        # Update statistics
        self.stats['total_designs'] += 1
        self.stats['by_category'][category] += 1
        self.stats['by_complexity'][complexity] += 1
        if design_record['metadata']['verified']:
            self.stats['verified'] += 1
        
        print(f"✓ Added design: {design_id} ({category}/{complexity})")
        
        return design_id
    
    def _calculate_quality_score(self, rtl_code: str, verification: Optional[Dict]) -> float:
        """Calculate quality score (0-10)."""
        score = 5.0  # Base score
        
        # Code quality factors
        if '// ' in rtl_code:
            score += 1.0  # Has comments
        
        if 'parameter' in rtl_code or 'localparam' in rtl_code:
            score += 0.5  # Parameterized
        
        if len(rtl_code.split('\n')) < 100:
            score += 0.5  # Concise
        
        # Verification factors
        if verification:
            if verification.get('passed'):
                score += 2.0
            
            if verification.get('simulation', {}).get('coverage', 0) > 90:
                score += 1.0
        
        return min(10.0, score)
    
    def _extract_tags(self, description: str, rtl_code: str) -> List[str]:
        """Extract tags from description and code."""
        tags = set()
        
        # Common keywords
        keywords = [
            'adder', 'counter', 'register', 'mux', 'demux',
            'alu', 'shifter', 'comparator', 'encoder', 'decoder',
            'fifo', 'memory', 'fsm', 'controller'
        ]
        
        desc_lower = description.lower()
        code_lower = rtl_code.lower()
        
        for keyword in keywords:
            if keyword in desc_lower or keyword in code_lower:
                tags.add(keyword)
        
        return sorted(list(tags))
    
    def get_statistics(self) -> Dict:
        """Get dataset statistics."""
        # Refresh stats by scanning directory
        self.stats = {
            'total_designs': 0,
            'by_category': {cat: 0 for cat in self.CATEGORIES},
            'by_complexity': {level: 0 for level in self.COMPLEXITY_LEVELS},
            'verified': 0,
            'synthesizable': 0,
        }
        
        for category in self.CATEGORIES:
            category_dir = self.designs_dir / category
            if category_dir.exists():
                designs = list(category_dir.glob('*.json'))
                self.stats['by_category'][category] = len(designs)
                self.stats['total_designs'] += len(designs)
                
                # Count verified
                for design_file in designs:
                    with open(design_file) as f:
                        data = json.load(f)
                        if data['metadata'].get('verified'):
                            self.stats['verified'] += 1
                        
                        complexity = data['metadata'].get('complexity', 'simple')
                        if complexity in self.COMPLEXITY_LEVELS:
                            self.stats['by_complexity'][complexity] += 1
        
        return self.stats
    
    def print_statistics(self):
        """Print formatted statistics."""
        stats = self.get_statistics()
        
        print("=" * 70)
        print("TRAINING DATASET STATISTICS")
        print("=" * 70)
        print(f"\nTotal Designs: {stats['total_designs']}")
        print(f"Verified: {stats['verified']} ({stats['verified']/max(1, stats['total_designs'])*100:.1f}%)")
        
        print("\nBy Category:")
        for category, count in stats['by_category'].items():
            print(f"  {category:15s}: {count:3d}")
        
        print("\nBy Complexity:")
        for level, count in stats['by_complexity'].items():
            print(f"  {level:10s}: {count:3d}")
        
        print("=" * 70)
    
    def export_for_training(self, format: str = 'jsonl') -> Path:
        """
        Export dataset in format suitable for model training.
        
        Args:
            format: Export format ('jsonl', 'csv', 'parquet')
            
        Returns:
            Path: Path to exported file
        """
        if format != 'jsonl':
            raise NotImplementedError(f"Format {format} not yet implemented")
        
        output_file = self.processed_dir / f'training_data_{datetime.now().strftime("%Y%m%d")}.jsonl'
        
        with open(output_file, 'w') as out:
            for category in self.CATEGORIES:
                category_dir = self.designs_dir / category
                if not category_dir.exists():
                    continue
                
                for design_file in category_dir.glob('*.json'):
                    with open(design_file) as f:
                        data = json.load(f)
                    
                    # Convert to training format
                    training_example = {
                        'messages': [
                            {
                                'role': 'user',
                                'content': data['description']['natural_language']
                            },
                            {
                                'role': 'assistant',
                                'content': f"```verilog\n{data['code']['rtl']}\n```\n\n```verilog\n{data['code']['testbench']}\n```"
                            }
                        ]
                    }
                    
                    out.write(json.dumps(training_example) + '\n')
        
        print(f"✓ Exported training data to: {output_file}")
        return output_file


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Dataset Manager Self-Test\n")
    
    manager = DatasetManager()
    
    # Test adding a design
    description = "4-bit adder with carry"
    rtl = """module adder_4bit(
    input [3:0] a, b,
    input cin,
    output [3:0] sum,
    output cout
);
    assign {cout, sum} = a + b + cin;
endmodule"""
    
    testbench = """module adder_4bit_tb;
    // Testbench code
endmodule"""
    
    design_id = manager.add_design(
        description=description,
        rtl_code=rtl,
        testbench=testbench,
        verification_results={'passed': True}
    )
    
    print(f"\nAdded design: {design_id}")
    
    # Print statistics
    manager.print_statistics()
    
    print("\n✓ Self-test complete")
