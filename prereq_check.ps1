<# 
prereq_check.ps1 - Quick validation of all prerequisites
========================================================
Run this BEFORE validate_pipeline.py to confirm system is ready.

Usage (PowerShell):
    .\prereq_check.ps1
#>

Write-Host ""
Write-Host ("=" * 70)
Write-Host "  RTL-Gen AI - Prerequisite Check"
Write-Host ("=" * 70)
Write-Host ""

$all_pass = $true

# Check 1: Docker running
Write-Host "Step 1: Docker..." -NoNewline
try {
    $result = docker ps 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Write-Host " [FAIL]" -ForegroundColor Red
        Write-Host "       Docker not running. Start the Docker Desktop application."
        $all_pass = $false
    }
} catch {
    Write-Host " [FAIL]" -ForegroundColor Red
    Write-Host "       Docker CLI not found. Install Docker Desktop."
    $all_pass = $false
}

# Check 2: OpenLane image
Write-Host "Step 2: OpenLane image..." -NoNewline
$images = docker images 2>$null | Select-String "openlane"
if ($images) {
    Write-Host " [OK]" -ForegroundColor Green
} else {
    Write-Host " [FAIL]" -ForegroundColor Red
    Write-Host "       OpenLane image not found."
    Write-Host "       Fix: docker pull efabless/openlane:latest"
    $all_pass = $false
}

# Check 3: PDK
Write-Host "Step 3: PDK..." -NoNewline
try {
    $output = python -c "from python.pdk_manager import PDKManager; PDKManager().validate()" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Write-Host " [FAIL]" -ForegroundColor Red
        Write-Host "       PDK validation failed."
        Write-Host "       Check: C:\pdk\sky130A exists with all libraries"
        $all_pass = $false
    }
} catch {
    Write-Host " [FAIL]" -ForegroundColor Red
    Write-Host "       PDK check failed: $_"
    $all_pass = $false
}

# Check 4: Yosys (optional - will be checked during synthesis)
Write-Host "Step 4: Yosys..." -NoNewline
$yosys = Get-Command yosys -ErrorAction SilentlyContinue
if ($yosys) {
    Write-Host " [OK]" -ForegroundColor Green
} else {
    Write-Host " [OPTIONAL - install before running validation]" -ForegroundColor Yellow
    Write-Host "       See: YOSYS_INSTALL.md (Conda recommended: conda install -c conda-forge yosys)"
}

Write-Host ""
if ($all_pass) {
    Write-Host "[OK] ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ready to run: python validate_pipeline.py"
    Write-Host ""
} else {
    Write-Host "[FAIL] Fix above checks before proceeding" -ForegroundColor Red
    Write-Host ""
    exit 1
}
