"""
Fine-Tuning Dataset Formatter

Prepares training data in format required by various LLM providers
for fine-tuning: Claude, GPT-4, Llama, etc.

Usage:
    from python.finetuning_formatter import FineTuningFormatter
    
    formatter = FineTuningFormatter()
    formatter.prepare_all_formats()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import random


class FineTuningFormatter:
    """Format training data for fine-tuning."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize formatter."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.finetuning_dir = self.base_dir / 'finetuning'
        self.finetuning_dir.mkdir(exist_ok=True)
        
        # Load system prompt from template
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from template."""
        template_file = Path('templates/system_prompt.txt')
        
        if template_file.exists():
            return template_file.read_text()
        
        # Default system prompt
        return """You are an expert Verilog hardware design engineer specializing in RTL code generation.

Your expertise includes:
- Writing clean, synthesizable Verilog/SystemVerilog code
- Following IEEE 1364-2005 and IEEE 1800-2017 standards
- Generating comprehensive testbenches
- Implementing combinational and sequential logic
- Designing finite state machines
- Creating memory elements and arithmetic units

When generating code:
1. Always include proper module declarations with all ports
2. Use appropriate coding styles (blocking vs non-blocking assignments)
3. Add clear, concise comments explaining functionality
4. Follow consistent naming conventions (lowercase with underscores)
5. Generate complete, working testbenches
6. Ensure all signals are properly declared
7. Consider synthesis implications

Generate professional, production-quality RTL code."""
    
    def load_all_designs(self) -> List[Dict]:
        """
        Load all verified designs.
        
        Returns:
            list: All design data
        """
        designs = []
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        for category in categories:
            category_dir = self.designs_dir / category
            if not category_dir.exists():
                continue
            
            for design_file in category_dir.glob('*.json'):
                with open(design_file) as f:
                    design = json.load(f)
                
                # Only include verified, high-quality designs
                if design['metadata'].get('verified', False):
                    if design['metadata'].get('quality_score', 0) >= 7.0:
                        designs.append(design)
        
        return designs
    
    def format_for_claude(self, designs: List[Dict]) -> str:
        """
        Format for Claude fine-tuning (Anthropic format).
        
        Args:
            designs: List of design data
            
        Returns:
            str: Path to output file
        """
        output_file = self.finetuning_dir / f'claude_finetuning_{datetime.now().strftime("%Y%m%d")}.jsonl'
        
        print(f"\nFormatting for Claude fine-tuning...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for design in designs:
                # Claude format: system message + user message + assistant response
                example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": self.system_prompt
                        },
                        {
                            "role": "user",
                            "content": design['description']['natural_language']
                        },
                        {
                            "role": "assistant",
                            "content": self._format_code_response(design)
                        }
                    ]
                }
                
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"  ✓ Created: {output_file}")
        print(f"  ✓ Examples: {len(designs)}")
        
        return str(output_file)
    
    def format_for_gpt4(self, designs: List[Dict]) -> str:
        """
        Format for GPT-4 fine-tuning (OpenAI format).
        
        Args:
            designs: List of design data
            
        Returns:
            str: Path to output file
        """
        output_file = self.finetuning_dir / f'gpt4_finetuning_{datetime.now().strftime("%Y%m%d")}.jsonl'
        
        print(f"\nFormatting for GPT-4 fine-tuning...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for design in designs:
                # GPT-4 format: similar to Claude
                example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": self.system_prompt
                        },
                        {
                            "role": "user",
                            "content": design['description']['natural_language']
                        },
                        {
                            "role": "assistant",
                            "content": self._format_code_response(design)
                        }
                    ]
                }
                
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"  ✓ Created: {output_file}")
        print(f"  ✓ Examples: {len(designs)}")
        
        return str(output_file)
    
    def format_for_llama(self, designs: List[Dict]) -> str:
        """
        Format for Llama fine-tuning (instruction format).
        
        Args:
            designs: List of design data
            
        Returns:
            str: Path to output file
        """
        output_file = self.finetuning_dir / f'llama_finetuning_{datetime.now().strftime("%Y%m%d")}.jsonl'
        
        print(f"\nFormatting for Llama fine-tuning...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for design in designs:
                # Llama instruction format
                instruction = f"{self.system_prompt}\n\n### Instruction:\n{design['description']['natural_language']}"
                response = self._format_code_response(design)
                
                example = {
                    "instruction": instruction,
                    "input": "",
                    "output": response
                }
                
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"  ✓ Created: {output_file}")
        print(f"  ✓ Examples: {len(designs)}")
        
        return str(output_file)
    
    def _format_code_response(self, design: Dict) -> str:
        """
        Format code response for training.
        
        Args:
            design: Design data
            
        Returns:
            str: Formatted response
        """
        response = f"""I'll create a {design['metadata']['category']} design for {design['metadata']['name']}.

**RTL Code:**

```verilog
{design['code']['rtl']}
```

**Testbench:**

```verilog
{design['code']['testbench']}
```

**Design Details:**
- Category: {design['metadata']['category']}
- Bit Width: {design['metadata']['bit_width']}
- Complexity: {design['metadata']['complexity']}

The design has been verified through simulation and is synthesizable.
"""
        return response
    
    def create_train_val_test_split(
        self,
        designs: List[Dict],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        random_seed: int = 42
    ) -> Dict[str, List[Dict]]:
        """
        Create train/validation/test splits.
        
        Args:
            designs: All designs
            train_ratio: Training ratio
            val_ratio: Validation ratio
            test_ratio: Test ratio
            random_seed: Random seed for reproducibility
            
        Returns:
            dict: Split datasets
        """
        # Shuffle with seed
        random.seed(random_seed)
        shuffled = designs.copy()
        random.shuffle(shuffled)
        
        total = len(shuffled)
        train_end = int(total * train_ratio)
        val_end = train_end + int(total * val_ratio)
        
        splits = {
            'train': shuffled[:train_end],
            'val': shuffled[train_end:val_end],
            'test': shuffled[val_end:],
        }
        
        return splits
    
    def prepare_all_formats(self):
        """Prepare fine-tuning data in all formats."""
        print("=" * 70)
        print("PREPARING FINE-TUNING DATASETS")
        print("=" * 70)
        
        # Load all designs
        print("\nLoading designs...")
        designs = self.load_all_designs()
        print(f"  ✓ Loaded {len(designs)} verified, high-quality designs")
        
        # Create splits
        print("\nCreating train/val/test splits...")
        splits = self.create_train_val_test_split(designs)
        print(f"  ✓ Train: {len(splits['train'])} examples")
        print(f"  ✓ Val: {len(splits['val'])} examples")
        print(f"  ✓ Test: {len(splits['test'])} examples")
        
        # Format for each provider
        outputs = {}
        
        # Claude format
        outputs['claude'] = self.format_for_claude(splits['train'])
        
        # GPT-4 format
        outputs['gpt4'] = self.format_for_gpt4(splits['train'])
        
        # Llama format
        outputs['llama'] = self.format_for_llama(splits['train'])
        
        # Save validation and test sets (Claude format)
        print("\nSaving validation and test sets...")
        
        val_file = self.finetuning_dir / 'validation_set.jsonl'
        with open(val_file, 'w', encoding='utf-8') as f:
            for design in splits['val']:
                example = {
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": design['description']['natural_language']},
                        {"role": "assistant", "content": self._format_code_response(design)}
                    ]
                }
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        print(f"  ✓ Validation set: {val_file}")
        
        test_file = self.finetuning_dir / 'test_set.jsonl'
        with open(test_file, 'w', encoding='utf-8') as f:
            for design in splits['test']:
                example = {
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": design['description']['natural_language']},
                        {"role": "assistant", "content": self._format_code_response(design)}
                    ]
                }
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        print(f"  ✓ Test set: {test_file}")
        
        # Create summary
        summary = {
            'created_at': datetime.now().isoformat(),
            'total_designs': len(designs),
            'train_size': len(splits['train']),
            'val_size': len(splits['val']),
            'test_size': len(splits['test']),
            'formats': list(outputs.keys()),
            'files': {
                **outputs,
                'validation': str(val_file),
                'test': str(test_file),
            }
        }
        
        summary_file = self.finetuning_dir / 'preparation_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✓ Summary saved: {summary_file}")
        
        print("\n" + "=" * 70)
        print("FINE-TUNING PREPARATION COMPLETE")
        print("=" * 70)
        print(f"\nFiles created:")
        for provider, filepath in outputs.items():
            print(f"  - {provider}: {filepath}")
        print(f"  - validation: {val_file}")
        print(f"  - test: {test_file}")
        print("=" * 70)
        
        return summary


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Fine-Tuning Formatter Self-Test\n")
    
    formatter = FineTuningFormatter()
    summary = formatter.prepare_all_formats()
    
    print("\n✓ Self-test complete")
    print(f"\nCreated {len(summary['files'])} files")
    print(f"Total examples: {summary['total_designs']}")
