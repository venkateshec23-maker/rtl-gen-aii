"""
Dataset Augmenter

Creates variations of existing designs to expand training dataset.

Usage:
    from python.dataset_augmenter import DatasetAugmenter
    
    augmenter = DatasetAugmenter()
    augmenter.augment_all(target_count=300)
"""

import json
from pathlib import Path
from typing import Dict, List
import re
import copy
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from python.dataset_manager import PathEncoder

class DatasetAugmenter:
    """Augment training dataset with variations."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize augmenter."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.augmented_count = 0
    
    def create_bitwidth_variant(self, data: Dict, new_bitwidth: int) -> Dict:
        """
        Create variant with different bit width.
        
        Args:
            data: Original design data
            new_bitwidth: New bit width
            
        Returns:
            dict: Augmented design
        """
        augmented = copy.deepcopy(data)
        
        old_bitwidth = data['metadata']['bit_width']
        
        # Update metadata
        augmented['metadata']['bit_width'] = new_bitwidth
        augmented['metadata']['id'] = data['metadata']['id'] + f"_w{new_bitwidth}"
        old_name = data['metadata']['name']
        
        # Create new name
        if str(old_bitwidth) in old_name:
            new_name = old_name.replace(str(old_bitwidth), str(new_bitwidth))
        else:
            new_name = f"{old_name}_{new_bitwidth}bit"
        
        augmented['metadata']['name'] = new_name
        
        # Update description
        old_desc = data['description']['natural_language']
        new_desc = old_desc.replace(f"{old_bitwidth}-bit", f"{new_bitwidth}-bit")
        augmented['description']['natural_language'] = new_desc
        
        # Update RTL code
        rtl = data['code']['rtl']
        
        # Replace bit width in port declarations
        # [7:0] -> [15:0] for 8->16 bit
        old_range = f"[{old_bitwidth-1}:0]"
        new_range = f"[{new_bitwidth-1}:0]"
        rtl = rtl.replace(old_range, new_range)
        
        # Replace module name
        rtl = rtl.replace(f"module {old_name}", f"module {new_name}")
        
        # Replace literal values
        # 8'd0 -> 16'd0
        rtl = re.sub(rf"{old_bitwidth}'d(\d+)", rf"{new_bitwidth}'d\1", rtl)
        rtl = re.sub(rf"{old_bitwidth}'b([01]+)", rf"{new_bitwidth}'b\1", rtl)
        rtl = re.sub(rf"{old_bitwidth}'h([0-9a-fA-F]+)", rf"{new_bitwidth}'h\1", rtl)
        
        augmented['code']['rtl'] = rtl
        
        # Update testbench
        tb = data['code']['testbench']
        tb = tb.replace(old_range, new_range)
        tb = tb.replace(old_name, new_name)
        tb = re.sub(rf"{old_bitwidth}'d(\d+)", rf"{new_bitwidth}'d\1", tb)
        tb = re.sub(rf"{old_bitwidth}'b([01]+)", rf"{new_bitwidth}'b\1", tb)
        
        augmented['code']['testbench'] = tb
        
        # Mark as augmented (not verified yet)
        augmented['metadata']['verified'] = False
        augmented['metadata']['augmented'] = True
        augmented['metadata']['augmentation_type'] = 'bitwidth_variant'
        augmented['metadata']['parent_id'] = data['metadata']['id']
        
        return augmented
    
    def create_style_variant(self, data: Dict, style: str) -> Dict:
        """
        Create variant with different coding style.
        
        Args:
            data: Original design data
            style: Style type ('always_comb', 'blocking', etc.)
            
        Returns:
            dict: Augmented design
        """
        augmented = copy.deepcopy(data)
        
        rtl = data['code']['rtl']
        
        if style == 'always_comb':
            # Convert always @(*) to always_comb
            rtl = rtl.replace('always @(*)', 'always_comb')
            rtl = rtl.replace('always @ (*)', 'always_comb')
        
        elif style == 'assign':
            # Convert simple always blocks to assign (combinational only)
            if 'always @(posedge' not in rtl:
                pass
        
        augmented['code']['rtl'] = rtl
        augmented['metadata']['augmented'] = True
        augmented['metadata']['augmentation_type'] = f'style_{style}'
        augmented['metadata']['verified'] = False
        
        return augmented
    
    def create_parameter_variant(self, data: Dict) -> Dict:
        """
        Add parameters to make design configurable.
        
        Args:
            data: Original design data
            
        Returns:
            dict: Augmented design with parameters
        """
        augmented = copy.deepcopy(data)
        
        rtl = data['code']['rtl']
        bitwidth = data['metadata']['bit_width']
        
        # Add parameter after module declaration
        module_match = re.search(r'(module\s+\w+\s*\()', rtl)
        if module_match:
            param_decl = f"\n  parameter WIDTH = {bitwidth};\n"
            
            # Replace [N:0] with [WIDTH-1:0]
            rtl_new = rtl.replace(f"[{bitwidth-1}:0]", "[WIDTH-1:0]")
            
            # Insert parameter
            insert_pos = module_match.end()
            rtl_new = rtl_new[:insert_pos] + param_decl + rtl_new[insert_pos:]
            
            augmented['code']['rtl'] = rtl_new
            augmented['metadata']['augmented'] = True
            augmented['metadata']['augmentation_type'] = 'parameterized'
            augmented['metadata']['verified'] = False
        
        return augmented
    
    def augment_design(
        self,
        filepath: Path,
        target_variants: int = 2
    ) -> List[Path]:
        """
        Create augmented variants of design.
        
        Args:
            filepath: Path to original design
            target_variants: Number of variants to create
            
        Returns:
            list: Paths to created variants
        """
        with open(filepath) as f:
            data = json.load(f)
        
        variants = []
        current_bitwidth = data['metadata']['bit_width']
        
        # Variant 1: Different bit width
        if current_bitwidth == 4:
            new_bitwidths = [8, 16]
        elif current_bitwidth == 8:
            new_bitwidths = [4, 16]
        elif current_bitwidth == 16:
            new_bitwidths = [8, 32]
        else:
            new_bitwidths = [8, 16]
        
        for new_bw in new_bitwidths[:target_variants]:
            try:
                variant = self.create_bitwidth_variant(data, new_bw)
                
                # Save variant
                variant_name = variant['metadata']['name']
                variant_file = filepath.parent / f"{variant_name}_{variant['metadata']['id'][:8]}.json"
                
                with open(variant_file, 'w') as f:
                    json.dump(variant, f, indent=2, cls=PathEncoder)
                
                variants.append(variant_file)
                self.augmented_count += 1
                
            except Exception as e:
                print(f"    Error creating variant: {e}")
        
        return variants
    
    def augment_category(
        self,
        category: str,
        variants_per_design: int = 2,
        max_designs: int = 50
    ):
        """
        Augment all designs in category.
        
        Args:
            category: Design category
            variants_per_design: Number of variants per design
            max_designs: Maximum designs to augment
        """
        category_dir = self.designs_dir / category
        if not category_dir.exists():
            return
        
        print(f"\nAugmenting {category}...")
        
        # Get non-augmented designs only
        design_files = []
        for f in category_dir.glob('*.json'):
            with open(f) as fp:
                data = json.load(fp)
            if not data['metadata'].get('augmented', False):
                design_files.append(f)
        
        design_files = design_files[:max_designs]
        
        for filepath in design_files:
            variants = self.augment_design(filepath, variants_per_design)
            if variants:
                print(f"  ✓ {filepath.name}: created {len(variants)} variants")
    
    def augment_all(
        self,
        target_count: int = 300,
        variants_per_design: int = 2
    ):
        """
        Augment dataset to reach target count.
        
        Args:
            target_count: Target total design count
            variants_per_design: Variants per original design
        """
        print("=" * 70)
        print(f"AUGMENTING DATASET (target={target_count})")
        print("=" * 70)
        
        # Get current count
        from python.dataset_manager import DatasetManager
        manager = DatasetManager()
        stats = manager.get_statistics()
        current_count = stats['total_designs']
        
        print(f"\nCurrent count: {current_count}")
        print(f"Target count: {target_count}")
        
        if current_count >= target_count:
            print("✓ Already at target count")
            return
        
        needed = target_count - current_count
        print(f"Need to create: {needed} more designs\n")
        
        # Distribute across categories
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        per_category = needed // len(categories)
        
        for category in categories:
            max_designs = max(1, per_category // variants_per_design)
            self.augment_category(category, variants_per_design, max_designs)
        
        print("\n" + "=" * 70)
        print("AUGMENTATION COMPLETE")
        print("=" * 70)
        print(f"Created: {self.augmented_count} variants")
        
        # Show new stats
        stats = manager.get_statistics()
        print(f"New total: {stats['total_designs']}")
        print("=" * 70)


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Dataset Augmenter Self-Test\n")
    
    augmenter = DatasetAugmenter()
    augmenter.augment_all(target_count=250, variants_per_design=2)
    
    print("\n✓ Augmentation complete")
