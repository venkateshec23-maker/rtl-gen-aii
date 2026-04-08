# ============================================================
# FILE: python/fix_pdk_synthesis.py
# Run this ONCE: python python/fix_pdk_synthesis.py
# It patches docker_manager.py and full_flow.py in-place.
# ============================================================

import re
from pathlib import Path

ROOT = Path(__file__).parent  # python/
DM   = ROOT / "docker_manager.py"
FF   = ROOT / "full_flow.py"

# ─────────────────────────────────────────────────────────────────
# PATCH 1 — docker_manager.py : expand _detect_pdk_root()
# ─────────────────────────────────────────────────────────────────
OLD_DETECT = '''    def _detect_pdk_root(self) -> Optional[str]:
        """Detect PDK root directory from env var or common locations."""
        env_root = os.environ.get("PDK_ROOT", "")
        if env_root:
            candidate = Path(env_root)
            if candidate.exists():
                return str(candidate)
        # Common Windows locations
        for p in [Path(r"C:\\pdk"), Path.home() / "pdk"]:
            if p.exists() and (p / "sky130A").exists():
                return str(p)
        return None'''

NEW_DETECT = '''    def _detect_pdk_root(self) -> Optional[str]:
        """
        Detect PDK root directory from environment variables or well-known locations.
        The PDK root must contain a sky130A subdirectory to be considered valid.
        Search order:
          1. PDK_ROOT env var
          2. PDKPATH env var
          3. Common Windows install locations
          4. WSL2 accessible paths
        """
        import os as _os
        # 1. Explicit environment variables (highest priority)
        for env_var in ("PDK_ROOT", "PDKPATH", "PDK_PATH"):
            env_root = _os.environ.get(env_var, "").strip()
            if env_root:
                candidate = Path(env_root)
                if candidate.exists() and (candidate / "sky130A").exists():
                    self.logger.info(f"PDK found via env {env_var}: {candidate}")
                    return str(candidate)

        # 2. Common Windows installation paths (ordered by likelihood)
        user_home = Path.home()
        common_paths = [
            Path(r"C:\\pdk"),
            Path(r"C:\\PDK"),
            Path(r"C:\\open_pdks"),
            Path(r"C:\\tools\\pdk"),
            Path(r"D:\\pdk"),
            user_home / "pdk",
            user_home / "PDK",
            user_home / "open_pdks",
            user_home / "Documents" / "pdk",
            user_home / "Documents" / "rtl-gen-aii" / "pdk",
            # OpenLane default
            Path(r"C:\\Users\\venka\\pdk"),
            Path(r"C:\\openlane\\pdks"),
        ]
        for p in common_paths:
            if p.exists() and (p / "sky130A").exists():
                self.logger.info(f"PDK found at: {p}")
                return str(p)

        # 3. Not found — warn clearly so user knows exactly what to do
        self.logger.warning(
            "Sky130A PDK not found. Synthesis will use generic cell mapping "
            "(no liberty file). Physical design stages (placement, CTS, routing) "
            "may be degraded or skipped.\\n"
            "To fix: set environment variable PDK_ROOT=<path containing sky130A/>\\n"
            "  e.g. set PDK_ROOT=C:\\\\pdk  (then restart VS Code)\\n"
            "Or install via: pip install volare && volare enable sky130"
        )
        return None'''

# ─────────────────────────────────────────────────────────────────
# PATCH 2 — docker_manager.py : fix windows_to_docker_path()
# Returns the correct CONTAINER path based on actual mounts,
# not the WSL /mnt/c/ format which is wrong for Docker Desktop.
# ─────────────────────────────────────────────────────────────────
OLD_W2D = '''    def windows_to_docker_path(self, win_path: str) -> str:
        """
        Convert Windows path to Docker (Linux) path format.
        Examples:
          C:\\\\Users\\\\venka\\\\work  → /mnt/c/Users/venka/work
          C:/data                 → /mnt/c/data
          /home/user              → /home/user  (already Docker format)
        """
        if not win_path:
            return ""

        # Already a Linux/Docker path
        if win_path.startswith("/"):
            return win_path

        # Normalize Windows path: C:\\path or C:/path
        # Replace backslashes with forward slashes
        path_str = str(win_path).replace("\\\\", "/")

        # Extract drive letter and path
        # Pattern: C: or c: followed by /path
        match = re.match(r"^([a-zA-Z]):(.*)$", path_str)
        if match:
            drive_letter = match.group(1).lower()
            rest_path = match.group(2)
            return f"/mnt/{drive_letter}{rest_path}"

        # Already relative or absolute Linux path
        return path_str'''

NEW_W2D = '''    def windows_to_docker_path(self, win_path: str) -> str:
        """
        Convert a Windows host path to its equivalent path INSIDE the Docker container,
        based on the volume mounts that this DockerManager will apply.

        Mount table (host → container):
          <host_work>  → /work
          <pdk_root>   → /pdk   (if PDK was detected)

        Docker Desktop on Windows handles -v C:\\path:/container natively.
        Inside the container the correct path is /container/..., NOT /mnt/c/...
        /mnt/c/ is WSL2 filesystem notation and is NOT the same as a Docker mount.

        Examples (assuming work_dir=C:\\Users\\venka\\Documents\\rtl-gen-aii\\work,
                          pdk_root=C:\\pdk):
          C:\\Users\\venka\\Documents\\rtl-gen-aii\\work\\rtl.v → /work/rtl.v
          C:\\pdk\\sky130A\\libs.ref\\...                        → /pdk/sky130A/libs.ref/...
          /work/already_linux                                    → /work/already_linux
        """
        if not win_path:
            return ""

        # Already a Linux/Docker path — return as-is
        if str(win_path).startswith("/"):
            return str(win_path)

        # Normalise to forward slashes for comparison
        norm = str(win_path).replace("\\\\", "/").replace("\\", "/")

        # Build mount table: {normalised_host_prefix → container_prefix}
        mount_table: dict[str, str] = {}

        # /work mount — resolve work_dir if available
        if hasattr(self, "work_dir") and self.work_dir:
            host_work_norm = str(self.work_dir).replace("\\\\", "/").replace("\\", "/")
            mount_table[host_work_norm.rstrip("/")] = "/work"

        # /pdk mount
        if self.pdk_root:
            pdk_norm = str(self.pdk_root).replace("\\\\", "/").replace("\\", "/")
            mount_table[pdk_norm.rstrip("/")] = "/pdk"

        # Match longest prefix first (most specific mount wins)
        for host_prefix in sorted(mount_table.keys(), key=len, reverse=True):
            if norm.startswith(host_prefix):
                container_prefix = mount_table[host_prefix]
                remainder = norm[len(host_prefix):]
                # Ensure leading slash
                if remainder and not remainder.startswith("/"):
                    remainder = "/" + remainder
                return container_prefix + remainder

        # Fallback: no known mount matched.
        # Use /mnt/<drive>/ convention as best-effort (WSL2 passthrough).
        match = re.match(r"^([a-zA-Z]):(.*)$", norm)
        if match:
            drive_letter = match.group(1).lower()
            rest_path = match.group(2).replace("\\\\", "/")
            self.logger.warning(
                f"Path '{win_path}' has no matching Docker mount. "
                f"Falling back to /mnt/{drive_letter}{rest_path}. "
                "Ensure the directory is mounted with extra_mounts."
            )
            return f"/mnt/{drive_letter}{rest_path}"

        return norm'''

# ─────────────────────────────────────────────────────────────────
# PATCH 3 — full_flow.py : fix empty module threshold
# endmodule is NOT excluded by the filter, so it counts as 1.
# A module with one logic line → 2 meaningful lines.
# Threshold must be <= 2, not <= 1.
# ─────────────────────────────────────────────────────────────────
OLD_THRESHOLD = '''        # Check if module has only port declarations (empty implementation)
        if len(meaningful_lines) <= 1:  # Only 'module name' and 'endmodule'
            raise FlowError(
                "synthesis",
                f"RTL module '{top_module}' has no implementation logic.\\n"
                f"Add combinational or sequential logic to your Verilog design.\\n"
                f"Example: assign out = in1 & in2;  // AND gate\\n"
                f"Or use a template (Counter, Adder, Traffic Light) instead of Blank.",
            )'''

NEW_THRESHOLD = '''        # Check if module has only port declarations (empty implementation).
        # The filter above does NOT exclude 'endmodule', so a truly empty module
        # yields exactly ["endmodule"] → len == 1.
        # A module with one logic statement yields ["<stmt>", "endmodule"] → len == 2.
        # Threshold is <= 1 to catch ONLY the completely empty case.
        # We keep <= 1 (not <= 2) so a single assign/always still passes.
        # What we also need to exclude: lines that are just punctuation (; { } begin end)
        meaningful_non_structural = [
            ln for ln in meaningful_lines
            if ln not in ("endmodule", "end", "begin", ";", ")")
            and not ln.startswith("end")  # endcase, endfunction, endtask, etc.
        ]
        if len(meaningful_non_structural) == 0:
            raise FlowError(
                "synthesis",
                f"RTL module '{top_module}' has no implementation logic.\\n"
                f"Add combinational or sequential logic to your Verilog design.\\n"
                f"Example: assign out = in1 & in2;  // AND gate\\n"
                f"Or use a template (Counter, Adder, Traffic Light) instead of Blank.",
            )'''

OLD_SYNTH_CALL = '''        # IMPORTANT: every path in this script uses /work/ or /pdk/.'''

NEW_SYNTH_CALL = '''        # IMPORTANT: every path in this script uses /work/ or /pdk/.
        # Detect whether PDK is available inside the container.
        # DockerManager mounts PDK at /pdk if pdk_root is set.
        pdk_available = (
            hasattr(self.docker, "pdk_root") and self.docker.pdk_root is not None
        ) if self.docker else False

        liberty_path = (
            "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        )'''

# ─────────────────────────────────────────────────────────────────
# APPLY ALL PATCHES
# ─────────────────────────────────────────────────────────────────
def apply_patch(filepath: Path, old: str, new: str, label: str):
    text = filepath.read_text(encoding="utf-8")
    if old not in text:
        # Try normalising line endings
        old_norm = old.replace("\r\n", "\n")
        text_norm = text.replace("\r\n", "\n")
        if old_norm in text_norm:
            text = text_norm.replace(old_norm, new)
            filepath.write_text(text, encoding="utf-8")
            print(f"  ✅  {label}")
            return
        print(f"  ⚠️  SKIP {label} — pattern not found (may already be patched)")
        return
    text = text.replace(old, new, 1)
    filepath.write_text(text, encoding="utf-8")
    print(f"  ✅  {label}")


print("\n=== RTL-Gen AI: PDK + Synthesis + Path Fix ===\n")

print("Patching docker_manager.py ...")
apply_patch(DM, OLD_DETECT, NEW_DETECT, "_detect_pdk_root() — expanded PDK search")
apply_patch(DM, OLD_W2D,    NEW_W2D,    "windows_to_docker_path() — mount-aware conversion")

print("\nPatching full_flow.py ...")
apply_patch(FF, OLD_THRESHOLD, NEW_THRESHOLD, "Empty module detection — fixed structural keyword exclusion")
apply_patch(FF, OLD_SYNTH_CALL, NEW_SYNTH_CALL, "Yosys synth — PDK availability detection injected")

print("\n=== Patch complete. ===")
print("Next steps:")
print("  1. Run: python python/fix_pdk_synthesis.py")
print("  2. Set env var if PDK exists:  set PDK_ROOT=C:\\pdk")
print("  3. Re-run full pipeline test")
print("  4. Check logs for 'PDK found at:' or 'Sky130A PDK not found' message")
print()
print("If PDK not installed, get it via:")
print("  pip install volare")
print("  volare enable --pdk sky130 --pdk-root C:\\pdk <version>")
print("Or manually: https://github.com/RTimothyEdwards/open_pdks")
