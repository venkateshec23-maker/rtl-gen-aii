# Fine-Tuning Guide for RTL-Gen AI

This guide explains how to fine-tune large language models for improved RTL code generation.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Data Preparation](#data-preparation)
4. [Fine-Tuning with Claude (Anthropic)](#fine-tuning-with-claude)
5. [Fine-Tuning with GPT-4 (OpenAI)](#fine-tuning-with-gpt-4)
6. [Fine-Tuning with Llama](#fine-tuning-with-llama)
7. [Evaluation](#evaluation)
8. [Deployment](#deployment)

---

## Overview

Fine-tuning improves model performance on RTL code generation by training on our curated dataset of 200+ verified designs.

### Benefits of Fine-Tuning

- **Higher Quality:** More consistent code generation
- **Domain Knowledge:** Better understanding of hardware design patterns
- **Fewer Errors:** Reduced syntax and semantic errors
- **Faster Generation:** More efficient prompt processing

### Expected Improvements

| Metric | Base Model | Fine-Tuned Model | Improvement |
|--------|-----------|------------------|-------------|
| Syntax Correctness | 85% | 95%+ | +10% |
| First-Try Success | 70% | 85%+ | +15% |
| Code Quality Score | 7.5/10 | 8.5/10 | +1.0 |
| Generation Speed | 15s | 12s | -20% |

---

## Prerequisites

### 1. Complete Dataset

Ensure you have completed Week 21:
- 200+ verified designs
- Train/val/test splits created
- Fine-tuning datasets formatted

```bash
# Verify dataset
python -c "
from python.dataset_manager import DatasetManager
manager = DatasetManager()
stats = manager.get_statistics()
print(f'Total designs: {stats[\"total_designs\"]}')
"
```

### 2. API Access

You'll need API keys for your chosen provider:

- **Claude:** Anthropic API key (requires enterprise account)
- **GPT-4:** OpenAI API key with fine-tuning access
- **Llama:** Hugging Face account or local setup

### 3. Budget

Fine-tuning costs vary by provider:

- **Claude:** ~$300-500 for full training
- **GPT-4:** ~$200-400 for full training
- **Llama:** Free (requires GPU)

---

## Data Preparation

### 1. Generate Fine-Tuning Datasets

```bash
# Create all formats
python python/finetuning_formatter.py

# Output files will be in training_data/finetuning/
```

### 2. Verify Data Quality

```python
import json

# Check training data
with open('training_data/finetuning/claude_finetuning_YYYYMMDD.jsonl') as f:
    lines = f.readlines()
    
print(f"Training examples: {len(lines)}")

# Verify first example
example = json.loads(lines[0])
print(f"System message length: {len(example['messages'][0]['content'])}")
print(f"User message: {example['messages'][1]['content'][:100]}...")
print(f"Assistant response length: {len(example['messages'][2]['content'])}")
```

### 3. Upload to Provider (if required)

Some providers require uploading training data:

```bash
# OpenAI example
openai api files.create \
  -f training_data/finetuning/gpt4_finetuning_YYYYMMDD.jsonl \
  -p fine-tune
```

---

## Fine-Tuning with Claude

### Step 1: Contact Anthropic

Fine-tuning Claude requires enterprise access:

1. Email: sales@anthropic.com
2. Request fine-tuning access
3. Provide use case details
4. Await approval (1-2 weeks)

### Step 2: Prepare Data

```bash
# Data already prepared by formatter
# File: training_data/finetuning/claude_finetuning_YYYYMMDD.jsonl
```

### Step 3: Submit Fine-Tuning Job

```python
import anthropic

client = anthropic.Client(api_key="your-api-key")

# Upload training data
with open('training_data/finetuning/claude_finetuning_YYYYMMDD.jsonl', 'rb') as f:
    training_file = client.files.create(
        file=f,
        purpose='fine-tune'
    )

# Create fine-tuning job
job = client.fine_tuning.create(
    training_file=training_file.id,
    model="claude-3-sonnet-20240229",  # Base model
    hyperparameters={
        "n_epochs": 3,
        "batch_size": 8,
        "learning_rate_multiplier": 0.1
    }
)

print(f"Job ID: {job.id}")
```

### Step 4: Monitor Training

```python
# Check status
status = client.fine_tuning.retrieve(job.id)
print(f"Status: {status.status}")
print(f"Progress: {status.trained_tokens}/{status.total_tokens} tokens")
```

### Step 5: Use Fine-Tuned Model

```python
# Once complete
response = client.messages.create(
    model=job.fine_tuned_model,  # Your fine-tuned model ID
    messages=[
        {"role": "user", "content": "8-bit adder with carry"}
    ]
)
```

---

## Fine-Tuning with GPT-4

### Step 1: Upload Training Data

```bash
# Using OpenAI CLI
openai api files.create \
  -f training_data/finetuning/gpt4_finetuning_YYYYMMDD.jsonl \
  -p fine-tune

# Or using Python
import openai

with open('training_data/finetuning/gpt4_finetuning_YYYYMMDD.jsonl', 'rb') as f:
    file_response = openai.File.create(
        file=f,
        purpose='fine-tune'
    )

file_id = file_response.id
```

### Step 2: Create Fine-Tuning Job

```python
import openai

openai.api_key = "your-api-key"

# Create fine-tuning job
job = openai.FineTuning.create(
    training_file=file_id,
    model="gpt-4-0613",  # Base model
    hyperparameters={
        "n_epochs": 3,
        "batch_size": 8,
        "learning_rate_multiplier": 0.1
    }
)

print(f"Job ID: {job.id}")
```

### Step 3: Monitor Training

```python
# List all fine-tuning jobs
jobs = openai.FineTuning.list()

# Get specific job
job_status = openai.FineTuning.retrieve(job.id)
print(f"Status: {job_status.status}")

# List events
events = openai.FineTuning.list_events(id=job.id)
for event in events['data']:
    print(event['message'])
```

### Step 4: Use Fine-Tuned Model

```python
# Once training completes (status='succeeded')
response = openai.ChatCompletion.create(
    model=job.fine_tuned_model,  # Format: ft:gpt-4:org:suffix:id
    messages=[
        {"role": "system", "content": "You are an expert Verilog engineer."},
        {"role": "user", "content": "8-bit adder with carry"}
    ]
)

print(response.choices[0].message.content)
```

---

## Fine-Tuning with Llama

### Option A: Hugging Face (Recommended)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from datasets import load_dataset

# Load model
model_name = "meta-llama/Llama-2-7b-hf"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Load training data
dataset = load_dataset('json', data_files={
    'train': 'training_data/finetuning/llama_finetuning_YYYYMMDD.jsonl',
    'validation': 'training_data/finetuning/validation_set.jsonl'
})

# Tokenize
def tokenize_function(examples):
    return tokenizer(examples['instruction'] + examples['output'], truncation=True, padding='max_length')

tokenized_dataset = dataset.map(tokenize_function, batched=True)

# Training arguments
training_args = TrainingArguments(
    output_dir="./rtl_gen_llama_finetuned",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    warmup_steps=100,
    weight_decay=0.01,
    logging_dir='./logs',
    logging_steps=10,
    evaluation_strategy="steps",
    eval_steps=50,
    save_steps=100,
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset['train'],
    eval_dataset=tokenized_dataset['validation'],
)

# Train
trainer.train()

# Save
model.save_pretrained("./rtl_gen_llama_final")
tokenizer.save_pretrained("./rtl_gen_llama_final")
```

### Option B: Local with PEFT/LoRA (Efficient)

```python
from peft import LoraConfig, get_peft_model, prepare_model_for_int8_training
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer

# Load model in 8-bit
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    load_in_8bit=True,
    device_map="auto"
)

# Prepare for training
model = prepare_model_for_int8_training(model)

# LoRA config
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply LoRA
model = get_peft_model(model, lora_config)

# Tokenizer
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
tokenizer.pad_token = tokenizer.eos_token

# Training
trainer = SFTTrainer(
    model=model,
    train_dataset=tokenized_dataset['train'],
    dataset_text_field="text",
    max_seq_length=2048,
    tokenizer=tokenizer,
    args=TrainingArguments(
        output_dir="./rtl_gen_llama_lora",
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=100,
    )
)

trainer.train()
```

---

## Evaluation

### 1. Quantitative Evaluation

**File:** `scripts/evaluate_finetuned_model.py`

```python
"""Evaluate fine-tuned model performance."""

import json
from python.rtl_generator import RTLGenerator

# Test set
test_file = 'training_data/finetuning/test_set.jsonl'

# Load test examples
test_examples = []
with open(test_file) as f:
    for line in f:
        test_examples.append(json.loads(line))

# Initialize generator with fine-tuned model
generator = RTLGenerator(
    use_mock=False,
    model_name="your-finetuned-model-id"  # Replace with actual ID
)

# Evaluate
results = {
    'total': len(test_examples),
    'syntax_correct': 0,
    'simulation_passed': 0,
    'quality_scores': [],
}

for example in test_examples:
    description = example['messages'][1]['content']
    
    result = generator.generate(description, verify=True)
    
    if result['success']:
        results['syntax_correct'] += 1
        
        if result.get('verification', {}).get('passed'):
            results['simulation_passed'] += 1
        
        quality = result.get('metadata', {}).get('quality_score', 0)
        results['quality_scores'].append(quality)

# Calculate metrics
results['syntax_rate'] = results['syntax_correct'] / results['total'] * 100
results['simulation_rate'] = results['simulation_passed'] / results['total'] * 100
results['avg_quality'] = sum(results['quality_scores']) / len(results['quality_scores'])

print(json.dumps(results, indent=2))
```

### 2. Qualitative Evaluation

Test on novel descriptions not in training set:

```python
novel_tests = [
    "16-bit barrel shifter with direction control",
    "Priority encoder 8-to-3 with valid output",
    "Synchronous FIFO with configurable depth",
]

for desc in novel_tests:
    result = generator.generate(desc, verify=True)
    print(f"\n{desc}:")
    print(f"  Success: {result['success']}")
    print(f"  Quality: {result.get('metadata', {}).get('quality_score', 0)}/10")
```

---

## Deployment

### Update RTL Generator Configuration

**File:** `python/config.py` (add)

```python
# Fine-tuned model configuration
FINE_TUNED_MODEL_ID = "your-model-id-here"
USE_FINE_TUNED_MODEL = True

# Model provider
MODEL_PROVIDER = "anthropic"  # or "openai" or "huggingface"
```

### Update LLM Client

**File:** `python/llm_client.py` (update)

```python
def __init__(self, use_mock: bool = False, model_name: Optional[str] = None):
    """Initialize with optional fine-tuned model."""
    # ... existing code ...
    
    if model_name:
        self.model_name = model_name
    elif USE_FINE_TUNED_MODEL and FINE_TUNED_MODEL_ID:
        self.model_name = FINE_TUNED_MODEL_ID
    else:
        self.model_name = DEFAULT_MODEL
```

---

## Cost Estimates

### Fine-Tuning Costs

| Provider | Base Cost | Per Epoch | Total (3 epochs) |
|----------|-----------|-----------|------------------|
| Claude | $100 | $100 | $300-400 |
| GPT-4 | $80 | $80 | $240-320 |
| Llama (Local) | $0 | $0 | $0 (GPU time) |

### Inference Costs

| Provider | Base Model | Fine-Tuned | Savings |
|----------|-----------|------------|---------|
| Claude | $0.015/1K tokens | $0.018/1K tokens | N/A |
| GPT-4 | $0.03/1K tokens | $0.036/1K tokens | N/A |

*Fine-tuned models cost slightly more per token but may generate better code faster*

---

## Troubleshooting

### Common Issues

**1. Training Fails to Start**
- Check API key permissions
- Verify data format
- Ensure sufficient quota

**2. Poor Results After Fine-Tuning**
- Increase training epochs
- Check data quality
- Try different learning rate

**3. Overfitting**
- Reduce epochs
- Add more diverse training data
- Use validation set for early stopping

---
