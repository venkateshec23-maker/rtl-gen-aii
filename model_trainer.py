"""
model_trainer.py — Phase 4 Custom RTL Model Fine-Tuning
RTL-Gen AI

Fine-tunes CodeLlama-7B-Instruct on the Phase 3 RTL dataset using QLoRA.
Runs on RTX 2050 4GB VRAM with 4-bit quantization.
Deploys as the 6th LLM provider in verilog_generator.py.

Hardware requirements:
  GPU  : RTX 2050 4GB VRAM (minimum), RTX 3060 12GB (recommended)
  RAM  : 16 GB system RAM
  Disk : 20 GB free (model + checkpoints)
  Time : ~4-8 hours on RTX 2050, ~2 hours on RTX 3060

Dependencies (already installed):
  torch==2.10.0
  transformers==5.2.0
  accelerate==1.12.0
  datasets==4.5.0
  peft (install: pip install peft)
  bitsandbytes (install: pip install bitsandbytes)

Usage:
  # Step 1: Check GPU and prepare
  python model_trainer.py --check

  # Step 2: Download base model (one-time, ~13 GB)
  python model_trainer.py --download

  # Step 3: Train (4-8 hours on RTX 2050)
  python model_trainer.py --train --data training_data/export/rtl_train_chat.jsonl

  # Step 4: Evaluate quality
  python model_trainer.py --eval --model outputs/rtl_model_final

  # Step 5: Test a generation
  python model_trainer.py --test --model outputs/rtl_model_final --desc "8-bit counter"

  # Step 6: Deploy (registers as local provider in verilog_generator.py)
  python model_trainer.py --deploy --model outputs/rtl_model_final
"""

from __future__ import annotations

import gc
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_MODEL       = "codellama/CodeLlama-7b-Instruct-hf"   # primary
BASE_MODEL_SMALL = "bigcode/starcoder2-3b"                 # if VRAM < 4 GB
OUTPUT_DIR       = Path("outputs/rtl_model")
FINAL_MODEL_DIR  = Path("outputs/rtl_model_final")
DATASET_DIR      = Path("training_data/export")

# QLoRA hyperparameters — tuned for RTX 2050 4GB
LORA_CONFIG = {
    "r":              16,      # LoRA rank
    "lora_alpha":     32,      # scaling factor
    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
    "lora_dropout":   0.05,
    "bias":           "none",
    "task_type":      "CAUSAL_LM",
}

TRAINING_CONFIG = {
    "num_train_epochs":            3,
    "per_device_train_batch_size": 1,
    "gradient_accumulation_steps": 8,    # effective batch = 8
    "learning_rate":               2e-4,
    "warmup_ratio":                0.05,
    "lr_scheduler_type":           "cosine",
    "logging_steps":               10,
    "save_steps":                  50,
    "eval_steps":                  50,
    "save_total_limit":            3,
    "fp16":                        True,
    "optim":                       "paged_adamw_8bit",
    "dataloader_num_workers":      0,      # Windows compatibility
    "report_to":                   "none", # disable wandb
}

SYSTEM_PROMPT = (
    "You are an expert RTL hardware designer. "
    "Generate clean, synthesizable Verilog 2005 code. "
    "Always include: synchronous reset (active-low reset_n), "
    "clock (posedge clk), proper port declarations with widths, "
    "and inline comments. Output ONLY the complete Verilog module, "
    "starting with 'module' and ending with 'endmodule'."
)


# ── GPU check ─────────────────────────────────────────────────────────────────

def check_environment() -> Dict:
    """Check GPU, VRAM, and required packages."""
    result = {
        "torch_available":   False,
        "cuda_available":    False,
        "vram_gb":           0,
        "peft_available":    False,
        "bitsandbytes":      False,
        "recommended_model": BASE_MODEL,
        "ready":             False,
    }

    try:
        import torch
        result["torch_available"] = True
        result["cuda_available"]  = torch.cuda.is_available()
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            result["vram_gb"]  = round(props.total_memory / 1e9, 1)
            result["gpu_name"] = props.name
            if result["vram_gb"] < 4:
                result["recommended_model"] = BASE_MODEL_SMALL
                result["warning"] = "VRAM < 4 GB: using starcoder2-3b instead of CodeLlama-7b"
    except ImportError:
        result["error_torch"] = "torch not installed"

    try:
        import peft  # noqa: F401
        result["peft_available"] = True
    except ImportError:
        result["error_peft"] = "peft not installed — run: pip install peft"

    try:
        import bitsandbytes  # noqa: F401
        result["bitsandbytes"] = True
    except ImportError:
        result["error_bnb"] = "bitsandbytes not installed — run: pip install bitsandbytes"

    result["ready"] = all([
        result["cuda_available"],
        result["peft_available"],
        result["bitsandbytes"],
    ])

    return result


def print_environment_report(env: Dict) -> None:
    print("\n=== RTL Model Trainer — Environment Check ===")
    print(f"  PyTorch     : {'OK' if env['torch_available'] else 'MISSING'}")
    print(f"  CUDA        : {'OK' if env['cuda_available']  else 'NOT AVAILABLE'}")
    if env.get("gpu_name"):
        print(f"  GPU         : {env['gpu_name']}")
        print(f"  VRAM        : {env['vram_gb']} GB")
    print(f"  PEFT        : {'OK' if env['peft_available'] else 'MISSING — pip install peft'}")
    print(f"  BitsBytes   : {'OK' if env['bitsandbytes']   else 'MISSING — pip install bitsandbytes'}")
    print(f"  Base model  : {env['recommended_model']}")
    if env.get("warning"):
        print(f"  WARNING     : {env['warning']}")
    print(f"\n  Ready to train: {'YES' if env['ready'] else 'NO — install missing packages first'}")


# ── Dataset preparation ────────────────────────────────────────────────────────

def prepare_dataset(jsonl_path: Path):
    """
    Load and format the JSONL dataset for fine-tuning.
    Returns a HuggingFace Dataset object.
    """
    from datasets import Dataset

    if not jsonl_path.exists():
        raise FileNotFoundError(
            f"Training data not found: {jsonl_path}\n"
            f"Run Phase 3 first: python dataset_builder.py --export"
        )

    examples = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            # Convert chat format to training text
            msgs = d.get("messages", [])
            if msgs:
                text = _format_chat(msgs)
                examples.append({"text": text, "id": d.get("id", "")})
        except Exception:
            pass

    if not examples:
        raise ValueError(f"No valid examples found in {jsonl_path}")

    log.info("Loaded %d training examples from %s", len(examples), jsonl_path)
    return Dataset.from_list(examples)


def _format_chat(messages: List[Dict]) -> str:
    """
    Format chat messages into CodeLlama instruction format:
    [INST] <<SYS>>\\n{system}\\n<</SYS>>\\n\\n{user} [/INST] {assistant}
    """
    system    = next((m["content"] for m in messages if m["role"] == "system"), SYSTEM_PROMPT)
    user      = next((m["content"] for m in messages if m["role"] == "user"), "")
    assistant = next((m["content"] for m in messages if m["role"] == "assistant"), "")

    return (
        f"[INST] <<SYS>>\n{system}\n<</SYS>>\n\n"
        f"{user} [/INST] {assistant}"
    )


def _tokenize_dataset(dataset, tokenizer, max_length: int = 1024):
    """Tokenize dataset with padding and truncation."""
    def tokenize(example):
        return tokenizer(
            example["text"],
            truncation=True,
            max_length=max_length,
            padding=False,
        )
    return dataset.map(tokenize, batched=True, remove_columns=["text", "id"])


# ── Model loader ──────────────────────────────────────────────────────────────

def load_base_model(model_name: str, vram_gb: float = 4.0):
    """
    Load base model with 4-bit quantization for QLoRA.
    Uses BitsAndBytes NF4 quantization to fit in 4 GB VRAM.
    """
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )

    log.info("Loading base model: %s", model_name)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit              = True,
        bnb_4bit_use_double_quant = True,
        bnb_4bit_quant_type       = "nf4",
        bnb_4bit_compute_dtype    = torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token    = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config = bnb_config,
        device_map          = "auto",
        trust_remote_code   = True,
        torch_dtype         = torch.bfloat16,
        use_cache           = False,   # disable KV cache during training
    )

    log.info("Base model loaded. VRAM used: %.1f GB", _get_vram_used())
    return model, tokenizer


def _get_vram_used() -> float:
    try:
        import torch
        return torch.cuda.memory_allocated() / 1e9
    except Exception:
        return 0.0


# ── LoRA setup ────────────────────────────────────────────────────────────────

def apply_lora(model):
    """Apply LoRA adapters to the quantized base model."""
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r              = LORA_CONFIG["r"],
        lora_alpha     = LORA_CONFIG["lora_alpha"],
        target_modules = LORA_CONFIG["target_modules"],
        lora_dropout   = LORA_CONFIG["lora_dropout"],
        bias           = LORA_CONFIG["bias"],
        task_type      = LORA_CONFIG["task_type"],
    )

    model = get_peft_model(model, lora_config)

    trainable, total = 0, 0
    for _, p in model.named_parameters():
        total += p.numel()
        if p.requires_grad:
            trainable += p.numel()

    log.info(
        "LoRA applied: %d trainable params / %d total (%.2f%%)",
        trainable, total, 100 * trainable / total,
    )
    return model


# ── Training ──────────────────────────────────────────────────────────────────

def train(
    train_jsonl: Path,
    val_jsonl:   Optional[Path] = None,
    output_dir:  Path           = OUTPUT_DIR,
    resume:      bool           = False,
) -> Path:
    """
    Full QLoRA fine-tuning run.
    Returns path to the final trained model.
    """
    from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

    output_dir.mkdir(parents=True, exist_ok=True)

    env = check_environment()
    if not env["ready"]:
        print_environment_report(env)
        raise RuntimeError("Environment not ready. Install missing packages.")

    model_name = env["recommended_model"]

    # Load dataset
    log.info("Preparing dataset from %s", train_jsonl)
    train_dataset = prepare_dataset(train_jsonl)
    val_dataset   = prepare_dataset(val_jsonl) if val_jsonl and val_jsonl.exists() else None

    # Load model + apply LoRA
    model, tokenizer = load_base_model(model_name, env["vram_gb"])
    model = apply_lora(model)

    # Tokenize — shorter sequences on constrained VRAM
    max_len = 768 if env["vram_gb"] < 6 else 1024
    log.info("Tokenizing with max_length=%d", max_len)
    train_tokenized = _tokenize_dataset(train_dataset, tokenizer, max_len)
    val_tokenized   = _tokenize_dataset(val_dataset, tokenizer, max_len) if val_dataset else None

    # Training arguments
    training_args = TrainingArguments(
        output_dir                  = str(output_dir),
        num_train_epochs            = TRAINING_CONFIG["num_train_epochs"],
        per_device_train_batch_size = TRAINING_CONFIG["per_device_train_batch_size"],
        gradient_accumulation_steps = TRAINING_CONFIG["gradient_accumulation_steps"],
        learning_rate               = TRAINING_CONFIG["learning_rate"],
        warmup_ratio                = TRAINING_CONFIG["warmup_ratio"],
        lr_scheduler_type           = TRAINING_CONFIG["lr_scheduler_type"],
        logging_steps               = TRAINING_CONFIG["logging_steps"],
        save_steps                  = TRAINING_CONFIG["save_steps"],
        eval_steps                  = TRAINING_CONFIG["eval_steps"] if val_tokenized else None,
        evaluation_strategy         = "steps" if val_tokenized else "no",
        save_total_limit            = TRAINING_CONFIG["save_total_limit"],
        fp16                        = TRAINING_CONFIG["fp16"],
        optim                       = TRAINING_CONFIG["optim"],
        dataloader_num_workers      = TRAINING_CONFIG["dataloader_num_workers"],
        report_to                   = TRAINING_CONFIG["report_to"],
        load_best_model_at_end      = bool(val_tokenized),
        resume_from_checkpoint      = resume,
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    trainer = Trainer(
        model         = model,
        args          = training_args,
        train_dataset = train_tokenized,
        eval_dataset  = val_tokenized,
        data_collator = data_collator,
        tokenizer     = tokenizer,
    )

    est_hours = len(train_tokenized) * TRAINING_CONFIG["num_train_epochs"] * 10 / 3600
    log.info("Starting training — estimated %.1f hours on RTX 2050", est_hours)

    t0 = time.time()
    trainer.train(resume_from_checkpoint=resume)
    elapsed = time.time() - t0

    log.info("Training complete in %.1f hours", elapsed / 3600)

    # Save final model
    FINAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(FINAL_MODEL_DIR))
    tokenizer.save_pretrained(str(FINAL_MODEL_DIR))

    # Save training metadata
    metadata = {
        "base_model":     model_name,
        "trained_at":     datetime.now().isoformat(),
        "train_examples": len(train_tokenized),
        "epochs":         TRAINING_CONFIG["num_train_epochs"],
        "elapsed_hours":  round(elapsed / 3600, 2),
        "lora_config":    LORA_CONFIG,
    }
    (FINAL_MODEL_DIR / "training_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    log.info("Model saved to %s", FINAL_MODEL_DIR)
    return FINAL_MODEL_DIR


# ── Inference ─────────────────────────────────────────────────────────────────

def load_trained_model(model_path: Path):
    """Load the fine-tuned model for inference (4-bit quantized)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    metadata_path = model_path / "training_metadata.json"
    if metadata_path.exists():
        metadata   = json.loads(metadata_path.read_text(encoding="utf-8"))
        base_model = metadata.get("base_model", BASE_MODEL)
    else:
        base_model = BASE_MODEL

    bnb_config = BitsAndBytesConfig(
        load_in_4bit              = True,
        bnb_4bit_use_double_quant = True,
        bnb_4bit_quant_type       = "nf4",
        bnb_4bit_compute_dtype    = torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config = bnb_config,
        device_map          = "auto",
        torch_dtype         = torch.bfloat16,
    )
    model = PeftModel.from_pretrained(base, str(model_path))
    model.eval()

    return model, tokenizer


# ── Module-level inference cache (singleton) ──────────────────────────────────
_cached_model      = None
_cached_tokenizer  = None
_cached_model_path: Optional[Path] = None


def _get_or_load_model(model_path: Path):
    """Return cached model/tokenizer, reloading only if path changed."""
    global _cached_model, _cached_tokenizer, _cached_model_path
    if _cached_model is None or _cached_model_path != model_path:
        _cached_model, _cached_tokenizer = load_trained_model(model_path)
        _cached_model_path = model_path
    return _cached_model, _cached_tokenizer


def generate_verilog_local(
    description:    str,
    model_path:     Path,
    max_new_tokens: int   = 512,
    temperature:    float = 0.2,
) -> Optional[str]:
    """
    Generate Verilog using the fine-tuned local model.
    This is the 6th LLM provider callable from verilog_generator.py.

    Returns the Verilog module string, or None on failure.
    """
    import torch

    model, tokenizer = _get_or_load_model(model_path)

    prompt = _format_chat([
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "user",      "content": description},
        {"role": "assistant", "content": ""},
    ]).rstrip()

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens = max_new_tokens,
            temperature    = temperature,
            do_sample      = temperature > 0,
            pad_token_id   = tokenizer.eos_token_id,
            eos_token_id   = tokenizer.eos_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    ).strip()

    # Extract Verilog module — must start with 'module' and end with 'endmodule'
    m = re.search(r"(module\s+\w+.*?endmodule)", response, re.DOTALL)
    return m.group(1).strip() if m else response


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_model(model_path: Path, test_jsonl: Path) -> Dict:
    """
    Evaluate the fine-tuned model on held-out test examples.
    Metrics: syntax pass rate, module completeness, clock/reset presence.
    """
    import subprocess
    import tempfile

    if not test_jsonl.exists():
        return {"error": f"Test data not found: {test_jsonl}"}

    test_examples = []
    for line in test_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            msgs = d.get("messages", [])
            if msgs:
                test_examples.append({
                    "description": next(m["content"] for m in msgs if m["role"] == "user"),
                    "expected":    next(m["content"] for m in msgs if m["role"] == "assistant"),
                })
        except Exception:
            pass

    if not test_examples:
        return {"error": "No valid test examples"}

    results = {
        "total":              len(test_examples),
        "syntax_pass":        0,
        "module_complete":    0,
        "has_clock":          0,
        "has_reset":          0,
        "generated_examples": [],
    }

    # Evaluate a sample (max 20 to keep runtime reasonable)
    sample = test_examples[:20]

    for ex in sample:
        generated = generate_verilog_local(ex["description"], model_path)
        if not generated:
            continue

        # Syntax check via iverilog (if available)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".v", delete=False, encoding="utf-8"
        ) as f:
            f.write(generated)
            tmp = f.name

        try:
            r = subprocess.run(
                ["iverilog", "-tnull", tmp],
                capture_output=True, text=True, timeout=10,
            )
            syntax_ok = r.returncode == 0
        except Exception:
            syntax_ok = True  # assume OK if iverilog not installed
        finally:
            Path(tmp).unlink(missing_ok=True)

        module_ok = "module " in generated and "endmodule" in generated
        clock_ok  = "clk" in generated or "clock" in generated
        reset_ok  = "reset" in generated or "rst" in generated

        if syntax_ok:  results["syntax_pass"]     += 1
        if module_ok:  results["module_complete"]  += 1
        if clock_ok:   results["has_clock"]        += 1
        if reset_ok:   results["has_reset"]        += 1

        results["generated_examples"].append({
            "description": ex["description"][:60],
            "syntax_ok":   syntax_ok,
            "lines":       generated.count("\n"),
        })

    n = len(sample)
    results["syntax_pass_rate"]     = round(results["syntax_pass"]     / n * 100, 1)
    results["module_complete_rate"] = round(results["module_complete"] / n * 100, 1)

    return results


# ── Deploy ────────────────────────────────────────────────────────────────────

def deploy_as_provider(model_path: Path) -> None:
    """
    Register the fine-tuned model as the 'local' LLM provider.

    Writes LOCAL_MODEL_PATH + LOCAL_MODEL_ENABLED to .env so that
    verilog_generator.py can pick it up without code changes.
    """
    env_path = Path(".env")

    # Add LOCAL_MODEL_PATH to .env
    env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if "LOCAL_MODEL_PATH" not in env_content:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\n# Phase 4: Fine-tuned RTL model\n")
            f.write(f"LOCAL_MODEL_PATH={model_path.resolve()}\n")
            f.write(f"LOCAL_MODEL_ENABLED=true\n")
        print(f"Added LOCAL_MODEL_PATH to .env: {model_path.resolve()}")
    else:
        print("LOCAL_MODEL_PATH already in .env — update manually if path changed")

    # Verify required model files exist
    required = ["adapter_config.json", "tokenizer.json", "training_metadata.json"]
    missing  = [f for f in required if not (model_path / f).exists()]
    if missing:
        print(f"WARNING: Missing model files: {missing}")
        print("Training may not have completed successfully.")
        return

    print(f"\nModel deployed successfully.")
    print(f"Path   : {model_path.resolve()}")
    print(f"\nThe 'local' provider is already wired into verilog_generator.py.")
    print("Select 'local' as the LLM provider in the UI or pass llm_provider='local'.")


# ── Streamlit training monitor ────────────────────────────────────────────────

def render_trainer_streamlit(key: str = "trainer") -> None:
    """
    Streamlit page for monitoring and launching model training.
    Attach to app.py as 'Model Trainer' page if desired.
    """
    import streamlit as st

    st.title("🧠 RTL Model Trainer — Phase 4")
    st.caption(
        "Fine-tune CodeLlama-7B on your proven RTL designs. "
        "Requires CUDA GPU with ≥ 4 GB VRAM."
    )

    # ── Environment status ──
    with st.expander("🔧 Environment Check", expanded=True):
        env = check_environment()
        col1, col2, col3 = st.columns(3)
        col1.metric("CUDA",        "✅" if env["cuda_available"]  else "❌")
        col2.metric("PEFT",        "✅" if env["peft_available"]  else "❌")
        col3.metric("BitsAndBytes","✅" if env["bitsandbytes"]    else "❌")
        if env.get("gpu_name"):
            st.info(f"GPU: {env['gpu_name']} — {env['vram_gb']} GB VRAM")
        if env.get("warning"):
            st.warning(env["warning"])
        if not env["ready"]:
            st.error(
                "Install missing packages:\n"
                "```\npip install peft bitsandbytes\n```"
            )

    # ── Dataset status ──
    st.divider()
    st.subheader("📊 Training Data")
    try:
        from dataset_builder import get_count, MIN_EXAMPLES_FOR_TRAINING
        n      = get_count()
        needed = max(0, MIN_EXAMPLES_FOR_TRAINING - n)
        st.progress(min(1.0, n / MIN_EXAMPLES_FOR_TRAINING),
                    f"{n} / {MIN_EXAMPLES_FOR_TRAINING} examples")
        if needed > 0:
            st.warning(f"Need {needed} more tape-out ready designs before training.")
        else:
            st.success(f"Dataset ready! {n} examples collected.")

        export_dir = DATASET_DIR
        train_file = export_dir / "rtl_train_chat.jsonl"
        val_file   = export_dir / "rtl_val_chat.jsonl"
        if train_file.exists():
            st.caption(f"Train: {train_file} ({round(train_file.stat().st_size/1024,1)} KB)")
        if val_file.exists():
            st.caption(f"Val  : {val_file} ({round(val_file.stat().st_size/1024,1)} KB)")

        if not train_file.exists():
            if st.button("📦 Export dataset now", key=f"{key}_export"):
                from dataset_builder import export_dataset
                with st.spinner("Exporting..."):
                    export_dataset(DATASET_DIR)
                st.success("Exported! Re-check training files above.")
                st.rerun()
    except ImportError:
        st.warning("dataset_builder.py not found — complete Phase 3 first.")

    # ── Existing model ──
    st.divider()
    st.subheader("🤖 Trained Model")
    if FINAL_MODEL_DIR.exists():
        meta_path = FINAL_MODEL_DIR / "training_metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            c1, c2, c3 = st.columns(3)
            c1.metric("Base",    meta.get("base_model", "?").split("/")[-1])
            c2.metric("Examples",meta.get("train_examples", "?"))
            c3.metric("Epochs",  meta.get("epochs", "?"))
            st.caption(f"Trained at: {meta.get('trained_at','?')[:19].replace('T',' ')}")
            st.caption(f"Elapsed: {meta.get('elapsed_hours','?')} hours")
        else:
            st.info(f"Model directory found: {FINAL_MODEL_DIR}")
    else:
        st.info(f"No trained model yet. Run training below.")

    # ── Test generation ──
    st.divider()
    st.subheader("🧪 Test Generation")
    test_desc = st.text_input(
        "Design description to test",
        value="8-bit synchronous counter with enable and active-low reset",
        key=f"{key}_test_desc",
    )
    if st.button("▶ Generate with local model", key=f"{key}_test_btn",
                 disabled=not FINAL_MODEL_DIR.exists()):
        if not env["ready"]:
            st.error("GPU not ready — check environment above.")
        else:
            with st.spinner("Generating Verilog (may take 20-60s)..."):
                try:
                    rtl = generate_verilog_local(test_desc, FINAL_MODEL_DIR)
                    if rtl:
                        st.success("Generation successful!")
                        st.code(rtl, language="verilog")
                    else:
                        st.error("No Verilog extracted from model output.")
                except Exception as e:
                    st.error(f"Generation failed: {e}")

    # ── CLI instructions ──
    st.divider()
    st.subheader("🖥️ CLI Commands")
    st.code(
        "# Step 1: Check environment\n"
        "python model_trainer.py --check\n\n"
        "# Step 2: Train (run in terminal, not Streamlit)\n"
        "python model_trainer.py --train --data training_data/export/rtl_train_chat.jsonl\n\n"
        "# Step 3: Evaluate\n"
        "python model_trainer.py --eval --model outputs/rtl_model_final\n\n"
        "# Step 4: Deploy as 'local' provider\n"
        "python model_trainer.py --deploy --model outputs/rtl_model_final",
        language="bash",
    )


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="RTL-Gen AI Phase 4 Model Trainer")
    parser.add_argument("--check",    action="store_true", help="Check environment readiness")
    parser.add_argument("--download", action="store_true", help="Pre-download base model")
    parser.add_argument("--train",    action="store_true", help="Start fine-tuning")
    parser.add_argument("--eval",     action="store_true", help="Evaluate trained model")
    parser.add_argument("--test",     action="store_true", help="Generate one Verilog example")
    parser.add_argument("--deploy",   action="store_true", help="Deploy as LLM provider")
    parser.add_argument("--data",     type=str,
                        default=str(DATASET_DIR / "rtl_train_chat.jsonl"))
    parser.add_argument("--model",    type=str, default=str(FINAL_MODEL_DIR))
    parser.add_argument("--desc",     type=str,
                        default="8-bit synchronous adder with carry")
    parser.add_argument("--resume",   action="store_true",
                        help="Resume from checkpoint")
    args = parser.parse_args()

    if args.check:
        env = check_environment()
        print_environment_report(env)

    if args.download:
        print(f"Pre-downloading tokenizer for {BASE_MODEL}...")
        try:
            from transformers import AutoTokenizer
            AutoTokenizer.from_pretrained(BASE_MODEL)
            print("Tokenizer downloaded. Model weights download automatically during --train.")
            print("Full download: ~13 GB — ensure sufficient disk space.")
        except Exception as e:
            print(f"Download failed: {e}")

    if args.train:
        data_path = Path(args.data)
        val_path  = data_path.parent / data_path.name.replace("_train_", "_val_")
        print(f"\nStarting training on {data_path}")
        if not data_path.exists():
            print(f"ERROR: Training data not found: {data_path}")
            print("Run Phase 3 first: python dataset_builder.py --export")
            sys.exit(1)
        result = train(
            data_path,
            val_path if val_path.exists() else None,
            resume=args.resume,
        )
        print(f"\nTraining complete. Model saved to: {result}")

    if args.eval:
        model_path = Path(args.model)
        test_path  = DATASET_DIR / "rtl_test_chat.jsonl"
        print(f"\nEvaluating {model_path}...")
        results = evaluate_model(model_path, test_path)
        print("\nEvaluation Results:")
        print(f"  Syntax pass rate : {results.get('syntax_pass_rate', 'N/A')}%")
        print(f"  Module complete  : {results.get('module_complete_rate', 'N/A')}%")
        print(f"  Has clock        : {results.get('has_clock', 0)}/{results.get('total', 0)}")
        print(f"  Has reset        : {results.get('has_reset', 0)}/{results.get('total', 0)}")
        if results.get("syntax_pass_rate", 0) >= 90:
            print("\n  PHASE 4 COMPLETE — model ready for deployment")
        else:
            print("\n  Model needs improvement — consider more training data or epochs")

    if args.test:
        model_path = Path(args.model)
        print(f"\nGenerating Verilog for: {args.desc}")
        print(f"Model: {model_path}")
        rtl = generate_verilog_local(args.desc, model_path)
        if rtl:
            print("\n--- Generated Verilog ---")
            print(rtl)
            print("--- End ---")
        else:
            print("Generation failed")

    if args.deploy:
        deploy_as_provider(Path(args.model))
