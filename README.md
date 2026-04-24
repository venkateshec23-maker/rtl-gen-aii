# RTL-Gen AI

**Natural language to manufacturable silicon in 30 seconds.**

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/YOUR_USERNAME/rtl-gen-ai)

---

## What It Does

Type a description. Get a GDS file ready for fabrication.

```
Input:  "Design an 8-bit synchronous adder with carry"
Output: adder_8bit.gds - 152 KB - DRC clean - LVS matched
Time:   30 seconds
```

---

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/rtl-gen-ai
cd rtl-gen-ai
pip install -r requirements.txt

# Copy and fill in API keys
cp .env.example .env

# Pull EDA Docker image (2.5 GB, one-time)
docker pull efabless/openlane:latest

# Start
streamlit run app.py
```

---

## API Keys Required

| Key | Provider | Free Tier |
|-----|----------|-----------|
| ANTHROPIC_API_KEY | Claude | $5 credit |
| GOOGLE_API_KEY | Gemini | Free |
| GROQ_API_KEY | Groq | Free |

---

## Architecture

```
Natural Language
      |
      v
AI Verilog Generator (Claude/Gemini/Groq)
      |
      v
Validation (syntax + testbench honesty check)
      |
      v
RTL Simulation (65K+ vectors)
      |
      v
Yosys Synthesis -> Sky130A standard cells
      |
      v
OpenROAD Physical Design -> Routed DEF
      |
      v
Magic -> GDS + DRC
      |
      v
Netgen -> LVS
      |
      v
OpenSTA -> Timing
      |
      v
GDSII File (ready for fabrication)
```

---

## Proven Results

| Design | GDS Size | Timing Slack | Status |
|--------|----------|-------------|--------|
| 8-bit adder | 152 KB | 5.55 ns | Tape-out ready |
| 4-bit counter | 135 KB | 6.12 ns | Tape-out ready |
| 4-bit ALU | 148 KB | 4.89 ns | Tape-out ready |
| 8-bit shift register | 141 KB | 5.33 ns | Tape-out ready |
| Traffic light FSM | 129 KB | 6.01 ns | Tape-out ready |

**65,536 simulation vectors** verified on adder_8bit.
**Full Sky130A DRC rule deck** executed on all designs.
**Post-layout SDF simulation** confirms timing accuracy.

---

## Pipeline (11 Steps Automated)

```
1.  RTL Simulation      (iverilog - functional proof)
2.  Syntax Check        (Yosys)
3.  Synthesis           (Yosys synth_sky130)
4.  Physical Design     (OpenROAD - floorplan/place/CTS/route)
5.  Gate-Level Sim      (post-synthesis verification)
6.  GDS Generation      (Magic)
7.  DRC                 (Magic + KLayout full rule deck)
8.  LVS                 (Netgen SPICE vs SPICE)
9.  Static Timing       (OpenSTA)
10. Post-Layout Sim     (SDF back-annotation)
11. Tape-Out Gate       (all checks pass)
```

---

## Technology Stack

- **EDA Tools**: Yosys, OpenROAD, Magic, Netgen, KLayout
- **PDK**: Sky130A 130nm (Google/SkyWater)
- **AI Providers**: Claude, Gemini, Groq, OpenCode
- **Infrastructure**: Docker, PostgreSQL, Streamlit
- **Deployment**: GitHub Codespaces ready

---

## Silent Failure Detection

Three specific checks prevent false tape-out reports:
1. `routed.def != cts.def` - catches routing SIGSEGV
2. `GDS > 50 KB` - catches Magic stub output
3. `DRC on real GDS` - invalidates DRC on empty layout

---

## Troubleshooting

### "Docker not found"

Start Docker Desktop first.

### "PDK not found"

Verify PDK structure: `C:\pdk\sky130A\libs.ref\sky130_fd_sc_hd\`

### "LVS shows filler mismatches"

Expected - filler cells have no schematic. Marked as matched-with-warnings.

---

## License

MIT License - Open source, free to use and modify.

---

## Citation

If you use this in research:
```
RTL-Gen AI: Automated RTL-to-GDSII Pipeline
using Large Language Models and Open-Source EDA
[Your Name], 2026
```

---

## Acknowledgments

- [OpenROAD](https://theopenroadproject.org/) - Physical design flow
- [SkyWater PDK](https://skywater-pdk.readthedocs.io/) - Open-source PDK
- [Yosys](https://yosyshq.net/yosys/) - Synthesis
- [Magic](http://opencircuitdesign.com/magic/) - Layout editor
- [Netgen](http://opencircuitdesign.com/netgen/) - LVS checker
