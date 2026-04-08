# 🎯 RTL-Gen AI — AIVerilog Generator + Full RTL-to-GDSII Pipeline

**Real hardware design generation with AI. Converts English descriptions → Verilog → GDS layout in 90 seconds.**

![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 What This Does

```
English Description
    ↓
Groq/OpenCode.ai API (AI Verilog Generation)
    ↓
Validate Verilog Syntax
    ↓
Quick Simulate (2 sec)
    ↓
Full RTL-to-GDSII Pipeline (Docker)
    ├─ Yosys Synthesis
    ├─ OpenROAD Place & Route
    ├─ Magic GDS Generation
    ├─ Netgen LVS Verification
    └─ OpenSTA Timing Analysis
    ↓
GDS File Ready for Tape-Out ✅
```

**Generated**: 4-bit counter in 82.9 seconds with 198.6 KB GDS file

---

## 📋 Quick Start

### Local (Windows)

```powershell
# Clone repo
git clone https://github.com/YOUR_USERNAME/rtl-gen-aii.git
cd rtl-gen-aii

# Install dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Set Groq API key (free tier)
$env:GROQ_API_KEY = "your-groq-api-key"

# Start app
streamlit run app.py
```

**Open:** http://localhost:8501

### Cloud (GitHub Codespaces)

1. Go to your repo: https://github.com/venkateshec23-maker/rtl-gen-aii
2. Click **Code** → **Codespaces** → **Create codespace on main**
3. Wait 2 minutes for container to build
4. In terminal:
   ```bash
   streamlit run app.py
   ```
5. Click the **Port 8501 forward** link

---

## 🔧 System Architecture

### What You Have

```
✅ verilog_generator.py
   ├─ generate_verilog_groq() → Groq API
   ├─ generate_verilog_opencode() → Local OpenCode.ai
   ├─ validate_verilog_syntax() → Quality gate
   ├─ simulate_in_docker() → Quick test
   └─ generate_and_validate() → Main orchestrator

✅ app.py (Streamlit Dashboard)
   ├─ Home & Metrics
   ├─ 🤖 AI Verilog Generator ← NEW
   ├─ RTL & Simulation
   ├─ Synthesis Results
   ├─ Physical Design
   ├─ GDS Layout
   ├─ Sign-Off (DRC/LVS/Timing)
   ├─ Download Files
   └─ Pipeline Status

✅ full_flow.py
   ├─ Docker orchestration
   ├─ EDA tool execution
   └─ Results parsing

✅ Deployment
   ├─ .devcontainer/ → GitHub Codespaces
   ├─ web.config → Azure App Service
   ├─ .github/workflows/deploy-azure.yml → CI/CD
   └─ requirements.txt → Dependencies
```

### Technology Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| **AI Generation** | Groq (primary) + OpenCode.ai (fallback) | Verilog synthesis from English |
| **Validation** | Custom Python | Syntax & testbench checks |
| **Simulation** | iverilog + verilator | Quick RTL validation |
| **Synthesis** | Yosys | RTL → netlist |
| **P&R** | OpenROAD | Placement & routing |
| **GDS** | Magic | Layout generation |
| **LVS** | Netgen | Layout vs schematic verification |
| **Timing** | OpenSTA | Static timing analysis |
| **PDK** | SKY130A 130nm | Open-source standard cell lib |
| **Web UI** | Streamlit | Interactive dashboard |
| **Container** | Docker | EDA tool isolation |
| **Cloud** | GitHub Codespaces + Azure | Deployment |

---

## 📊 AI Providers Comparison

| Provider | Cost | Speed | Quality | Setup |
|----------|------|-------|---------|-------|
| **Groq** | 🟢 Free tier | ⚡ 4-6 sec | 🟡 Good | Easy |
| **OpenCode.ai** | 🟢 Free (local) | ⚡⚡ 2-3 sec | 🟢 Excellent | Medium |
| **Claude (deprecated)** | 🔴 $0.003/req | ⚡⚡⚡ Best quality | 🟢 Perfect | Easy |

**Current Setup**: Groq (default) with OpenCode.ai fallback

---

## 🌩️ Azure Deployment

### Prerequisites

1. **GitHub Account** ✅ (you have this)
2. **Azure Subscription** (free with GitHub Edu Pack)
3. **GitHub Edu Pack** (claim at https://education.github.com/pack)

### Step 1: Claim GitHub Edu Pack

👉 Go to: **https://education.github.com/pack**

This gives you:
- ✅ **GitHub Codespaces**: 180 core-hours/month FREE
- ✅ **Azure for Students**: $100 credit/month
- ✅ **Namecheap**: Free domain for 1 year

### Step 2: Create Azure App Service

```powershell
# Login to Azure (first time)
az login

# Create resource group
az group create --name rtl-gen-ai --location eastus

# Create App Service Plan (free tier)
az appservice plan create \
  --name rtl-gen-plan \
  --resource-group rtl-gen-ai \
  --sku FREE

# Create web app
az webapp create \
  --resource-group rtl-gen-ai \
  --plan rtl-gen-plan \
  --name rtl-gen-ai-yourname \
  --runtime "PYTHON:3.11"

# Get publish profile
az webapp deployment profile show \
  --resource-group rtl-gen-ai \
  --name rtl-gen-ai-yourname \
  > publishProfile.json
```

### Step 3: Add GitHub Secrets

1. Go to: https://github.com/venkateshec23-maker/rtl-gen-aii/settings/secrets/actions
2. Click **New repository secret**
3. Add these 2 secrets:

| Name | Value |
|------|-------|
| `AZURE_APP_NAME` | `rtl-gen-ai-yourname` |
| `AZURE_PUBLISH_PROFILE` | (paste content of publishProfile.json) |

### Step 4: Deploy

```powershell
# Push a change to main branch
git add .
git commit -m "Add Azure deployment"
git push origin main
```

GitHub Actions will automatically deploy!

### Step 5: Access Your App

your-app-name.azurewebsites.net

---

## 🔑 API Keys Setup

### Groq (Free Tier - Recommended)

1. Go to: https://console.groq.com
2. Sign up (free)
3. Get API key
4. Set environment variable:
   ```powershell
   $env:GROQ_API_KEY = "your-key"
   ```

### OpenCode.ai (Local - No Key Needed)

```bash
# Install
npm install -g @opencode-ai/cli

# Start server
opencode serve --port 8000

# Use in app (automatic fallback)
```

---

## 📁 Project Structure

```
rtl-gen-aii/
├── app.py                    # Streamlit dashboard
├── verilog_generator.py      # AI Verilog generation
├── full_flow.py              # RTL-to-GDSII pipeline
├── requirements.txt          # Python dependencies
├── web.config                # Azure App Service config
├── .devcontainer/
│   └── devcontainer.json     # GitHub Codespaces config
├── .github/workflows/
│   └── deploy-azure.yml      # CI/CD pipeline
├── .gitignore
└── README.md                 # This file
```

---

## 🧪 Testing

### Test Generator (Local)

```powershell
$env:GROQ_API_KEY = "your-key"
python verilog_generator.py
```

**Expected Output:**
```
============================================================
Generating Verilog for: up_counter_4bit
Provider: groq
============================================================

Attempt 1/3...
Saved RTL: C:\tools\OpenLane\designs\up_counter_4bit\up_counter_4bit.v
Saved TB:  C:\tools\OpenLane\designs\up_counter_4bit\up_counter_4bit_tb.v
Running quick simulation...
✅ Quick simulation PASSED
STATUS: READY_FOR_PIPELINE
```

### Test App (Local)

```powershell
$env:GROQ_API_KEY = "your-key"
streamlit run app.py
```

Open http://localhost:8501 → **AI Verilog Generator** page → Try 4-bit ALU

---

## 🎨 Example Designs

### 1. 4-bit ALU

```
Module: alu_4bit
Inputs: A[3:0], B[3:0], opcode[1:0]
Operations: ADD, SUB, AND, OR
Output: result[3:0], carry_out
Expected: 60-80 cells, 3-5 min synthesis
```

### 2. 8-bit Shift Register

```
Module: shift_reg_8bit
Inputs: serial_in, shift_enable
Output: parallel_out[7:0]
Expected: 40-50 cells, 2-3 min synthesis
```

### 3. Traffic Light FSM

```
Module: traffic_light
States: RED(30), GREEN(25), YELLOW(5) cycles
Outputs: red, green, yellow signals
Expected: 50-70 cells, 3-5 min synthesis
```

---

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| **Verilog Generation Time** | 5-10 sec (Groq) |
| **Syntax Validation** | <1 sec |
| **Simulation** | 2 sec |
| **Full Pipeline** | 70-90 sec |
| **Total E2E** | ~100 sec |
| **GDS File Size** | 150-250 KB (4-bit designs) |
| **Cells Generated** | 60-150 (4-bit designs) |

---

## 🐛 Troubleshooting

### "No module named 'groq'"

```powershell
pip install groq httpx
```

### "GROQ_API_KEY not found"

```powershell
$env:GROQ_API_KEY = "your-key"
```

### "Docker connection failed"

Full pipeline requires Docker Desktop running. Quick test will fail but generator works fine.

### "Streamlit emoji error"

Normal on Windows. Set:
```powershell
$env:PYTHONIOENCODING = "utf-8"
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

MIT License - see LICENSE file

---

## 🙌 Credits

- **Groq** - Fast LLM inference
- **OpenCode.ai** - Local AI agent
- **Efabless OpenLane** - RTL-to-GDSII flow
- **Google Skywater PDK** - Open-source standard cells
- **Streamlit** - Web framework

---

## 📞 Support

- **Issues**: https://github.com/venkateshec23-maker/rtl-gen-aii/issues
- **Discussions**: https://github.com/venkateshec23-maker/rtl-gen-aii/discussions
- **Email**: venka@example.com

---

**Made with ❤️ by Venka**

*Last Updated: April 8, 2026*
