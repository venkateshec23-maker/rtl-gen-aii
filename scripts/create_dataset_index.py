"""
Create Dataset Index

Creates searchable index of all designs.

Usage: python scripts/create_dataset_index.py
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class DatasetIndexer:
    """Create searchable index of dataset."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize indexer."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.metadata_dir = self.base_dir / 'metadata'
        self.metadata_dir.mkdir(exist_ok=True)
    
    def create_index(self) -> Dict:
        """
        Create complete dataset index.
        
        Returns:
            dict: Dataset index
        """
        index = {
            'created_at': datetime.now().isoformat(),
            'total_designs': 0,
            'by_category': {},
            'by_complexity': {},
            'by_pattern': {},
            'designs': [],
        }
        
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        for category in categories:
            category_dir = self.designs_dir / category
            if not category_dir.exists():
                continue
            
            index['by_category'][category] = 0
            
            for filepath in category_dir.glob('*.json'):
                with open(filepath) as f:
                    data = json.load(f)
                
                # Create index entry
                entry = {
                    'id': data['metadata']['id'],
                    'name': data['metadata']['name'],
                    'category': data['metadata']['category'],
                    'complexity': data['metadata']['complexity'],
                    'bit_width': data['metadata']['bit_width'],
                    'verified': data['metadata']['verified'],
                    'quality_score': data['metadata']['quality_score'],
                    'tags': data['metadata'].get('tags', []),
                    'file_path': str(filepath.relative_to(self.base_dir)),
                }
                
                # Add enhanced metadata if available
                if 'enhanced_metadata' in data:
                    entry['keywords'] = data['enhanced_metadata']['keywords']
                    entry['design_pattern'] = data['enhanced_metadata']['design_pattern']
                    entry['complexity_metrics'] = data['enhanced_metadata']['complexity_metrics']
                
                index['designs'].append(entry)
                
                # Update counts
                index['total_designs'] += 1
                index['by_category'][category] += 1
                
                # Update complexity count
                complexity = data['metadata']['complexity']
                if complexity not in index['by_complexity']:
                    index['by_complexity'][complexity] = 0
                index['by_complexity'][complexity] += 1
                
                # Update pattern count
                if 'enhanced_metadata' in data:
                    pattern = data['enhanced_metadata']['design_pattern']
                    if pattern not in index['by_pattern']:
                        index['by_pattern'][pattern] = 0
                    index['by_pattern'][pattern] += 1
        
        return index
    
    def save_index(self, index: Dict):
        """
        Save index to file.
        
        Args:
            index: Dataset index
        """
        import os
        import sys
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from python.dataset_manager import PathEncoder

        # Save full index
        index_file = self.metadata_dir / 'dataset_index.json'
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2, cls=PathEncoder)
        
        print(f"✓ Full index saved: {index_file}")
        
        # Save summary
        summary = {
            'created_at': index['created_at'],
            'total_designs': index['total_designs'],
            'by_category': index['by_category'],
            'by_complexity': index['by_complexity'],
            'by_pattern': index['by_pattern'],
        }
        
        summary_file = self.metadata_dir / 'dataset_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, cls=PathEncoder)
        
        print(f"✓ Summary saved: {summary_file}")
        
        # Save README
        readme = self.create_readme(summary)
        readme_file = self.metadata_dir / 'DATASET_README.md'
        readme_file.write_text(readme)
        
        print(f"✓ README saved: {readme_file}")
    
    def create_readme(self, summary: Dict) -> str:
        """
        Create README for dataset.
        
        Args:
            summary: Dataset summary
            
        Returns:
            str: README content
        """
        readme = f"""# RTL-Gen AI Training Dataset

**Created:** {summary['created_at']}
**Total Designs:** {summary['total_designs']}

## Overview

This dataset contains verified Verilog/SystemVerilog designs for training
AI models on hardware description language code generation.

## Statistics

### By Category
"""
        for cat, count in summary['by_category'].items():
            pct = count / summary['total_designs'] * 100
            readme += f"- {cat}: {count} ({pct:.1f}%)\n"
        
        readme += "\n### By Complexity\n"
        for comp, count in summary['by_complexity'].items():
            pct = count / summary['total_designs'] * 100
            readme += f"- {comp}: {count} ({pct:.1f}%)\n"
        
        readme += "\n### By Design Pattern\n"
        for pattern, count in summary['by_pattern'].items():
            pct = count / summary['total_designs'] * 100
            readme += f"- {pattern}: {count} ({pct:.1f}%)\n"
        
        readme += """
## Structure

Each design includes:
- Natural language description
- Synthesizable RTL code
- Comprehensive testbench
- Verification results
- Quality metrics
- Rich metadata

## Usage

```python
from python.dataset_manager import DatasetManager

manager = DatasetManager()
stats = manager.get_statistics()
print(f"Total designs: {stats['total_designs']}")

# Export for training
training_file = manager.export_for_training(format='jsonl')
print(f"Training data: {training_file}")
```

## Quality Assurance

All designs have been:
- ✓ Validated for correct JSON structure
- ✓ Compiled with Icarus Verilog
- ✓ Simulated with comprehensive testbenches
- ✓ Checked for code quality
- ✓ Enhanced with rich metadata

## License

This dataset is provided for training AI models only.
Individual designs maintain their original licenses.
"""
        return readme
    
    def run(self):
        """Run indexing process."""
        print("=" * 70)
        print("CREATING DATASET INDEX")
        print("=" * 70)
        
        index = self.create_index()
        self.save_index(index)
        
        print("\n" + "=" * 70)
        print("INDEXING COMPLETE")
        print("=" * 70)
        if index['total_designs'] == 0:
            print("No designs found.")
            return
        print(f"Total designs: {index['total_designs']}")
        print("\nBy category:")
        for cat, count in index['by_category'].items():
            print(f"  {cat}: {count}")
        print("=" * 70)


def main():
    """Main entry point."""
    indexer = DatasetIndexer()
    indexer.run()


if __name__ == "__main__":
    main()
