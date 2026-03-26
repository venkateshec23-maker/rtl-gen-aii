"""
docker_manager.py  –  Docker Desktop / OpenLane Container Manager (Windows)
===========================================================================
Manages Docker container lifecycle for OpenLane/OpenROAD workflows.
Handles:
  - Docker Desktop verification (installed, running, WSL2 backend)
  - OpenLane image pulling and caching
  - Container lifecycle (create, run, cleanup)
  - Windows ↔ Docker path translation
  - Volume mounting and working directory setup

Usage:
    from python.docker_manager import DockerManager
    docker = DockerManager()
    status = docker.verify_installation()
    if status.docker_running:
        result = docker.run_openroad(
            work_dir="C:/path/to/work",
            command="openroad /path/to/script.tcl"
        )

Environment:
    DOCKER_IMAGE: Override default OpenLane image (default: efabless/openlane:latest)
    DOCKER_CONTAINER_TIMEOUT: seconds for container operations (default: 300)

Requirements:
    - Docker Desktop for Windows (with WSL2 backend)
    - PowerShell 5.1+ for Windows
    - Administrative privileges (first-time Docker setup only)
"""

from __future__ import annotations

import os
import sys
import re
import json
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Dict, List, Optional, Tuple
import platform


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS & DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

class DockerBackend(Enum):
    """Docker runtime backend type."""
    WSL2       = "wsl2"       # Windows Subsystem for Linux 2
    HYPER_V    = "hyperv"     # Hyper-V virtualization
    NATIVE_LINUX = "linux"    # Native Linux installation
    UNKNOWN    = "unknown"


@dataclass
class DockerStatus:
    """Result of Docker installation/readiness check."""
    installed: bool = False           # Docker CLI found
    running: bool = False             # Docker daemon running
    backend: DockerBackend = DockerBackend.UNKNOWN
    version: str = ""                 # Docker version string
    wsl2_capable: bool = False        # Windows: WSL2 available
    error: Optional[str] = None       # Error message if check failed


@dataclass
class ContainerResult:
    """Result of container execution."""
    returncode: int = 0               # Exit code
    stdout: str = ""                  # Standard output
    stderr: str = ""                  # Standard error
    exception: Optional[Exception] = None
    is_success: bool = field(init=False)

    def __post_init__(self):
        self.is_success = self.returncode == 0 and self.exception is None


@dataclass
class ImageInfo:
    """Metadata about a Docker image."""
    name: str                         # e.g., "efabless/openlane:latest"
    size_gb: float = 0.0              # Approximate size in GB
    pulling: bool = False             # Currently being pulled
    exists_locally: bool = False


@dataclass
class RunResult:
    """Result of running a script in Docker container."""
    command: str = ""                 # Command that was run
    return_code: int = 0              # Exit code (0 = success)
    stdout: str = ""                  # Standard output
    stderr: str = ""                  # Standard error
    success: bool = field(init=False) # Computed from return_code
    duration_sec: float = 0.0         # Execution time

    def __post_init__(self):
        """Set success based on return code."""
        self.success = self.return_code == 0

    def combined_output(self) -> str:
        """Return stdout and stderr combined, line-separated if both exist."""
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout)
        if self.stderr.strip():
            parts.append(self.stderr)
        return "\n".join(parts) if parts else ""


# ──────────────────────────────────────────────────────────────────────────────
# DOCKER MANAGER
# ──────────────────────────────────────────────────────────────────────────────

class DockerManager:
    """
    Manages Docker Desktop and container lifecycle for OpenLane workflows.
    Abstracts platform-specific details (Windows WSL2, Linux, etc.) behind
    a clean interface.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_windows = sys.platform.startswith("win")
        self.is_linux = sys.platform.startswith("linux")
        # Use latest OpenLane image - compatible after PDK NAMECASESENSITIVE patch
        self.docker_image = os.environ.get("DOCKER_IMAGE", "efabless/openlane:latest")
        self.container_timeout = int(os.environ.get("DOCKER_CONTAINER_TIMEOUT", "300"))
        # Auto-detect PDK root so it can be mounted into containers
        self.pdk_root = self._detect_pdk_root()

    def _detect_pdk_root(self) -> Optional[str]:
        """Detect PDK root directory from env var or common locations."""
        env_root = os.environ.get("PDK_ROOT", "")
        if env_root:
            candidate = Path(env_root)
            if candidate.exists():
                return str(candidate)
        # Common Windows locations
        for p in [Path(r"C:\pdk"), Path.home() / "pdk"]:
            if p.exists() and (p / "sky130A").exists():
                return str(p)
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # VERIFICATION & STATUS
    # ──────────────────────────────────────────────────────────────────────────

    def verify_installation(self) -> DockerStatus:
        """
        Check if Docker is installed, running, and properly configured.
        Returns: DockerStatus with detailed information.
        """
        status = DockerStatus()

        # Check if docker CLI exists
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status.installed = True
                status.version = result.stdout.strip()
            else:
                status.error = "docker --version failed"
                return status
        except FileNotFoundError:
            status.error = "Docker CLI not found. Install Docker Desktop."
            return status
        except subprocess.TimeoutExpired:
            status.error = "docker --version timed out"
            return status

        # Check if Docker daemon is running
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            status.running = result.returncode == 0
            if not status.running:
                status.error = "Docker daemon not running. Start Docker Desktop."
        except subprocess.TimeoutExpired:
            status.error = "docker ps timed out"

        # Detect backend
        if self.is_windows:
            status.backend = DockerBackend.WSL2
            status.wsl2_capable = self._check_wsl2()
        elif self.is_linux:
            status.backend = DockerBackend.NATIVE_LINUX
        else:
            status.backend = DockerBackend.UNKNOWN

        return status

    def _check_wsl2(self) -> bool:
        """Check if WSL2 is available on Windows."""
        try:
            result = subprocess.run(
                ["wsl", "--status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "WSL version" in result.stdout
        except:
            return False

    def ensure_docker_running(self) -> Tuple[bool, str]:
        """
        Ensure Docker daemon is running. Attempt to start it automatically on Windows.
        Returns: (success: bool, message: str)
        """
        status = self.verify_installation()
        
        # If not running, try to start it
        if not status.running:
            if self.is_windows:
                return self._start_docker_windows()
            elif self.is_linux:
                return self._start_docker_linux()
            else:
                return False, "Cannot auto-start Docker on this platform. Please start Docker Desktop manually."
        
        return True, "Docker is running"

    def _start_docker_windows(self) -> Tuple[bool, str]:
        """Attempt to start Docker Desktop on Windows."""
        import time as _time
        
        try:
            # Common Docker Desktop locations
            docker_desktop_paths = [
                r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
                r"C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe",
                Path.home() / "AppData" / "Local" / "Docker" / "Docker Desktop.exe",
            ]
            
            for docker_exe in docker_desktop_paths:
                exe_path = Path(docker_exe)
                if exe_path.exists():
                    self.logger.info(f"Starting Docker Desktop from {exe_path}")
                    subprocess.Popen([str(exe_path)])
                    
                    # Wait for Docker daemon to start (up to 30 seconds)
                    for attempt in range(30):
                        _time.sleep(1)
                        status = self.verify_installation()
                        if status.running:
                            self.logger.info("Docker daemon started successfully")
                            return True, "Docker Desktop started automatically"
                    
                    return False, "Docker Desktop started but daemon not responding (timeout)"
            
            return False, "Docker Desktop executable not found. Please install Docker Desktop for Windows."
        except Exception as e:
            return False, f"Failed to start Docker: {str(e)}"

    def _start_docker_linux(self) -> Tuple[bool, str]:
        """Attempt to start Docker daemon on Linux."""
        try:
            subprocess.run(["sudo", "systemctl", "start", "docker"], 
                          capture_output=True, timeout=10)
            import time as _time
            _time.sleep(2)
            
            status = self.verify_installation()
            if status.running:
                return True, "Docker daemon started via systemctl"
            else:
                return False, "systemctl start docker completed but daemon not responding"
        except Exception as e:
            return False, f"Failed to start Docker daemon: {str(e)}"

    # ──────────────────────────────────────────────────────────────────────────
    # PATH TRANSLATION (Windows ↔ Docker/Linux)
    # ──────────────────────────────────────────────────────────────────────────

    def windows_to_docker_path(self, win_path: str) -> str:
        """
        Convert Windows path to Docker (Linux) path format.
        Examples:
          C:\\Users\\venka\\work  → /mnt/c/Users/venka/work
          C:/data                 → /mnt/c/data
          /home/user              → /home/user  (already Docker format)
        """
        if not win_path:
            return ""

        # Already a Linux/Docker path
        if win_path.startswith("/"):
            return win_path

        # Normalize Windows path: C:\path or C:/path
        # Replace backslashes with forward slashes
        path_str = str(win_path).replace("\\", "/")

        # Extract drive letter and path
        # Pattern: C: or c: followed by /path
        match = re.match(r"^([a-zA-Z]):(.*)$", path_str)
        if match:
            drive_letter = match.group(1).lower()
            rest_path = match.group(2)
            return f"/mnt/{drive_letter}{rest_path}"

        # Already relative or absolute Linux path
        return path_str

    def docker_to_windows_path(self, docker_path: str) -> str:
        """
        Convert Docker (Linux) path back to Windows format.
        Examples:
          /mnt/c/Users/venka/work  → C:\\Users\\venka\\work
          /home/user               → /home/user  (no conversion for Linux paths)
        """
        if not docker_path:
            return ""

        # Pattern: /mnt/X/... → X:/...
        match = re.match(r"^/mnt/([a-zA-Z])/(.*)$", docker_path)
        if match:
            drive_letter = match.group(1).upper()
            rest_path = match.group(2).replace("/", "\\")
            return f"{drive_letter}:\\{rest_path}"

        return docker_path

    # ──────────────────────────────────────────────────────────────────────────
    # IMAGE MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────

    def check_image(self) -> ImageInfo:
        """Check if OpenLane image exists locally."""
        info = ImageInfo(name=self.docker_image)

        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.docker_image],
                capture_output=True,
                text=True,
                timeout=5
            )
            info.exists_locally = result.returncode == 0

            if info.exists_locally:
                try:
                    img_data = json.loads(result.stdout)
                    if img_data:
                        size_bytes = img_data[0].get("Size", 0)
                        info.size_gb = size_bytes / (1024**3)
                except:
                    pass
        except:
            pass

        return info

    def pull_image(self, progress_callback=None) -> ContainerResult:
        """
        Pull OpenLane Docker image from registry.
        progress_callback: Optional function(line) called for each output line.
        Returns: ContainerResult with pull status.
        """
        result = ContainerResult()

        try:
            process = subprocess.Popen(
                ["docker", "pull", self.docker_image],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            output_lines = []
            for line in process.stdout:
                line = line.rstrip()
                output_lines.append(line)
                if progress_callback:
                    progress_callback(line)

            process.wait(timeout=self.container_timeout)
            result.returncode = process.returncode
            result.stdout = "\n".join(output_lines)

        except subprocess.TimeoutExpired:
            process.kill()
            result.returncode = 1
            result.exception = TimeoutError(f"Image pull exceeded {self.container_timeout}s")
        except Exception as e:
            result.returncode = 1
            result.exception = e

        return result

    # ──────────────────────────────────────────────────────────────────────────
    # CONTAINER EXECUTION
    # ──────────────────────────────────────────────────────────────────────────

    def run_script(
        self,
        script_content: str,
        script_name: str,
        work_dir=None,
        interpreter=None,
        extra_mounts=None,
        env_vars=None,
        timeout: int = 3600,
    ) -> RunResult:
        """
        Write script_content to work_dir/script_name and execute it inside
        the OpenLane Docker container.

        This is the generic entry point used by all phase modules:
          Placer, CTSEngine,  DetailRouter, GDSGenerator, etc.

        Interpreter selection by file extension (or explicit override):
          .tcl  →  openroad /work/<script_name> [default]
          .sh   →  bash /work/<script_name>
          .py   →  python3 /work/<script_name>
          other →  bash -c /work/<script_name>
          
        Args:
            script_content: Text content of the script to run.
            script_name:    Filename (e.g. "placement.tcl").
                            Written to work_dir on Windows; visible at
                            /work/<script_name> inside the container.
            work_dir:       Windows directory mounted as /work.
                            Defaults to current tmp directory.
            interpreter:    Override interpreter detection (e.g., "yosys", "openroad")
            extra_mounts:   Extra {host_path: container_path} mounts.
            env_vars:       Extra {KEY: value} environment variables.
            timeout:        Seconds before the container is killed.

        Returns:
            RunResult with .success, .stdout, .stderr, .combined_output()
        """
        import time as _time
        from pathlib import Path as _Path

        # ── resolve work directory ────────────────────────────────────
        host_work = _Path(work_dir or ".") if work_dir else _Path.cwd()
        host_work = _Path(host_work).resolve()
        host_work.mkdir(parents=True, exist_ok=True)

        # ── write script to disk so Docker can mount it ───────────────
        script_path = host_work / script_name
        script_path.write_text(script_content, encoding="utf-8")
        
        # DEBUG: Log script write for troubleshooting
        if not script_path.exists():
            return RunResult(
                command     = f"openroad {script_name}",
                return_code = -1,
                stderr      = f"CRITICAL: Script file not written! {script_path}",
            )

        # ── pick interpreter from file extension or explicit parameter ──
        ext = _Path(script_name).suffix.lower()
        interpreter_map = {
            ".tcl": "openroad -no_init -exit",
            ".sh":  "bash",
            ".py":  "python3",
        }
        if interpreter:
            # Explicit interpreter override
            selected_interpreter = interpreter
        else:
            # Auto-detect from extension
            selected_interpreter = interpreter_map.get(ext, "bash")

        # ── build container command ───────────────────────────────────
        container_script = f"/work/{script_name}"
        if ext == ".sh":
            command = f"chmod +x {container_script} && {container_script}"
        else:
            command = f"{selected_interpreter} {container_script}"

        # ── delegate to internal helper ────────────────────────────────
        return self._docker_run_with_work(
            command      = command,
            host_work    = host_work,
            extra_mounts = extra_mounts or {},
            extra_env    = env_vars or {},
            timeout      = timeout,
        )

    def _docker_run_with_work(
        self,
        command: str,
        host_work,
        extra_mounts: dict,
        extra_env: dict,
        timeout: int,
    ) -> RunResult:
        """
        Internal: run command inside Docker with explicit work dir mount.

        Separated from run_openroad() so we can pass the correct host_work
        without changing existing method signatures.
        """
        import subprocess as _sp
        import time as _time
        from pathlib import Path as _Path

        # ── Ensure Docker is running ──────────────────────────────────
        docker_ok, docker_msg = self.ensure_docker_running()
        if not docker_ok:
            return RunResult(
                command     = command,
                return_code = -1,
                stderr      = f"CRITICAL: {docker_msg}",
            )

        docker_exe = self._find_docker_exe()
        if not docker_exe:
            return RunResult(
                command     = command,
                return_code = -1,
                stderr      = "ERROR: docker.exe not found in PATH",
            )

        # ── build mount arguments ─────────────────────────────────────
        # Use Windows-style paths for -v mounts; Docker Desktop handles
        # the translation to Linux paths internally.
        host_work_str = str(host_work)

        mounts = [
            "-v", f"{host_work_str}:/work",
        ]

        # Always mount PDK if available
        if self.pdk_root:
            mounts.extend(["-v", f"{self.pdk_root}:/pdk"])

        for host_p, cont_p in extra_mounts.items():
            mounts += ["-v", f"{str(host_p)}:{cont_p}"]

        # ── build environment variable arguments ──────────────────────
        base_env = {
            "DEBIAN_FRONTEND": "noninteractive",
        }
        if self.pdk_root:
            base_env.update({
                "PDK_ROOT":         "/pdk",
                "PDK":              "sky130A",
                "STD_CELL_LIBRARY": "sky130_fd_sc_hd",
            })
        base_env.update(extra_env)
        
        env_args = []
        for k, v in base_env.items():
            env_args += ["-e", f"{k}={v}"]

        # ── assemble and run ──────────────────────────────────────────
        cmd = (
            [docker_exe, "run", "--rm"]
            + mounts
            + env_args
            + ["-w", "/work", self.docker_image, "/bin/sh", "-c", command]
        )
        
        # DEBUG: Log the command (first 500 chars)
        import logging as _logging
        _logger = _logging.getLogger(__name__)
        _logger.debug(f"Docker command: {' '.join(cmd[:15])}... [full: {' '.join(cmd)}]")

        start = _time.time()
        try:
            proc = _sp.run(
                cmd,
                capture_output = True,
                text           = True,
                timeout        = timeout,
            )
            return RunResult(
                command      = command,
                return_code  = proc.returncode,
                stdout       = proc.stdout,
                stderr       = proc.stderr,
                duration_sec = _time.time() - start,
            )
        except _sp.TimeoutExpired:
            return RunResult(
                command      = command,
                return_code  = -1,
                stderr       = f"ERROR: command timed out after {timeout}s",
                duration_sec = _time.time() - start,
            )
        except Exception as exc:
            return RunResult(
                command     = command,
                return_code = -1,
                stderr      = f"ERROR: {exc}",
            )

    def _find_docker_exe(self) -> str:
        """Find docker.exe in PATH, return full path or None."""
        import shutil
        return shutil.which("docker.exe") or shutil.which("docker")

    def run_openroad(
        self,
        work_dir: str,
        command: str,
        mounts: Optional[Dict[str, str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ContainerResult:
        """
        Run OpenROAD command inside Docker container.
        
        Args:
            work_dir: Windows or Linux path to mount as /work
            command: Full command to run (e.g., "openroad /work/script.tcl")
            mounts: Additional {host_path: container_path} mounts
            env_vars: Environment variables to pass into container
        
        Returns: ContainerResult with output
        """
        result = ContainerResult()

        try:
            # Translate paths
            docker_work = self.windows_to_docker_path(work_dir)
            
            # Build mount dict
            all_mounts = {work_dir: "/work"}
            if mounts:
                all_mounts.update(mounts)

            # Build docker run command
            cmd = ["docker", "run", "--rm"]

            # Add mounts
            for host_path, container_path in all_mounts.items():
                # Convert host path for Docker
                docker_host_path = self.windows_to_docker_path(host_path) if self.is_windows else host_path
                cmd.extend(["-v", f"{docker_host_path}:{container_path}"])

            # Add environment variables
            if env_vars:
                for key, val in env_vars.items():
                    cmd.extend(["-e", f"{key}={val}"])

            # Add working directory and image
            cmd.extend(["-w", "/work", self.docker_image])

            # Add the actual command (as shell command)
            cmd.append("sh")
            cmd.append("-c")
            cmd.append(command)

            # Run container
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.container_timeout
            )

            result.returncode = process.returncode
            result.stdout = process.stdout
            result.stderr = process.stderr

        except subprocess.TimeoutExpired:
            result.returncode = 1
            result.exception = TimeoutError(f"Container execution exceeded {self.container_timeout}s")
        except Exception as e:
            result.returncode = 1
            result.stderr = str(e)
            result.exception = e

        return result

    def run_magic(
        self,
        work_dir: str,
        command: str,
        mounts: Optional[Dict[str, str]] = None,
    ) -> ContainerResult:
        """Run Magic/extract command inside Docker container."""
        return self.run_openroad(
            work_dir=work_dir,
            command=command,
            mounts=mounts
        )

    # ──────────────────────────────────────────────────────────────────────────
    # UTILITY METHODS
    # ──────────────────────────────────────────────────────────────────────────

    def get_docker_info(self) -> Dict:
        """Get Docker system info as dictionary."""
        result = {
            "installed": False,
            "running": False,
            "info": {}
        }

        try:
            output = subprocess.check_output(
                ["docker", "info", "--format", "json"],
                text=True,
                timeout=5
            )
            result["installed"] = True
            result["running"] = True
            try:
                result["info"] = json.loads(output)
            except:
                pass
        except:
            pass

        return result

    def print_status(self):
        """Print formatted Docker status."""
        status = self.verify_installation()
        
        print("\n" + "="*70)
        print("  Docker Status  –  RTL-Gen AI")
        print("="*70)
        print(f"  Installed     : {'✅ Yes' if status.installed else '❌ No'}")
        print(f"  Running       : {'✅ Yes' if status.running else '❌ No'}")
        print(f"  Version       : {status.version if status.version else 'N/A'}")
        print(f"  Backend       : {status.backend.value}")
        if self.is_windows:
            print(f"  WSL2 Ready    : {'✅ Yes' if status.wsl2_capable else '❌ No'}")
        if status.error:
            print(f"  Error         : ⚠️  {status.error}")

        image = self.check_image()
        print(f"\n  Image         : {image.name}")
        print(f"  Local Copy    : {'✅ Yes' if image.exists_locally else '❌ No'}")
        if image.exists_locally:
            print(f"  Size          : {image.size_gb:.2f} GB")

        print("="*70 + "\n")
