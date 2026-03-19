# Training Dataset Schema

## Directory Structure

```
training_data/
├── designs/
│   ├── combinational/    # Combinational logic designs
│   ├── sequential/       # Sequential circuits
│   ├── fsm/             # Finite state machines
│   ├── memory/          # Memory elements
│   ├── arithmetic/      # ALUs, adders, multipliers
│   └── control/         # Controllers, decoders
├── validation/          # Validation results
├── metadata/            # Design metadata
└── processed/           # Processed training data
```

## File Naming Convention

```
{category}_{name}_{bitwidth}_{variant}.json
```

Examples:
- `combinational_adder_8bit_ripple.json`
- `sequential_counter_16bit_updown.json`
- `fsm_traffic_light_3state_v1.json`

## JSON Structure

```json
{
  "metadata": {
    "id": "unique_id",
    "category": "combinational|sequential|fsm|memory|arithmetic|control",
    "name": "human_readable_name",
    "bit_width": 8,
    "complexity": "simple|medium|complex",
    "verified": true,
    "quality_score": 9.5,
    "created_date": "2026-02-21",
    "tags": ["adder", "arithmetic", "carry"]
  },
  "description": {
    "natural_language": "8-bit ripple carry adder with overflow detection",
    "detailed_spec": "...",
    "requirements": [
      "Two 8-bit inputs",
      "One 8-bit output",
      "Carry output",
      "Overflow flag"
    ]
  },
  "code": {
    "rtl": "module adder_8bit(...);...endmodule",
    "testbench": "module adder_8bit_tb;...endmodule",
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
  "learning_notes": {
    "common_errors": [],
    "best_practices": [],
    "optimization_tips": []
  }
}
```
