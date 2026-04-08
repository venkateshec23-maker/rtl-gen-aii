# 🚀 Quick Commands Reference

## Installation (One-Time Setup)

### Windows
```powershell
.\install.ps1
```

### macOS/Linux
```bash
pip install -r requirements.txt
docker pull efabless/openlane:latest
mkdir -p ~/.tools/pdk/sky130A
```

---

## 🎯 Launch Commands

### With OpenCode.ai (Recommended)

**Terminal 1 — Start OpenCode.ai:**
```powershell
opencode serve --port 8000
```

**Terminal 2 — Start RTL-Gen AI:**
```powershell
cd C:\Users\venka\Documents\rtl-gen-aii
streamlit run app.py
```

Then open: **http://localhost:8501**

---

### With Groq (No Local Setup)

```powershell
$env:GROQ_API_KEY = "gsk_YOUR_API_KEY"
streamlit run app.py
```

Get free API key→ https://console.groq.com

---

### Without AI (View Existing Designs)

```powershell
streamlit run app.py
```

---

## 🧪 Testing

### Quick Import Test
```powershell
python -c "from verilog_generator import generate_and_validate; print('✅ Ready')"
```

### Test Design Generation (Requires OpenCode.ai)
```powershell
python verilog_generator.py
```

Expected output:
```
============================================================
Generating Verilog for: up_counter_4bit
Provider: opencode
============================================================
Saved RTL: C:\tools\OpenLane\designs\up_counter_4bit\...
✅ Quick simulation PASSED
STATUS: READY_FOR_PIPELINE
```

### Syntax Check
```powershell
python -m py_compile verilog_generator.py
python -m py_compile app.py
```

---

## 📊 Check Status

### Is OpenCode.ai running?
```powershell
curl http://localhost:8000/v1/models
```

### Is Streamlit running?
```powershell
curl http://localhost:8501
```

### List available designs
```powershell
ls C:\tools\OpenLane\designs\
```

### View latest GDS
```powershell
ls C:\tools\OpenLane\results\*.gds | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

---

## 🔧 Environment Variables

```powershell
# For Groq provider
$env:GROQ_API_KEY = "gsk_..."

# Custom OpenCode.ai port (if not 8000)
$env:OPENCODE_API_URL = "http://localhost:9000/v1"

# Streamlit config
$env:STREAMLIT_SERVER_PORT = "8501"
$env:STREAMLIT_SERVER_ADDRESS = "0.0.0.0"
```

---

## 🆘 Troubleshooting

### OpenCode.ai won't connect
```powershell
# Make sure it's running in another terminal
opencode serve --port 8000

# Check if it's listening
netstat -an | findstr 8000
```

### Docker image not found
```powershell
docker pull efabless/openlane:latest
```

### Streamlit port already in use
```powershell
# Kill process on 8501
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Or use different port
streamlit run app.py --server.port 8502
```

### Clear cache & rebuild
```powershell
streamlit cache clear
```

---

## 📁 Important Directories

```
C:\tools\OpenLane\designs\         → Your RTL files
C:\tools\OpenLane\results\         → Generated outputs (GDS, netlists, etc)
C:\Users\venka\Documents\rtl-gen-aii\  → This project
C:\pdk\sky130A\                    → PDK files
```

---

## 🎯 Typical Workflow

1. **Start services** (Terminal 1)
   ```powershell
   opencode serve --port 8000
   ```

2. **Launch app** (Terminal 2)
   ```powershell
   streamlit run app.py
   ```

3. **Open browser**
   → http://localhost:8501

4. **Generate design** (in browser)
   - Click **🤖 AI Verilog Generator**
   - Describe your chip
   - Click **🚀 Generate**
   - Wait ~90 seconds
   - Download GDS file

5. **View results**
   - Check metrics in **Home** page
   - View netlist in **Synthesis** page
   - Download all files in **Download Files** page

---

## 📈 Next Steps (Cloud Deployment)

### GitHub Codespaces
```bash
# Push code to GitHub
git add .
git commit -m "OpenCode.ai integration"
git push

# Then on GitHub: Code → Codespaces → Create codespace on main
# Wait 5 min, then in terminal:
streamlit run app.py
```

### Local Testing Before Cloud
```powershell
# Test that everything works locally first
python verilog_generator.py
streamlit run app.py
```

---

**Pro Tip:** Create a PowerShell script to launch both OpenCode.ai and Streamlit:

**start-all.ps1:**
```powershell
# Start OpenCode.ai in background
Start-Process {opencode serve --port 8000}

# Give it time to start
Start-Sleep -Seconds 3

# Launch Streamlit
streamlit run app.py
```

Then just run: `.\start-all.ps1`

---

**Last Updated:** April 7, 2026  
**Status:** ✅ Ready for production
