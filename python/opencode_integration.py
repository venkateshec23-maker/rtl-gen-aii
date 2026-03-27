"""
OpenCode AI Integration Module

Integrates OpenCode AI coding agent with RTL-Gen-AII pipeline.
Enables natural language to Verilog RTL code generation.

OpenCode must be installed:
  npm install -g opencode-ai@latest
  or
  Manual installation from https://opencode.ai/download
"""

import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Optional, Tuple
import tempfile

logger = logging.getLogger(__name__)


class OpenCodeGenerator:
    """Interface to OpenCode AI for Verilog code generation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenCode generator.
        
        Args:
            api_key: Optional API key for remote models (Claude, OpenAI, etc.)
                    If not provided, uses local/free tier configuration
        """
        self.api_key = api_key
        self.opencode_available = self._check_opencode_installed()
        
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
            return False, "", "⚠️ OpenCode not installed. Install with: npm install -g opencode-ai@latest"
        
        try:
            # Create prompt for OpenCode
            prompt = self._create_verilog_prompt(
                description, 
                module_name, 
                width, 
                style
            )
            
            # Write prompt to temp file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.txt', 
                delete=False
            ) as f:
                f.write(prompt)
                temp_file = f.name
            
            # Call OpenCode via CLI
            result = subprocess.run(
                ["opencode", f"Generate Verilog RTL based on: {prompt}"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return False, "", f"OpenCode error: {result.stderr}"
            
            # Extract Verilog from response
            verilog_code = self._extract_verilog(result.stdout)
            
            if not verilog_code:
                return False, "", "Failed to extract Verilog from OpenCode response"
            
            log_msg = f"✅ Generated Verilog module '{module_name}' successfully"
            return True, verilog_code, log_msg
            
        except subprocess.TimeoutExpired:
            return False, "", "OpenCode generation timed out (>60s)"
        except Exception as e:
            return False, "", f"Error during Verilog generation: {str(e)}"
        finally:
            if 'temp_file' in locals():
                Path(temp_file).unlink(missing_ok=True)
    
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
