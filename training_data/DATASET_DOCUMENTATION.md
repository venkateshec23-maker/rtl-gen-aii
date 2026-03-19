# RTL-Gen AI Training Dataset Documentation

Version: 1.0  
Created: February 2026  
Total Designs: 200+

---

## Table of Contents

1. [Overview](#overview)
2. [Dataset Structure](#dataset-structure)
3. [Data Format](#data-format)
4. [Quality Assurance](#quality-assurance)
5. [Usage Examples](#usage-examples)
6. [Statistics](#statistics)
7. [Licensing](#licensing)

---

## Overview

This dataset contains high-quality, verified Verilog/SystemVerilog hardware designs
for training AI models on RTL code generation. Each design includes:

- Natural language description
- Synthesizable RTL code
- Comprehensive testbench
- Verification results
- Quality metrics
- Rich metadata

### Design Categories

1. **Combinational Logic** - Adders, multiplexers, comparators, encoders
2. **Sequential Logic** - Counters, registers, shift registers
3. **Finite State Machines** - Controllers, protocol handlers
4. **Memory Elements** - FIFOs, RAMs, buffers
5. **Arithmetic Units** - ALUs, multipliers, dividers
6. **Control Logic** - Controllers, arbiters, decoders

---

## Dataset Structure

```
training_data/
├── designs/                    # Design files organized by category
│   ├── combinational/
│   ├── sequential/
│   ├── fsm/
│   ├── memory/
│   ├── arithmetic/
│   └── control/
├── metadata/                   # Dataset metadata and indices
│   ├── dataset_index.json     # Complete dataset index
│   ├── dataset_summary.json   # Summary statistics
│   └── DATASET_README.md      # Quick reference
├── processed/                  # Training-ready exports
│   ├── training_data.jsonl    # JSONL format
│   ├── training_data.csv      # CSV format
│   ├── train_split.jsonl      # Training split (80%)
│   ├── val_split.jsonl        # Validation split (10%)
│   └── test_split.jsonl       # Test split (10%)
├── validation/                 # Validation results
│   └── validation_report.json
├── reports/                    # Quality reports
│   ├── quality_report.md
│   ├── statistics.json
│   └── dataset_visualizations.png
└── quarantine/                 # Low-quality designs (excluded)
```

---

## Data Format

### JSON Schema

Each design file follows this schema:

```json
{
  "metadata": {
    "id": "unique_identifier",
    "category": "combinational|sequential|fsm|memory|arithmetic|control",
    "name": "module_name",
    "bit_width": 8,
    "complexity": "simple|medium|complex",
    "verified": true,
    "quality_score": 8.5,
    "created_date": "2026-02-25T10:30:00",
    "tags": ["adder", "arithmetic", "carry"],
    "augmented": false,
    "augmentation_type": null,
    "parent_id": null
  },
  "description": {
    "natural_language": "8-bit adder with carry input and output",
    "detailed_spec": "Detailed specification if available",
    "requirements": ["Two 8-bit inputs", "Carry in/out", "Overflow detection"]
  },
  "code": {
    "rtl": "module adder_8bit(...); ... endmodule",
    "testbench": "module adder_8bit_tb; ... endmodule",
    "language": "verilog",
    "style": "ieee_standard"
  },
  "verification": {
    "compilation": {
      "passed": true,
      "errors": []
    },
    "simulation": {
      "passed": true,
      "tests_total": 256,
      "tests_passed": 256,
      "coverage": 100.0
    },
    "synthesis": {
      "synthesizable": true,
      "gate_count": 124,
      "critical_path_ns": 2.5
    }
  },
  "enhanced_metadata": {
    "keywords": ["add", "carry", "arithmetic"],
    "complexity_metrics": {
      "total_lines": 45,
      "code_lines": 38,
      "comment_lines": 7,
      "cyclomatic_complexity": 2
    },
    "ports": {
      "inputs": [{"name": "a", "width": "7:0"}, {"name": "b", "width": "7:0"}],
      "outputs": [{"name": "sum", "width": "7:0"}, {"name": "cout", "width": "0:0"}]
    },
    "design_pattern": "combinational",
    "searchable_text": "8-bit adder arithmetic carry ..."
  },
  "learning_notes": {
    "common_errors": [],
    "best_practices": ["Use non-blocking for sequential", "Comment complex logic"],
    "optimization_tips": []
  }
}
```

---

## Quality Assurance

### Validation Process

Every design in the dataset has been:

1. **Structure Validated**
   - Valid JSON format
   - Complete required fields
   - Proper schema compliance

2. **Syntax Validated**
   - Compiled with Icarus Verilog
   - Zero syntax errors
   - IEEE standard compliance

3. **Functionally Verified**
   - Simulated with testbench
   - All tests passed
   - Waveforms generated

4. **Quality Checked**
   - Code style compliance
   - Comment density > 10%
   - Proper naming conventions
   - Best practices followed

5. **Metadata Enhanced**
   - Keywords extracted
   - Complexity analyzed
   - Ports documented
   - Patterns identified

### Quality Metrics

- **Verification Rate:** 95%+
- **Average Quality Score:** 8.0+/10
- **Syntax Correctness:** 100%
- **Test Coverage:** 90%+

---

## Usage Examples

### Python API

```python
from python.dataset_manager import DatasetManager

# Initialize manager
manager = DatasetManager()

# Get statistics
stats = manager.get_statistics()
print(f"Total designs: {stats['total_designs']}")

# Export for training
training_file = manager.export_for_training(format='jsonl')
print(f"Training data exported: {training_file}")
```

### Search Dataset

```python
import json
from pathlib import Path

# Load index
with open('training_data/metadata/dataset_index.json') as f:
    index = json.load(f)

# Search by category
combinational = [d for d in index['designs'] if d['category'] == 'combinational']
print(f"Combinational designs: {len(combinational)}")

# Search by complexity
simple = [d for d in index['designs'] if d['complexity'] == 'simple']
print(f"Simple designs: {len(simple)}")

# Search by keyword
adders = [d for d in index['designs'] if 'adder' in d.get('keywords', [])]
print(f"Adders: {len(adders)}")
```

### Load Specific Design

```python
import json

# Load design by file path
design_file = 'training_data/designs/combinational/adder_8bit_abc123.json'
with open(design_file) as f:
    design = json.load(f)

print(f"Name: {design['metadata']['name']}")
print(f"Description: {design['description']['natural_language']}")
print(f"\nRTL Code:\n{design['code']['rtl']}")
```

---

## Statistics

### Current Dataset (as of February 2026)

- **Total Designs:** 200+
- **Verified:** 95%+
- **Categories:** 6
- **Bit Widths:** 4, 8, 16, 32
- **Complexity Levels:** Simple (40%), Medium (45%), Complex (15%)

### Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| Combinational | 45 | 22% |
| Sequential | 50 | 25% |
| FSM | 30 | 15% |
| Memory | 25 | 12% |
| Arithmetic | 35 | 17% |
| Control | 15 | 9% |

---

## Licensing

### Dataset License

This training dataset is provided for educational and research purposes.

**Usage Rights:**
- ✓ Train AI/ML models
- ✓ Research and development
- ✓ Academic publications
- ✗ Direct commercial use of designs without modification
- ✗ Redistribution without attribution

**Attribution:**
```
RTL-Gen AI Training Dataset
Generated by RTL-Gen AI System
https://github.com/yourusername/rtl-gen-ai
```

### Design Licenses

Individual designs are auto-generated and provided "as-is" without warranty.
Verify synthesizability and correctness before production use.

---

## Contributing

To contribute additional designs:

1. Use the `DatasetManager` to add designs
2. Ensure designs pass validation
3. Submit pull request with new designs
4. Include verification results

---

## Contact

For questions, issues, or contributions:
- GitHub: [rtl-gen-ai](https://github.com/yourusername/rtl-gen-ai)
- Email: your.email@example.com

---

*Last Updated: February 2026*
