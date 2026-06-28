"""
modal_train_rtl.py -- RTL-Gen AI Phase 4 Training on Modal.com

Runs QLoRA fine-tuning of CodeLlama-7b-Instruct on Modal A10G GPU (24GB VRAM).
Estimated cost: ~$3-6 (within the $30 free credit)
Estimated time: 2-3 hours (A10G is 3x faster than RTX 2050)

One-time setup:
    modal setup       <- opens browser login, 30 seconds
    modal run modal_train_rtl.py  <- then fully autonomous

The script will:
  1. Upload your training data automatically
  2. Pull CodeLlama-7b-Instruct from HuggingFace
  3. Fine-tune with QLoRA (4-bit, LoRA r=16)
  4. Save final model to Modal persistent volume
  5. Download model back to outputs/rtl_model_final/
  6. Write LOCAL_MODEL_PATH + LOCAL_MODEL_ENABLED=true to .env
"""

from __future__ import annotations
import modal
from pathlib import Path

# --- Modal image ---
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.3.1",
        "transformers==4.44.2",
        "accelerate==0.33.0",
        "peft==0.12.0",
        "bitsandbytes==0.43.3",
        "datasets==2.21.0",
        "trl==0.10.1",
        "scipy",
        "sentencepiece",
        "protobuf",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
)

app = modal.App("rtl-gen-ai-trainer", image=image)
volume = modal.Volume.from_name("rtl-model-volume", create_if_missing=True)

SYSTEM_PROMPT = (
    "You are an expert RTL hardware designer. "
    "Generate clean, synthesizable Verilog 2005 code. "
    "Always include: synchronous reset (active-low reset_n), "
    "clock (posedge clk), proper port declarations with widths, "
    "and inline comments. Output ONLY the complete Verilog module."
)


@app.function(
    gpu="A10G",
    timeout=14400,
    volumes={"/outputs": volume},
    memory=32768,
)
def train_rtl_model(train_jsonl: str, val_jsonl: str) -> dict:
    import time, torch
    from pathlib import Path
    from datasets import load_dataset
    from transformers import (
        AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig,
        TrainingArguments, Trainer, DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, TaskType

    Path("/tmp/data").mkdir(exist_ok=True)
    Path("/tmp/data/train.jsonl").write_text(train_jsonl)
    Path("/tmp/data/val.jsonl").write_text(val_jsonl)

    print(f"GPU  : {torch.cuda.get_device_name(0)}")
    print(f"VRAM : {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")

    dataset = load_dataset("json", data_files={
        "train": "/tmp/data/train.jsonl",
        "validation": "/tmp/data/val.jsonl",
    })
    print(f"Train: {len(dataset['train'])} examples | Val: {len(dataset['validation'])} examples")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    BASE_MODEL = "codellama/CodeLlama-7b-Instruct-hf"
    print(f"Loading {BASE_MODEL}...")
    t0 = time.time()

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb_config, device_map="auto"
    )
    model.config.use_cache = False
    print(f"Loaded in {time.time()-t0:.0f}s | VRAM: {torch.cuda.memory_allocated()/1e9:.1f} GB")

    lora_cfg = LoraConfig(
        r=16, lora_alpha=32,
        target_modules=["q_proj","v_proj","k_proj","o_proj"],
        lora_dropout=0.05, bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_cfg)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"LoRA: {trainable:,} trainable params")

    def format_and_tokenize(example):
        messages = example.get("messages", [])
        text = ""
        for m in messages:
            role, content = m.get("role",""), m.get("content","")
            if role == "system":
                text += f"<s>[INST] <<SYS>>\n{content}\n<</SYS>>\n\n"
            elif role == "user":
                if not text:
                    text += f"<s>[INST] <<SYS>>\n{SYSTEM_PROMPT}\n<</SYS>>\n\n"
                text += f"{content} [/INST] "
            elif role == "assistant":
                text += f"{content} </s>"
        tok = tokenizer(text, truncation=True, max_length=1024, padding="max_length")
        tok["labels"] = tok["input_ids"].copy()
        return tok

    tokenized = dataset.map(
        format_and_tokenize,
        remove_columns=dataset["train"].column_names,
        batched=False,
    )

    OUTPUT_DIR = "/outputs/rtl_model"
    FINAL_DIR  = "/outputs/rtl_model_final"

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_steps=50,
        eval_strategy="steps",
        eval_steps=50,
        save_total_limit=2,
        fp16=True,
        optim="paged_adamw_8bit",
        report_to="none",
        dataloader_num_workers=0,
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )

    print(f"\nStarting training ({len(tokenized['train'])} examples, 3 epochs)...")
    t1 = time.time()
    trainer.train()
    elapsed = (time.time() - t1) / 3600
    print(f"Training done in {elapsed:.2f} hours")

    trainer.save_model(FINAL_DIR)
    tokenizer.save_pretrained(FINAL_DIR)
    volume.commit()
    print(f"Model saved to volume at {FINAL_DIR}")

    return {
        "status": "complete",
        "elapsed_hours": round(elapsed, 2),
        "train_examples": len(tokenized["train"]),
        "model_path": FINAL_DIR,
    }


@app.local_entrypoint()
def main():
    import re, sys, time
    from pathlib import Path

    print("=" * 60)
    print("RTL-Gen AI -- Modal Cloud Training Launcher")
    print("=" * 60)

    train_path = Path("training_data/export/rtl_train_chat.jsonl")
    val_path   = Path("training_data/export/rtl_val_chat.jsonl")

    if not train_path.exists():
        print("ERROR: Dataset not found. Run:")
        print("  python dataset_builder.py --export --output training_data/export")
        sys.exit(1)

    with open(train_path) as f:
        n = sum(1 for _ in f)
    print(f"Dataset : {n} training examples ({train_path.stat().st_size//1024} KB)")
    print("Submitting to Modal A10G GPU (2-3 hours, ~$4 cost)...")
    print("=" * 60)

    result = train_rtl_model.remote(
        train_jsonl=train_path.read_text(encoding="utf-8"),
        val_jsonl=val_path.read_text(encoding="utf-8"),
    )

    print(f"\nTraining complete!")
    print(f"  Status  : {result['status']}")
    print(f"  Elapsed : {result['elapsed_hours']} hours")
    print(f"  Examples: {result['train_examples']}")

    # Pull model files from volume
    print("\nTo download the model locally, run:")
    print("  modal volume get rtl-model-volume rtl_model_final/ outputs/")

    # Update .env
    env_path = Path(".env")
    env_text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    local_model = str(Path("outputs/rtl_model_final").resolve())
    for key, val in [("LOCAL_MODEL_PATH", local_model), ("LOCAL_MODEL_ENABLED", "true")]:
        if key in env_text:
            env_text = re.sub(rf"^{key}=.*$", f"{key}={val}", env_text, flags=re.MULTILINE)
        else:
            env_text += f"\n{key}={val}\n"
    env_path.write_text(env_text, encoding="utf-8")
    print(f"\n.env updated: LOCAL_MODEL_PATH={local_model}")
    print("Done! Run: python model_trainer.py --deploy --model outputs/rtl_model_final")
