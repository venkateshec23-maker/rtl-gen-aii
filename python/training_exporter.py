"""
Training Data Exporter

Exports dataset in various formats for model training.

Usage:
    from python.training_exporter import TrainingExporter
    
    exporter = TrainingExporter()
    exporter.export_all_formats()
"""

import json
import csv
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class TrainingExporter:
    """Export dataset for model training."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize exporter."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.processed_dir = self.base_dir / 'processed'
        self.processed_dir.mkdir(exist_ok=True)
    
    def export_jsonl(self, output_file: str = None) -> Path:
        """
        Export in JSONL format (for Claude/GPT fine-tuning).
        
        Args:
            output_file: Output filename
            
        Returns:
            Path: Path to exported file
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'training_data_{timestamp}.jsonl'
        
        output_path = self.processed_dir / output_file
        
        print(f"\nExporting JSONL format...")
        
        count = 0
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        with open(output_path, 'w', encoding='utf-8') as out:
            for category in categories:
                category_dir = self.designs_dir / category
                if not category_dir.exists():
                    continue
                
                for design_file in category_dir.glob('*.json'):
                    with open(design_file, encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Skip unverified designs
                    if not data['metadata'].get('verified', False):
                        continue
                    
                    # Create training example
                    training_example = {
                        'messages': [
                            {
                                'role': 'system',
                                'content': 'You are an expert Verilog hardware design engineer. Generate professional, synthesizable RTL code from natural language descriptions.'
                            },
                            {
                                'role': 'user',
                                'content': data['description']['natural_language']
                            },
                            {
                                'role': 'assistant',
                                'content': f"```verilog\n{data['code']['rtl']}\n```\n\n```verilog\n{data['code']['testbench']}\n```"
                            }
                        ]
                    }
                    
                    out.write(json.dumps(training_example, ensure_ascii=False) + '\n')
                    count += 1
        
        print(f"  ✓ Exported {count} examples")
        print(f"  ✓ File: {output_path}")
        
        return output_path
    
    def export_csv(self, output_file: str = None) -> Path:
        """
        Export in CSV format.
        
        Args:
            output_file: Output filename
            
        Returns:
            Path: Path to exported file
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'training_data_{timestamp}.csv'
        
        output_path = self.processed_dir / output_file
        
        print(f"\nExporting CSV format...")
        
        count = 0
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as out:
            writer = csv.writer(out)
            
            # Write header
            writer.writerow([
                'id', 'category', 'name', 'bit_width', 'complexity',
                'description', 'rtl_code', 'testbench', 'verified', 'quality_score'
            ])
            
            for category in categories:
                category_dir = self.designs_dir / category
                if not category_dir.exists():
                    continue
                
                for design_file in category_dir.glob('*.json'):
                    with open(design_file, encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Skip unverified
                    if not data['metadata'].get('verified', False):
                        continue
                    
                    writer.writerow([
                        data['metadata']['id'],
                        data['metadata']['category'],
                        data['metadata']['name'],
                        data['metadata']['bit_width'],
                        data['metadata']['complexity'],
                        data['description']['natural_language'],
                        data['code']['rtl'],
                        data['code']['testbench'],
                        data['metadata']['verified'],
                        data['metadata']['quality_score'],
                    ])
                    count += 1
        
        print(f"  ✓ Exported {count} examples")
        print(f"  ✓ File: {output_path}")
        
        return output_path
    
    def export_huggingface(self, output_file: str = None) -> Path:
        """
        Export in Hugging Face dataset format.
        
        Args:
            output_file: Output filename
            
        Returns:
            Path: Path to exported file
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'training_data_hf_{timestamp}.jsonl'
        
        output_path = self.processed_dir / output_file
        
        print(f"\nExporting Hugging Face format...")
        
        count = 0
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        with open(output_path, 'w', encoding='utf-8') as out:
            for category in categories:
                category_dir = self.designs_dir / category
                if not category_dir.exists():
                    continue
                
                for design_file in category_dir.glob('*.json'):
                    with open(design_file, encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if not data['metadata'].get('verified', False):
                        continue
                    
                    # Hugging Face format
                    hf_example = {
                        'instruction': data['description']['natural_language'],
                        'input': '',
                        'output': data['code']['rtl'],
                        'category': data['metadata']['category'],
                        'complexity': data['metadata']['complexity'],
                        'verified': data['metadata']['verified'],
                    }
                    
                    out.write(json.dumps(hf_example, ensure_ascii=False) + '\n')
                    count += 1
        
        print(f"  ✓ Exported {count} examples")
        print(f"  ✓ File: {output_path}")
        
        return output_path
    
    def create_train_val_test_split(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1
    ) -> Dict[str, Path]:
        """
        Create train/validation/test splits.
        
        Args:
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            test_ratio: Test set ratio
            
        Returns:
            dict: Paths to split files
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.01, "Ratios must sum to 1.0"
        
        print(f"\nCreating train/val/test split ({train_ratio}/{val_ratio}/{test_ratio})...")
        
        # Collect all designs
        all_designs = []
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        for category in categories:
            category_dir = self.designs_dir / category
            if not category_dir.exists():
                continue
            
            for design_file in category_dir.glob('*.json'):
                with open(design_file, encoding='utf-8') as f:
                    data = json.load(f)
                
                if data['metadata'].get('verified', False):
                    all_designs.append(data)
        
        # Shuffle deterministically
        import random
        random.seed(42)
        random.shuffle(all_designs)
        
        # Calculate split points
        total = len(all_designs)
        train_end = int(total * train_ratio)
        val_end = train_end + int(total * val_ratio)
        
        train_data = all_designs[:train_end]
        val_data = all_designs[train_end:val_end]
        test_data = all_designs[val_end:]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save splits
        splits = {}
        
        for split_name, split_data in [('train', train_data), ('val', val_data), ('test', test_data)]:
            filename = f'{split_name}_{timestamp}.jsonl'
            filepath = self.processed_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                for design in split_data:
                    training_example = {
                        'messages': [
                            {
                                'role': 'user',
                                'content': design['description']['natural_language']
                            },
                            {
                                'role': 'assistant',
                                'content': f"```verilog\n{design['code']['rtl']}\n```\n\n```verilog\n{design['code']['testbench']}\n```"
                            }
                        ]
                    }
                    f.write(json.dumps(training_example, ensure_ascii=False) + '\n')
            
            splits[split_name] = filepath
            print(f"  ✓ {split_name}: {len(split_data)} examples -> {filepath}")
        
        return splits
    
    def export_all_formats(self):
        """Export in all supported formats."""
        print("=" * 70)
        print("EXPORTING TRAINING DATA")
        print("=" * 70)
        
        # Export formats
        jsonl_file = self.export_jsonl()
        csv_file = self.export_csv()
        hf_file = self.export_huggingface()
        
        # Create splits
        splits = self.create_train_val_test_split()
        
        print("\n" + "=" * 70)
        print("EXPORT COMPLETE")
        print("=" * 70)
        print("\nExported files:")
        print(f"  - JSONL: {jsonl_file}")
        print(f"  - CSV: {csv_file}")
        print(f"  - Hugging Face: {hf_file}")
        print(f"  - Train split: {splits['train']}")
        print(f"  - Val split: {splits['val']}")
        print(f"  - Test split: {splits['test']}")
        print("=" * 70)
        
        return {
            'jsonl': jsonl_file,
            'csv': csv_file,
            'huggingface': hf_file,
            'splits': splits,
        }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Training Exporter Self-Test\n")
    
    exporter = TrainingExporter()
    files = exporter.export_all_formats()
    
    print("\n✓ Export complete")
