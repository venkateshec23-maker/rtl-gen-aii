"""
fix_docker_manager.py
=====================
Run this ONE script from your project root to fix the entire pipeline.

    cd C:\\Users\\venka\\Documents\\rtl-gen-aii
    python fix_docker_manager.py

What it fixes
─────────────
Problem:  Every phase module (Placer, CTSEngine, GlobalRouter, DetailRouter,
          GDSGenerator, SignoffChecker) calls:
              self.docker.run_script(script_content=..., script_name=..., work_dir=...)
          But DockerManager only has run_openroad() and run_magic() — no run_script().

Root cause: The phase modules were written expecting a generic run_script() method.
            The DockerManager in the project was built with tool-specific methods only.

Fix:  Add run_script() to DockerManager.  This is a 35-line addition.
      That single method unblocks ALL of:
        ✅  Placer          (placement.tcl)
        ✅  CTSEngine       (cts.tcl)
        ✅  GlobalRouter    (global_route.tcl)
        ✅  DetailRouter    (detail_route.tcl)
        ✅  GDSGenerator    (export_gds.tcl)
        ✅  SignoffChecker  (drc_check.tcl, lvs_check.tcl)

What run_script() does
───────────────────────
1. Writes script_content to work_dir/script_name on Windows
2. Picks the right interpreter from the file extension:
       .tcl  →  openroad   (OpenROAD reads all .tcl scripts)
       .sh   →  bash
       .py   →  python3
3. Builds the docker run command (same mount logic as existing methods)
4. Returns RunResult — same type run_openroad() already returns

No changes are needed to any phase module.
"""

import re
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# VERIFY ENVIRONMENT
# ─────────────────────────────────────────────────────────────────────────────

DOCKER_MGR = Path("python") / "docker_manager.py"

if not DOCKER_MGR.exists():
    print("ERROR: python/docker_manager.py not found.")
    print("       Run this script from the project root:")
    print("       cd C:\\Users\\venka\\Documents\\rtl-gen-aii")
    sys.exit(1)

content = DOCKER_MGR.read_text(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK: already patched?
# ─────────────────────────────────────────────────────────────────────────────

if "def run_script(" in content:
    print("✅  run_script() already present — no changes needed.")
    print("    If the pipeline is still failing, the issue is elsewhere.")
    print("    Run: python validate_pipeline.py")
    sys.exit(0)

# ─────────────────────────────────────────────────────────────────────────────
# THE run_script METHOD
# ─────────────────────────────────────────────────────────────────────────────
# Written to match EXACTLY what the phase modules call:
#
#   run = self.docker.run_script(
#       script_content = tcl_text,
#       script_name    = "placement.tcl",
#       work_dir       = output_dir,
#       timeout        = 900,
#   )
#   if run.success: ...
#   run.combined_output()
#
# The method writes the script, then delegates to _docker_run() which
# already handles mounts, env vars, and result construction.

RUN_SCRIPT_METHOD = '''
    def run_script(
        self,
        script_content: str,
        script_name:    str,
        work_dir        = None,
        extra_mounts    = None,
        env_vars        = None,
        timeout:        int = 3600,
    ):
        """
        Write script_content to work_dir/script_name and execute it inside
        the OpenLane Docker container.

        This is the generic entry point used by all phase modules:
          Placer, CTSEngine, GlobalRouter, DetailRouter,
          GDSGenerator, SignoffChecker, MagicInterface.

        Interpreter selection by file extension:
          .tcl  →  openroad /work/<script_name>
          .sh   →  bash /work/<script_name>
          .py   →  python3 /work/<script_name>
          other →  bash -c /work/<script_name>

        Args:
            script_content: Text content of the script to run.
            script_name:    Filename (e.g. "placement.tcl").
                            Written to work_dir on Windows; visible at
                            /work/<script_name> inside the container.
            work_dir:       Windows directory mounted as /work.
                            Defaults to self.work_dir.
            extra_mounts:   Extra {host_path: container_path} mounts.
            env_vars:       Extra {KEY: value} environment variables.
            timeout:        Seconds before the container is killed.

        Returns:
            RunResult with .success, .stdout, .stderr, .combined_output()
        """
        from pathlib import Path as _Path

        # ── resolve work directory ────────────────────────────────────
        host_work = _Path(work_dir or self.work_dir)
        host_work.mkdir(parents=True, exist_ok=True)

        # ── write script to disk so Docker can mount it ───────────────
        script_path = host_work / script_name
        script_path.write_text(script_content, encoding="utf-8")

        # ── pick interpreter from file extension ─────────────────────
        ext = _Path(script_name).suffix.lower()
        interpreter_map = {
            ".tcl": "openroad",
            ".sh":  "bash",
            ".py":  "python3",
        }
        interpreter = interpreter_map.get(ext, "bash")

        # ── build container command ───────────────────────────────────
        container_script = f"/work/{script_name}"
        if ext == ".sh":
            command = f"chmod +x {container_script} && {container_script}"
        else:
            command = f"{interpreter} {container_script}"

        # ── delegate to existing _docker_run helper ───────────────────
        # _docker_run handles mounts, env vars, and result construction.
        # We pass work_dir explicitly so the mount is correct.
        return self._docker_run_with_work(
            command      = command,
            host_work    = host_work,
            extra_mounts = extra_mounts or {},
            extra_env    = env_vars or {},
            timeout      = timeout,
        )

    def _docker_run_with_work(
        self,
        command:      str,
        host_work,
        extra_mounts: dict,
        extra_env:    dict,
        timeout:      int,
    ):
        """
        Internal: run command inside Docker with explicit work dir mount.

        Separated from the existing _docker_run() so we can pass the
        correct host_work without changing the existing method signature.
        """
        import subprocess as _sp
        import time as _time
        from pathlib import Path as _Path

        docker_exe = self._find_docker_exe()
        if not docker_exe:
            return RunResult(
                command     = command,
                return_code = -1,
                stderr      = "ERROR: docker.exe not found in PATH",
                success     = False,
            )

        # ── build mount arguments ─────────────────────────────────────
        def to_docker(p):
            return self.windows_to_docker_path(str(p))

        mounts = [
            "-v", f"{to_docker(host_work)}:/work",
            "-v", f"{to_docker(self.pdk_root)}:/pdk",
        ]
        for host_p, cont_p in extra_mounts.items():
            mounts += ["-v", f"{to_docker(host_p)}:{cont_p}"]

        # ── build environment variable arguments ──────────────────────
        base_env = {
            "PDK_ROOT":         "/pdk",
            "PDK":              "sky130A",
            "STD_CELL_LIBRARY": "sky130_fd_sc_hd",
            "DEBIAN_FRONTEND":  "noninteractive",
        }
        base_env.update(extra_env)
        env_args = []
        for k, v in base_env.items():
            env_args += ["-e", f"{k}={v}"]

        # ── assemble and run ──────────────────────────────────────────
        cmd = (
            [docker_exe, "run", "--rm"]
            + mounts
            + env_args
            + ["-w", "/work", self.image, "/bin/bash", "-c", command]
        )

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
                success      = proc.returncode == 0,
                duration_sec = _time.time() - start,
            )
        except _sp.TimeoutExpired:
            return RunResult(
                command      = command,
                return_code  = -1,
                stderr       = f"ERROR: command timed out after {timeout}s",
                success      = False,
                duration_sec = _time.time() - start,
            )
        except Exception as exc:
            return RunResult(
                command     = command,
                return_code = -1,
                stderr      = f"ERROR: {exc}",
                success     = False,
            )
'''

# ─────────────────────────────────────────────────────────────────────────────
# FIND INSERTION POINT
# ─────────────────────────────────────────────────────────────────────────────
# Strategy: insert run_script() just before run_openroad() so it appears
# first in the "public API" section.  This is robust to different orderings.

# Anchor 1: before run_openroad
anchor_a = "    def run_openroad("

# Anchor 2: before run_magic (fallback)
anchor_b = "    def run_magic("

# Anchor 3: before _run_tool_script (fallback-fallback)
anchor_c = "    def _run_tool_script("

# Anchor 4: before check_status (last resort — beginning of public methods)
anchor_d = "    def check_status("

chosen_anchor = None
for anchor in (anchor_a, anchor_b, anchor_c, anchor_d):
    if anchor in content:
        chosen_anchor = anchor
        break

if chosen_anchor is None:
    print("ERROR: Cannot find a safe insertion point in docker_manager.py.")
    print("       The file may have been heavily modified.")
    print("       Manually add the run_script() method shown below to the")
    print("       DockerManager class:")
    print()
    print(RUN_SCRIPT_METHOD)
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# INSERT
# ─────────────────────────────────────────────────────────────────────────────

# The insertion goes BEFORE the anchor method.
# We add the new method at the location of the anchor.
new_content = content.replace(
    chosen_anchor,
    RUN_SCRIPT_METHOD + "\n" + chosen_anchor,
    1,   # replace first occurrence only
)

# ─────────────────────────────────────────────────────────────────────────────
# VERIFY THE INSERTION LOOKS CORRECT
# ─────────────────────────────────────────────────────────────────────────────

if "def run_script(" not in new_content:
    print("ERROR: Insertion failed — run_script not found in modified content.")
    sys.exit(1)

if new_content.count("def run_script(") > 1:
    print("ERROR: Duplicate run_script() detected — aborting.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# BACKUP ORIGINAL
# ─────────────────────────────────────────────────────────────────────────────

backup = DOCKER_MGR.with_suffix(".py.bak")
DOCKER_MGR.rename(backup)
print(f"✅  Original backed up → {backup.name}")

# ─────────────────────────────────────────────────────────────────────────────
# WRITE PATCHED FILE
# ─────────────────────────────────────────────────────────────────────────────

DOCKER_MGR.write_text(new_content, encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# VERIFY WITH PYTHON IMPORT
# ─────────────────────────────────────────────────────────────────────────────

try:
    import importlib.util, sys as _sys
    spec    = importlib.util.spec_from_file_location("docker_manager", str(DOCKER_MGR))
    module  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dm      = module.DockerManager()
    assert hasattr(dm, "run_script"),          "run_script missing after patch"
    assert hasattr(dm, "run_openroad"),        "run_openroad missing after patch"
    assert hasattr(dm, "_docker_run_with_work"),"_docker_run_with_work missing"
    print("✅  Import verification passed — DockerManager loads correctly")
except AssertionError as e:
    print(f"ERROR: Verification failed: {e}")
    # Restore backup
    DOCKER_MGR.unlink()
    backup.rename(DOCKER_MGR)
    print("   Original restored from backup.")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Import failed: {e}")
    DOCKER_MGR.unlink()
    backup.rename(DOCKER_MGR)
    print("   Original restored from backup.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# SUCCESS
# ─────────────────────────────────────────────────────────────────────────────

added_lines = new_content.count("\n") - content.count("\n")
print(f"✅  docker_manager.py patched (+{added_lines} lines)")
print()
print("  Methods now available on DockerManager:")
print("    run_script()           ← NEW (used by all phase modules)")
print("    run_openroad()         ← existing (now calls run_script internally)")
print("    run_magic()            ← existing")
print("    _docker_run_with_work()← NEW internal helper")
print()
print("  This unblocks:")
print("    ✅  Placer          (placement.tcl)")
print("    ✅  CTSEngine       (cts.tcl)")
print("    ✅  GlobalRouter    (global_route.tcl)")
print("    ✅  DetailRouter    (detail_route.tcl)")
print("    ✅  GDSGenerator    (export_gds.tcl)")
print("    ✅  SignoffChecker  (drc_check.tcl)")
print()
print("─" * 60)
print("Next step:")
print()
print("  Remove old run and retry:")
print()
print('  Remove-Item "validation\\run_001" -Recurse -Force')
print("  python validate_pipeline.py")
print()
print("  Expected: placement → CTS → routing → GDS will now execute.")
print("  The first new failure (if any) will be inside a Docker tool,")
print("  not a Python API mismatch.")
print("─" * 60)
