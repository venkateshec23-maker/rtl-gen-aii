"""
Input Sanitizer

Sanitizes and validates all user inputs for security.

Usage:
    from python.input_sanitizer import InputSanitizer
    
    sanitizer = InputSanitizer()
    clean_input = sanitizer.sanitize_description(user_input)
"""

import re
from typing import Optional


class InputSanitizer:
    """Input sanitization and validation."""
    
    def __init__(self):
        """Initialize input sanitizer."""
        self.max_description_length = 5000
        self.max_module_name_length = 100
        self.max_file_path_length = 255
        
        self.allowed_module_name_chars = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        self.allowed_file_chars = re.compile(r'^[a-zA-Z0-9_\-./\\]+$')
        
        self.dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'eval\(',
            r'exec\(',
            r'__import__',
            r'\$\{',
            r'\.\./',
            r'%00',
        ]
    
    def sanitize_description(self, description: str) -> str:
        """Sanitize design description."""
        if not description:
            raise ValueError("Description cannot be empty")
        
        if not isinstance(description, str):
            raise ValueError("Description must be a string")
        
        if len(description) > self.max_description_length:
            raise ValueError(f"Description too long (max {self.max_description_length} characters)")
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                raise ValueError(f"Description contains potentially dangerous content")
        
        description = description.replace('\x00', '')
        description = ' '.join(description.split())
        description = re.sub(r'<[^>]+>', '', description)
        
        return description
    
    def sanitize_module_name(self, module_name: str) -> str:
        """Sanitize module name."""
        if not module_name:
            raise ValueError("Module name cannot be empty")
        
        if len(module_name) > self.max_module_name_length:
            raise ValueError(f"Module name too long")
        
        if not self.allowed_module_name_chars.match(module_name):
            raise ValueError("Module name must be valid Verilog identifier")
        
        verilog_keywords = {
            'module', 'endmodule', 'input', 'output', 'wire', 'reg',
            'always', 'assign', 'begin', 'end', 'if', 'else', 'case',
        }
        
        if module_name.lower() in verilog_keywords:
            raise ValueError(f"Module name cannot be Verilog keyword")
        
        return module_name
    
    def sanitize_file_path(self, file_path: str, base_dir: Optional[str] = None) -> str:
        """Sanitize file path and prevent path traversal."""
        if not file_path:
            raise ValueError("File path cannot be empty")
        
        if len(file_path) > self.max_file_path_length:
            raise ValueError(f"File path too long")
        
        if '..' in file_path:
            raise ValueError("Path traversal not allowed")
        
        if file_path.startswith('/') or ':' in file_path:
            if not base_dir:
                raise ValueError("Absolute paths not allowed")
        
        if not self.allowed_file_chars.match(file_path):
            raise ValueError("File path contains invalid characters")
        
        return file_path
    
    def sanitize_integer(self, value: any, min_val: int = 0, max_val: int = 1000000) -> int:
        """Sanitize integer input."""
        try:
            int_val = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid integer: {value}")
        
        if int_val < min_val or int_val > max_val:
            raise ValueError(f"Integer out of range")
        
        return int_val


if __name__ == "__main__":
    print("Input Sanitizer Self-Test\n")
    
    sanitizer = InputSanitizer()
    
    # Test normal input
    try:
        clean = sanitizer.sanitize_description("Create an 8-bit adder")
        print(f"✓ Normal: '{clean}'")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Test dangerous input
    try:
        sanitizer.sanitize_description("<script>alert('xss')</script>")
        print("✗ Should have rejected dangerous input")
    except ValueError:
        print("✓ Dangerous input rejected")
    
    print("\n✓ Self-test complete")
