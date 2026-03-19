"""
Input Processor
Parses natural language descriptions for RTL-Gen AI.
"""

from typing import Dict
from python.input_validator import InputValidator

class InputProcessor:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.validator = InputValidator()

    def parse_description(self, description: str) -> Dict:
        # VALIDATE AND SANITIZE FIRST
        validation = self.validator.validate_and_sanitize(description)
        
        if not validation['valid']:
            return {
                'valid': False,
                'errors': validation['errors'],
                'original_description': description,
            }
        
        # Use sanitized version
        description = validation['sanitized']
        
        return {
            'valid': True,
            'component_type': 'custom_module',
            'bit_width': 'unknown',
            'original_description': description,
            'errors': []
        }
