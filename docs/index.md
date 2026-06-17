# RTL-Gen AI

**RTL-Gen AI** is an open-source, LLM-powered RTL-to-GDSII pipeline. It generates synthesizable Verilog from plain English descriptions, runs it through a complete EDA toolchain (Yosys, OpenROAD, Magic, KLayout), and produces tapeout-ready GDSII files.

## Key Features

- **Conversational RTL Designer** — refine designs in plain English (v2.9)
- **RAG-Enhanced Generation** — 30+ proven examples improve first-pass synthesis (v3.0)
- **Complete EDA Pipeline** — synthesis → floorplan → placement → routing → DRC → LVS → GDS
- **Interactive Dashboard** — Streamlit-based sign-off dashboard with waveform/layout viewers
- **Multi-PDK Support** — Sky130A, GF180MCU (beta), IHP SG13G2 (roadmap)
- **No Commercial Tools Required** — fully Docker-based, runs on Windows/Mac/Linux

## Quick Start

```bash
# 1. Clone
git clone https://github.com/venkateshec23-maker/rtl-gen-aii.git
cd rtl-gen-aii

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API keys (Groq is free tier)
echo "GROQ_API_KEY=gsk_..." > .env

# 4. Start the dashboard
streamlit run app.py
```

## Usage

1. Open the dashboard at `http://localhost:8501`
2. Click "Generate / Upload" and describe your design
3. Click "Sign-Off" to view the full pipeline results
4. Use "Conversational Designer" to iteratively refine designs

## Architecture

```
app.py (Streamlit Dashboard)
├── guaranteed_flow.py — LLM + synthesis pipeline
├── full_flow.py — OpenROAD + DRC + LVS + GDS
├── qor_engine.py — Power/Timing/Area analysis
├── conversational_rtl.py — Multi-turn design chat
├── rag_engine.py — Retrieval-augmented generation
├── drc_engine.py — KLayout DRC engine
├── lvs_engine.py — Netlist comparison
└── parsers/ — STA, congestion, power report parsers
```

## License

MIT License — free for commercial and academic use.
