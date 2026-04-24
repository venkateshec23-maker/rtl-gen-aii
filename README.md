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

## Demo Screenshots

| Home Dashboard | Physical Design |
|:-------------:|:---------------:|
| ![Home](docs/home.png) | ![Layout](docs/layout.png) |

| Sign-off Checks | GDS Download |
|:---------------:|:------------:|
| ![Signoff](docs/signoff.png) | ![GDS](docs/gds.png) |

---

## Quick Start (5 minutes)

### Prerequisites

- **Docker Desktop** - [Install](https://www.docker.com/products/docker-desktop/)
- **Python 3.10+** - [Install](https://www.python.org/downloads/)
- **16GB RAM** (8GB minimum)
- **50GB disk** (PDK + Docker images)

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/rtl-gen-ai.git
cd rtl-gen-ai
pip install -r requirements.txt
```

### 2. Pull Docker Image (~5GB)

```bash
docker pull efabless/openlane:latest
```

### 3. Download PDK (~2GB)

```bash
# Windows
mkdir C:\pdk
# Download from https://github.com/RTimothyEdwards/open_pdks
# Extract sky130A to C:\pdk\sky130A

# Linux/Mac
mkdir -p ~/pdk
# Same extraction process
```

### 4. Run the App

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## How It Works

```
User Description
      |
      v
+-------------+
| LLM Generation |  <-- Gemini / OpenCode / Groq
+-------------+
      |
      v
+-------------+
| RTL Synthesis  |  <-- Yosys + Sky130
+-------------+
      |
      v
+-------------+
| Floorplan      |  <-- OpenROAD
| Placement      |
| CTS            |
| Routing        |
+-------------+
      |
      v
+-------------+
| DRC / LVS      |  <-- Magic / Netgen
| STA            |  <-- OpenSTA
+-------------+
      |
      v
+-------------+
| GDS II Output  |  <-- Ready for fab
+-------------+
```

---

## Architecture

```
rtl-gen-ai/
├── app.py                 # Streamlit UI (5 pages)
├── full_flow.py           # 11-step RTL-to-GDSII pipeline
├── verilog_generator.py   # LLM-based Verilog generation
├── database.py            # PostgreSQL / JSON storage
├── generate_wpi_report.py # Professional HTML reports
└── designs/               # Example RTL modules
    ├── adder_8bit/
    ├── counter_4bit/
    ├── alu_4bit/
    └── shift_reg_8bit/
```

---

## Pipeline Steps

| Step | Tool | Output |
|------|------|--------|
| 1. RTL Simulation | iverilog | VCD waveform |
| 2. Synthesis | Yosys | Sky130 netlist |
| 3. Floorplan | OpenROAD | DEF placement |
| 4. Placement | OpenROAD | Optimized placement |
| 5. CTS | OpenROAD | Clock tree |
| 6. Routing | OpenROAD | Routed DEF |
| 7. DRC | Magic | Clean layout |
| 8. LVS | Netgen | Schematic match |
| 9. STA | OpenSTA | Timing closure |
| 10. GDS | Magic | Final layout |
| 11. Sign-off | Custom | Tape-out ready |

---

## API Keys (Optional)

RTL-Gen AI works without API keys using local models.
For best results with cloud LLMs:

```bash
# Google Gemini (Recommended - Free tier available)
export GEMINI_API_KEY=your_key_here

# OR OpenCode.ai (Free local AI)
pip install opencode-ai
opencode acp --port 4096

# OR Groq (Fast, but rate-limited)
export GROQ_API_KEY=your_key_here
```

---

## Configuration

Edit `full_flow.py` to customize:

```python
DOCKER_IMAGE = "efabless/openlane:latest"  # EDA container
PDK_ROOT     = "C:\\pdk\\sky130A"           # PDK location
CLOCK_PERIOD = 10.0                         # Target frequency
```

---

## Production Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  rtlgenai:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./pdk:/pdk
      - ./results:/results
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
```

```bash
docker-compose up -d
```

### PostgreSQL (Optional)

```bash
docker run -d --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rtlgenai \
  -p 5432:5432 \
  postgres:15
```

The app automatically falls back to JSON storage if PostgreSQL is unavailable.

---

## Troubleshooting

### "Docker not found"

```bash
# Start Docker Desktop
open -a Docker  # Mac
start Docker Desktop  # Windows
```

### "PDK not found"

```bash
# Verify PDK structure
ls C:\pdk\sky130A\libs.ref\sky130_fd_sc_hd\
# Should show: lef/, lib/, verilog/, etc.
```

### "Routing failed with zero-length nets"

This happens with very small designs. The flow handles it gracefully.
If it persists, try a slightly larger design.

### "LVS shows filler mismatches"

This is expected - filler cells have no schematic.
The tool recognizes this and marks LVS as matched-with-warnings.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Backend | Python 3.10+ |
| EDA Tools | OpenROAD, Yosys, Magic, Netgen |
| PDK | Sky130A (130nm open-source) |
| Container | Docker |
| Database | PostgreSQL / JSON |
| LLM | Gemini / OpenCode / Groq |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Acknowledgments

- [OpenROAD](https://theopenroadproject.org/) - Physical design flow
- [SkyWater PDK](https://skywater-pdk.readthedocs.io/) - Open-source PDK
- [Yosys](https://yosyshq.net/yosys/) - Synthesis
- [Magic](http://opencircuitdesign.com/magic/) - Layout editor
- [Netgen](http://opencircuitdesign.com/netgen/) - LVS checker

---

## Star History

If you find this useful, please star the repo!

[![Star History Chart](https://api.star-history.com/svg?repos=YOUR_USERNAME/rtl-gen-ai&type=Date)](https://star-history.com/#YOUR_USERNAME/rtl-gen-ai&Date)
