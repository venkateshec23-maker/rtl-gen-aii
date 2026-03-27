"""
OpenCode AI Integration Module

Integrates OpenCode AI coding agent with RTL-Gen-AII pipeline.
Enables natural language to Verilog RTL code generation.

Installation options:
1. Local: npm install -g opencode-ai@latest
2. Docker: (automatic fallback if local not available)
3. Manual: https://opencode.ai/download
"""

import subprocess
import json
import re
import logging
import os
from pathlib import Path
from typing import Optional, Tuple
import tempfile

logger = logging.getLogger(__name__)


class OpenCodeGenerator:
    """Interface to OpenCode AI for Verilog code generation.
    
    Supports both local installation and Docker execution.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_docker: bool = False):
        """Initialize OpenCode generator.
        
        Args:
            api_key: Optional API key for remote models (Claude, OpenAI, etc.)
            use_docker: Force Docker usage instead of local OpenCode
        """
        self.api_key = api_key
        self.use_docker = use_docker
        self.docker_available = self._check_docker_available()
        self.opencode_available = self._check_opencode_installed()
        
        if not self.opencode_available and self.docker_available:
            logger.info("Local OpenCode not available, will use Docker")
            self.opencode_available = True  # Can use Docker fallback
        
    def _check_docker_available(self) -> bool:
        """Check if Docker is installed and daemon is running."""
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
    
    def _check_opencode_installed(self) -> bool:
        """Check if OpenCode is installed and accessible."""
        try:
            result = subprocess.run(
                ["opencode", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
    
    def _run_opencode_command(self, command: str, timeout: int = 60) -> Tuple[int, str, str]:
        """Execute OpenCode command via local installation or Docker.
        
        Args:
            command: OpenCode command to run
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        # Try local installation first
        if not self.use_docker:
            try:
                result = subprocess.run(
                    ["opencode"] + command.split(),
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return result.returncode, result.stdout, result.stderr
            except (FileNotFoundError, OSError):
                pass  # Fall through to Docker
        
        # Fall back to Docker
        if self.docker_available:
            cwd = os.getcwd()
            cmd = [
                "docker", "run", "-it", "--rm",
                "-v", f"{cwd}:/workspace",
                "-w", "/workspace",
                "node:25",
                "sh", "-c",
                f"npm install -g opencode-ai@latest > /dev/null 2>&1 && opencode {command}"
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                return 1, "", "Docker command timed out"
            except Exception as e:
                return 1, "", str(e)
        
        return 1, "", "Neither local OpenCode nor Docker available"
    
    def generate_verilog(
        self, 
        description: str,
        module_name: str = "generated_design",
        width: int = 8,
        style: str = "behavioral"
    ) -> Tuple[bool, str, str]:
        """Generate Verilog RTL from natural language description.
        
        Args:
            description: Natural language description of the circuit
            module_name: Name for the generated Verilog module
            width: Default data width for ports
            style: "behavioral", "dataflow", or "structural"
            
        Returns:
            Tuple of (success, verilog_code, log_message)
        """
        if not self.opencode_available:
            msg = "⚠️ OpenCode not available.\n"
            msg += "Install locally: npm install -g opencode-ai@latest\n"
            msg += "OR install Docker: https://docker.com/get-started/"
            return False, "", msg
        
        try:
            # Create prompt for OpenCode
            prompt = self._create_verilog_prompt(
                description, 
                module_name, 
                width, 
                style
            )
            
            # Run OpenCode command (local or Docker)
            returncode, stdout, stderr = self._run_opencode_command(
                f"run \"{prompt}\"",
                timeout=120  # Docker needs more time on first run
            )
            
            if returncode != 0:
                return False, "", f"OpenCode error: {stderr or stdout}"
            
            # Extract Verilog from response
            verilog_code = self._extract_verilog(stdout)
            
            if not verilog_code:
                return False, "", "Failed to extract Verilog from OpenCode response"
            
            log_msg = f"✅ Generated Verilog module '{module_name}' successfully (via {'Docker' if self.docker_available else 'local'})"
            return True, verilog_code, log_msg
            
        except subprocess.TimeoutExpired:
            return False, "", "OpenCode generation timed out (>120s)"
        except Exception as e:
            return False, "", f"Error during Verilog generation: {str(e)}"
    
    def analyze_verilog(self, verilog_code: str) -> Tuple[bool, str]:
        """Analyze Verilog code using OpenCode AI.
        
        Args:
            verilog_code: Verilog code to analyze
            
        Returns:
            Tuple of (success, analysis_text)
        """
        if not self.opencode_available:
            return False, "OpenCode not installed"
        
        try:
            prompt = f"Analyze this Verilog code and suggest improvements:\n\n{verilog_code}"
            
            result = subprocess.run(
                ["opencode", prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
                
        except Exception as e:
            return False, str(e)
    
    def optimize_design(self, verilog_code: str) -> Tuple[bool, str, str]:
        """Optimize Verilog design using OpenCode.
        
        Args:
            verilog_code: Verilog code to optimize
            
        Returns:
            Tuple of (success, optimized_code, log_message)
        """
        if not self.opencode_available:
            return False, verilog_code, "OpenCode not installed"
        
        try:
            prompt = f"""Optimize this Verilog code for area and speed.
Return only the optimized Verilog code without explanations.

Original code:
{verilog_code}"""
            
            result = subprocess.run(
                ["opencode", prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return False, verilog_code, f"Optimization error: {result.stderr}"
            
            optimized = self._extract_verilog(result.stdout)
            
            if optimized:
                return True, optimized, "✅ Design optimized successfully"
            else:
                return False, verilog_code, "Failed to extract optimized Verilog"
                
        except Exception as e:
            return False, verilog_code, f"Optimization failed: {str(e)}"
    
    def _create_verilog_prompt(
        self, 
        description: str, 
        module_name: str,
        width: int,
        style: str
    ) -> str:
        """Create optimized prompt for Verilog generation."""
        
        style_guidance = {
            "behavioral": "Use assign statements and always blocks",
            "dataflow": "Use only combinational logic",
            "structural": "Instantiate submodules if applicable"
        }.get(style, "Use any appropriate style")
        
        prompt = f"""Generate Verilog RTL code for the following circuit:

Circuit Description: {description}

Requirements:
- Module name: {module_name}
- Data width: {width} bits
- Style: {style_guidance}
- Include clock and reset signals where applicable
- Add comprehensive comments
- Ensure synthesis-friendly code
- Return only the complete module code (no explanations)

Format:
module {module_name} (
  // ports here
);
  // implementation here
endmodule
"""
        return prompt
    
    @staticmethod
    def _extract_verilog(text: str) -> str:
        """Extract Verilog code block from text response."""
        
        # Try to find Verilog module definition
        pattern = r'module\s+(\w+)\s*\([^)]*\)[^;]*?endmodule'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(0)
        
        # Fallback: try to extract code block
        if '```verilog' in text:
            start = text.find('```verilog') + 10
            end = text.find('```', start)
            if end > start:
                return text[start:end].strip()
        
        if '```' in text:
            parts = text.split('```')
            if len(parts) >= 3:
                return parts[1].strip()
        
        # Last resort: return text if it looks like Verilog
        if 'module' in text.lower() and 'endmodule' in text.lower():
            return text
        
        return ""
    
    def get_templates_from_ai(self, category: str) -> dict:
        """Get design templates from OpenCode AI.
        
        Args:
            category: Type of design (counter, shift_register, mux, alu, etc.)
            
        Returns:
            Dict with template code and metadata
        """
        if not self.opencode_available:
            return {}
        
        try:
            prompt = f"""Provide a complete, synthesis-ready Verilog implementation of a {category}.
Include:
- Module definition
- All necessary ports (clock, reset, data, control)
- Behavioral implementation
- Comments explaining functionality

Return only the Verilog code."""
            
            result = subprocess.run(
                ["opencode", prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                code = self._extract_verilog(result.stdout)
                if code:
                    return {
                        "success": True,
                        "category": category,
                        "code": code,
                        "source": "opencode_ai"
                    }
        
        except Exception as e:
            logger.error(f"Error fetching template: {e}")
        
        return {"success": False}


# Convenience functions for Streamlit integration

def generate_rtl_from_description(description: str) -> Tuple[bool, str, str]:
    """Generate RTL code from natural language description.
    
    Args:
        description: What the user wants to build
        
    Returns:
        (success, verilog_code, message)
    """
    gen = OpenCodeGenerator()
    
    # Extract module name from description if possible
    module_name = extract_module_name_from_text(description)
    
    return gen.generate_verilog(
        description=description,
        module_name=module_name,
        style="behavioral"
    )


def extract_module_name_from_text(text: str) -> str:
    """Extract reasonable module name from description."""
    # Try to find words that could be module names
    words = re.findall(r'\b[a-z]+(?:_[a-z]+)*\b', text.lower())
    
    candidates = [w for w in words if len(w) > 2 and w not in 
                  {'the', 'that', 'this', 'with', 'from', 'into', 'with'}]
    
    if candidates:
        return candidates[0]
    
    return "generated_design"


if __name__ == "__main__":
    # Test the integration
    gen = OpenCodeGenerator()
    print(f"OpenCode Available: {gen.opencode_available}")
    
    if gen.opencode_available:
        # Test generation
        success, code, msg = gen.generate_verilog(
            "An 8-bit counter with clock and reset",
            "test_counter"
        )
        print(f"Success: {success}")
        print(f"Message: {msg}")
        if success:
            print(f"Generated code:\n{code}")
