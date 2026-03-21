# install_yosys.ps1
# Quick Yosys installation via Conda

Write-Host ""
Write-Host ("=" * 70)
Write-Host "  Installing Yosys via Conda..."
Write-Host ("=" * 70)
Write-Host ""

# Check if conda is available
$conda = Get-Command conda -ErrorAction SilentlyContinue
if (-not $conda) {
    Write-Host "ERROR: Conda not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Miniconda from:"
    Write-Host "  https://docs.conda.io/projects/miniconda/en/latest/"
    Write-Host ""
    Write-Host "Then run this script again."
    Write-Host ""
    exit 1
}

Write-Host "Running: conda install -c conda-forge yosys"
Write-Host ""

conda install -c conda-forge yosys -y

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Installation failed" -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host ("=" * 70)
Write-Host "  Installation Complete!"
Write-Host ("=" * 70)
Write-Host ""

Write-Host "Testing installation..."
$version = & yosys -version 2>&1
Write-Host "  $version"

Write-Host ""
Write-Host "✅ Yosys is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next step:"
Write-Host "  python validate_pipeline.py"
Write-Host ""
