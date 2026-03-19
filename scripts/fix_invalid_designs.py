"""
Fix Invalid Designs

Automatically fixes common issues in training data.

Usage: python scripts/fix_invalid_designs.py
"""

import json
from pathlib import Path
from typing import Dict, List
import re


class DesignFixer:
    """Fix common issues in training data."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize fixer."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.fixed_count = 0
        self.unfixable_count = 0
    
    def fix_indentation(self, code: str) -> str:
        """
        Fix inconsistent indentation.
        
        Args:
            code: Verilog code
            
        Returns:
            str: Fixed code
        """
        lines = code.split('\n')
        fixed_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                fixed_lines.append('')
                continue
            
            # Decrease indent for end keywords
            if any(stripped.startswith(kw) for kw in ['end', 'endmodule', 'endcase', 'endfunction']):
                indent_level = max(0, indent_level - 1)
            
            # Add line with proper indentation
            fixed_lines.append('  ' * indent_level + stripped)
            
            # Increase indent for begin keywords
            if any(kw in stripped for kw in ['begin', 'case', 'function']):
                if not stripped.endswith('end'):  # Single line begin-end
                    indent_level += 1
            
            # Decrease after module
            if stripped.startswith('module '):
                indent_level += 1
        
        return '\n'.join(fixed_lines)
    
    def fix_blocking_assignments(self, code: str) -> str:
        """
        Fix blocking assignments in sequential logic.
        
        Args:
            code: Verilog code
            
        Returns:
            str: Fixed code
        """
        # Find sequential always blocks
        pattern = r'always\s*@\s*\(posedge[^)]+\)(.*?)(?=always|endmodule|$)'
        
        def replace_blocking(match):
            block = match.group(0)
            # Replace = with <= but not in comparisons
            fixed = re.sub(r'(\w+)\s*=\s*([^=])', r'\1 <= \2', block)
            return fixed
        
        fixed_code = re.sub(pattern, replace_blocking, code, flags=re.DOTALL)
        return fixed_code
    
    def add_missing_comments(self, code: str, module_name: str) -> str:
        """
        Add header comment if missing.
        
        Args:
            code: Verilog code
            module_name: Module name
            
        Returns:
            str: Code with header
        """
        if code.strip().startswith('//'):
            return code  # Already has comments
        
        header = f"""//============================================================================
// Module: {module_name}
// Description: Auto-generated RTL design
// Generator: RTL-Gen AI
//============================================================================

"""
        return header + code
    
    def fix_testbench(self, testbench: str, module_name: str) -> str:
        """
        Fix common testbench issues.
        
        Args:
            testbench: Testbench code
            module_name: Module name
            
        Returns:
            str: Fixed testbench
        """
        fixed = testbench
        
        # Add timescale if missing
        if '`timescale' not in fixed:
            fixed = '`timescale 1ns/1ps\n\n' + fixed
        
        # Add $finish if missing
        if '$finish' not in fixed and 'initial begin' in fixed:
            # Find last initial block
            lines = fixed.split('\n')
            for i in range(len(lines)-1, -1, -1):
                if 'end' in lines[i] and i > 0:
                    # Insert before this end
                    lines.insert(i, '    $finish;')
                    break
            fixed = '\n'.join(lines)
        
        # Add waveform dump if missing
        if '$dumpfile' not in fixed and 'initial begin' in fixed:
            dump_code = f"""    $dumpfile("{module_name}.vcd");
    $dumpvars(0, {module_name}_tb);
    """
            # Insert after initial begin
            fixed = fixed.replace('initial begin', f'initial begin\n{dump_code}')
        
        return fixed
    
    def fix_design(self, filepath: Path) -> bool:
        """
        Fix design file.
        
        Args:
            filepath: Path to design JSON
            
        Returns:
            bool: True if fixed successfully
        """
        try:
            with open(filepath) as f:
                data = json.load(f)
        except:
            print(f"  ✗ Cannot read: {filepath.name}")
            self.unfixable_count += 1
            return False
        
        fixed = False
        
        # Fix RTL code
        if 'code' in data and 'rtl' in data['code']:
            original_rtl = data['code']['rtl']
            
            # Apply fixes
            fixed_rtl = original_rtl
            fixed_rtl = self.fix_indentation(fixed_rtl)
            fixed_rtl = self.fix_blocking_assignments(fixed_rtl)
            fixed_rtl = self.add_missing_comments(fixed_rtl, data['metadata']['name'])
            
            if fixed_rtl != original_rtl:
                data['code']['rtl'] = fixed_rtl
                fixed = True
        
        # Fix testbench
        if 'code' in data and 'testbench' in data['code']:
            original_tb = data['code']['testbench']
            fixed_tb = self.fix_testbench(original_tb, data['metadata']['name'])
            
            if fixed_tb != original_tb:
                data['code']['testbench'] = fixed_tb
                fixed = True
        
        # Save if fixed
        if fixed:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.fixed_count += 1
            return True
        
        return False
    
    def fix_all(self):
        """Fix all designs in dataset."""
        print("=" * 70)
        print("FIXING INVALID DESIGNS")
        print("=" * 70)
        
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        for category in categories:
            category_dir = self.designs_dir / category
            if not category_dir.exists():
                continue
            
            print(f"\nFixing {category}...")
            
            design_files = list(category_dir.glob('*.json'))
            for filepath in design_files:
                if self.fix_design(filepath):
                    print(f"  ✓ Fixed: {filepath.name}")
        
        print("\n" + "=" * 70)
        print("FIXING COMPLETE")
        print("=" * 70)
        print(f"Fixed: {self.fixed_count}")
        print(f"Unfixable: {self.unfixable_count}")
        print("=" * 70)


def main():
    """Main entry point."""
    fixer = DesignFixer()
    fixer.fix_all()
    
    # Re-validate after fixing
    print("\n" + "=" * 70)
    print("RE-VALIDATING AFTER FIXES")
    print("=" * 70)
    
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from python.dataset_validator import DatasetValidator
    validator = DatasetValidator()
    validator.validate_all()


if __name__ == "__main__":
    main()
