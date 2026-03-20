#!/usr/bin/env python3
"""
RTL-Gen AI: Deployment Verification Script

Checks if all dependencies, configurations, and prerequisites are ready
for cloud deployment to DigitalOcean or AWS.

Usage:
    python verify_deployment.py [--verbose] [--digitalocean] [--aws] [--all]

Examples:
    python verify_deployment.py                    # Check all
    python verify_deployment.py --verbose          # Detailed output
    python verify_deployment.py --digitalocean     # DigitalOcean only
    python verify_deployment.py --aws              # AWS only
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any

# Color codes for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class DeploymentVerifier:
    """Verify RTL-Gen AI deployment readiness"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks_passed = []
        self.checks_failed = []
        self.workspace_root = Path(__file__).parent.resolve()
        
    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
        print(f"{BOLD}{BLUE}{text:^60}{RESET}")
        print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
    
    def print_check(self, name: str, passed: bool, details: str = ""):
        """Print individual check result"""
        status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        symbol = "✓" if passed else "✗"
        
        if not details:
            print(f"  {status} {name}")
        else:
            print(f"  {status} {name}")
            if self.verbose or not passed:
                for line in details.split('\n'):
                    if line.strip():
                        print(f"     {line}")
        
        if passed:
            self.checks_passed.append(name)
        else:
            self.checks_failed.append(name)
    
    def run_command(self, cmd: str, shell: bool = True) -> Tuple[bool, str]:
        """Run command and return success status and output"""
        try:
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def check_file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        full_path = self.workspace_root / file_path
        return full_path.exists()
    
    def check_python_package(self, package: str) -> Tuple[bool, str]:
        """Check if Python package is installed"""
        try:
            __import__(package)
            version = ""
            try:
                version = f" ({__import__(package).__version__})"
            except:
                pass
            return True, f"Found{version}"
        except ImportError:
            return False, "Not installed"
    
    # ========================================================================
    # Core Checks
    # ========================================================================
    
    def verify_core_files(self):
        """Verify core application files exist"""
        self.print_header("Core Application Files")
        
        core_files = [
            'app.py',
            'requirements.txt',
            'config.json',
            'python/llm_client.py',
            'python/waveform_generator.py',
            'python/synthesis_engine.py',
            'python/testbench_generator.py',
            'python/database.py',
        ]
        
        for file_path in core_files:
            exists = self.check_file_exists(file_path)
            self.print_check(f"File: {file_path}", exists)
    
    def verify_python_env(self):
        """Verify Python environment"""
        self.print_header("Python Environment")
        
        # Check Python version
        version_cmd = "python --version"
        success, version = self.run_command(version_cmd)
        self.print_check("Python installed", success, version)
        
        if success and "3.11" not in version and "3.12" not in version:
            print(f"     {YELLOW}⚠ Recommended: Python 3.11 or 3.12{RESET}")
    
    def verify_dependencies(self):
        """Verify required dependencies"""
        self.print_header("Python Dependencies")
        
        packages = {
            'streamlit': 'Streamlit UI framework',
            'anthropic': 'Anthropic Claude API',
            'requests': 'HTTP client',
            'pytest': 'Testing framework',
            'sqlalchemy': 'Database ORM',
            'psycopg2': 'PostgreSQL driver',
            'matplotlib': 'Visualization',
        }
        
        for package, description in packages.items():
            success, details = self.check_python_package(package)
            self.print_check(f"{package}: {description}", success, details)
    
    def verify_docker(self):
        """Verify Docker installation"""
        self.print_header("Docker Setup")
        
        # Check Docker installed
        success, details = self.run_command("docker --version")
        self.print_check("Docker installed", success, details)
        
        # Check Docker running
        success_running, _ = self.run_command("docker ps")
        self.print_check("Docker daemon running", success_running, 
                        "Start Docker Desktop if not running")
        
        # Check Dockerfile exists
        dockerfile_exists = self.check_file_exists('Dockerfile')
        self.print_check("Dockerfile present", dockerfile_exists)
    
    def verify_deployment_files(self):
        """Verify deployment configuration files"""
        self.print_header("Deployment Configuration Files")
        
        deployment_files = [
            ('deploy/digitalocean/app.yaml', 'DigitalOcean'),
            ('deploy/digitalocean/README.md', 'DigitalOcean guide'),
            ('deploy/aws/cloudformation.yaml', 'AWS CloudFormation'),
            ('deploy/aws/ecs-task.json', 'AWS ECS task'),
            ('deploy/aws/README.md', 'AWS guide'),
            ('.github/workflows/deploy.yml', 'GitHub Actions pipeline'),
            ('CLOUD_DEPLOYMENT_QUICKSTART.md', 'Quick start guide'),
            ('CLOUD_INTEGRATION_GUIDE.md', 'Integration guide'),
        ]
        
        for file_path, description in deployment_files:
            exists = self.check_file_exists(file_path)
            self.print_check(f"{description}: {file_path}", exists)
    
    def verify_tests(self):
        """Verify tests can run"""
        self.print_header("Test Suite")
        
        tests_exist = self.check_file_exists('tests/')
        self.print_check("Tests directory exists", tests_exist)
        
        if tests_exist:
            success, output = self.run_command("python -m pytest tests/ --collect-only -q")
            test_count = len([l for l in output.split('\n') if l.startswith('tests/')])
            details = f"Found {test_count} tests" if test_count > 0 else "No tests found"
            self.print_check("Tests discovered", success, details)
    
    # ========================================================================
    # DigitalOcean Checks
    # ========================================================================
    
    def verify_digitalocean_cli(self):
        """Verify DigitalOcean CLI"""
        self.print_header("DigitalOcean: CLI Setup")
        
        # Check doctl installed
        success, version = self.run_command("doctl version")
        self.print_check("doctl CLI installed", success, version if success else "Install: https://github.com/digitalocean/doctl")
        
        if success:
            # Check authentication
            auth_success, _ = self.run_command("doctl auth list")
            self.print_check("doctl authenticated", auth_success, 
                            "Run: doctl auth init" if not auth_success else "Connected")
    
    def verify_digitalocean_config(self):
        """Verify DigitalOcean configuration"""
        self.print_header("DigitalOcean: Configuration")
        
        yaml_exists = self.check_file_exists('deploy/digitalocean/app.yaml')
        self.print_check("app.yaml present", yaml_exists)
        
        if yaml_exists:
            try:
                with open(self.workspace_root / 'deploy/digitalocean/app.yaml') as f:
                    content = f.read()
                    has_name = 'name:' in content
                    has_services = 'services:' in content
                    has_databases = 'databases:' in content
                    
                    self.print_check("app.yaml has 'name'", has_name)
                    self.print_check("app.yaml has 'services'", has_services)
                    self.print_check("app.yaml has 'databases'", has_databases)
                    
                    all_valid = has_name and has_services and has_databases
                    if not all_valid:
                        print(f"     {YELLOW}⚠ Check app.yaml format{RESET}")
            except Exception as e:
                self.print_check("app.yaml validates", False, str(e))
    
    # ========================================================================
    # AWS Checks
    # ========================================================================
    
    def verify_aws_cli(self):
        """Verify AWS CLI"""
        self.print_header("AWS: CLI Setup")
        
        # Check AWS CLI installed
        success, version = self.run_command("aws --version")
        self.print_check("AWS CLI installed", success, version if success else "Install: https://aws.amazon.com/cli/")
        
        if success:
            # Check credentials configured
            creds_success, _ = self.run_command("aws sts get-caller-identity")
            self.print_check("AWS credentials configured", creds_success,
                            "Run: aws configure" if not creds_success else "Authenticated")
    
    def verify_aws_config(self):
        """Verify AWS configuration files"""
        self.print_header("AWS: Configuration")
        
        cfn_exists = self.check_file_exists('deploy/aws/cloudformation.yaml')
        self.print_check("cloudformation.yaml present", cfn_exists)
        
        if cfn_exists:
            try:
                with open(self.workspace_root / 'deploy/aws/cloudformation.yaml') as f:
                    content = f.read()
                    has_format = 'AWSTemplateFormatVersion' in content
                    has_parameters = 'Parameters:' in content
                    has_resources = 'Resources:' in content
                    has_outputs = 'Outputs:' in content
                    
                    self.print_check("CloudFormation: Has format", has_format)
                    self.print_check("CloudFormation: Has parameters", has_parameters)
                    self.print_check("CloudFormation: Has resources", has_resources)
                    self.print_check("CloudFormation: Has outputs", has_outputs)
                    
                    all_valid = has_format and has_parameters and has_resources and has_outputs
                    if not all_valid:
                        print(f"     {YELLOW}⚠ Check CloudFormation template{RESET}")
            except Exception as e:
                self.print_check("CloudFormation validates", False, str(e))
    
    # ========================================================================
    # Configuration Checks
    # ========================================================================
    
    def verify_api_keys(self):
        """Check for API key environment variables"""
        self.print_header("API Keys & Secrets")
        
        keys = {
            'ANTHROPIC_API_KEY': 'Anthropic Claude API',
            'DEEPSEEK_API_KEY': 'DeepSeek API (optional)',
        }
        
        for key, description in keys.items():
            is_set = key in os.environ and os.environ[key]
            required = 'optional' not in description.lower()
            details = "Set" if is_set else "Not set"
            
            if not is_set and required:
                details = "Required for deployment"
            
            self.print_check(f"{description} ({key})", is_set or not required, details)
    
    def verify_database_config(self):
        """Verify database configuration"""
        self.print_header("Database Configuration")
        
        db_exists = self.check_file_exists('python/database.py')
        self.print_check("database.py exists", db_exists)
        
        if db_exists:
            success, output = self.run_command(
                "python -c 'from python.database import DesignDatabase; print(\"DesignDatabase imported successfully\")'"
            )
            self.print_check("database.py imports successfully", success, output if not success else "")
    
    # ========================================================================
    # Summary & Recommendations
    # ========================================================================
    
    def print_summary(self):
        """Print verification summary"""
        total = len(self.checks_passed) + len(self.checks_failed)
        
        self.print_header("Verification Summary")
        
        passed_count = len(self.checks_passed)
        failed_count = len(self.checks_failed)
        
        print(f"Total Checks: {total}")
        print(f"{GREEN}Passed: {passed_count}{RESET}")
        if failed_count > 0:
            print(f"{RED}Failed: {failed_count}{RESET}")
        print()
        
        if failed_count == 0:
            print(f"{GREEN}✓ All checks passed! You're ready to deploy!{RESET}\n")
            return True
        else:
            print(f"{YELLOW}⚠ Fix the {failed_count} failed check(s) before deploying:{RESET}\n")
            for check in self.checks_failed:
                print(f"  {RED}✗{RESET} {check}")
            print()
            return False
    
    def print_next_steps(self) -> str:
        """Print deployment next steps"""
        self.print_header("Deployment Next Steps")
        
        print(f"{BOLD}Option 1: DigitalOcean (Recommended - 5 minutes){RESET}")
        print("  1. doctl auth init")
        print("  2. doctl apps create --spec deploy/digitalocean/app.yaml")
        print("  3. doctl apps list")
        print()
        
        print(f"{BOLD}Option 2: AWS (Enterprise - 20 minutes){RESET}")
        print("  1. docker build -t rtl-gen-ai:latest .")
        print("  2. aws ecr get-login-password | docker login ...")
        print("  3. docker push ...")
        print("  4. aws cloudformation create-stack ...")
        print()
        
        print(f"{BOLD}Option 3: GitHub Actions (Automated){RESET}")
        print("  1. Configure GitHub Secrets")
        print("  2. git push origin main")
        print()
        
        print("For detailed instructions, see:")
        print("  - CLOUD_DEPLOYMENT_QUICKSTART.md")
        print("  - CLOUD_INTEGRATION_GUIDE.md")
        print("  - deploy/digitalocean/README.md")
        print("  - deploy/aws/README.md")
    
    def run_all_checks(self, check_digitalocean: bool = True, check_aws: bool = True):
        """Run all verification checks"""
        print(f"\n{BOLD}RTL-Gen AI: Deployment Verification{RESET}")
        print(f"Workspace: {self.workspace_root}\n")
        
        # Core checks
        self.verify_core_files()
        self.verify_python_env()
        self.verify_dependencies()
        self.verify_docker()
        self.verify_deployment_files()
        self.verify_tests()
        self.verify_api_keys()
        self.verify_database_config()
        
        # Optional checks
        if check_digitalocean:
            self.verify_digitalocean_cli()
            self.verify_digitalocean_config()
        
        if check_aws:
            self.verify_aws_cli()
            self.verify_aws_config()
        
        # Summary
        ready = self.print_summary()
        self.print_next_steps()
        
        return ready


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Verify RTL-Gen AI deployment readiness'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--digitalocean', action='store_true', help='Check DigitalOcean only')
    parser.add_argument('--aws', action='store_true', help='Check AWS only')
    parser.add_argument('--all', action='store_true', help='Check all (default)')
    
    args = parser.parse_args()
    
    # Determine what to check
    check_do = check_aws = True
    if args.digitalocean:
        check_aws = False
    elif args.aws:
        check_do = False
    
    # Run verification
    verifier = DeploymentVerifier(verbose=args.verbose)
    ready = verifier.run_all_checks(check_digitalocean=check_do, check_aws=check_aws)
    
    # Exit with appropriate code
    sys.exit(0 if ready else 1)


if __name__ == '__main__':
    main()
