# Yosys Setup Guide for Windows
## Complete Installation Instructions

### Option 1: Using Pre-built Binaries (Easiest)

#### Download Latest Release
1. Visit: https://github.com/YosysHQ/yosys/releases
2. Download the latest Windows binary:
   - Look for: `yosys-win32-x64-*.zip` or similar
   - Or download nightly build: `yosys-nightly-x86_64.zip`

3. Extract to a location (example: `C:\yosys`)
4. Add to Windows PATH (see step 4 below)

#### Add Yosys to Windows PATH

**Method 1: Using PowerShell (Admin)**
```powershell
# Run PowerShell as Administrator, then:
$yosysPath = "C:\yosys\bin"
if (-not ($env:Path -like "*$yosysPath*")) {
    $env:Path += ";$yosysPath"
    [Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::Machine)
    Write-Host "Added $yosysPath to PATH permanently"
}
```

**Method 2: Using Windows GUI**
1. Press `Win + X` → Settings
2. Search for "Environment Variables"
3. Click "Edit the system environment variables"
4. Click "Environment Variables" button
5. Under "System variables", find "Path" and click "Edit"
6. Click "New" and add: `C:\yosys\bin`
7. Click OK, OK, OK
8. Restart PowerShell/Command Prompt

#### Verify Installation
```powershell
yosys -V
```
Expected output: `Yosys ... (Open Source Verilog Synthesis Suite)`

---

### Option 2: Docker (Alternative)

If you prefer isolated environment:

```powershell
docker run --rm -v C:\your\verilog\path:/work yosys/yosys:latest
```

---

### Option 3: Build from Source (Advanced)

#### Prerequisites
- MSYS2 or Cygwin
- Build tools: cmake, make, g++
- Tcl development files

#### Build Steps
```bash
# Clone repository
git clone https://github.com/YosysHQ/yosys.git
cd yosys

# Configure and build
make config-gcc
make -j$(nproc)
make install
```

---

## Troubleshooting

### "yosys: command not found"
**Solution**: Add Yosys to PATH (see section above)

### Download fails from GitHub
**Solution**: Try alternative sources:
- https://github.com/ghdl/ghdl-yosys-plugin/releases
- Direct OSS CAD Suite: https://github.com/YosysHQ/oss-cad-suite-build/releases

### PATH changes not taking effect
**Solution**: Restart terminal or run:
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

---

## Verify Synthesis Works with RTL-Gen AI

After installation, run:

```bash
cd C:\Users\venka\Documents\rtl-gen-aii
python -m pytest tests/test_synthesis_engine.py -v
```

You should see real Yosys synthesis instead of mock mode.

---

## Next Steps

Once Yosys is installed:

1. Run integration test with real synthesis:
   ```bash
   python complete_integration.py
   ```

2. Verify more accurate metrics:
   ```bash
   python synthesis_engine.py  # May include synthesis output
   ```

3. Netlists will use actual Yosys results instead of mock estimates

---

## Getting Help

**Yosys Documentation**: https://yosyshq.net/
**GitHub Issues**: https://github.com/YosysHQ/yosys/issues
**RTL-Gen AI Guide**: See docs/SYNTHESIS_GUIDE.md
