"""
Dataset Curation Script

Removes low-quality designs based on quality scores and validation results.

Usage: python scripts/curate_dataset.py [--threshold 6.0]
"""

import json
import argparse
from pathlib import Path
import shutil
from typing import Dict, Tuple


class DatasetCurator:
    """Curate training dataset by removing low-quality examples."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize curator."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.quarantine_dir = self.base_dir / 'quarantine'
        self.quarantine_dir.mkdir(exist_ok=True)
        
        self.removed_count = 0
        self.kept_count = 0
    
    def should_remove(self, data: Dict, threshold: float = 6.0) -> Tuple[bool, str]:
        """
        Determine if design should be removed.
        
        Args:
            data: Design data
            threshold: Quality score threshold
            
        Returns:
            tuple: (should_remove, reason)
        """
        # Check quality score
        quality = data['metadata'].get('quality_score', 0)
        if quality < threshold:
            return True, f"Low quality score: {quality}"
        
        # Check verification
        if not data['metadata'].get('verified', False):
            return True, "Not verified"
        
        # Check if simulation passed
        if 'verification' in data and data['verification']:
            if 'simulation' in data['verification']:
                if not data['verification']['simulation'].get('passed', False):
                    return True, "Simulation failed"
        
        # Check code length (too short = incomplete)
        rtl_lines = len(data['code']['rtl'].split('\n'))
        if rtl_lines < 10:
            return True, f"Code too short: {rtl_lines} lines"
        
        # Check for missing module
        if 'module ' not in data['code']['rtl']:
            return True, "No module declaration"
        
        return False, "OK"
    
    def curate_category(self, category: str, threshold: float = 6.0):
        """
        Curate designs in specific category.
        
        Args:
            category: Design category
            threshold: Quality threshold
        """
        category_dir = self.designs_dir / category
        if not category_dir.exists():
            return
        
        print(f"\nCurating {category}...")
        
        quarantine_cat_dir = self.quarantine_dir / category
        quarantine_cat_dir.mkdir(exist_ok=True)
        
        design_files = list(category_dir.glob('*.json'))
        
        for filepath in design_files:
            with open(filepath) as f:
                data = json.load(f)
            
            should_remove, reason = self.should_remove(data, threshold)
            
            if should_remove:
                # Move to quarantine
                dest = quarantine_cat_dir / filepath.name
                shutil.move(str(filepath), str(dest))
                
                print(f"  ✗ Removed: {filepath.name} ({reason})")
                self.removed_count += 1
            else:
                self.kept_count += 1
    
    def curate_all(self, threshold: float = 6.0):
        """
        Curate entire dataset.
        
        Args:
            threshold: Quality threshold
        """
        print("=" * 70)
        print(f"CURATING DATASET (threshold={threshold})")
        print("=" * 70)
        
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        for category in categories:
            self.curate_category(category, threshold)
        
        print("\n" + "=" * 70)
        print("CURATION COMPLETE")
        print("=" * 70)
        print(f"Kept: {self.kept_count}")
        print(f"Removed: {self.removed_count}")
        if (self.kept_count + self.removed_count) > 0:
            print(f"Removal rate: {self.removed_count/(self.kept_count+self.removed_count)*100:.1f}%")
        print("=" * 70)
        
        print(f"\nRemoved designs moved to: {self.quarantine_dir}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Curate dataset')
    parser.add_argument('--threshold', type=float, default=6.0,
                       help='Quality score threshold (default: 6.0)')
    
    args = parser.parse_args()
    
    curator = DatasetCurator()
    curator.curate_all(threshold=args.threshold)


if __name__ == "__main__":
    main()
