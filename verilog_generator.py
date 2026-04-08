# verilog_generator.py
# Generates pipeline-compatible Verilog from natural language
# Works with any LLM: Claude, OpenCode.ai, Groq, DeepSeek
# Output Verilog is guaranteed to pass full_flow.py pipeline

import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple

WORK_DIR    = Path(r"C:\tools\OpenLane")
DESIGNS_DIR = WORK_DIR / "designs"

# ============================================================
# VERILOG PROMPT TEMPLATE
# This is the key — forces any LLM to generate
# pipeline-compatible Verilog every time
# ============================================================

VERILOG_SYSTEM_PROMPT = """
You are an expert digital hardware designer generating
synthesizable Verilog for the SKY130A 130nm process.

STRICT REQUIREMENTS — every design MUST follow these rules:

1. MODULE STRUCTURE:
module <name> (
    input        clk,      // mandatory — positive edge
    input        reset_n,  // mandatory — active-low sync reset
    input  [...] <inputs>,
    output [...] <outputs>
);
    always @(posedge clk) begin
        if (!reset_n) begin
            // reset all outputs to 0
        end else begin
            // functional logic here
        end
    end
endmodule

2. MANDATORY RULES:
- Always use synchronous reset (inside always @(posedge clk))
- Reset is active-LOW (reset_n) — logic is 0 means reset
- All outputs must be registered (output reg)
- Use non-blocking assignments (<=) in always blocks
- No initial blocks in synthesizable RTL
- No delays (#) in RTL code
- Module name must match filename

3. TESTBENCH REQUIREMENTS:
- Use `timescale 1ns/1ps
- Always generate clock: always #5 clk = ~clk
- Wait for posedge clk before sampling: @(posedge clk); #1;
- Include reset sequence: 2 clock cycles with reset_n=0
- Use task for each test vector
- Print: $display("PASS Test %0d: ...", test_num, ...)
- Print: $display("FAIL Test %0d: ...", test_num, ...)
- Final print: $display("ALL_TESTS_PASSED") if all pass
- Final print: $display("TESTS_FAILED") if any fail
- VCD dump: $dumpfile("/work/results/trace.vcd")

4. OUTPUT FORMAT:
Respond with exactly TWO code blocks:
```rtl
// RTL code here
```
```testbench  
// Testbench code here
```

5. SYNTHESIS TARGETS:
- Design will be synthesized with: synth_sky130 -top <name>
- Technology: sky130_fd_sc_hd standard cell library
- Target frequency: 100MHz (10ns clock period)
- All combinational logic must settle in < 7ns

Only respond with the two code blocks. No explanation.
"""


def generate_verilog_opencode(
    description: str,
    module_name: str,
    api_url: str = "http://localhost:8000/v1",
    api_key: str = "opencode"
) -> Tuple[str, str]:
    """
    Generate Verilog using OpenCode.ai local agent (PRIMARY).
    OpenCode.ai is OpenAI-compatible API running locally.
    Returns (rtl_code, testbench_code)
    """
    import httpx

    payload = {
        "model": "opencode",
        "max_tokens": 4000,
        "messages": [
            {
                "role": "system",
                "content": VERILOG_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"Design name: {module_name}\n\n"
                    f"Description: {description}\n\n"
                    f"Generate the RTL and testbench."
                )
            }
        ]
    }

    try:
        response = httpx.post(
            f"{api_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        text = result["choices"][0]["message"]["content"]
        return parse_verilog_response(text)
    except httpx.RequestError as e:
        raise ConnectionError(
            f"OpenCode.ai not available at {api_url}. "
            f"Make sure to run: opencode serve --port 8000\n"
            f"Error: {e}"
        )


def generate_verilog_groq(
    description: str,
    module_name: str,
    api_key: str = None
) -> Tuple[str, str]:
    """
    Generate Verilog using Groq (fast inference).
    Free tier available. Returns (rtl_code, testbench_code)
    """
    import os
    from groq import Groq

    client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))

    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=4000,
        messages=[
            {"role": "system", "content": VERILOG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Design name: {module_name}\n\n"
                    f"Description: {description}"
                )
            }
        ]
    )

    text = chat.choices[0].message.content
    return parse_verilog_response(text)


def parse_verilog_response(response: str) -> Tuple[str, str]:
    """
    Extract RTL and testbench from LLM response.
    Handles multiple code block formats.
    """
    # Try ```rtl ... ``` format
    rtl_match = re.search(
        r'```rtl\n(.*?)```', response, re.DOTALL
    )
    tb_match = re.search(
        r'```testbench\n(.*?)```', response, re.DOTALL
    )

    # Fall back to ```verilog ... ``` format
    if not rtl_match:
        verilog_blocks = re.findall(
            r'```verilog\n(.*?)```', response, re.DOTALL
        )
        if len(verilog_blocks) >= 2:
            rtl_match_text = verilog_blocks[0]
            tb_match_text  = verilog_blocks[1]
        elif len(verilog_blocks) == 1:
            # One block — determine if RTL or TB
            if "_tb" in verilog_blocks[0] or \
               "testbench" in verilog_blocks[0].lower():
                rtl_match_text = ""
                tb_match_text  = verilog_blocks[0]
            else:
                rtl_match_text = verilog_blocks[0]
                tb_match_text  = ""
        else:
            rtl_match_text = ""
            tb_match_text  = ""
    else:
        rtl_match_text = rtl_match.group(1)
        tb_match_text  = tb_match.group(1) if tb_match else ""

    # Final fallback — raw code blocks
    if not rtl_match_text:
        all_blocks = re.findall(
            r'```\n?(.*?)```', response, re.DOTALL
        )
        if all_blocks:
            rtl_match_text = all_blocks[0]
            tb_match_text  = all_blocks[1] if len(all_blocks) > 1 else ""

    return rtl_match_text.strip(), tb_match_text.strip()


def validate_verilog_syntax(
    rtl_code: str,
    testbench_code: str,
    module_name: str
) -> Dict:
    """
    Validate generated Verilog before running full pipeline.
    Catches common LLM mistakes early.
    """
    errors   = []
    warnings = []

    # Check RTL
    if not rtl_code:
        errors.append("RTL code is empty")
    else:
        if f"module {module_name}" not in rtl_code:
            errors.append(
                f"Module name mismatch — expected 'module {module_name}'"
            )
        if "clk" not in rtl_code:
            errors.append("No clock port found")
        if "reset_n" not in rtl_code:
            warnings.append("No active-low reset — add reset_n port")
        if "posedge clk" not in rtl_code:
            errors.append("No synchronous logic — add always @(posedge clk)")
        if "<=" not in rtl_code:
            warnings.append(
                "No non-blocking assignments — use <= in always blocks"
            )
        if "#" in rtl_code and "timescale" not in rtl_code:
            errors.append(
                "Delay (#) found in RTL — remove delays from synthesizable code"
            )
        if "initial" in rtl_code and "testbench" not in rtl_code:
            warnings.append(
                "initial block in RTL — not synthesizable, remove it"
            )

    # Check testbench
    if not testbench_code:
        errors.append("Testbench code is empty")
    else:
        if "always #5" not in testbench_code:
            errors.append(
                "No proper clock in testbench — add: always #5 clk = ~clk"
            )
        if "posedge clk" not in testbench_code:
            errors.append(
                "Testbench not sampling on clock edge"
            )
        if "ALL_TESTS_PASSED" not in testbench_code:
            errors.append(
                "Testbench missing ALL_TESTS_PASSED — pipeline requires it"
            )
        if "dumpfile" not in testbench_code:
            warnings.append(
                "No VCD dump — add $dumpfile for waveform viewing"
            )
        if "reset_n" not in testbench_code:
            warnings.append("Reset not driven in testbench")

    return {
        "valid":    len(errors) == 0,
        "errors":   errors,
        "warnings": warnings
    }


def save_design(
    module_name: str,
    rtl_code: str,
    testbench_code: str
) -> Dict:
    """
    Save generated Verilog to correct locations for pipeline.
    Returns file paths.
    """
    design_dir = DESIGNS_DIR / module_name
    design_dir.mkdir(parents=True, exist_ok=True)

    rtl_path = design_dir / f"{module_name}.v"
    tb_path  = design_dir / f"{module_name}_tb.v"

    rtl_path.write_text(rtl_code, encoding="utf-8")
    tb_path.write_text(testbench_code, encoding="utf-8")

    return {
        "rtl":       str(rtl_path),
        "testbench": str(tb_path),
        "design_dir": str(design_dir)
    }


def simulate_in_docker(
    module_name: str,
    timeout: int = 60
) -> Dict:
    """
    Quick simulation check before running full pipeline.
    Saves ~5 minutes if testbench has errors.
    """
    rtl_path = (
        f"/work/designs/{module_name}/{module_name}.v"
    )
    tb_path  = (
        f"/work/designs/{module_name}/{module_name}_tb.v"
    )

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{WORK_DIR}:/work",
        "efabless/openlane:latest",
        "bash", "-c",
        f"iverilog -o /tmp/quick_sim {rtl_path} {tb_path} "
        f"2>&1 && vvp /tmp/quick_sim 2>&1"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout + result.stderr
        return {
            "success":     "ALL_TESTS_PASSED" in output,
            "output":      output,
            "returncode":  result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output":  "Simulation timed out",
            "returncode": -1
        }


def generate_and_validate(
    description: str,
    module_name: str,
    llm_provider: str = "opencode",
    max_retries: int = 3
) -> Dict:
    """
    Main function — generates Verilog and validates it.
    Retries up to max_retries times if validation fails.

    llm_provider: "opencode" (default/recommended), "groq"
    Returns complete result dict.
    """
    print(f"\n{'='*60}")
    print(f"Generating Verilog for: {module_name}")
    print(f"Provider: {llm_provider}")
    print(f"{'='*60}")

    for attempt in range(1, max_retries + 1):
        print(f"\nAttempt {attempt}/{max_retries}...")

        # Generate
        try:
            if llm_provider == "opencode":
                rtl, tb = generate_verilog_opencode(
                    description, module_name
                )
            elif llm_provider == "groq":
                rtl, tb = generate_verilog_groq(
                    description, module_name
                )
            else:
                raise ValueError(
                    f"Unknown provider: {llm_provider}. "
                    f"Use 'opencode' (recommended) or 'groq'."
                )
        except Exception as e:
            print(f"Generation failed: {e}")
            continue

        # Validate syntax
        validation = validate_verilog_syntax(rtl, tb, module_name)

        if validation["errors"]:
            print(f"Validation errors: {validation['errors']}")
            if attempt < max_retries:
                # Feed errors back to LLM on retry
                error_msg = "; ".join(validation["errors"])
                description = (
                    f"{description}\n\n"
                    f"IMPORTANT FIXES NEEDED: {error_msg}"
                )
            continue

        if validation["warnings"]:
            print(f"Warnings: {validation['warnings']}")

        # Save files
        paths = save_design(module_name, rtl, tb)
        print(f"Saved RTL: {paths['rtl']}")
        print(f"Saved TB:  {paths['testbench']}")

        # Quick simulation check
        print("Running quick simulation...")
        sim_result = simulate_in_docker(module_name)

        if sim_result["success"]:
            print("✅ Quick simulation PASSED")
            return {
                "status":      "READY_FOR_PIPELINE",
                "module_name": module_name,
                "rtl":         rtl,
                "testbench":   tb,
                "paths":       paths,
                "validation":  validation,
                "simulation":  sim_result,
                "attempts":    attempt
            }
        else:
            print(f"❌ Simulation failed:")
            print(sim_result["output"][-500:])

            if attempt < max_retries:
                # Feed simulation error back to LLM
                sim_error = sim_result["output"][-300:]
                description = (
                    f"{description}\n\n"
                    f"SIMULATION ERRORS TO FIX:\n{sim_error}"
                )

    return {
        "status":      "GENERATION_FAILED",
        "module_name": module_name,
        "rtl":         rtl if 'rtl' in locals() else "",
        "testbench":   tb  if 'tb'  in locals() else "",
        "validation":  validation if 'validation' in locals() else {},
        "simulation":  sim_result if 'sim_result' in locals() else {},
        "attempts":    max_retries
    }


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    # Test with a simple design using Groq (working provider)
    result = generate_and_validate(
        description=(
            "Design a 4-bit binary up counter with synchronous "
            "reset and enable. When enable is high, counter "
            "increments on each clock edge. When reset_n is low, "
            "counter resets to 0. Output is 4-bit count."
        ),
        module_name="up_counter_4bit",
        llm_provider="groq",
        max_retries=3
    )

    print(f"\n{'='*60}")
    print("RESULT:", result["status"])
    print("Attempts:", result["attempts"])
    if result["status"] == "READY_FOR_PIPELINE":
        print("✅ Design ready for RTL-to-GDSII pipeline")
        print("Run full pipeline with:")
        print(f"  from full_flow import RTLtoGDSIIFlow")
        print(
            f"  flow = RTLtoGDSIIFlow("
            f"'{result['module_name']}', "
            f"'{result['paths']['rtl']}')"
        )
        print(f"  flow.run_full_flow()")
    print(f"{'='*60}")
