# install.ps1
# RTL-Gen AI Installer for Windows 10/11
# One-command setup for OpenCode.ai + RTL-to-GDSII pipeline

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  RTL-Gen AI — OpenCode.ai Edition Installer                 ║" -ForegroundColor Cyan
Write-Host "║  AI-Powered RTL → GDS Synthesis on SKY130A 130nm            ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check Python 3.10+
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "❌ Python not found. Installing Python 3.12..." -ForegroundColor Red
    winget install Python.Python.3.12 -e
    Write-Host "✅ Python 3.12 installed. Please restart PowerShell and run installer again." -ForegroundColor Green
    exit 0
}

$pythonVersion = python --version 2>&1
Write-Host "✅ $pythonVersion" -ForegroundColor Green

# Check Docker
Write-Host ""
Write-Host "Checking Docker installation..." -ForegroundColor Yellow
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "❌ Docker not found. Installing Docker Desktop..." -ForegroundColor Red
    winget install Docker.DockerDesktop -e
    Write-Host "⚠️  Docker Desktop installed. Please restart the system and run installer again." -ForegroundColor Yellow
    exit 0
}

Write-Host "✅ Docker Desktop found" -ForegroundColor Green

# Install Python dependencies
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

Write-Host "✅ Python dependencies installed" -ForegroundColor Green

# Pull OpenLane Docker image
Write-Host ""
Write-Host "Downloading EDA tools (2.5GB, one-time)..." -ForegroundColor Yellow
Write-Host "This may take 5-10 minutes..." -ForegroundColor Gray
docker pull efabless/openlane:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ EDA tools ready" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to pull Docker image. Check Docker Desktop is running." -ForegroundColor Red
    exit 1
}

# Create PDK directory structure
Write-Host ""
Write-Host "Setting up PDK directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "C:\pdk\sky130A\libs.ref\sky130_fd_sc_hd\lib" | Out-Null

Write-Host "✅ PDK directories created" -ForegroundColor Green

# Success message
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ Installation Complete!                                  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "Next step: Start RTL-Gen AI" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option 1 — With OpenCode.ai (recommended):" -ForegroundColor White
Write-Host "  1. Open a new PowerShell window  " -ForegroundColor Gray
Write-Host "  2. Run: opencode serve --port 8000" -ForegroundColor Gray
Write-Host "  3. In this window, run: streamlit run app.py" -ForegroundColor Gray
Write-Host ""

Write-Host "Option 2 — With Groq (free API, no local setup):" -ForegroundColor White
Write-Host "  1. Set GROQ_API_KEY: \$env:GROQ_API_KEY='your-key'" -ForegroundColor Gray
Write-Host "  2. Run: streamlit run app.py" -ForegroundColor Gray
Write-Host ""

Write-Host "Option 3 — Without AI (run existing designs only):" -ForegroundColor White
Write-Host "  1. Run: streamlit run app.py" -ForegroundColor Gray
Write-Host ""

Write-Host "Dashboard will open at: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
