"""
Advanced Prompt Builder with Context Awareness

Builds sophisticated prompts using RAG (Retrieval-Augmented Generation)
and context management for improved code generation quality.

Usage:
    from python.advanced_prompt_builder import AdvancedPromptBuilder
    
    builder = AdvancedPromptBuilder()
    prompt = builder.build_context_aware_prompt(description, context)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from collections import defaultdict


class AdvancedPromptBuilder:
    """Advanced prompt builder with context awareness and RAG."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize advanced prompt builder."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.templates_dir = Path('templates')
        
        # Load design index for RAG
        self.design_index = self._load_design_index()
        
        # Context memory
        self.context_memory = defaultdict(list)
        
        # Load templates
        self.templates = self._load_templates()
    
    def _load_design_index(self) -> List[Dict]:
        """Load design index for similarity search."""
        index_file = self.base_dir / 'metadata' / 'dataset_index.json'
        
        if not index_file.exists():
            return []
        
        with open(index_file) as f:
            data = json.load(f)
            return data.get('designs', [])
    
    def _load_templates(self) -> Dict:
        """Load prompt templates."""
        templates = {}
        
        template_files = {
            'system': 'system_prompt.txt',
            'combinational': 'combinational_prompt.txt',
            'sequential': 'sequential_prompt.txt',
            'fsm': 'fsm_prompt.txt',
            'testbench': 'testbench_prompt.txt',
        }
        
        for name, filename in template_files.items():
            filepath = self.templates_dir / filename
            if filepath.exists():
                templates[name] = filepath.read_text()
            else:
                templates[name] = ""
        
        return templates
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Input text
            
        Returns:
            list: Keywords
        """
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter stopwords and short words
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        
        return keywords
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple similarity score between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            float: Similarity score (0-1)
        """
        keywords1 = set(self.extract_keywords(text1))
        keywords2 = set(self.extract_keywords(text2))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # Jaccard similarity
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def retrieve_similar_designs(
        self,
        description: str,
        top_k: int = 3,
        min_similarity: float = 0.2
    ) -> List[Dict]:
        """
        Retrieve similar designs using RAG approach.
        
        Args:
            description: Design description
            top_k: Number of similar designs to retrieve
            min_similarity: Minimum similarity threshold
            
        Returns:
            list: Similar designs
        """
        if not self.design_index:
            return []
        
        # Calculate similarity for each design
        similarities = []
        for design in self.design_index:
            # Use description and keywords for matching
            design_text = design['name'] + ' ' + ' '.join(design.get('tags', []))
            
            if 'keywords' in design:
                design_text += ' ' + ' '.join(design['keywords'])
            
            similarity = self.calculate_similarity(description, design_text)
            
            if similarity >= min_similarity:
                similarities.append((similarity, design))
        
        # Sort by similarity
        similarities.sort(reverse=True, key=lambda x: x[0])
        
        # Return top-k
        return [design for _, design in similarities[:top_k]]
    
    def load_design_code(self, design_info: Dict) -> Optional[Dict]:
        """
        Load full design code from file.
        
        Args:
            design_info: Design info from index
            
        Returns:
            dict: Full design data or None
        """
        file_path = self.base_dir / design_info['file_path']
        
        if not file_path.exists():
            return None
        
        with open(file_path) as f:
            return json.load(f)
    
    def format_example(self, design_data: Dict) -> str:
        """
        Format design as example for prompt.
        
        Args:
            design_data: Full design data
            
        Returns:
            str: Formatted example
        """
        example = f"""
Example: {design_data['metadata']['name']}
Description: {design_data['description']['natural_language']}

Code:
```verilog
{design_data['code']['rtl']}
```

Key features:
"""
        
        # Extract key features
        if 'enhanced_metadata' in design_data:
            features = design_data['enhanced_metadata'].get('keywords', [])
            for feature in features[:5]:
                example += f"- {feature}\n"
        
        return example
    
    def build_context_from_history(
        self,
        user_id: str = "default",
        max_items: int = 3
    ) -> str:
        """
        Build context from previous interactions.
        
        Args:
            user_id: User identifier
            max_items: Maximum previous items to include
            
        Returns:
            str: Context string
        """
        history = self.context_memory.get(user_id, [])
        
        if not history:
            return ""
        
        context = "\n\nPrevious interactions:\n"
        
        for item in history[-max_items:]:
            context += f"\nUser asked for: {item['description']}"
            if item.get('success'):
                context += " (Successfully generated)"
            else:
                context += f" (Failed: {item.get('error', 'Unknown error')})"
        
        return context
    
    def add_to_context_memory(
        self,
        user_id: str,
        description: str,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Add interaction to context memory.
        
        Args:
            user_id: User identifier
            description: Design description
            success: Whether generation succeeded
            error: Error message if failed
        """
        self.context_memory[user_id].append({
            'description': description,
            'success': success,
            'error': error,
        })
        
        # Keep only last 10 items
        if len(self.context_memory[user_id]) > 10:
            self.context_memory[user_id] = self.context_memory[user_id][-10:]
    
    def build_context_aware_prompt(
        self,
        description: str,
        design_type: Optional[str] = None,
        user_id: str = "default",
        include_examples: bool = True,
        include_history: bool = False
    ) -> str:
        """
        Build comprehensive context-aware prompt.
        
        Args:
            description: Design description
            design_type: Design type (combinational, sequential, etc.)
            user_id: User identifier
            include_examples: Whether to include similar examples
            include_history: Whether to include user history
            
        Returns:
            str: Complete prompt
        """
        # Start with system prompt
        prompt = self.templates.get('system', '')
        
        # Add design-type specific guidance
        if design_type and design_type in self.templates:
            prompt += "\n\n" + self.templates[design_type]
        
        # Add RAG examples if requested
        if include_examples:
            similar_designs = self.retrieve_similar_designs(description, top_k=2)
            
            if similar_designs:
                prompt += "\n\n## Similar Design Examples\n"
                prompt += "\nHere are similar designs for reference:\n"
                
                for design_info in similar_designs:
                    design_data = self.load_design_code(design_info)
                    if design_data:
                        prompt += self.format_example(design_data)
        
        # Add user history if requested
        if include_history:
            history_context = self.build_context_from_history(user_id)
            if history_context:
                prompt += history_context
        
        # Add the actual request
        prompt += f"\n\n## Your Task\n\nGenerate RTL code for: {description}\n"
        
        # Add quality reminders
        prompt += """
## Quality Requirements

1. Generate complete, synthesizable Verilog code
2. Include proper module declaration with all ports
3. Add clear comments explaining the functionality
4. Use appropriate coding style (blocking vs non-blocking)
5. Follow IEEE Verilog standards
6. Ensure all signals are properly declared
7. Generate a comprehensive testbench

## Output Format

Provide:
1. RTL code in ```verilog``` blocks
2. Testbench in separate ```verilog``` block
3. Brief explanation of the design

Begin your response now.
"""
        
        return prompt
    
    def build_refinement_prompt(
        self,
        original_description: str,
        original_code: str,
        error_message: str,
        attempt_number: int
    ) -> str:
        """
        Build prompt for refining failed generation.
        
        Args:
            original_description: Original description
            original_code: Previously generated code
            error_message: Error message
            attempt_number: Attempt number
            
        Returns:
            str: Refinement prompt
        """
        prompt = f"""The previous attempt to generate code had issues. Please fix and regenerate.

## Original Request
{original_description}

## Previous Code (Attempt #{attempt_number})
```verilog
{original_code}
```

## Error Encountered
{error_message}

## Instructions
1. Analyze the error carefully
2. Identify the root cause
3. Generate corrected code that fixes the issue
4. Ensure the fix doesn't introduce new problems

Please provide the corrected code now.
"""
        return prompt
    
    def build_testbench_prompt(
        self,
        rtl_code: str,
        module_name: str,
        design_description: str
    ) -> str:
        """
        Build specialized prompt for testbench generation.
        
        Args:
            rtl_code: RTL code to test
            module_name: Module name
            design_description: Design description
            
        Returns:
            str: Testbench generation prompt
        """
        # Extract ports from RTL
        ports_info = self._extract_ports_info(rtl_code)
        
        prompt = f"""Generate a comprehensive testbench for the following Verilog module.

## Module to Test
```verilog
{rtl_code}
```

## Module Information
- Name: {module_name}
- Description: {design_description}
- Input ports: {', '.join(ports_info['inputs'])}
- Output ports: {', '.join(ports_info['outputs'])}

## Testbench Requirements

1. Include timescale directive: `timescale 1ns/1ps
2. Declare all test signals
3. Instantiate the DUT (Design Under Test)
4. Generate appropriate test stimulus:
   - For combinational logic: Test all input combinations or representative samples
   - For sequential logic: Generate clock and test sequences
   - For FSM: Test all state transitions
5. Check outputs and report results
6. Include $dumpfile and $dumpvars for waveform generation
7. Use $display to show test progress
8. End with $finish

## Output
Provide complete testbench code in ```verilog``` block.
"""
        return prompt
    
    def _extract_ports_info(self, rtl_code: str) -> Dict:
        """Extract port information from RTL code."""
        ports = {
            'inputs': [],
            'outputs': [],
        }
        
        # Find module ports
        module_match = re.search(r'module\s+\w+\s*\((.*?)\);', rtl_code, re.DOTALL)
        if not module_match:
            return ports
        
        port_list = module_match.group(1)
        
        # Extract input ports
        for match in re.finditer(r'input\s+(?:\[.*?\])?\s*(\w+)', port_list):
            ports['inputs'].append(match.group(1))
        
        # Extract output ports
        for match in re.finditer(r'output\s+(?:reg\s+)?(?:\[.*?\])?\s*(\w+)', port_list):
            ports['outputs'].append(match.group(1))
        
        return ports


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Advanced Prompt Builder Self-Test\n")
    
    builder = AdvancedPromptBuilder()
    
    # Test 1: Basic context-aware prompt
    print("Test 1: Context-aware prompt")
    print("=" * 70)
    
    description = "8-bit adder with carry"
    prompt = builder.build_context_aware_prompt(
        description=description,
        design_type='combinational',
        include_examples=True
    )
    
    print(f"Generated prompt length: {len(prompt)} characters")
    print(f"First 500 characters:\n{prompt[:500]}...\n")
    
    # Test 2: Retrieve similar designs
    print("\nTest 2: Similar design retrieval")
    print("=" * 70)
    
    similar = builder.retrieve_similar_designs("4-bit counter", top_k=3)
    print(f"Found {len(similar)} similar designs:")
    for design in similar:
        print(f"  - {design['name']} ({design['category']})")
    
    # Test 3: Refinement prompt
    print("\nTest 3: Refinement prompt")
    print("=" * 70)
    
    refinement_prompt = builder.build_refinement_prompt(
        original_description="8-bit adder",
        original_code="module adder(...); endmodule",
        error_message="Syntax error: missing port declarations",
        attempt_number=2
    )
    
    print(f"Refinement prompt length: {len(refinement_prompt)} characters")
    
    print("\n✓ Self-test complete")
