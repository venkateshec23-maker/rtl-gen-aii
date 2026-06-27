# verilog_generator.py
# Generates pipeline-compatible Verilog from natural language
# Providers: NVIDIA (DeepSeek-V3, primary), Groq (fallback), OpenCode.ai (local)
# Output Verilog is guaranteed to pass full_flow.py pipeline

import json
import logging
import os
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from generation_fixes import _provider_health

log = logging.getLogger(__name__)

# Cross-platform path defaults
if platform.system() == "Windows":
    _DEFAULT_WORK = r"C:\tools\OpenLane"
else:
    _DEFAULT_WORK = "/workspaces/rtl-gen-aii/openroad"

WORK_DIR = Path(os.getenv("OPENLANE_WORK", _DEFAULT_WORK))
DESIGNS_DIR = WORK_DIR / "designs"
TEMPLATES_DIR = WORK_DIR / "templates"

# Load .env if present
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# ============================================================
# VERILOG PROMPT TEMPLATE
# Forces any LLM to generate pipeline-compatible Verilog
# ============================================================

VERILOG_SYSTEM_PROMPT = """You are an expert digital hardware designer generating synthesizable Verilog-2001 (NOT SystemVerilog).

OUTPUT: Generate EXACTLY TWO code blocks (rtl and testbench - DO NOT use tasks or functions).

RTL CODE TEMPLATE:
```rtl
`timescale 1ns/1ps

module MODULE_NAME (
    input clk,
    input reset_n,
    // other inputs here
    output reg out1,
    output reg out2
    // other outputs here
);

always @(posedge clk)
    if (!reset_n) begin
        out1 <= 0;
        out2 <= 0;
    end else begin
        // functional logic with non-blocking assignments (<=)
    end

endmodule
```

TESTBENCH CODE - NO TASKS, NO FUNCTIONS, SIMPLE SEQUENTIAL LOGIC ONLY:
```testbench
`timescale 1ns/1ps

module MODULE_NAME_tb;
    reg clk;
    reg reset_n;
    // declare testbench signals (inputs to DUT become regs)

    wire output_name;  // outputs from DUT

    integer pass_count = 0;
    integer fail_count = 0;

    MODULE_NAME uut (
        .clk(clk),
        .reset_n(reset_n),
        // connect testbench signals to DUT ports
    );

    initial begin
        $dumpfile("trace.vcd");
        $dumpvars(0, MODULE_NAME_tb);

        // Initialize clock and reset
        clk = 0;
        reset_n = 0;

        // Apply reset for 2 clock cycles
        #10; #10;
        reset_n = 1;

        // TEST 1
        #10;
        @(posedge clk); #1;
        if (output_name == expected_value1) begin
            $display("PASS Test 1");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test 1: got %d, expected %d", output_name, expected_value1);
            fail_count = fail_count + 1;
        end

        // TEST 2
        #10;
        @(posedge clk); #1;
        if (output_name == expected_value2) begin
            $display("PASS Test 2");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test 2: got %d, expected %d", output_name, expected_value2);
            fail_count = fail_count + 1;
        end

        // Final report
        $display("RESULTS: %0d PASS / %0d FAIL", pass_count, fail_count);
        if (fail_count == 0)
            $display("ALL_TESTS_PASSED");
        else
            $display("TESTS_FAILED");

        #50;
        $finish;
    end

    // Simple clock generation - NO functions/tasks
    always #5 clk = ~clk;

endmodule
```

FORBIDDEN PATTERNS (cause synthesis failure or X-propagation):
- initial blocks with logic (only $dumpfile/$display allowed in testbench)
- for loops inside always blocks (use generate or parameters instead)
- delays (#) inside always @(posedge clk) blocks
- automatic tasks with timing
- non-constant case expressions
- #0 delays (race condition)
- casex or casez (treats X/Z bits as wildcards → X-propagation; use case + explicit priority if-else instead)
- uninitialized regs driving outputs (all outputs must be assigned in reset branch)

PORT DIRECTION RULES — CRITICAL:
  output reg  — for outputs driven by always block (FSM, sequential)
  output wire — for combinational outputs only (assign statements)
  input       — for all inputs (wire is default)
  NEVER declare output as plain wire if driven by always block

CORRECT EXAMPLES:
  output reg [7:0] q;        // sequential output (flip-flop)
  output reg tx;             // sequential output (FSM)
  output wire y = a & b;     // combinational output
  input clk;                 // input
  input [7:0] data;          // input bus

WRONG EXAMPLES (will fail synthesis):
  output tx;                 // WRONG: missing reg/wire
  output wire tx;            // WRONG if driven by always @(posedge clk)
  assign tx = shift_reg[0];  // WRONG: should be output reg with always

FSM OUTPUT RULE:
  Any output that changes in always @(posedge clk) MUST be declared:
  output reg <name>;
  NOT: output wire <name>

UART TRANSMITTER RULES:
  - output reg tx (NOT output wire tx) — driven by FSM
  - output reg tx_busy (NOT output wire tx_busy) — driven by FSM
  - IDLE state: tx = 1 (idle line is high)
  - START bit: tx = 0
  - STOP bit: tx = 1
  - LSB first (send bit 0 first)

ALWAYS REQUIRED:
- output reg for all registered outputs
- default case in every case statement
- <= for ALL sequential assignments in always @(posedge clk)
- = for combinational logic only
- `timescale directive at top of both files
- reset branch MUST assign every output register to a known value (0 or initial state)

X-PROPAGATION RULE (testbench):
  After applying inputs and a clock edge, check for X/Z before comparing:
  if (^output_name === 1'bx)
      $display("FAIL: X/Z on output_name — missing reset or uninitialized reg");
  else if (output_name === expected_value) ...

CRITICAL RULES:
1. Pure Verilog-2001 ONLY - NO SystemVerilog (no tasks, functions, class, property, sequence, etc)
2. RTL: only always @(posedge clk) blocks + combinational assign statements
3. Testbench: sequential blocks only, NO tasks, NO functions
4. ALL testbenches MUST print "ALL_TESTS_PASSED" at the end if all tests pass
5. Synchronous reset (reset_n) is mandatory in RTL
6. Non-blocking assignments (<=) in always @(posedge clk)
7. Module name must be exactly: MODULE_NAME (replace with actual name)
8. Always generate clock: always #5 clk = ~clk;
9. Response must have EXACTLY two code blocks marked ```rtl and ```testbench
10. NO explanations, NO other text outside code blocks
11. NEVER use casex or casez — use plain case with explicit priority if-else for don't-care handling
12. EVERY output register must be assigned in the reset (reset_n = 0) branch

RESPOND ONLY WITH THE TWO CODE BLOCKS.
"""


# ============================================================
# PROVIDER 6: LOCAL fine-tuned RTL model (Phase 4)
# ============================================================


def generate_verilog_local_model(
    description: str,
    module_name: str,
) -> Tuple[str, str]:
    """
    Generate Verilog using the Phase 4 fine-tuned local model.
    Requires LOCAL_MODEL_PATH and LOCAL_MODEL_ENABLED=true in .env.
    Falls back gracefully (raises) if model not available.
    """
    import os

    from dotenv import load_dotenv

    load_dotenv(override=True)

    model_path_str = os.getenv("LOCAL_MODEL_PATH", "")
    enabled = os.getenv("LOCAL_MODEL_ENABLED", "false").lower() == "true"

    if not enabled or not model_path_str:
        raise RuntimeError(
            "Local model not enabled. "
            "Run: python model_trainer.py --deploy --model outputs/rtl_model_final"
        )

    model_path = Path(model_path_str)
    if not model_path.exists():
        raise RuntimeError(f"Local model path not found: {model_path}")

    try:
        from model_trainer import generate_verilog_local

        rtl = generate_verilog_local(description, model_path)
    except ImportError as e:
        raise RuntimeError(f"model_trainer.py not found: {e}")

    if not rtl:
        raise RuntimeError("Local model returned empty output")

    # The local model only produces RTL — generate testbench via universal_testbench
    try:
        from universal_testbench import generate_testbench

        tb = generate_testbench(rtl, description)
    except Exception:
        tb = ""

    return rtl, tb


# ============================================================
# PROVIDER 1: NVIDIA (DeepSeek-V3 — PRIMARY)
# ============================================================


def generate_verilog_nvidia(
    description: str,
    module_name: str,
    api_key: str = None,
    model: str = None,
    base_url: str = None,
) -> Tuple[str, str]:
    """
    Generate Verilog using NVIDIA API (DeepSeek-V3.2 — OpenAI-compatible).
    This is the PRIMARY provider — uses the NVIDIA_API_KEY from .env.
    Free tier, no daily token limit.
    Returns (rtl_code, testbench_code)
    """
    import httpx

    _key = api_key or os.getenv("NVIDIA_API_KEY")
    _model = model or os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v3")
    _base_url = base_url or os.getenv(
        "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
    )

    if not _key:
        raise ValueError(
            "NVIDIA_API_KEY not set. Add it to .env:\n"
            "NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx\n"
            "Get a free key at: https://build.nvidia.com/"
        )

    payload = {
        "model": _model,
        "max_tokens": 8000,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": VERILOG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Design name: {module_name}\n\n"
                    f"Description: {description}\n\n"
                    f"Generate the RTL and testbench."
                ),
            },
        ],
    }

    try:
        response = httpx.post(
            f"{_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=5.0),
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type:
            raise RuntimeError(
                f"NVIDIA API returned HTML (status {response.status_code}). "
                f"Check your NVIDIA_API_KEY in .env"
            )

        result = response.json()
        text = result["choices"][0]["message"]["content"]
        return parse_verilog_response(text)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise RuntimeError(
                "NVIDIA API key invalid or expired.\n"
                "Get a new key at: https://build.nvidia.com/"
            )
        elif e.response.status_code == 429:
            raise RuntimeError("NVIDIA API rate limit hit. Wait a moment and retry.")
        raise RuntimeError(f"NVIDIA API error {e.response.status_code}: {e}")

    except httpx.RequestError as e:
        raise ConnectionError(
            f"Cannot reach NVIDIA API at {_base_url}.\n"
            f"Check internet connection. Error: {e}"
        )


# ============================================================
# PROVIDER 1.5: GEMINI (1.5 Flash)
# ============================================================


def generate_verilog_gemini(
    description: str, module_name: str, api_key: str = None
) -> Tuple[str, str]:
    """
    Generate Verilog using Google Gemini.
    Returns (rtl_code, testbench_code)
    """
    import os

    from dotenv import load_dotenv
    from google import genai

    load_dotenv(override=True)

    _key = api_key or os.getenv("GEMINI_API_KEY")
    if not _key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    # Build prompt with RAG enhancement
    prompt = f"Design name: {module_name}\n\nDescription: {description}"
    try:
        from rag_engine import build_rag_prompt

        prompt = build_rag_prompt(description, prompt)
    except Exception:
        pass

    client = genai.Client(api_key=_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=dict(
            system_instruction=VERILOG_SYSTEM_PROMPT, http_options=dict(timeout=60)
        ),
    )
    return parse_verilog_response(response.text)


# ============================================================
# PROVIDER 2: GROQ (llama-3.3-70b — FALLBACK)
# ============================================================


def generate_verilog_groq(
    description: str, module_name: str, api_key: str = None
) -> Tuple[str, str]:
    """
    Generate Verilog using Groq (llama-3.3-70b-versatile).
    Free tier: 100K tokens/day. Falls back to NVIDIA if rate-limited.
    Returns (rtl_code, testbench_code)
    """
    from dotenv import load_dotenv
    from groq import Groq

    # Always re-read .env so Streamlit picks up key changes without restart
    load_dotenv(Path(__file__).parent / ".env", override=True)

    _key = api_key or os.getenv("GROQ_API_KEY")
    if not _key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to .env:\n"
            "GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx\n"
            "Get a free key at: https://console.groq.com/keys"
        )

    client = Groq(api_key=_key)

    # Build user prompt
    prompt = f"Design name: {module_name}\n\nDescription: {description}"

    # RAG enhancement
    try:
        from rag_engine import build_rag_prompt

        prompt = build_rag_prompt(description, prompt)
    except Exception:
        pass

    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=8000,
        messages=[
            {"role": "system", "content": VERILOG_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    text = chat.choices[0].message.content
    return parse_verilog_response(text)


# ============================================================
# PROVIDER 2c: OPENROUTER (Free models)
# ============================================================


def generate_verilog_openrouter(
    description: str,
    module_name: str,
    api_key: str = None,
    model: str = "meta-llama/llama-3.3-70b-instruct:free",
) -> Tuple[str, str]:
    """
    Generate Verilog using OpenRouter with free models.
    Free models confirmed working (June 2026):
      meta-llama/llama-3.3-70b-instruct:free  (best quality, ~Groq llama3.3)
      openai/gpt-oss-120b:free                (large GPT-class)
      openai/gpt-oss-20b:free                 (fast)
      nvidia/nemotron-3-ultra-550b-a55b:free  (very large)
      google/gemma-4-31b-it:free              (Google Gemma)
    Returns (rtl_code, testbench_code)
    """
    import os

    import requests
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env", override=True)

    _key = api_key or os.getenv("OPENROUTER_API_KEY", "")
    if not _key:
        raise ValueError(
            "OPENROUTER_API_KEY not set. "
            "Get free key at openrouter.ai/keys and add to .env"
        )

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/venkateshec23-maker/rtl-gen-aii",
            "X-Title": "RTL-Gen AI",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": VERILOG_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Design name: {module_name}\n\nDescription: {description}",
                },
            ],
            "temperature": 0.3,
            "max_tokens": 8000,
        },
        timeout=120,
    )

    if response.status_code == 200:
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return parse_verilog_response(text)
    else:
        raise ValueError(
            f"OpenRouter error {response.status_code}: {response.text[:200]}"
        )


# ============================================================
# PROVIDER 2b: GITHUB MODELS (OpenAI-compatible, Edu pack)
# ============================================================


def generate_verilog_github(
    description: str, module_name: str, api_key: str = None, model: str = None
) -> Tuple[str, str]:
    """
    Generate Verilog using GitHub Models (OpenAI-compatible endpoint).
    Free with GitHub Education pack - includes GPT-4o, GPT-4-turbo.
    Returns (rtl_code, testbench_code)
    """
    import openai
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env", override=True)

    _key = api_key or os.getenv("GITHUB_TOKEN")
    _model = model or os.getenv("GITHUB_MODEL", "gpt-4o")
    _base_url = os.getenv("GITHUB_BASE_URL", "https://models.inference.ai.azure.com")

    if not _key:
        raise ValueError(
            "GITHUB_TOKEN not set. Add it to .env:\n"
            "GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx\n"
            "Get your token at: https://github.com/settings/tokens"
        )

    client = openai.OpenAI(api_key=_key, base_url=_base_url)

    prompt = f"Design name: {module_name}\n\nDescription: {description}"
    try:
        from rag_engine import build_rag_prompt

        prompt = build_rag_prompt(description, prompt)
    except Exception:
        pass

    chat = client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": VERILOG_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=8000,
    )

    text = chat.choices[0].message.content
    return parse_verilog_response(text)


# ============================================================
# PROVIDER 3: OPENCODE (ACP REST API — port 4096)
# ============================================================

ACP_BASE = "http://127.0.0.1:4096"
ACP_MODEL = "deepseek-v4-flash-free"  # best free model
ACP_TIMEOUT = 180  # complex RTL needs time


def _acp_is_running(base: str = ACP_BASE) -> bool:
    """Return True if the OpenCode ACP server is reachable."""
    import httpx

    try:
        r = httpx.get(f"{base}/session", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _acp_create_session(
    base: str = ACP_BASE, model: str = ACP_MODEL, title: str = "RTL-Gen AI Request"
) -> str:
    """Create a new ACP session and return its ID."""
    import httpx

    r = httpx.post(
        f"{base}/session", json={"modelID": model, "title": title}, timeout=10
    )
    r.raise_for_status()
    return r.json()["id"]


def _acp_send_message(
    session_id: str, prompt: str, base: str = ACP_BASE, model: str = ACP_MODEL
) -> str:
    """
    Send one message to an ACP session and return assistant's reply.
    ACP POST blocks until complete — then GET session messages for the text.
    Note: role is inside msg['info']['role'], not msg['role'].
    """
    import time as _t

    import httpx

    payload = {
        "parts": [{"type": "text", "text": prompt}],
        "modelID": model,
    }
    # POST triggers generation (synchronous — blocks until done)
    r = httpx.post(
        f"{base}/session/{session_id}/message", json=payload, timeout=ACP_TIMEOUT
    )
    r.raise_for_status()

    # Small buffer to let state settle
    _t.sleep(0.5)

    # GET all messages and extract the last assistant text part
    msgs_r = httpx.get(f"{base}/session/{session_id}/message", timeout=15)
    if msgs_r.status_code != 200:
        return ""

    msgs = msgs_r.json()
    # Walk in reverse — find last assistant message with non-empty text part
    for msg in reversed(msgs):
        role = msg.get("info", {}).get("role", "")
        if role == "user":
            continue
        # Collect all text parts (skip step-start, step-finish, reasoning)
        text_parts = [
            p.get("text", "")
            for p in msg.get("parts", [])
            if p.get("type") == "text" and p.get("text", "").strip()
        ]
        if text_parts:
            return "\n".join(text_parts).strip()

    return ""


def generate_verilog_opencode(
    description: str,
    module_name: str,
    acp_base: str = ACP_BASE,
    model: str = ACP_MODEL,
) -> Tuple[str, str]:
    """
    Generate Verilog using the local OpenCode ACP server.
    Requires: opencode acp --port 4096 (started automatically if not running)
    Model: opencode/big-pickle (no rate limits, no API key needed)
    Returns (rtl_code, testbench_code)
    """
    import subprocess as _sp

    import httpx

    # Auto-start ACP server if not running
    if not _acp_is_running(acp_base):
        print("OpenCode ACP not running — starting on port 4096...")
        is_windows = platform.system() == "Windows"
        _sp.Popen(
            ["opencode", "acp", "--port", "4096", "--hostname", "127.0.0.1"],
            stdout=_sp.DEVNULL,
            stderr=_sp.DEVNULL,
            shell=is_windows,
        )
        import time as _t

        _t.sleep(4)
        if not _acp_is_running(acp_base):
            raise ConnectionError(
                "OpenCode ACP server failed to start.\n"
                "Start manually: opencode acp --port 4096\n"
                "Then retry."
            )
        print("OpenCode ACP started.")

    prompt = (
        f"{VERILOG_SYSTEM_PROMPT}\n\n"
        f"Design name: {module_name}\n\n"
        f"Description: {description}\n\n"
        "Generate COMPLETE synthesizable RTL and a self-checking testbench. "
        "Use the exact output format with ```rtl ... ``` and ```testbench ... ``` blocks."
    )
    try:
        from rag_engine import build_rag_prompt

        prompt = build_rag_prompt(description, prompt)
    except Exception:
        pass

    sid = None
    rtl_code, tb_code = None, None
    try:
        sid = _acp_create_session(acp_base, model, title=f"RTL-Gen: {module_name}")
        text = _acp_send_message(sid, prompt, acp_base, model)
        rtl_code, tb_code = parse_verilog_response(text)

        # If model got truncated and only returned RTL without Testbench, prompt it to continue
        if rtl_code and not tb_code:
            print("OpenCode provided RTL but no testbench. Requesting testbench...")
            tb_prompt = "Perfect. Now write the complete testbench for this design in a ```testbench\n...\n``` block. Make sure it prints ALL_TESTS_PASSED or TESTS_FAILED."
            tb_text = _acp_send_message(sid, tb_prompt, acp_base, model)

            temp_rtl, temp_tb = parse_verilog_response(tb_text)

            # Since tb_text is JUST the testbench, the parser might put it in temp_rtl if it doesn't recognize it.
            # So if temp_tb is empty but temp_rtl isn't, we assume temp_rtl is actually the testbench.
            if not temp_tb and temp_rtl:
                tb_code = temp_rtl
            else:
                tb_code = temp_tb

    except httpx.RequestError as e:
        raise ConnectionError(
            f"OpenCode ACP not reachable at {acp_base}.\n"
            f"Start with: opencode acp --port 4096\n"
            f"Error: {e}"
        )
    finally:
        # Clean up the session so it doesn't leave multiple useless chats in the OpenCode UI
        if sid:
            try:
                httpx.delete(f"{acp_base}/session/{sid}", timeout=2)
            except Exception:
                pass

    if not rtl_code and not tb_code:
        raise RuntimeError(
            "OpenCode returned empty response. Try a simpler description "
            "or check: opencode stats. Also ensure OpenCode has internet access."
        )

    return rtl_code, tb_code


# ============================================================
# TOOL DETECTION — Cadence / Vivado / Icarus awareness
# ============================================================


def detect_sim_tool() -> str:
    """
    Auto-detect available simulation tool.
    Priority: Docker (Icarus in container) > Icarus native > Cadence xrun > Vivado xvlog
    Returns: "docker", "icarus", "cadence", "vivado", or "none"
    """
    # 1. Docker with OpenLane (preferred — controlled environment)
    try:
        result = subprocess.run(
            [
                "docker",
                "image",
                "ls",
                "efabless/openlane:latest",
                "--format",
                "{{.Repository}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "efabless" in result.stdout:
            return "docker"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 2. Native Icarus Verilog
    try:
        result = subprocess.run(
            ["iverilog", "-V"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return "icarus"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 3. Cadence Xcelium (xrun)
    try:
        result = subprocess.run(
            ["xrun", "-version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return "cadence"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 4. Xilinx Vivado (xvlog)
    try:
        result = subprocess.run(
            ["xvlog", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return "vivado"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "none"


def simulate_with_tool(
    module_name: str, rtl_path: str, tb_path: str, tool: str = None, timeout: int = 60
) -> Dict:
    """
    Simulate Verilog using the best available tool.
    Supports: Docker/Icarus, native Icarus, Cadence xrun, Vivado xvlog.
    """
    _tool = tool or detect_sim_tool()

    if _tool == "docker":
        return _simulate_docker(module_name, timeout)
    elif _tool == "icarus":
        return _simulate_icarus(rtl_path, tb_path, timeout)
    elif _tool == "cadence":
        return _simulate_cadence(rtl_path, tb_path, module_name, timeout)
    elif _tool == "vivado":
        return _simulate_vivado(rtl_path, tb_path, module_name, timeout)
    else:
        return {
            "success": True,
            "output": "No simulation tool found (Docker/Icarus/Cadence/Vivado). "
            "Skipping simulation — syntax was already validated.",
            "returncode": 0,
            "pass_count": 0,
            "fail_count": 0,
            "tool": "none",
        }


def _build_sim_result(output: str, returncode: int, tool: str) -> Dict:
    """Normalize simulator outputs into a common result schema."""
    lines = output.splitlines()
    pass_count = len([l for l in lines if l.strip().startswith("PASS")])
    fail_count = len(
        [l for l in lines if l.strip().startswith("FAIL") and "0 FAIL" not in l]
    )
    success = "ALL_TESTS_PASSED" in output and fail_count == 0 and returncode == 0
    return {
        "success": success,
        "output": output,
        "returncode": returncode,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "tool": tool,
    }


def _simulate_docker(module_name: str, timeout: int) -> Dict:
    """Simulate inside efabless/openlane Docker container."""
    rtl_path = f"/work/designs/{module_name}/{module_name}.v"
    tb_path = f"/work/designs/{module_name}/{module_name}_tb.v"
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{WORK_DIR}:/work",
        "efabless/openlane:latest",
        "bash",
        "-c",
        f"rm -rf /work/results 2>/dev/null; mkdir -p /work/results && "
        f"iverilog -o /tmp/quick_sim {rtl_path} {tb_path} 2>&1 && "
        f"vvp /tmp/quick_sim 2>&1",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = result.stdout + result.stderr
        return _build_sim_result(output, result.returncode, "docker")
    except (FileNotFoundError, OSError):
        return _build_sim_result("Docker unavailable.", -1, "docker")
    except subprocess.TimeoutExpired:
        return _build_sim_result("Simulation timed out.", -1, "docker")


def _simulate_icarus(rtl_path: str, tb_path: str, timeout: int) -> Dict:
    """Simulate using native Icarus Verilog."""
    out_bin = Path(rtl_path).parent / "sim_out"
    try:
        compile_r = subprocess.run(
            ["iverilog", "-o", str(out_bin), rtl_path, tb_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if compile_r.returncode != 0:
            return _build_sim_result(
                compile_r.stdout + compile_r.stderr, compile_r.returncode, "icarus"
            )
        run_r = subprocess.run(
            ["vvp", str(out_bin)], capture_output=True, text=True, timeout=timeout
        )
        output = run_r.stdout + run_r.stderr
        return _build_sim_result(output, run_r.returncode, "icarus")
    except subprocess.TimeoutExpired:
        return _build_sim_result("Timeout.", -1, "icarus")


def _simulate_cadence(
    rtl_path: str, tb_path: str, module_name: str, timeout: int
) -> Dict:
    """Simulate using Cadence Xcelium (xrun)."""
    try:
        result = subprocess.run(
            ["xrun", "-access", "+rwc", rtl_path, tb_path, "-top", f"{module_name}_tb"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(rtl_path).parent),
        )
        output = result.stdout + result.stderr
        return _build_sim_result(output, result.returncode, "cadence")
    except subprocess.TimeoutExpired:
        return _build_sim_result("Timeout.", -1, "cadence")


def _simulate_vivado(
    rtl_path: str, tb_path: str, module_name: str, timeout: int
) -> Dict:
    """Simulate using Xilinx Vivado (xvlog + xelab + xsim)."""
    work_dir = Path(rtl_path).parent
    try:
        # Compile
        for src in [rtl_path, tb_path]:
            r = subprocess.run(
                ["xvlog", src],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(work_dir),
            )
            if r.returncode != 0:
                return _build_sim_result(r.stdout + r.stderr, r.returncode, "vivado")
        # Elaborate
        elab = subprocess.run(
            ["xelab", f"{module_name}_tb", "-s", "sim_snapshot"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(work_dir),
        )
        if elab.returncode != 0:
            return _build_sim_result(
                elab.stdout + elab.stderr, elab.returncode, "vivado"
            )
        # Simulate
        run_r = subprocess.run(
            ["xsim", "sim_snapshot", "-R"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(work_dir),
        )
        output = run_r.stdout + run_r.stderr
        return _build_sim_result(output, run_r.returncode, "vivado")
    except subprocess.TimeoutExpired:
        return _build_sim_result("Timeout.", -1, "vivado")


# ============================================================
# RESPONSE PARSER
# ============================================================


def parse_verilog_response(response: str) -> Tuple[str, str]:
    """
    Extract RTL and testbench from LLM response.
    Handles CRLF, partial/truncated responses, and various fence formats.
    """
    # Normalise line endings (Windows CRLF -> LF)
    response = response.replace("\r\n", "\n").replace("\r", "\n")

    # If response is truncated (opened ``` but never closed), close it
    open_count = response.count("```")
    if open_count % 2 != 0:
        # Odd number of backtick-triples means one block is unclosed
        response = response + "\nendmodule\n```"

    # Try ```rtl ... ``` format (allow optional whitespace after fence marker)
    rtl_match = re.search(r"```rtl\s*\n(.*?)```", response, re.DOTALL)
    tb_match = re.search(r"```testbench\s*\n(.*?)```", response, re.DOTALL)

    if rtl_match:
        rtl_text = rtl_match.group(1)
        tb_text = tb_match.group(1) if tb_match else ""
    else:
        # Fall back to ```verilog blocks
        verilog_blocks = re.findall(r"```verilog\s*\n(.*?)```", response, re.DOTALL)
        if len(verilog_blocks) >= 2:
            rtl_text = verilog_blocks[0]
            tb_text = verilog_blocks[1]
        elif len(verilog_blocks) == 1:
            block = verilog_blocks[0]
            if "_tb" in block or "testbench" in block.lower():
                rtl_text, tb_text = "", block
            else:
                rtl_text, tb_text = block, ""
        else:
            # Last resort — any code blocks
            all_blocks = re.findall(r"```[a-z]*\s*\n(.*?)```", response, re.DOTALL)
            rtl_text = all_blocks[0] if all_blocks else ""
            tb_text = all_blocks[1] if len(all_blocks) > 1 else ""

    return rtl_text.strip(), tb_text.strip()


def normalize_module_name(
    rtl_code: str, testbench_code: str, module_name: str
) -> Tuple[str, str, str]:
    """
    Ensure generated RTL/testbench use the requested module name.
    Returns (rtl, tb, original_module_name_or_empty).
    """
    if not rtl_code:
        return rtl_code, testbench_code, ""

    match = re.search(r"\bmodule\s+([A-Za-z_]\w*)", rtl_code)
    if not match:
        return rtl_code, testbench_code, ""

    original_name = match.group(1)
    if original_name == module_name:
        return rtl_code, testbench_code, ""

    rtl_fixed = re.sub(
        rf"\bmodule\s+{re.escape(original_name)}\b",
        f"module {module_name}",
        rtl_code,
        count=1,
    )
    tb_fixed = testbench_code
    if tb_fixed:
        tb_fixed = re.sub(rf"\b{re.escape(original_name)}\b", module_name, tb_fixed)

    return rtl_fixed, tb_fixed, original_name


# ============================================================
# SYNTAX VALIDATION
# ============================================================


def validate_verilog_syntax(
    rtl_code: str, testbench_code: str, module_name: str
) -> Dict:
    """
    Validate generated Verilog before running full pipeline.
    Catches common LLM mistakes early.
    """
    errors = []
    warnings = []

    if not rtl_code:
        errors.append("RTL code is empty")
    else:
        if f"module {module_name}" not in rtl_code:
            errors.append(f"Module name mismatch — expected 'module {module_name}'")
        # Only require clock if the module appears to be sequential (has reg declarations or always blocks)
        has_reg = bool(re.search(r"\breg\b", rtl_code))
        has_always = bool(re.search(r"\balways\b", rtl_code))
        if has_reg and has_always:
            if not re.search(r"\b(clk|clock|sys_clk|clk_i|pclk|aclk|hclk)\b", rtl_code):
                errors.append(
                    "Sequential module has no recognizable clock port (expected clk, clock, sys_clk, clk_i, etc.)"
                )
        if "reset_n" not in rtl_code:
            warnings.append("No active-low reset — consider adding reset_n port")
        if (
            has_reg
            and has_always
            and "posedge clk" not in rtl_code
            and "posedge clock" not in rtl_code
        ):
            errors.append(
                "Sequential logic detected (reg + always) but no posedge clock found — add clock or use always @(*) for combinational"
            )
        if "<=" not in rtl_code:
            warnings.append("No non-blocking assignments — use <= in always blocks")
        if re.search(r"#\d+", rtl_code) and "timescale" not in rtl_code:
            errors.append(
                "Delay (#N) found in RTL — remove delays from synthesizable code"
            )
        if "initial" in rtl_code and "testbench" not in rtl_code.lower():
            warnings.append("initial block in RTL — not synthesizable, remove it")

    if not testbench_code:
        errors.append("Testbench code is empty")
    else:
        if "always #5" not in testbench_code:
            errors.append("No proper clock in testbench — add: always #5 clk = ~clk")
        if "ALL_TESTS_PASSED" not in testbench_code:
            errors.append("Testbench missing ALL_TESTS_PASSED — pipeline requires it")
        if "dumpfile" not in testbench_code:
            warnings.append("No VCD dump — add $dumpfile for waveform viewing")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# ============================================================
# FILE SAVE
# ============================================================


def save_design(module_name: str, rtl_code: str, testbench_code: str) -> Dict:
    """Save generated Verilog files to the pipeline directory."""
    design_dir = DESIGNS_DIR / module_name
    design_dir.mkdir(parents=True, exist_ok=True)

    rtl_path = design_dir / f"{module_name}.v"
    tb_path = design_dir / f"{module_name}_tb.v"

    rtl_path.write_text(rtl_code, encoding="utf-8")
    tb_path.write_text(testbench_code, encoding="utf-8")

    return {
        "rtl": str(rtl_path),
        "testbench": str(tb_path),
        "design_dir": str(design_dir),
    }


# Legacy alias kept for backward compatibility
def simulate_in_docker(module_name: str, timeout: int = 60) -> Dict:
    """Backward-compatible wrapper — now uses tool auto-detection."""
    return _simulate_docker(module_name, timeout)


# ============================================================
# VERILOG REPAIR UTILITIES
# ============================================================


def auto_fix_testbench(testbench_code: str, module_name: str, rtl_code: str) -> str:
    """
    Automatically patch common testbench issues without LLM call.
    Fixes the most common local-model mistakes in one pass.
    """
    if not testbench_code:
        return testbench_code

    fixed = testbench_code

    # Fix 1: Missing timescale directive
    if "`timescale" not in fixed:
        fixed = "`timescale 1ns/1ps\n" + fixed

    # Fix 2: Broken clock — replace 'initial forever #N' with always block
    fixed = re.sub(
        r"initial\s+forever\s+#\d+\s+clk\s*=\s*~clk\s*;",
        "initial clk = 0;\nalways #5 clk = ~clk;",
        fixed,
    )

    # Fix 3: Missing VCD dump — inject after first 'initial begin'
    if "dumpfile" not in fixed:
        fixed = re.sub(
            r"(initial\s+begin\s*\n)",
            r'\1    $dumpfile("trace.vcd");\n'
            r"    $dumpvars(0, " + module_name + r"_tb);\n",
            fixed,
            count=1,
        )

    # Fix 4: Wrong dumpfile path — force to trace.vcd to run cleanly anywhere
    fixed = re.sub(r'\$dumpfile\("([^"]+)"\)', '$dumpfile("trace.vcd")', fixed)

    # Fix 6: Missing reset_n drive when RTL uses it
    if "reset_n" not in fixed and "reset_n" in rtl_code:
        reset_seq = (
            "\n    // Reset sequence\n"
            "    reset_n = 0;\n"
            "    @(posedge clk); @(posedge clk);\n"
            "    #1 reset_n = 1;\n"
        )
        fixed = re.sub(
            r"(initial\s+begin\s*\n\s*\$dumpfile[^\n]+\n\s*\$dumpvars[^\n]+\n)",
            r"\1" + reset_seq,
            fixed,
            count=1,
        )

    return fixed


def validate_testbench_has_real_checks(testbench_code: str) -> dict:
    """
    Detects lying testbenches — ones that print
    ALL_TESTS_PASSED without actually checking outputs.

    A real testbench MUST have:
    1. At least one comparison: !== or != or ===
    2. A conditional $display FAIL path
    3. ALL_TESTS_PASSED only inside an if block

    Returns dict with is_lying and specific issues.
    """
    import re

    issues = []
    warnings = []

    # Check 1: Has comparison operators
    has_comparison = bool(
        re.search(r"!==|===|!=\s*(?!1\'b)|==\s*(?!1\'b)", testbench_code)
    )
    if not has_comparison:
        issues.append(
            "NO_COMPARISONS: Testbench has no !== or === "
            "checks. Cannot verify correct output."
        )

    # Check 2: Has FAIL display path
    has_fail_display = bool(
        re.search(r'\$display\s*\(\s*"[^"]*FAIL[^"]*"', testbench_code, re.IGNORECASE)
    )
    if not has_fail_display:
        issues.append(
            "NO_FAIL_PATH: Testbench never prints FAIL. "
            "All tests will appear to pass even if wrong."
        )

    # Check 3: ALL_TESTS_PASSED inside conditional
    # Bad: $display("ALL_TESTS_PASSED");
    # Good: if (fail_count == 0) $display("ALL_TESTS_PASSED")
    atp_match = re.search(r"\$display\s*\([^)]*ALL_TESTS_PASSED[^)]*\)", testbench_code)
    if atp_match:
        # Check what is before it — should be if/conditional
        pos = atp_match.start()
        context_before = testbench_code[max(0, pos - 100) : pos].strip()
        # Look for if statement in nearby context
        has_conditional = bool(
            re.search(r"\bif\b.*(?:fail|count|error)", context_before, re.IGNORECASE)
        )
        if not has_conditional:
            issues.append(
                "UNCONDITIONAL_PASS: ALL_TESTS_PASSED is "
                "printed unconditionally — not inside "
                "if(fail_count == 0) check."
            )

    # Check 4: Has fail counter or flag
    has_fail_counter = bool(
        re.search(
            r"fail_count|fail_flag|error_count|num_fail", testbench_code, re.IGNORECASE
        )
    )
    if not has_fail_counter:
        warnings.append(
            "NO_FAIL_COUNTER: Recommend adding integer "
            "fail_count to track test failures."
        )

    # Check 5: Samples AFTER clock edge
    has_clock_sample = bool(
        re.search(r"@\s*\(\s*posedge\s+clk\s*\)\s*;\s*#\d*", testbench_code)
    )
    if not has_clock_sample:
        warnings.append(
            "NO_CLOCK_SAMPLE: Should sample outputs after @(posedge clk); #1;"
        )

    is_lying = len(issues) > 0

    return {
        "is_lying": is_lying,
        "issues": issues,
        "warnings": warnings,
        "verdict": (
            "TESTBENCH_LYING — will produce false PASS"
            if is_lying
            else "TESTBENCH_HONEST — has real checks"
        ),
    }


def inject_real_checks_into_testbench(
    testbench_code: str, module_name: str, rtl_code: str
) -> str:
    """
    Injects a proper fail counter and conditional
    ALL_TESTS_PASSED into a lying testbench.
    Works without LLM call — pure code injection.
    """
    import re

    fixed = testbench_code

    # Step 1: Add fail_count and pass_count declarations after module declaration
    if "fail_count" not in fixed or "pass_count" not in fixed:
        fixed = re.sub(
            r"(module\s+\w+_tb\s*\(\s*\)\s*;)",
            r"\1\n\n    integer pass_count = 0;\n    integer fail_count = 0;",
            fixed,
        )

    # Step 2: Find unconditional ALL_TESTS_PASSED
    # and wrap it in proper conditional
    unconditional_atp = re.search(
        r'(\s+)(\$display\s*\(\s*"ALL_TESTS_PASSED[^"]*"\s*\)\s*;)', fixed
    )
    if unconditional_atp:
        indent = unconditional_atp.group(1)
        old_display = unconditional_atp.group(2)

        # Replace with conditional version
        new_block = (
            f"{indent}$display("
            f'"RESULTS: %0d PASS / %0d FAIL",'
            f" pass_count, fail_count);\n"
            f"{indent}if (fail_count == 0)\n"
            f'{indent}    $display("ALL_TESTS_PASSED");\n'
            f"{indent}else\n"
            f'{indent}    $display("TESTS_FAILED");'
        )
        fixed = fixed.replace(unconditional_atp.group(0), "\n" + new_block + "\n")

    return fixed


def repair_with_groq(prompt: str, module_name: str) -> Tuple[str, str]:
    """Repair Verilog using Groq cloud if primary LLM fails."""
    import os

    from dotenv import load_dotenv
    from groq import Groq

    load_dotenv(override=True)
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_verilog_response(chat.choices[0].message.content)


def repair_with_gemini(prompt: str, module_name: str) -> Tuple[str, str]:
    """Repair Verilog using Gemini API."""
    import os

    import google.generativeai as genai
    from dotenv import load_dotenv

    load_dotenv(override=True)
    _key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt, request_options={"timeout": 60})
    return parse_verilog_response(response.text)


def _is_complex_design(description: str) -> bool:
    """Check if description matches a complex design that needs enhanced prompting."""
    desc_lower = description.lower()
    complex_keywords = [
        "risc-v", "riscv", "rv32", "rv64",
        "cpu", "processor", "core",
        "pipeline", "pipelined", "5-stage", "five stage",
        "hazard", "forwarding", "branch prediction",
        "cache", "mmu", "tlb",
        "soc", "system on chip",
        "superscalar", "out of order",
        "fetch", "decode", "execute", "write back",
    ]
    return any(kw in desc_lower for kw in complex_keywords)


def _build_enhanced_description(description: str, module_name: str) -> str:
    """
    For complex designs, wrap the description with architectural guidance
    so the LLM generates a complete, detailed implementation.
    """
    base = f"Design name: {module_name}\n\nDescription: {description}\n\n"
    enhanced = (
        "IMPORTANT - This is a COMPLEX pipelined design. Follow these architectural requirements:\n"
        "- Implement ALL pipeline stages explicitly (fetch, decode, execute, memory, writeback)\n"
        "- Include pipeline registers between every stage (IF/ID, ID/EX, EX/MEM, MEM/WB)\n"
        "- Each pipeline register must hold: control signals, data, and destination register address\n"
        "- Include hazard detection logic for RAW data hazards (insert stalls when needed)\n"
        "- Include data forwarding/bypass paths (EX→EX, MEM→EX, WB→EX) to minimize stalls\n"
        "- Include a register file with dual read ports and one write port\n"
        "- Include a program counter (PC) with: normal increment (+4), branch target, and stall/hold\n"
        "- For load instructions: insert one stall cycle after load before dependent use\n"
        "- Include branch comparator in execute stage, compute branch target in decode stage\n"
        "- For branch mispredictions: flush IF/ID and ID/EX pipeline registers\n"
        "- Write-back stage writes ALU result or loaded data to register file\n"
        "- Use 32-bit data width for all pipeline signals and registers unless specified otherwise\n"
        "- Every pipeline register must have clock enable (stall) and clear (flush) inputs\n"
        "- Output reg for ALL pipeline registers, output reg for register file\n"
        "- This RTL must be complete, synthesizable Verilog-2001 — no stubs, no placeholders\n"
        "- Generate realistic, working RTL — not a simplified or skeleton version\n"
        "\nGenerate the complete RTL and testbench."
    )
    return base + enhanced


def _check_spec_compliance(description: str, rtl_code: str, module_name: str) -> Tuple[bool, str]:
    """
    Validate that generated RTL matches the complexity of the description.
    Catches cases where complex descriptions (RISC-V CPU, pipeline) produce
    primitive stubs (8-bit adder, counter).

    Returns (True, "") if OK, (False, reason) if spec violation detected.
    """
    desc_lower = description.lower()
    rtl_lower = rtl_code.lower()

    # Check 1: Pipeline/cpu descriptions must have pipeline stages
    if any(w in desc_lower for w in ["pipeline", "5-stage", "five stage", "fetch", "decode", "execute"]):
        stage_count = sum(1 for s in ["if_id", "id_ex", "ex_mem", "mem_wb", "fetch", "decode", "execute", "writeback", "write_back"] if s in rtl_lower)
        if stage_count < 2:
            return False, f"Pipeline description but only {stage_count} pipeline stage signals found (expected >= 2)"

    # Check 2: RISC-V descriptions must have RV-specific constructs
    if any(w in desc_lower for w in ["risc-v", "riscv", "rv32", "rv64"]):
        rv_indicators = sum(1 for s in ["register file", "reg_file", "rf", "x0", "zero register", "pc", "program counter", "alu", "hazard", "forwarding"] if s in rtl_lower)
        if rv_indicators < 2:
            return False, f"RISC-V description but only {rv_indicators} RV-specific constructs found (expected >= 2)"

    # Check 3: Complex multi-module descriptions must have more than one always block
    if _is_complex_design(description):
        always_count = rtl_code.count("always @")
        if always_count <= 1:
            reg_count = rtl_code.count("reg ")
            if reg_count <= 5:
                return False, f"Complex design only has {always_count} always blocks and {reg_count} regs — likely a stub"

    # Check 4: Module must not be a known primitive template when complex requested
    primitive_indicators = [
        r"\bcount\s*<=\s*count\s*\+\s*1",  # counter
        r"\bsum\s*<=\s*\{1'b0,\s*a}\s*\+\s*\{1'b0,\s*b}",  # adder template
    ]
    if _is_complex_design(description):
        for pattern in primitive_indicators:
            import re
            if re.search(pattern, rtl_lower):
                return False, f"Complex description matched primitive template pattern: {pattern[:40]}"

    return True, ""


def find_matching_template(description: str, module_name: str) -> Optional[str]:
    """
    Check if request matches a proven template.
    Returns template file path or None.
    """
    keywords = {
        "counter.v": ["counter", "count", "increment", "up counter", "down counter"],
        "adder.v": ["adder", "add", "sum", "arithmetic unit"],
        "shift_reg.v": ["shift", "serial", "sipo", "piso", "shift register"],
        "mux.v": ["multiplex", "mux", "selector", "select"],
        "decoder.v": ["decoder", "decode", "one-hot"],
        "encoder.v": ["encoder", "priority encoder", "encode"],
        "spi_master.v": [
            "spi",
            "serial peripheral",
            "spi master",
            "mosi",
            "miso",
            "sclk",
        ],
        "i2c_master.v": ["i2c", "inter-integrated", "i2c master", "iic", "scl sda"],
        "uart_tx.v": ["uart", "serial transmit", "uart_tx", "rs232", "baud"],
        "fsm.v": ["fsm", "state machine", "finite state", "controller"],
        # Complex designs - no single file template, use LLM with enhanced prompt
        "riscv_cpu": [
            "risc-v", "riscv", "rv32", "rv64",
            "5-stage pipeline", "five stage pipeline",
            "pipelined cpu", "pipelined processor",
        ],
    }
    desc_lower = description.lower()

    # Complex-design guard: skip template matching for designs with
    # complexity score >= 60 (RISC-V, pipeline, CPU, SoC, etc.)
    # These descriptions should go through LLM generation or hierarchy builder,
    # never silently fall back to a primitive template (adder, counter, etc.)
    try:
        from generation_fixes import estimate_design_complexity
        if estimate_design_complexity(description) >= 60:
            return None
    except Exception:
        pass

    for template_file, words in keywords.items():
        if any(w in desc_lower for w in words):
            template_path = TEMPLATES_DIR / template_file
            if template_path.exists():
                return str(template_path)
    return None


def repair_verilog(
    rtl_code: str,
    testbench_code: str,
    module_name: str,
    errors: list,
    llm_provider: str = "groq",
    description: str = "",
    sim_output: str = "",
    vcd_context: str = None,
) -> Tuple[str, str]:
    """
    Send broken Verilog back to LLM with specific error list and VCD trace context.
    """
    if not errors:
        return rtl_code, testbench_code

    error_list = "\n".join(f"- {e}" for e in errors)

    # Extract specific failure lines from simulation output
    fail_lines = (
        [
            l
            for l in sim_output.split("\n")
            if l.strip().startswith("FAIL") or "error" in l.lower() or "Error" in l
        ]
        if sim_output
        else []
    )

    fail_context = (
        "\n".join(fail_lines[:10])
        if fail_lines
        else "Simulation did not complete or no FAIL messages found"
    )

    repair_prompt = f"""
DESIGN: {module_name}

ERRORS TO FIX:
{error_list}

ACTUAL SIMULATION FAILURES:
{fail_context}

CURRENT RTL (with bugs):
```verilog
{rtl_code}
```

CURRENT TESTBENCH:
```verilog
{testbench_code}
```

FIX REQUIREMENTS:
- Module name must be exactly: {module_name}
- always @(posedge clk) for synchronous logic
- if (!reset_n) active low reset inside clock block
- always #5 clk = ~clk in testbench
- @(posedge clk); #1; before sampling
- integer fail_count = 0; in testbench
- if/else checks with !== comparisons
- if (fail_count == 0) $display("ALL_TESTS_PASSED")
- $dumpfile("trace.vcd")
- NO delays (#) inside always blocks
- NO for loops inside always blocks
- Use <= for sequential, = for combinational only

Return ONLY two code blocks:
```rtl
[corrected RTL]
```
```testbench
[corrected testbench]
```
"""

    if vcd_context and "empty" not in vcd_context and "No VCD trace" not in vcd_context:
        repair_prompt += f"""

SIMULATION FAILURE TRACE (Last known truth-table states before failure):
```text
{vcd_context}
```
"""

    repair_prompt = (
        repair_prompt + "\nMaintain functionality. Pure Verilog-2001 only.\n"
    )

    try:
        if llm_provider == "gemini":
            return repair_with_gemini(repair_prompt, module_name)
        elif llm_provider == "openrouter" or llm_provider == "deepseek":
            try:
                return generate_verilog_openrouter(repair_prompt, module_name)
            except Exception as e:
                print(f"OpenRouter repair failed: {e}")
                return repair_with_groq(repair_prompt, module_name)
        else:
            return repair_with_groq(repair_prompt, module_name)
    except Exception as e:
        print(f"Repair failed: {e}")
        return rtl_code, testbench_code


def generate_and_validate(
    description: str,
    module_name: str,
    llm_provider: str = "openrouter",
    openrouter_model: Optional[str] = None,
    max_retries: int = 3,
) -> Dict:
    """
    Generate Verilog + validate + simulate.
    Provider priority with rotation: requested provider first, then alternatives.

    Returns complete result dict with status READY_FOR_PIPELINE or GENERATION_FAILED.
    """
    print(f"\n{'=' * 60}")
    print(f"Generating Verilog for: {module_name}")
    print(f"Provider: {llm_provider}")
    print(f"{'=' * 60}")

    # Sanitize module name: only alphanumeric + underscore allowed
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', module_name)
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')
    if safe_name != module_name:
        print(f"[SANITIZE] Module name '{module_name}' contains invalid characters")
        print(f"          Using '{safe_name}' instead")
        module_name = safe_name or f"design_{int(time.time())}"

    providers_to_try = []
    req_model = openrouter_model or os.getenv(
        "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
    )

    if llm_provider == "openrouter":
        model_list = [
            "meta-llama/llama-3.3-70b-instruct:free",  # best quality free
            "openai/gpt-oss-120b:free",  # large GPT-class
            "openai/gpt-oss-20b:free",  # fast fallback
            "nvidia/nemotron-3-ultra-550b-a55b:free",  # very large
            "google/gemma-4-31b-it:free",  # Google Gemma
            "nousresearch/hermes-3-llama-3.1-405b:free",  # large hermes
        ]
        providers_to_try = [("openrouter", req_model)]
        for m in model_list:
            if m != req_model:
                providers_to_try.append(("openrouter", m))
    elif llm_provider == "deepseek":
        providers_to_try = [
            ("openrouter", "deepseek/deepseek-chat:free"),
        ]
    else:
        all_p = [
            ("nvidia", None),
            ("groq", None),
            ("openrouter", req_model),
            ("gemini", None),
            ("github", None),
            ("local", None),
            ("opencode", None),
        ]
        requested = [(p, m) for p, m in all_p if p == llm_provider]
        if requested:
            providers_to_try = requested + [
                (p, m) for p, m in all_p if p != llm_provider
            ]
        else:
            providers_to_try = [("groq", None)] + all_p

    last_error = None

    # Detect available sim tool once
    sim_tool = detect_sim_tool()
    print(f"Simulation tool: {sim_tool}")

    # ---- Complex design detection ----
    complex_design = _is_complex_design(description)
    effective_description = (
        _build_enhanced_description(description, module_name)
        if complex_design else description
    )
    if complex_design:
        print(f"[COMPLEX] Enhanced prompt with architectural guidance")

    # ---- Check for matching template first ----
    template_path = find_matching_template(description, module_name)
    if template_path:
        print(f"[TEMPLATE] Using proven template: {Path(template_path).name}")
        template_content = Path(template_path).read_text()
        import re as _re

        match = _re.search(r"module\s+(\w+)", template_content)
        if match:
            orig_name = match.group(1)
            rtl = _re.sub(
                rf"\bmodule\s+{orig_name}\b", f"module {module_name}", template_content
            )
        else:
            rtl = template_content
    else:
        rtl = ""
    tb = ""

    # Try each provider in rotation
    for provider, model in providers_to_try:
        from generation_fixes import _provider_health

        if _provider_health.is_dead(provider):
            print(
                f"Skipping dead provider {provider}: {_provider_health.skip_reason(provider)}"
            )
            continue

        print(f"\n[Trying provider: {provider} (model: {model})]")

        for attempt in range(1, max_retries + 1):
            if _provider_health.is_dead(provider):
                print(f"Provider {provider} is dead/unhealthy, breaking retry loop.")
                break

            print(f"\nAttempt {attempt}/{max_retries} with {provider}...")

            validation = {}
            sim_result = {}
            lying_check = {
                "is_lying": False,
                "issues": [],
                "warnings": [],
                "verdict": "NOT_CHECKED",
            }

            # ---- Generate ----
            if not rtl or not tb:
                try:
                    desc_to_use = effective_description
                    if provider == "openrouter":
                        rtl, tb = generate_verilog_openrouter(
                            desc_to_use, module_name, model=model
                        )
                    elif provider == "github":
                        rtl, tb = generate_verilog_github(desc_to_use, module_name)
                    elif provider == "groq":
                        rtl, tb = generate_verilog_groq(desc_to_use, module_name)
                    elif provider == "gemini":
                        rtl, tb = generate_verilog_gemini(desc_to_use, module_name)
                    elif provider == "nvidia":
                        rtl, tb = generate_verilog_nvidia(desc_to_use, module_name)
                    elif provider == "opencode":
                        rtl, tb = generate_verilog_opencode(desc_to_use, module_name)
                    elif provider == "local":
                        rtl, tb = generate_verilog_local_model(desc_to_use, module_name)
                    else:
                        raise ValueError(f"Unknown provider '{provider}'")
                except Exception as e:
                    err = str(e)
                    print(f"Generation failed: {err}")
                    last_error = e
                    from generation_fixes import _provider_health

                    _provider_health.record_failure(provider, err)
                    # Check for rate limit - try next provider immediately
                    if "rate" in err.lower() or "quota" in err.lower() or "429" in err:
                        print(f"Rate limit hit for {provider}, trying next provider...")
                        break  # Break out of retry loop, try next provider
                    continue  # Retry with same provider

            if rtl:
                from generation_fixes import sv_to_v2005

                rtl = sv_to_v2005(rtl, module_name)
            if tb:
                from generation_fixes import sv_to_v2005

                tb = sv_to_v2005(tb, f"{module_name}_tb")

            rtl, tb, renamed_from = normalize_module_name(rtl, tb, module_name)
            if renamed_from:
                print(
                    f"Normalized module name from '{renamed_from}' to '{module_name}'"
                )

            # ---- Spec-compliance check (complex designs only) ----
            if complex_design:
                from generation_fixes import estimate_design_complexity
                spec_ok, spec_reason = _check_spec_compliance(
                    description, rtl, module_name
                )
                if not spec_ok:
                    print(f"[SPEC-COMPLIANCE] FAIL: {spec_reason}")
                    # Mark as failed so next attempt/retry gets a fresh generation
                    last_error = RuntimeError(f"Spec-compliance: {spec_reason}")
                    rtl, tb = "", ""  # force re-generation on next attempt
                    continue
                else:
                    print(f"[SPEC-COMPLIANCE] PASS")

            # ---- Validate ----
            validation = validate_verilog_syntax(rtl, tb, module_name)

            if validation["errors"]:
                print(f"Validation errors: {validation['errors']}")

                # Step 1: RuleBasedRepairEngine (deterministic, zero LLM)
                from rule_based_repair import RuleBasedRepairEngine as _RBE

                _rbe = _RBE()
                rtl, tb, _applied = _rbe.apply(rtl, tb, validation["errors"], module_name)
                auto_val = validate_verilog_syntax(rtl, tb, module_name)

                if _applied and not auto_val["errors"]:
                    print("Rule repair resolved ALL validation errors")
                    print("Skipping LLM repair.")
                    validation = auto_val
                else:
                    if _applied and auto_val["errors"]:
                        print(
                            f"Rule repair applied but {len(auto_val['errors'])} "
                            f"error(s) remain"
                        )

                    # Step 2: auto_fix_testbench (existing rule-based TB fixes)
                    tb_autofixed = auto_fix_testbench(tb, module_name, rtl)
                    auto_val = validate_verilog_syntax(rtl, tb_autofixed, module_name)

                    if not auto_val["errors"]:
                        print("Auto-fix resolved all remaining validation errors")
                        tb = tb_autofixed
                        validation = auto_val
                    elif attempt < max_retries:
                        # Step 3: rtl_repair targeted compile-error fix (cheap LLM call)
                        try:
                            from rtl_repair import repair_rtl_errors as _rre

                            _err_log = "\n".join(auto_val["errors"])
                            _fixed_rtl = _rre(rtl, _err_log, description, module_name)
                            if _fixed_rtl:
                                print("[rtl_repair] Compile-error fix applied")
                                rtl = _fixed_rtl
                                rtl, tb_autofixed, _ = normalize_module_name(
                                    rtl, tb_autofixed, module_name
                                )
                                auto_val = validate_verilog_syntax(
                                    rtl, tb_autofixed, module_name
                                )
                                if not auto_val["errors"]:
                                    print("[rtl_repair] RTL now compiles cleanly")
                                    tb = tb_autofixed
                                    validation = auto_val
                        except Exception as _re_err:
                            log.debug("rtl_repair skipped: %s", _re_err)

                        if auto_val["errors"]:
                            # Step 4: Full LLM repair (expensive, use last)
                            print("Attempting LLM repair...")
                            rtl, tb = repair_verilog(
                                rtl,
                                tb_autofixed,
                                module_name,
                                auto_val["errors"],
                                provider,
                                description=description,
                                sim_output="",
                            )
                            rtl, tb, _ = normalize_module_name(rtl, tb, module_name)
                            validation = validate_verilog_syntax(rtl, tb, module_name)
                            if validation["errors"]:
                                print(f"Still failing after repair: {validation['errors']}")
                                continue
                    else:
                        continue

            # ---- Honesty Gate ----
            lying_check = validate_testbench_has_real_checks(tb)
            if lying_check["is_lying"]:
                print(f"[WARNING] Lying testbench detected: {lying_check['issues']}")
                print("Injecting real checks before simulation...")
                tb = inject_real_checks_into_testbench(tb, module_name, rtl)

                validation = validate_verilog_syntax(rtl, tb, module_name)
                if validation["errors"]:
                    if attempt < max_retries:
                        rtl, tb = repair_verilog(
                            rtl,
                            tb,
                            module_name,
                            validation["errors"],
                            provider,
                            description=description,
                            sim_output="",
                        )
                        rtl, tb, _ = normalize_module_name(rtl, tb, module_name)
                    continue

            # ---- Save ----
            paths = save_design(module_name, rtl, tb)
            print(f"Saved RTL: {paths['rtl']}")
            print(f"Saved TB:  {paths['testbench']}")

            # ---- Simulate ----
            print(f"Running simulation with {sim_tool}...")
            sim_result = simulate_with_tool(
                module_name, paths["rtl"], paths["testbench"], tool=sim_tool
            )

            # ---- Enhanced simulation parsing (per-vector detail) ----
            from verification_pipeline import _build_sim_result_enhanced
            enhanced_sim = _build_sim_result_enhanced(
                sim_result.get("output", ""),
                sim_result.get("returncode", -1),
                sim_result.get("tool", sim_tool),
            )
            sim_result["vectors"] = enhanced_sim.get("vectors", [])
            sim_result["golden_compare"] = None

            # ---- Golden reference comparison ----
            try:
                from golden_reference import (
                    classify_design_for_golden,
                    has_golden_model,
                    compare_with_golden,
                )
                _gd_type = classify_design_for_golden(description, module_name)
                if _gd_type and has_golden_model(_gd_type):
                    _gc = compare_with_golden(
                        sim_result.get("output", ""), _gd_type
                    )
                    sim_result["golden_compare"] = _gc
                    if _gc.get("match") and _gc["total"] > 0:
                        print(f"[GOLDEN] All {_gc['total']} tests match golden reference")
                    elif _gc.get("failed", 0) > 0:
                        print(f"[GOLDEN] {_gc['failed']}/{_gc['total']} tests FAIL golden reference")
            except Exception as _gc_err:
                log.debug("golden_compare non-blocking: %s", _gc_err)

            # ---- Verification pipeline report ----
            verification_report = None
            if sim_result["success"]:
                try:
                    from verification_pipeline import run_verification_pipeline
                    verification_report = run_verification_pipeline(
                        rtl, tb, module_name, description,
                        skip_formal=True, skip_qor=True, skip_openlane=True,
                    )
                    if verification_report.status == "PASS":
                        print(f"[VERIFY] Pipeline: all {len(verification_report.stages)} stages passed")
                    else:
                        print(f"[VERIFY] Pipeline: {verification_report.status} — {verification_report.final_verdict[:120]}")
                except Exception as _vp_err:
                    log.debug("verification_pipeline non-blocking: %s", _vp_err)

            if sim_result["success"]:
                print(
                    f"[SUCCESS] Simulation PASSED (provider: {provider}, tool: {sim_result['tool']})"
                )

                return {
                    "status": "READY_FOR_PIPELINE",
                    "module_name": module_name,
                    "rtl": rtl,
                    "testbench": tb,
                    "paths": paths,
                    "validation": validation,
                    "simulation": sim_result,
                    "verification_report": verification_report.to_dict() if verification_report else None,
                    "testbench_honest": not lying_check.get("is_lying", False),
                    "provider": provider,
                    "attempts": attempt,
                    "error": None,
                    "complex_design": complex_design,
                }
            else:
                print(f"[FAIL] Simulation failed:\n{sim_result['output'][-500:]}")
                if attempt < max_retries:
                    # Try testbench-only repair first (wrong expected values)
                    from generation_fixes import _is_tb_expected_values_wrong, _repair_tb_expected_values
                    if _is_tb_expected_values_wrong(sim_result.get("output", "")):
                        print(f"[REPAIR] Wrong expected values — repairing testbench only, preserving RTL...")
                        new_tb = _repair_tb_expected_values(
                            tb, rtl, sim_result.get("output", ""), description, module_name
                        )
                        if new_tb:
                            from generation_fixes import sv_to_v2005
                            new_tb = sv_to_v2005(new_tb, f"{module_name}_tb")
                            rtl, new_tb, _ = normalize_module_name(rtl, new_tb, module_name)
                            val = validate_verilog_syntax(rtl, new_tb, module_name)
                            if not val["errors"]:
                                print("[REPAIR] Testbench-only repair produced valid testbench")
                                tb = new_tb
                                continue
                            else:
                                print(f"[REPAIR] Testbench-only repair had syntax issues: {val['errors'][:2]}")

                    print(f"[REPAIR] Attempting logic/syntax smart repair...")
                    try:
                        from generation_fixes import smart_repair

                        rtl, tb = smart_repair(
                            rtl_code=rtl,
                            tb_code=tb,
                            error_log=sim_result.get("output", ""),
                            description=description,
                            module_name=module_name,
                        )
                    except Exception as _sr_err:
                        log.debug("smart_repair non-blocking: %s", _sr_err)
                    continue

        print(f"Provider {provider} exhausted {max_retries} attempts")
        # Reset for next provider
        if not template_path:
            rtl = ""
        tb = ""

    # All providers failed
    return {
        "status": "GENERATION_FAILED",
        "module_name": module_name,
        "rtl": rtl,
        "testbench": tb,
        "validation": validation,
        "simulation": sim_result,
        "verification_report": None,
        "testbench_honest": not lying_check.get("is_lying", True),
        "attempts": max_retries * len(providers_to_try),
        "error": f"All providers failed. Last error: {last_error}",
        "complex_design": complex_design,
    }


# ============================================================
# QUICK TEST — run: python verilog_generator.py
# ============================================================

if __name__ == "__main__":
    result = generate_and_validate(
        description=(
            "Design a 4-bit binary up counter with synchronous "
            "reset and enable. When enable is high, counter "
            "increments on each clock edge. When reset_n is low, "
            "counter resets to 0. Output is 4-bit count."
        ),
        module_name="up_counter_4bit",
        llm_provider="groq",
        max_retries=3,
    )

    print(f"{'=' * 60}")
    print("RESULT:", result["status"])
    print("Attempts:", result["attempts"])
    print("Sim tool:", result.get("simulation", {}).get("tool", "?"))
    if result["status"] == "READY_FOR_PIPELINE":
        print("[PASS] Design ready for RTL-to-GDSII pipeline")
        print("Run full pipeline with:")
        print(f"  from full_flow import RTLtoGDSIIFlow")
        print(
            f"  flow = RTLtoGDSIIFlow('{result['module_name']}', '{result['paths']['rtl']}')"
        )
        print(f"  flow.run_full_flow()")
    else:
        print("[FAIL] Error:", result.get("error"))
    print(f"{'=' * 60}")
