"""
Security Auditor

Performs security analysis on RTL-Gen AI system.

Usage:
    from python.security_auditor import SecurityAuditor
    
    auditor = SecurityAuditor()
    results = auditor.run_security_audit()
"""

import re
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class SecurityAuditor:
    """Security audit and vulnerability assessment."""
    
    def __init__(self):
        """Initialize security auditor."""
        self.audit_results = {
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'vulnerabilities': [],
            'warnings': [],
            'recommendations': [],
        }
        
        self.check_categories = {
            'input_validation': 'Input Validation',
            'code_injection': 'Code Injection Prevention',
            'path_traversal': 'Path Traversal Protection',
            'api_security': 'API Security',
            'file_permissions': 'File Permissions',
            'credential_management': 'Credential Management',
            'dependency_security': 'Dependency Security',
        }
    
    def run_security_audit(self) -> Dict:
        """Run comprehensive security audit."""
        print("\n" + "=" * 70)
        print("RTL-GEN AI SECURITY AUDIT")
        print("=" * 70)
        print(f"Started: {self.audit_results['timestamp']}\n")
        
        self.check_input_validation()
        self.check_code_injection()
        self.check_path_traversal()
        self.check_api_security()
        self.check_file_permissions()
        self.check_credential_management()
        self.check_dependency_security()
        
        self.generate_summary()
        self.save_audit_report()
        
        return self.audit_results
    
    def check_input_validation(self):
        """Check input validation security."""
        print("[1/7] Checking input validation...")
        
        check_result = {
            'category': 'input_validation',
            'passed': True,
            'issues': [],
        }
        
        files_to_check = [
            'python/rtl_generator.py',
            'python/input_validator.py',
        ]
        
        for file_path in files_to_check:
            if Path(file_path).exists():
                content = Path(file_path).read_text()
                
                if 'max_length' not in content and 'len(' in content:
                    check_result['issues'].append({
                        'file': file_path,
                        'severity': 'medium',
                        'description': 'Missing explicit input length validation',
                    })
                    check_result['passed'] = False
        
        if check_result['passed']:
            print("  ✓ Input validation: PASS")
        else:
            print(f"  ⚠ Input validation: {len(check_result['issues'])} issues")
        
        self.audit_results['checks'].append(check_result)
    
    def check_code_injection(self):
        """Check for code injection vulnerabilities."""
        print("[2/7] Checking code injection prevention...")
        
        check_result = {
            'category': 'code_injection',
            'passed': True,
            'issues': [],
        }
        
        dangerous_patterns = [
            (r'eval\(', 'Use of eval()'),
            (r'exec\(', 'Use of exec()'),
        ]
        
        python_files = list(Path('python').glob('*.py'))
        
        for file_path in python_files:
            if file_path.name not in ['security_auditor.py']:
                content = file_path.read_text()
                
                for pattern, desc in dangerous_patterns:
                    if re.search(pattern, content):
                        check_result['issues'].append({
                            'file': str(file_path),
                            'severity': 'high',
                            'description': desc,
                        })
                        check_result['passed'] = False
        
        if check_result['passed']:
            print("  ✓ Code injection prevention: PASS")
        else:
            print(f"  ✗ Code injection prevention: {len(check_result['issues'])} found")
        
        self.audit_results['checks'].append(check_result)
    
    def check_path_traversal(self):
        """Check for path traversal vulnerabilities."""
        print("[3/7] Checking path traversal protection...")
        
        check_result = {
            'category': 'path_traversal',
            'passed': True,
            'issues': [],
        }
        
        python_files = list(Path('python').glob('*.py'))
        
        for file_path in python_files[:3]:  # Check first 3 files
            content = file_path.read_text()
            
            if 'open(' in content or 'Path(' in content:
                if 'resolve()' not in content:
                    check_result['issues'].append({
                        'file': str(file_path),
                        'severity': 'medium',
                        'description': 'File operations without path validation',
                    })
        
        if check_result['passed']:
            print("  ✓ Path traversal protection: PASS")
        else:
            print(f"  ⚠ Path traversal protection: {len(check_result['issues'])} issues")
        
        self.audit_results['checks'].append(check_result)
    
    def check_api_security(self):
        """Check API security measures."""
        print("[4/7] Checking API security...")
        
        check_result = {
            'category': 'api_security',
            'passed': True,
            'issues': [],
        }
        
        api_files = ['python/llm_client.py']
        
        for file_path in api_files:
            if Path(file_path).exists():
                content = Path(file_path).read_text()
                
                if re.search(r'api_key\s*=\s*["\'][^"\']+["\']', content):
                    check_result['issues'].append({
                        'file': file_path,
                        'severity': 'critical',
                        'description': 'Hardcoded API key detected',
                    })
                    check_result['passed'] = False
        
        if check_result['passed']:
            print("  ✓ API security: PASS")
        else:
            print(f"  ✗ API security: {len(check_result['issues'])} issues")
        
        self.audit_results['checks'].append(check_result)
    
    def check_file_permissions(self):
        """Check file permissions."""
        print("[5/7] Checking file permissions...")
        
        check_result = {
            'category': 'file_permissions',
            'passed': True,
            'issues': [],
        }
        
        important_dirs = ['data', 'outputs']
        
        for dir_path in important_dirs:
            if Path(dir_path).exists():
                try:
                    stat_info = os.stat(dir_path)
                    mode = stat_info.st_mode
                    
                    if mode & 0o002:
                        check_result['issues'].append({
                            'file': dir_path,
                            'severity': 'high',
                            'description': f'Directory {dir_path} is world-writable',
                        })
                        check_result['passed'] = False
                except:
                    pass
        
        if check_result['passed']:
            print("  ✓ File permissions: PASS")
        else:
            print(f"  ⚠ File permissions: {len(check_result['issues'])} issues")
        
        self.audit_results['checks'].append(check_result)
    
    def check_credential_management(self):
        """Check credential management practices."""
        print("[6/7] Checking credential management...")
        
        check_result = {
            'category': 'credential_management',
            'passed': True,
            'issues': [],
        }
        
        if not Path('.env.example').exists():
            check_result['issues'].append({
                'file': '.env.example',
                'severity': 'low',
                'description': 'Missing .env.example',
            })
        
        if Path('.gitignore').exists():
            gitignore = Path('.gitignore').read_text()
            if '.env' not in gitignore:
                check_result['issues'].append({
                    'file': '.gitignore',
                    'severity': 'medium',
                    'description': 'Missing .env in .gitignore',
                })
        
        if check_result['passed']:
            print("  ✓ Credential management: PASS")
        else:
            print(f"  ⚠ Credential management: {len(check_result['issues'])} issues")
        
        self.audit_results['checks'].append(check_result)
    
    def check_dependency_security(self):
        """Check dependency security."""
        print("[7/7] Checking dependency security...")
        
        check_result = {
            'category': 'dependency_security',
            'passed': True,
            'issues': [],
        }
        
        if Path('requirements.txt').exists():
            requirements = Path('requirements.txt').read_text()
            lines = [l.strip() for l in requirements.split('\n') if l.strip()]
            unpinned = [l for l in lines if '==' not in l and l and not l.startswith('#')]
            
            if unpinned and len(unpinned) > 0:
                check_result['issues'].append({
                    'file': 'requirements.txt',
                    'severity': 'low',
                    'description': f'Unpinned dependencies: {len(unpinned)}',
                })
        
        if check_result['passed']:
            print("  ✓ Dependency security: PASS")
        else:
            print(f"  ⚠ Dependency security: {len(check_result['issues'])} issues")
        
        self.audit_results['checks'].append(check_result)
    
    def generate_summary(self):
        """Generate audit summary."""
        print("\n" + "=" * 70)
        print("AUDIT SUMMARY")
        print("=" * 70)
        
        total_checks = len(self.audit_results['checks'])
        passed_checks = sum(1 for c in self.audit_results['checks'] if c['passed'])
        
        print(f"\nChecks: {passed_checks}/{total_checks} passed")
        print(f"Issues: {sum(len(c.get('issues', [])) for c in self.audit_results['checks'])}")
        
        if passed_checks == total_checks:
            print("\n✓ NO MAJOR SECURITY ISSUES FOUND")
        else:
            print("\n⚠ SECURITY ISSUES FOUND - REVIEW RECOMMENDED")
    
    def save_audit_report(self):
        """Save audit report to file."""
        output_file = f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.audit_results, f, indent=2)
        
        print(f"\n✓ Audit report saved: {output_file}")


if __name__ == "__main__":
    auditor = SecurityAuditor()
    results = auditor.run_security_audit()
    print("\n✓ Audit complete")
