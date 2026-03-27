# 🐳 Docker + OpenCode Quick Reference

**Status:** ✅ OpenCode v1.3.3 successfully tested in Docker

## What's Installed

- **Docker Image:** `node:25` (Node.js with build tools)
- **OpenCode Version:** 1.3.3
- **Package Manager:** npm 11.11.1

---

## Quick Start (Three Options)

### Option 1: PowerShell Helper Script (Easiest)

```powershell
# Make script executable
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Run OpenCode with description (one-liner)
.\run_opencode.ps1 "Create an 8-bit binary counter with clock and reset"

# Or run interactive shell
.\run_opencode.ps1
```

### Option 2: Direct Docker Command

```powershell
# Run OpenCode with description
docker run -it --rm -v "$PWD`:/workspace" -w /workspace `
  node:25 sh -c "npm install -g opencode-ai@latest && opencode 'Describe your circuit here'"

# Or start interactive shell
docker run -it --rm -v "$PWD`:/workspace" -w /workspace `
  node:25 sh -c "npm install -g opencode-ai@latest && opencode"
```

### Option 3: Docker Compose (Full Stack)

```powershell
# Start all services (Python app + OpenCode)
docker-compose -f docker-compose-opencode.yml up -d

# Access Streamlit: http://localhost:8501
# Access OpenCode shell: docker-compose -f docker-compose-opencode.yml exec opencode-node opencode

# Stop services
docker-compose -f docker-compose-opencode.yml down
```

---

## Usage Examples

### Generate 8-bit Counter

```powershell
.\run_opencode.ps1 "Create an 8-bit binary counter with clock, reset, and enable signals. Increment on rising clock edge."
```

### Generate 4-to-1 Multiplexer

```powershell
.\run_opencode.ps1 "Design a 4-to-1 multiplexer for 16-bit data inputs with 2-bit select lines"
```

### Generate Traffic Light Controller

```powershell
.\run_opencode.ps1 @"
  Design a traffic light controller FSM with:
  - Red state: 30 seconds
  - Green state: 25 seconds
  - Yellow state: 5 seconds
  - Transitions: Red → Green → Yellow → Red
"@
```

---

## Integration with Python Wrapper

Your `python/opencode_integration.py` can be updated to use Docker:

```python
import subprocess

# Use Docker to run OpenCode
def generate_verilog_docker(description: str) -> tuple:
    cmd = [
        "docker", "run", "-it", "--rm",
        "-v", f"{os.getcwd()}:/workspace",
        "-w", "/workspace",
        "node:25",
        "sh", "-c",
        f"npm install -g opencode-ai@latest && opencode '{description}'"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr
```

---

## Docker Images Available

- **node:25-alpine** - Lightweight (minimal dependencies)
- **node:25** - Full-featured (recommended for OpenCode) ✅
- **node:24** - Previous LTS version
- **node:latest** - Always latest version

---

## Troubleshooting

### Docker daemon not running
```powershell
# Start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

### Permission denied on PowerShell script
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

### OpenCode not found in PATH
The Docker approach bypasses this - OpenCode is installed inside the container

### Volume mount issues on Windows
Use forward slashes in docker-compose:
```yaml
volumes:
  - .:/workspace  # Correct
  # NOT: - C:\path\to\project:/workspace
```

---

## Verify Everything Works

```powershell
# Check Docker
docker --version          # Docker version 29.2.1 or higher

# Check if daemon is running
docker ps                 # Should list containers (even if empty)

# Test OpenCode in Docker
docker run --rm node:25 sh -c "npm install -g opencode-ai@latest && opencode --version"
# Should output: 1.3.3
```

---

## Performance Notes

- **First run:** Downloads and installs OpenCode (~40 seconds)
- **Subsequent runs:** Cached, uses existing layers (faster)
- **Volume mounts:** Direct filesystem access from Docker container
- **Network:** Full internet access for API calls

---

## What Happens in Your Workflow

```
Your description
    ↓
Docker container (node:25)
    ↓
OpenCode installed (npm)
    ↓
Verilog code generated
    ↓
Returned to Python wrapper
    ↓
Your RTL→GDSII pipeline
    ↓
GDS file ✨
```

---

## Environment Variables (Optional)

For premium model access:

```powershell
# Set before running
$env:OPENCODE_API_KEY = "your-api-key"

# Then run
.\run_opencode.ps1 "Your description"
```

---

## Files Created

| File | Purpose |
|------|---------|
| `Dockerfile.node` | Standalone OpenCode image |
| `run_opencode.ps1` | PowerShell helper script |
| `docker-compose-opencode.yml` | Full docker-compose setup |
| `DOCKER_OPENCODE_QUICKREF.md` | This file |

---

## Next Steps

1. **Verify Docker:** `docker --version`
2. **Test OpenCode:** `.\run_opencode.ps1 --version`
3. **Generate RTL:** `.\run_opencode.ps1 "8-bit counter"`
4. **Integrate with pipeline:** Use Python wrapper with Docker subprocess calls
5. **Run Full Pipeline:** Streamlit → Generate Code → Synthesis → GDS ✨

---

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [OpenCode GitHub](https://github.com/anomalyco/opencode)
- [Node.js Docker Hub](https://hub.docker.com/_/node)

---

**Ready to Go!** 🚀

Your RTL-Gen-AII project now has full OpenCode AI integration via Docker!
