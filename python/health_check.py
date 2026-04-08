"""
Health Check System for RTL-Gen AI

Usage:
    from python.health_check import HealthChecker
    
    checker = HealthChecker()
    status = checker.check_all()
    print(status)
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List
import time


class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self):
        """Initialize health checker."""
        self.checks = []
    
    def check_python_version(self) -> Dict:
        """Check Python version."""
        version = sys.version_info
        
        if version.major == 3 and version.minor >= 9:
            return {
                'name': 'Python Version',
                'status': 'OK',
                'message': f'Python {version.major}.{version.minor}.{version.micro}',
                'healthy': True,
            }
        else:
            return {
                'name': 'Python Version',
                'status': 'ERROR',
                'message': f'Python 3.9+ required, found {version.major}.{version.minor}',
                'healthy': False,
            }
    
    def check_dependencies(self) -> Dict:
        """Check if all dependencies are installed."""
        required = [
            'groq',
            'streamlit',
            'click',
            'pytest',
            'psutil',
        ]
        
        missing = []
        for package in required:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        if not missing:
            return {
                'name': 'Dependencies',
                'status': 'OK',
                'message': f'All {len(required)} packages installed',
                'healthy': True,
            }
        else:
            return {
                'name': 'Dependencies',
                'status': 'ERROR',
                'message': f'Missing: {", ".join(missing)}',
                'healthy': False,
            }
    
    def check_iverilog(self) -> Dict:
        """Check if Icarus Verilog is installed."""
        try:
            result = subprocess.run(
                ['iverilog', '-v'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = result.stderr.decode().split('\n')[0]
                return {
                    'name': 'Icarus Verilog',
                    'status': 'OK',
                    'message': version,
                    'healthy': True,
                }
            else:
                return {
                    'name': 'Icarus Verilog',
                    'status': 'WARNING',
                    'message': 'Installed but version check failed',
                    'healthy': True,
                }
        
        except FileNotFoundError:
            return {
                'name': 'Icarus Verilog',
                'status': 'ERROR',
                'message': 'Not installed or not in PATH',
                'healthy': False,
            }
        
        except Exception as e:
            return {
                'name': 'Icarus Verilog',
                'status': 'ERROR',
                'message': f'Check failed: {str(e)}',
                'healthy': False,
            }
    
    def check_directories(self) -> Dict:
        """Check if required directories exist."""
        required_dirs = [
            'cache',
            'cache/responses',
            'cache/verification',
            'outputs',
            'logs',
            'templates',
        ]
        
        missing = []
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing.append(dir_path)
        
        if not missing:
            return {
                'name': 'Directories',
                'status': 'OK',
                'message': f'All {len(required_dirs)} directories present',
                'healthy': True,
            }
        else:
            # Create missing directories
            for dir_path in missing:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            
            return {
                'name': 'Directories',
                'status': 'WARNING',
                'message': f'Created missing: {", ".join(missing)}',
                'healthy': True,
            }
    
    def check_disk_space(self) -> Dict:
        """Check available disk space."""
        import psutil
        
        disk = psutil.disk_usage('.')
        free_gb = disk.free / (1024**3)
        
        if free_gb > 1:
            return {
                'name': 'Disk Space',
                'status': 'OK',
                'message': f'{free_gb:.2f} GB free',
                'healthy': True,
            }
        elif free_gb > 0.5:
            return {
                'name': 'Disk Space',
                'status': 'WARNING',
                'message': f'Only {free_gb:.2f} GB free',
                'healthy': True,
            }
        else:
            return {
                'name': 'Disk Space',
                'status': 'ERROR',
                'message': f'Low disk space: {free_gb:.2f} GB',
                'healthy': False,
            }
    
    def check_memory(self) -> Dict:
        """Check available memory."""
        import psutil
        
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)
        
        if available_gb > 1:
            return {
                'name': 'Memory',
                'status': 'OK',
                'message': f'{available_gb:.2f} GB available',
                'healthy': True,
            }
        else:
            return {
                'name': 'Memory',
                'status': 'WARNING',
                'message': f'Low memory: {available_gb:.2f} GB',
                'healthy': True,
            }
    
    def check_api_key(self) -> Dict:
        """Check if API key is configured."""
        try:
            from python.config import NVIDIA_API_KEY, ENABLE_MOCK_LLM
            
            if ENABLE_MOCK_LLM:
                return {
                    'name': 'API Key',
                    'status': 'INFO',
                    'message': 'Using mock LLM (no API key needed)',
                    'healthy': True,
                }
            elif NVIDIA_API_KEY and NVIDIA_API_KEY != 'your-api-key-here':
                return {
                    'name': 'API Key',
                    'status': 'OK',
                    'message': 'Configured (NVIDIA/Groq)',
                    'healthy': True,
                }
            else:
                return {
                    'name': 'API Key',
                    'status': 'WARNING',
                    'message': 'Not configured (mock LLM will be used)',
                    'healthy': True,
                }
        except ImportError:
             return {
                'name': 'API Key',
                'status': 'WARNING',
                'message': 'Could not check config file',
                'healthy': True,
            }
    
    def check_all(self) -> Dict:
        """Run all health checks."""
        start_time = time.time()
        
        checks = [
            self.check_python_version(),
            self.check_dependencies(),
            self.check_iverilog(),
            self.check_directories(),
            self.check_disk_space(),
            self.check_memory(),
            self.check_api_key(),
        ]
        
        healthy_count = sum(1 for c in checks if c['healthy'])
        all_healthy = all(c['healthy'] for c in checks)
        
        duration = time.time() - start_time
        
        return {
            'overall_status': 'HEALTHY' if all_healthy else 'UNHEALTHY',
            'healthy': all_healthy,
            'checks': checks,
            'summary': {
                'total': len(checks),
                'healthy': healthy_count,
                'unhealthy': len(checks) - healthy_count,
                'duration_seconds': duration,
            },
            'timestamp': time.time(),
        }
    
    def print_report(self):
        """Print formatted health check report."""
        result = self.check_all()
        
        print("=" * 70)
        print("HEALTH CHECK REPORT")
        print("=" * 70)
        
        print(f"\nOverall Status: {result['overall_status']}")
        print(f"Duration: {result['summary']['duration_seconds']:.2f}s")
        
        print("\n" + "-" * 70)
        print("Component Checks:")
        print("-" * 70)
        
        for check in result['checks']:
            status_icon = {
                'OK': '✓',
                'WARNING': '⚠',
                'ERROR': '✗',
                'INFO': 'ℹ',
            }.get(check['status'], '•')
            
            print(f"{status_icon} {check['name']}: {check['status']}")
            print(f"  {check['message']}")
        
        print("\n" + "=" * 70)
        print(f"Summary: {result['summary']['healthy']}/{result['summary']['total']} healthy")
        print("=" * 70)
        
        return result['healthy']


# ============================================================================
# SELF-TEST & CLI
# ============================================================================

if __name__ == "__main__":
    print("RTL-Gen AI Health Check\n")
    
    checker = HealthChecker()
    is_healthy = checker.print_report()
    
    sys.exit(0 if is_healthy else 1)
