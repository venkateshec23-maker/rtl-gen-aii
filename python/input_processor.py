"""
Input Processor
Parses natural language descriptions for RTL-Gen AI.
"""

from typing import Dict

class InputProcessor:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def parse_description(self, description: str) -> Dict:
        if not description or not description.strip():
            return {'valid': False, 'errors': ["Empty description"]}
            
        return {
            'valid': True,
            'component_type': 'custom_module',
            'bit_width': 'unknown',
            'original_description': description,
            'errors': []
        }
