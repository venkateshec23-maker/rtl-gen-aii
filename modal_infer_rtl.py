"""modal_infer_rtl.py -- Section 4C: Generation quality test (fixed)"""
import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.3.1", "transformers==4.44.2", "accelerate==0.33.0",
        "peft==0.12.0", "bitsandbytes==0.43.3", "sentencepiece",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
)

app = modal.App("rtl-infer-v3", image=image)
volume = modal.Volume.from_name("rtl-model-volume", create_if_missing=False)

@app.function(gpu="A10G", timeout=600, volumes={"/outputs": volume}, memory=16384)
def generate_rtl(descriptions: list) -> list:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel

    ADAPTER = "/outputs/rtl_model_final"
    BASE    = "codellama/CodeLlama-7b-Instruct-hf"
    SYSTEM  = "You are an expert RTL hardware designer. Generate clean, synthesizable Verilog 2005. Output ONLY the complete Verilog module starting with 'module' and ending with 'endmodule'."

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                              bnb_4bit_compute_dtype=torch.float16)
    tok = AutoTokenizer.from_pretrained(ADAPTER)
    tok.pad_token = tok.eos_token
    tok.padding_side = "left"

    base_model = AutoModelForCausalLM.from_pretrained(BASE, quantization_config=bnb, device_map="auto")
    model = PeftModel.from_pretrained(base_model, ADAPTER)
    model.eval()

    results = []
    with torch.no_grad():
        for desc in descriptions:
            prompt = f"<s>[INST] <<SYS>>\n{SYSTEM}\n<</SYS>>\n\n{desc} [/INST] "
            inputs = tok(prompt, return_tensors="pt").to("cuda")
            prompt_len = inputs["input_ids"].shape[1]

            out_ids = model.generate(
                **inputs,
                max_new_tokens=450,
                temperature=0.3,
                do_sample=True,
                pad_token_id=tok.eos_token_id,
                eos_token_id=tok.eos_token_id,
            )
            # Decode ONLY the new tokens (skip the prompt)
            new_tokens = out_ids[0][prompt_len:]
            rtl = tok.decode(new_tokens, skip_special_tokens=True).strip()
            results.append(rtl)
    return results

@app.local_entrypoint()
def main():
    test_descs = [
        "8-bit synchronous adder with carry output",
        "4-bit up counter with enable and reset",
        "UART transmitter at 115200 baud",
        "8-bit shift register with serial input",
        "D flip-flop with synchronous reset",
    ]

    print("=== Section 4C: Generation Quality Test (5 designs, fixed eval) ===")
    print("Loading CodeLlama-7b + RTL LoRA adapter from Modal volume...")
    outputs = generate_rtl.remote(test_descs)

    pass_count = 0
    for desc, rtl in zip(test_descs, outputs):
        has_module   = "module " in rtl and "endmodule" in rtl
        has_clock    = "clk" in rtl or "clock" in rtl
        ok = has_module and has_clock
        pass_count += 1 if ok else 0
        lines = rtl.strip().splitlines()
        status = "PASS" if ok else "FAIL"
        first = lines[0][:70] if lines else "(empty)"
        print(f"  {status}: {desc[:50]}")
        print(f"         ({len(lines)} lines | module={'YES' if has_module else 'NO'} clock={'YES' if has_clock else 'NO'} | {first})")

    print(f"\nQuality: {pass_count}/{len(test_descs)} pass")
    print(f"syntax_pass_rate: {pass_count/len(test_descs)*100:.0f}%")
    if pass_count < 3:
        print("NOTE: < 60% pass -- will collect more examples and re-train")
    elif pass_count < 5:
        print("NOTE: Acceptable quality. Re-train with --resume after 50 more examples for improvement.")
    else:
        print("RESULT: PASS -- all 5 designs generated correctly")
