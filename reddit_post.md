# Reddit Post — r/chipdesign + r/FPGA + r/ECE

## TITLE:
Built open-source RTL-to-GDSII with AI + REST API
— 30 seconds from plain English to real silicon layout

## BODY:
I spent 3 months building RTL-Gen AI.
It converts natural language descriptions
into manufacturable GDS files automatically.

**What it does:**
- Describe a circuit in plain English
- AI generates synthesizable Verilog
- Full physical design runs automatically
- Real DRC/LVS verification included
- GDS file ready in ~60 seconds

**Proven results (not demos):**

| Design | GDS Size | LVS | Timing |
|--------|----------|-----|--------|
| 8-bit adder | 268 KB | Matched | 7ns slack |
| Simple ALU | 152 KB | 69 devices matched | 5.57ns |
| UART TX | 171 KB | Matched | MET |
| 4-bit counter | 254 KB | Matched | MET |

LVS says "Circuits match uniquely" on all designs.
That means transistor-level equivalence proven.

**REST API:**
```
POST /api/generate
{"description": "4-bit counter with enable"}

GET /api/status/{job_id}
{"status": "complete", "gds_size_kb": 171.7}

GET /api/download/{job_id}
→ Returns real GDSII binary file
```

**Tech stack:**
- AI: Claude / Gemini / Groq
- Synthesis: Yosys synth_sky130
- P&R: OpenROAD full flow
- Verification: Magic + KLayout + Netgen
- PDK: SKY130A 130nm
- API: FastAPI
- UI: Streamlit

**9 design templates:**
counter, adder, ALU, shift register, MUX,
FSM, UART TX, SPI master, I2C master

GitHub: github.com/venkateshec23-maker/rtl-gen-aii

What designs should I test next?