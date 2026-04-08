# RTL-Gen AI — OpenCode.ai Edition

AI-powered RTL-to-GDSII synthesis platform. **Describe your chip in English, get GDS in 90 seconds.**

![Status](https://img.shields.io/badge/Status-Production%20Ready-green)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- **Python 3.10+**
- **Docker Desktop** (EDA tools run in containers)
- **OpenCode.ai** (optional, for AI Verilog generation)

### Windows Installation (One Command)

```powershell
# Run this in PowerShell
.\install.ps1
```

### macOS/Linux Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Pull EDA Docker image (2.5 GB, one-time)
docker pull efabless/openlane:latest

# Create PDK directories
mkdir -p /tools/pdk/sky130A
```

---

## 🎯 Usage

### With OpenCode.ai (Recommended)

**Terminal 1** — Start OpenCode.ai local agent:
```bash
opencode serve --port 8000
```

**Terminal 2** — Start RTL-Gen AI:
```bash
streamlit run app.py
```

Browser opens → http://localhost:8501

**In the app:**
1. Click **🤖 AI Verilog Generator**
2. Write: "Design a 4-bit ALU with ADD, SUB, AND, OR"
3. Click **🚀 Generate Verilog + Run Full Pipeline**
4. Get GDS in 90 seconds ✅

### Without OpenCode.ai (Use Groq)

```bash
# Set Groq API key first
$env:GROQ_API_KEY = "your-key-here"

# Then start app
streamlit run app.py
```

Groq is **free tier available** — sign up at https://console.groq.com

### Run Existing Designs

No AI needed — just use the dashboard to view/process existing RTL:

```bash
streamlit run app.py
```

Navigate to **RTL & Simulation** → **Synthesis** → **Physical Design** → **GDS Layout**

---

## 📁 What's Inside

```
rtl-gen-aii/
├── app.py                        # Main Streamlit dashboard
├── verilog_generator.py          # AI Verilog generation (OpenCode.ai)
├── full_flow.py                  # RTL-to-GDSII pipeline orchestrator
├── requirements.txt              # Python dependencies
├── install.ps1                   # Windows setup script
├── start.sh                       # Linux/Mac startup script
└── .devcontainer/
    └── devcontainer.json         # GitHub Codespaces config
```

---

## 🏗️ Pipeline Architecture

```
User Input (English description)
    ↓
OpenCode.ai / Groq (Generate Verilog)
    ↓
Validation (syntax check + quick sim)
    ↓
Iverilog (RTL simulation)
    ↓
Yosys (synthesis → Sky130A netlist)
    ↓
OpenROAD (placement & routing)
    ↓
Magic (GDS layout generation)
    ↓
Netgen (LVS verification)
    ↓
OpenSTA (timing analysis)
    ↓
GDS Download ✅
```

**Total time: ~90 seconds**

---

## 🎨 Dashboard Pages

- **🏠 Home** — Quick metrics (GDS size, cell count, LVS status)
- **🤖 AI Verilog Generator** — Describe chip → Get GDS
- **📄 RTL & Simulation** — View source code, waveforms
- **⚗️ Synthesis** — Cell distribution, netlist analysis
- **🏗️ Physical Design** — DEF stats, routing info
- **🔲 GDS Layout** — Layout preview, file info
- **✅ Sign-Off** — DRC/LVS/Timing verification
- **⬇️ Download Files** — All 26+ output files
- **📊 Pipeline Status** — Real-time verification checks

---

## 🧠 AI Providers

### OpenCode.ai (Recommended)
✅ **Best for:** Runs locally, full control, no API keys  
⚠️ **Setup:** `opencode serve --port 8000`  
📊 **Quality:** Enterprise-grade Verilog generation  
💰 **Cost:** Free (open-source)

```bash
# Install OpenCode.ai
npm install -g @opencode-ai/cli

# Start server
opencode serve --port 8000
```

### Groq (Fast & Free)
✅ **Best for:** No local setup needed  
⚠️ **Setup:** Requires API key (free at https://console.groq.com)  
📊 **Quality:** Very good  
💰 **Cost:** Free tier available

```powershell
$env:GROQ_API_KEY = "gsk_..."
streamlit run app.py
```

---

## 📊 Validation Levels

Generated Verilog is validated at 3 levels:

1. **Syntax Check** — Module structure, port names, reset signals
2. **Quick Simulation** — iverilog + GTKWave (2 sec, catches major errors)
3. **Full Pipeline** — Synthesis, placement, routing, verification (90 sec)

If validation fails, AI automatically retries up to 3 times with error feedback.

---

## 🔧 Configuration

Environment variables:
```powershell
# Optional — for Groq provider
$env:GROQ_API_KEY = "your-key"

# Optional — custom OpenCode.ai port
$env:OPENCODE_API_URL = "http://localhost:8000/v1"
```

---

## 🌐 Cloud Deployment

### GitHub Codespaces (Easiest)

1. Push repo to GitHub
2. Click **Code** → **Codespaces** → **Create codespace on main**
3. Wait ~5 min for Docker pull
4. Terminal: `streamlit run app.py`
5. Click "Open in browser"

Free tier: **180 core-hours/month** ✅

### Azure (GitHub Edu Pack)

Use GitHub Edu Pack to get **$100 credit**:
1. Register at [GitHub Edu](https://education.github.com)
2. Create Azure Web App
3. Deploy via GitHub Actions
4. Custom domain via Namecheap (free domain included)

---

## 🧪 Testing

```bash
# Test imports
python -c "from verilog_generator import generate_and_validate; print('✅ Generator loaded')"

# Test with sample design
python verilog_generator.py

# Expected output:
# ============================================================
# Generating Verilog for: up_counter_4bit
# Provider: opencode
# ============================================================
# Attempt 1/3...
# ✅ Quick simulation PASSED
# STATUS: READY_FOR_PIPELINE
```

---

## 🐛 Troubleshooting

**Problem:** `ConnectionError: OpenCode.ai not available`
```powershell
# Solution: Start OpenCode.ai in another terminal
opencode serve --port 8000
```

**Problem:** Docker image not found
```powershell
# Solution: Pull it
docker pull efabless/openlane:latest
```

**Problem:** Streamlit says "Missing ScriptRunContext"
```bash
# Normal warning — doesn't affect app. Use:
streamlit run app.py
# NOT: python app.py
```

---

## 📚 Learn More

- **OpenCode.ai Docs**: https://docs.opencode.ai
- **Streamlit**: https://docs.streamlit.io
- **OpenLane**: https://openlane.readthedocs.io
- **SKY130A PDK**: https://github.com/google/skywater-pdk

---

## 📝 Roadmap

- [x] OpenCode.ai integration ✅
- [x] AI Verilog generator with validation
- [x] Full RTL-to-GDSII pipeline
- [x] Web dashboard
- [ ] GitHub Codespaces deployment (Week 2)
- [ ] Azure App Service (Week 3)
- [ ] User accounts + design history (Week 4)
- [ ] Custom domain (Week 4)

---

## 📄 License

MIT — Free for commercial use

---

## 🤝 Contributing

Issues & PRs welcome!

```bash
git clone https://github.com/yourusername/rtl-gen-aii
cd rtl-gen-aii
git checkout -b feature/my-feature
```

---

**Made with ❤️ for hardware engineers**
