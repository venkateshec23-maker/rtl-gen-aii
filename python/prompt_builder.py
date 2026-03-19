"""
Prompt Builder
Builds optimized LLM prompts for RTL-Gen AI using formal templates.
"""
from typing import Dict
from pathlib import Path

class PromptBuilder:
    """Build optimized prompts for LLM code generation."""
    
    def __init__(self, debug: bool = False):
        """Initialize prompt builder."""
        self.debug = debug
        self.templates_dir = Path(__file__).parent.parent / 'templates'
        
        # Load templates
        self.system_prompt = self._load_template('system_prompt.txt')
        self.combinational_template = self._load_template('combinational_prompt.txt')
        self.sequential_template = self._load_template('sequential_prompt.txt')
        self.fsm_template = self._load_template('fsm_prompt.txt')
        self.testbench_template = self._load_template('testbench_prompt.txt')
    
    def _load_template(self, filename: str) -> str:
        """Load template from file."""
        template_path = self.templates_dir / filename
        
        if template_path.exists():
            return template_path.read_text()
        else:
            # Fallback to inline template
            return self._get_default_template(filename)
    
    def _get_default_template(self, filename: str) -> str:
        """Get default template if file not found."""
        defaults = {
            'system_prompt.txt': "You are an expert Verilog engineer...",
            'combinational_prompt.txt': "Generate combinational logic...",
            'sequential_prompt.txt': "Generate sequential logic...",
            'fsm_prompt.txt': "Generate FSM...",
            'testbench_prompt.txt': "Generate testbench...",
        }
        return defaults.get(filename, "")
    
    def build_prompt(self, parsed_input: Dict) -> str:
        """Build complete prompt from parsed input."""
        component_type = parsed_input.get('component_type', 'combinational')
        
        # Select appropriate template
        if 'fsm' in component_type.lower() or 'state machine' in component_type.lower():
            user_template = self.fsm_template
        elif component_type in ['sequential', 'counter', 'register', 'shift register']:
            user_template = self.sequential_template
        else:
            user_template = self.combinational_template
        
        # Fill in template
        user_prompt = user_template.format(
            description=parsed_input.get('original_description', ''),
            module_name=parsed_input.get('module_name', 'design_module'),
            bit_width=parsed_input.get('module_parameters', {}).get('width', 8), # Adjusted generic mapping
            inputs=', '.join(parsed_input.get('inputs', ['in1', 'in2'])) if isinstance(parsed_input.get('inputs'), list) else parsed_input.get('inputs', 'a, b'),
            outputs=', '.join(parsed_input.get('outputs', ['out1'])) if isinstance(parsed_input.get('outputs'), list) else parsed_input.get('outputs', 'out'),
            states='IDLE, ACTIVE, DONE' # Placeholder since existing InputProcessor might not extract states
        )
        
        # Combine system and user prompts
        full_prompt = f"{self.system_prompt}\n\n{user_prompt}"
        
        return full_prompt
