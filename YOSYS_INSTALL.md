# Installing Yosys on Windows

Yosys is required to synthesize Verilog designs. Here are the recommended installation methods (in order of ease):

## Option 1: Miniconda/Conda (EASIEST - Recommended)

If you have Miniconda or Anaconda installed:

```powershell
conda install -c conda-forge yosys
```

Verify:
```powershell
yosys -version
```

**Advantages:**
- One command
- Reliable cross-platform builds
- Automatically added to PATH
- Easy to remove: `conda remove yosys`

If you don't have Conda installed, you can install Miniconda for Windows:
- Download from: https://docs.conda.io/projects/miniconda/en/latest/
- Pick the Windows installer
- Run installer and follow defaults

---

## Option 2: Pre-built Binary (Direct Download)

1. Visit: https://github.com/YosysHQ/yosys/releases

2. Look for a release tagged with Windows binaries (older releases might have them):
   - Search for `win32`, `msys2`, or `.zip` files
   - Download the ZIP file (e.g., `yosys-*.zip`)

3. Extract to: `C:\Tools\yosys`

4. Add to PATH:
   - Windows Start Menu → "Edit environment variables"
   - Select "Environment Variables"
   - Under "User variables", click "New"
   - Variable name: `PATH`
   - Variable value: `C:\Tools\yosys\bin`
   
5. Restart PowerShell and test:
   ```powershell
   yosys -version
   ```

---

## Option 3: Using Windows Subsystem for Linux (WSL)

If you have WSL2 installed:

```bash
# In WSL terminal:
sudo apt-get update
sudo apt-get install yosys
```

Then modify `full_flow.py` to call WSL version if Windows version not found (advanced).

---

## Option 4: Build from Source (Advanced - 30-60 min)

For experienced developers:

```powershell
# Install prerequisites first:
# - MSYS2 (https://www.msys2.org/)
# - Visual Studio Build Tools (https://visualstudio.microsoft.com/downloads/)

git clone https://github.com/YosysHQ/yosys.git
cd yosys
make
make install
```

---

## Quick Test After Installation

```powershell
# Verify installation
yosys -version

# Run a simple test
echo 'module test(input a, output b); assign b = a; endmodule' > test.v
yosys -p "read_verilog test.v; write_json test.json"
ls test.json  # Should exist
```
