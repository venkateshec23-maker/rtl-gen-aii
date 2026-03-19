"""
Input Validator for RTL-Gen AI
Sanitizes and validates user input to prevent injection attacks.

Usage:
    validator = InputValidator()
    cleaned = validator.sanitize(user_input)
    if validator.is_valid(cleaned):
        # Process input
"""

import re
from typing import Dict, List, Tuple


class InputValidator:
    """Validate and sanitize user input."""
    
    # Dangerous patterns that should be rejected
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',                 # JavaScript protocol
        r'on\w+\s*=',                  # Event handlers
        r'eval\s*\(',                  # eval() calls
        r'exec\s*\(',                  # exec() calls
        r'__import__',                 # Import statements
        r'subprocess',                 # Subprocess calls
        r'\${.*?}',                    # Template injection
        r'`.*?`',                      # Command execution
    ]
    
    # Allowed characters (alphanumeric + common punctuation)
    ALLOWED_CHARS = r'^[a-zA-Z0-9\s\-_.,;:()\[\]{}\/\'\"+*=<>!&|~@#%]+$'
    
    def __init__(self, max_length: int = 5000):
        """
        Initialize validator.
        
        Args:
            max_length: Maximum allowed input length
        """
        self.max_length = max_length
    
    def sanitize(self, text: str) -> str:
        """
        Sanitize input text.
        
        Args:
            text: Raw input text
            
        Returns:
            str: Sanitized text
        """
        if not text:
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Trim to max length
        if len(text) > self.max_length:
            text = text[:self.max_length]
        
        # Remove dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def is_valid(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check if input is valid.
        
        Args:
            text: Input text to validate
            
        Returns:
            tuple: (is_valid, list of errors)
        """
        errors = []
        
        # Check length
        if not text:
            errors.append("Input cannot be empty")
            return False, errors
        
        if len(text) < 10:
            errors.append("Input too short (minimum 10 characters)")
        
        if len(text) > self.max_length:
            errors.append(f"Input too long (maximum {self.max_length} characters)")
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append("Input contains potentially dangerous content")
                break
        
        # Check allowed characters
        if not re.match(self.ALLOWED_CHARS, text):
            errors.append("Input contains invalid characters")
        
        # Check for minimum meaningful content
        if len(text.split()) < 2:
            errors.append("Input should contain at least 2 words")
        
        return len(errors) == 0, errors
    
    def validate_and_sanitize(self, text: str) -> Dict:
        """
        Combined validation and sanitization.
        
        Args:
            text: Raw input text
            
        Returns:
            dict: Result with sanitized text and validation status
        """
        # Sanitize first
        clean_text = self.sanitize(text)
        
        # Then validate
        is_valid, errors = self.is_valid(clean_text)
        
        return {
            'original': text,
            'sanitized': clean_text,
            'valid': is_valid,
            'errors': errors,
        }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Input Validator Self-Test\n")
    
    validator = InputValidator()
    
    test_cases = [
        ("4-bit adder", True),
        ("8-bit counter with reset", True),
        ("<script>alert('xss')</script>", False),
        ("eval(malicious_code)", False),
        ("", False),
        ("x", False),
        ("a" * 6000, False),  # Too long
        ("Design a 16-bit ALU with ADD, SUB operations", True),
    ]
    
    print("Testing validation:")
    for text, should_pass in test_cases:
        result = validator.validate_and_sanitize(text)
        
        status = "✓" if result['valid'] == should_pass else "✗"
        preview = text[:50] + "..." if len(text) > 50 else text
        
        print(f"{status} '{preview}'")
        if result['errors']:
            print(f"   Errors: {', '.join(result['errors'])}")
    
    print("\n✓ Self-test complete")
