"""
Dataset Validator for RTL-Gen AI

Validates quality, completeness, and correctness of training data.

Usage:
    from python.dataset_validator import DatasetValidator
    
    validator = DatasetValidator()
    report = validator.validate_all()
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import re
import subprocess


class DatasetValidator:
    """Comprehensive dataset validation."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize validator."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.validation_dir = self.base_dir / 'validation'
        self.validation_dir.mkdir(exist_ok=True)
        
        self.issues = []
        self.stats = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'warnings': 0,
        }
    
    def validate_json_structure(self, filepath: Path) -> Tuple[bool, List[str]]:
        """
        Validate JSON file structure.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            tuple: (is_valid, list of errors)
        """
        errors = []
        
        try:
            with open(filepath) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except Exception as e:
            return False, [f"Error reading file: {e}"]
        
        # Required top-level keys
        required_keys = ['metadata', 'description', 'code', 'verification']
        for key in required_keys:
            if key not in data:
                errors.append(f"Missing required key: {key}")
        
        # Validate metadata
        if 'metadata' in data:
            meta = data['metadata']
            required_meta = ['id', 'category', 'name', 'verified', 'created_date']
            for key in required_meta:
                if key not in meta:
                    errors.append(f"Missing metadata.{key}")
        
        # Validate description
        if 'description' in data:
            desc = data['description']
            if 'natural_language' not in desc:
                errors.append("Missing description.natural_language")
            elif len(desc['natural_language']) < 10:
                errors.append("Description too short (< 10 chars)")
        
        # Validate code
        if 'code' in data:
            code = data['code']
            if 'rtl' not in code:
                errors.append("Missing code.rtl")
            elif len(code['rtl']) < 50:
                errors.append("RTL code too short")
            
            if 'testbench' not in code:
                errors.append("Missing code.testbench")
        
        return len(errors) == 0, errors
    
    def validate_verilog_syntax(self, rtl_code: str, module_name: str) -> Tuple[bool, List[str]]:
        """
        Validate Verilog syntax using iverilog.
        
        Args:
            rtl_code: RTL code
            module_name: Module name for temp file
            
        Returns:
            tuple: (is_valid, list of errors)
        """
        errors = []
        
        # Create temporary file
        temp_file = self.validation_dir / f"temp_{module_name}.v"
        temp_file.write_text(rtl_code)
        
        try:
            # Try to compile with iverilog
            result = subprocess.run(
                ['iverilog', '-t', 'null', str(temp_file)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # Parse errors
                error_lines = result.stderr.split('\n')
                for line in error_lines:
                    if 'error:' in line.lower() or 'syntax error' in line.lower():
                        errors.append(line.strip())
            
        except FileNotFoundError:
            errors.append("iverilog not found - cannot validate syntax")
        except subprocess.TimeoutExpired:
            errors.append("Compilation timeout")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        finally:
            # Cleanup
            if temp_file.exists():
                temp_file.unlink()
        
        return len(errors) == 0, errors
    
    def validate_code_quality(self, rtl_code: str) -> Tuple[bool, List[str]]:
        """
        Check code quality standards.
        
        Args:
            rtl_code: RTL code
            
        Returns:
            tuple: (meets_standards, list of warnings)
        """
        warnings = []
        
        # Check for module declaration
        if not re.search(r'module\s+\w+', rtl_code):
            warnings.append("No module declaration found")
        
        # Check for endmodule
        if 'endmodule' not in rtl_code:
            warnings.append("No endmodule found")
        
        # Check for comments
        comment_lines = rtl_code.count('//')
        total_lines = len(rtl_code.split('\n'))
        if total_lines > 20 and comment_lines < total_lines * 0.1:
            warnings.append("Low comment density (< 10%)")
        
        # Check for proper indentation
        lines = rtl_code.split('\n')
        inconsistent_indent = False
        indents = []
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    indents.append(indent)
        
        if indents:
            # Check if indents are multiples of 2 or 4
            unique_indents = set(indents)
            base_indent = min(unique_indents)
            if base_indent not in [2, 4]:
                warnings.append(f"Non-standard indentation (base={base_indent})")
        
        # Check for blocking vs non-blocking in sequential
        if 'always @(posedge' in rtl_code or 'always_ff' in rtl_code:
            # Sequential logic - should use non-blocking (<=)
            if ' = ' in rtl_code and '<=' not in rtl_code:
                warnings.append("Sequential logic using blocking assignments")
        
        # Check signal naming
        signals = re.findall(r'\b([a-z_][a-z0-9_]*)\b', rtl_code)
        camel_case_signals = [s for s in signals if re.match(r'[a-z]+[A-Z]', s)]
        if camel_case_signals:
            warnings.append("Found camelCase signals (prefer snake_case)")
        
        return len(warnings) == 0, warnings
    
    def validate_testbench(self, testbench_code: str) -> Tuple[bool, List[str]]:
        """
        Validate testbench completeness.
        
        Args:
            testbench_code: Testbench code
            
        Returns:
            tuple: (is_complete, list of warnings)
        """
        warnings = []
        
        # Check for module declaration
        if not re.search(r'module\s+\w+', testbench_code):
            warnings.append("No testbench module found")
        
        # Check for timescale
        if '`timescale' not in testbench_code:
            warnings.append("No timescale directive")
        
        # Check for DUT instantiation
        if not re.search(r'\w+\s+\w+\s*\(', testbench_code):
            warnings.append("No DUT instantiation found")
        
        # Check for initial block
        if 'initial begin' not in testbench_code:
            warnings.append("No initial block found")
        
        # Check for $finish
        if '$finish' not in testbench_code:
            warnings.append("No $finish statement")
        
        # Check for waveform dump
        if '$dumpfile' not in testbench_code:
            warnings.append("No waveform dump ($dumpfile)")
        
        # Check for test reporting
        has_display = '$display' in testbench_code
        has_monitor = '$monitor' in testbench_code
        if not has_display and not has_monitor:
            warnings.append("No output reporting ($display or $monitor)")
        
        return len(warnings) < 3, warnings  # Allow up to 2 warnings
    
    def validate_verification_results(self, verification: Dict) -> Tuple[bool, List[str]]:
        """
        Validate verification results structure.
        
        Args:
            verification: Verification results dict
            
        Returns:
            tuple: (is_valid, list of errors)
        """
        errors = []
        
        # Check for compilation results
        if 'compilation' not in verification:
            errors.append("Missing compilation results")
        else:
            comp = verification['compilation']
            if 'passed' not in comp:
                errors.append("Missing compilation.passed")
        
        # Check for simulation results
        if 'simulation' not in verification:
            errors.append("Missing simulation results")
        else:
            sim = verification['simulation']
            if 'passed' not in sim:
                errors.append("Missing simulation.passed")
        
        return len(errors) == 0, errors
    
    def validate_design(self, filepath: Path) -> Dict:
        """
        Comprehensive validation of single design.
        
        Args:
            filepath: Path to design JSON file
            
        Returns:
            dict: Validation report
        """
        report = {
            'file': str(filepath),
            'valid': True,
            'errors': [],
            'warnings': [],
        }
        
        # 1. JSON structure
        json_valid, json_errors = self.validate_json_structure(filepath)
        if not json_valid:
            report['valid'] = False
            report['errors'].extend(json_errors)
            return report  # Can't continue without valid JSON
        
        # Load data
        with open(filepath) as f:
            data = json.load(f)
        
        # 2. Verilog syntax
        rtl_code = data['code']['rtl']
        module_name = data['metadata']['name']
        
        syntax_valid, syntax_errors = self.validate_verilog_syntax(rtl_code, module_name)
        if not syntax_valid:
            report['valid'] = False
            report['errors'].extend(syntax_errors)
        
        # 3. Code quality (warnings only)
        quality_ok, quality_warnings = self.validate_code_quality(rtl_code)
        report['warnings'].extend(quality_warnings)
        
        # 4. Testbench
        testbench_code = data['code']['testbench']
        tb_ok, tb_warnings = self.validate_testbench(testbench_code)
        if not tb_ok:
            report['warnings'].extend(tb_warnings)
        
        # 5. Verification results
        if 'verification' in data and data['verification']:
            verif_ok, verif_errors = self.validate_verification_results(data['verification'])
            if not verif_ok:
                report['errors'].extend(verif_errors)
        
        return report
    
    def validate_all(self) -> Dict:
        """
        Validate entire dataset.
        
        Returns:
            dict: Complete validation report
        """
        print("=" * 70)
        print("DATASET VALIDATION")
        print("=" * 70)
        
        all_reports = []
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        for category in categories:
            category_dir = self.designs_dir / category
            if not category_dir.exists():
                continue
            
            print(f"\nValidating {category}...")
            
            design_files = list(category_dir.glob('*.json'))
            for filepath in design_files:
                self.stats['total'] += 1
                
                report = self.validate_design(filepath)
                all_reports.append(report)
                
                if report['valid']:
                    self.stats['valid'] += 1
                    status = "✓"
                else:
                    self.stats['invalid'] += 1
                    status = "✗"
                
                if report['warnings']:
                    self.stats['warnings'] += len(report['warnings'])
                
                print(f"  {status} {filepath.name}")
                
                # Show errors
                for error in report['errors']:
                    print(f"      ERROR: {error}")
                
                # Show warnings (first 2 only)
                for warning in report['warnings'][:2]:
                    print(f"      WARNING: {warning}")
        
        # Save validation report
        report_file = self.validation_dir / 'validation_report.json'
        with open(report_file, 'w') as f:
            json.dump({
                'stats': self.stats,
                'reports': all_reports,
            }, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Total designs: {self.stats['total']}")
        print(f"Valid: {self.stats['valid']} ({self.stats['valid']/max(1,self.stats['total'])*100:.1f}%)")
        print(f"Invalid: {self.stats['invalid']}")
        print(f"Total warnings: {self.stats['warnings']}")
        print("=" * 70)
        
        print(f"\n✓ Report saved: {report_file}")
        
        return {
            'stats': self.stats,
            'report_file': str(report_file),
        }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Dataset Validator Self-Test\n")
    
    validator = DatasetValidator()
    report = validator.validate_all()
    
    print("\n✓ Validation complete")
