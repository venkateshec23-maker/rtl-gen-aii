"""
Prompt Builder
Builds LLM prompts for RTL-Gen AI.
"""

from typing import Dict

class PromptBuilder:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def build_prompt(self, parsed: Dict) -> str:
        desc = parsed.get('original_description', '')
        return f"Write a complete, synthesizable Verilog module based on this description: {desc}\nAlso provide a comprehensive testbench."
