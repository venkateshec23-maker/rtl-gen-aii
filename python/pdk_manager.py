"""
pdk_manager.py  –  Sky130 PDK Manager for RTL-Gen AI (Windows)
================================================================
Manages the SkyWater Sky130 Process Design Kit (PDK) on Windows.
Provides a single, clean interface for every other physical-design
module to ask "where is file X?" without knowing the PDK directory
layout.

Sky130A directory tree (what we expect):
    <pdk_root>/sky130A/
    ├── libs.ref/
    │   ├── sky130_fd_sc_hd/       ← High-Density cells (our default)
    │   │   ├── lef/               ← Cell abstracts for placement
    │   │   ├── lib/               ← Timing files per corner
    │   │   ├── gds/               ← Cell GDSII layouts
    │   │   └── spice/             ← SPICE netlists for LVS
    │   ├── sky130_fd_sc_hs/       ← High-Speed cells
    │   └── sky130_fd_io/          ← I/O cells
    └── libs.tech/
        ├── klayout/               ← KLayout DRC / LVS rule decks
        ├── magic/                 ← Magic tech files
        └── openlane/              ← OpenROAD / OpenLane configs

How to get the PDK (run once from PowerShell):
    pip install volare
    volare enable --pdk sky130 --pdk-root C:\\pdk bdc9412b3e468c102d01b7cf6337be06ec6e9c9a
    [System.Environment]::SetEnvironmentVariable("PDK_ROOT","C:\\pdk","User")

Usage example:
    from python.pdk_manager import PDKManager, Sky130Library, TimingCorner
    pdk = PDKManager()          # auto-detects from PDK_ROOT env var
    result = pdk.validate()
    if result.is_valid:
        lef = pdk.get_tech_lef()
        lib = pdk.get_timing_lib(corner=TimingCorner.TT)
    pdk.print_summary()
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class Sky130Library(Enum):
    """
    Available Sky130 standard-cell libraries.
    Pick one per design – HD is the best starting point for ASICs.
    """
    HD   = "sky130_fd_sc_hd"     # High Density   – best area; most used
    HS   = "sky130_fd_sc_hs"     # High Speed     – fastest timing
    MS   = "sky130_fd_sc_ms"     # Medium Speed
    LS   = "sky130_fd_sc_ls"     # Low Speed / Low Power
    HDLL = "sky130_fd_sc_hdll"   # HD + Low Leakage
    LP   = "sky130_fd_sc_lp"     # Low Power
    IO   = "sky130_fd_io"        # I/O ring cells (pad cells)


class TimingCorner(Enum):
    """
    PVT (Process-Voltage-Temperature) corners used in timing analysis.
    TT  = Typical  → use for quick checks
    SS  = Slow     → worst-case setup timing (sign-off)
    FF  = Fast     → worst-case hold timing  (sign-off)
    """
    TT = "tt_025C_1v80"    # Typical process, 25 °C, 1.80 V
    SS = "ss_100C_1v60"    # Slow process, 100 °C, 1.60 V  (slowest)
    FF = "ff_n40C_1v95"    # Fast process, −40 °C, 1.95 V  (fastest)


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class PDKValidationResult:
    """
    Returned by PDKManager.validate().
    is_valid is False if ANY error is present;
    warnings are non-fatal and do not set is_valid=False.
    """
    is_valid: bool                              # Overall pass / fail
    errors:           List[str] = field(default_factory=list)   # Fatal problems
    warnings:         List[str] = field(default_factory=list)   # Non-fatal notes
    missing_files:    List[str] = field(default_factory=list)   # Files not found
    found_libraries:  List[str] = field(default_factory=list)   # Detected libs


@dataclass
class CellInfo:
    """
    File-path record for one standard cell.
    Created by PDKManager.get_cell_info(); cached for speed.
    """
    name:        str               # e.g. "sky130_fd_sc_hd__and2_1"
    library:     str               # e.g. "sky130_fd_sc_hd"
    lef_path:    Optional[Path]    # Abstract (for placement tools)
    gds_path:    Optional[Path]    # Layout   (for GDSII merge)
    spice_path:  Optional[Path]    # SPICE netlist (for LVS)
    lib_paths:   Dict[str, Path] = field(default_factory=dict)  # corner→.lib


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class PDKManager:
    """
    Single source of truth for all Sky130 PDK file paths.

    All other physical-design modules (floorplanner, placer, router,
    drc_checker, gds_generator …) hold a reference to one PDKManager
    instance and call its helper methods instead of hard-coding paths.

    Construction
    ────────────
    PDKManager()                 → auto-detects via PDK_ROOT env var
    PDKManager(pdk_root="C:\\pdk\\sky130A")  → explicit path
    """

    # ── directories that MUST exist for a valid installation ───────────
    _REQUIRED_DIRS = ["libs.ref", "libs.tech"]

    # ── the minimum library set we need ────────────────────────────────
    _REQUIRED_LIBS = [Sky130Library.HD.value]

    def __init__(
        self,
        pdk_root:    Optional[str] = None,
        variant:     str = "sky130A",
        auto_detect: bool = True,
    ) -> None:
        """
        Initialise the PDK manager.

        Args:
            pdk_root:    Full path to sky130A directory.
                         When None and auto_detect=True, common locations
                         are searched (env var, C:\\pdk, home folder …).
            variant:     PDK variant string written into env vars.
            auto_detect: Search common paths if pdk_root is None.
        """
        self.logger = logging.getLogger(__name__)
        self.variant = variant

        # ── resolve the root path ─────────────────────────────────────
        if pdk_root:
            # Caller gave an explicit path – use it regardless of env vars
            self.pdk_root = Path(pdk_root)
            self.logger.info(f"PDK root set explicitly: {self.pdk_root}")

        elif auto_detect:
            # Search the usual suspects on Windows
            detected = self._auto_detect_pdk()
            if detected:
                self.pdk_root = detected
                self.logger.info(f"PDK auto-detected at: {self.pdk_root}")
            else:
                # Fall back to the recommended install path so the
                # error message tells the user exactly where to put it
                self.pdk_root = Path(r"C:\pdk") / variant
                self.logger.warning(
                    f"PDK not found.  Expected at: {self.pdk_root}\n"
                    f"  → Run: pip install volare && "
                    f"volare enable --pdk sky130 --pdk-root C:\\pdk "
                    f"bdc9412b3e468c102d01b7cf6337be06ec6e9c9a"
                )
        else:
            # No auto-detect; user will call pdk.pdk_root = ... later
            self.pdk_root = Path(r"C:\pdk") / variant

        # ── internal caches ───────────────────────────────────────────
        self._cell_cache: Dict[str, CellInfo] = {}   # "lib::name" → CellInfo
        self._is_validated: bool = False              # True after validate() passes

        self.logger.debug(f"PDKManager ready | root={self.pdk_root}")

    # ──────────────────────────────────────────────────────────────────────
    # VALIDATION
    # ──────────────────────────────────────────────────────────────────────

    def validate(self) -> PDKValidationResult:
        """
        Check that the PDK installation is complete enough for us to use.

        Checks (in order):
          1. Root directory exists.
          2. Required sub-directories exist.
          3. At least one required library is present.
          4. KLayout tech files present (warning if missing).
          5. OpenROAD/OpenLane config files present (warning if missing).
          6. Timing libraries (.lib) present for each found library.

        Returns:
            PDKValidationResult – inspect .is_valid and .errors for details.
        """
        result = PDKValidationResult(is_valid=True)

        # ── 1. root must exist ────────────────────────────────────────
        if not self.pdk_root.exists():
            result.is_valid = False
            result.errors.append(
                f"PDK root not found: {self.pdk_root}\n"
                f"  Install: pip install volare\n"
                f"  Then:    volare enable --pdk sky130 "
                f"--pdk-root C:\\pdk bdc9412b3e468c102d01b7cf6337be06ec6e9c9a"
            )
            return result   # nothing else to check without the root

        # ── 2. required sub-directories ───────────────────────────────
        for sub in self._REQUIRED_DIRS:
            if not (self.pdk_root / sub).exists():
                result.is_valid = False
                result.errors.append(
                    f"Required directory missing: {self.pdk_root / sub}"
                )

        # ── 3. standard-cell libraries ────────────────────────────────
        libs_ref = self.pdk_root / "libs.ref"
        if libs_ref.exists():
            for lib_enum in Sky130Library:
                lib_path = libs_ref / lib_enum.value
                if lib_path.exists():
                    result.found_libraries.append(lib_enum.value)

        # Must have at least the HD library
        for req in self._REQUIRED_LIBS:
            if req not in result.found_libraries:
                result.is_valid = False
                result.errors.append(
                    f"Required library absent: {req}\n"
                    f"  This is part of the Sky130A PDK."
                )

        # ── 4. KLayout tech files (warning only) ─────────────────────
        kl_dir = self.pdk_root / "libs.tech" / "klayout"
        if not kl_dir.exists():
            result.warnings.append(
                f"KLayout tech dir missing: {kl_dir}\n"
                f"  DRC and LVS via KLayout will not work."
            )

        # ── 5. OpenROAD/OpenLane config (warning only) ────────────────
        ol_dir = self.pdk_root / "libs.tech" / "openlane"
        if not ol_dir.exists():
            result.warnings.append(
                f"OpenROAD config dir missing: {ol_dir}\n"
                f"  Physical design flow will not work."
            )

        # ── 6. timing libraries per found library ─────────────────────
        for lib_name in result.found_libraries:
            for corner in TimingCorner:
                lib_file = self._resolve_lib_file(lib_name, corner.value)
                if not lib_file:
                    result.warnings.append(
                        f"Timing library missing: {lib_name} @ {corner.value}"
                    )

        # ── final status ──────────────────────────────────────────────
        self._is_validated = result.is_valid
        level = logging.INFO if result.is_valid else logging.ERROR
        self.logger.log(
            level,
            f"PDK validation {'PASSED' if result.is_valid else 'FAILED'} | "
            f"libs={result.found_libraries} | "
            f"errors={len(result.errors)} warnings={len(result.warnings)}"
        )
        return result

    # ──────────────────────────────────────────────────────────────────────
    # PATH RESOLUTION – technology / global files
    # ──────────────────────────────────────────────────────────────────────

    def get_tech_lef(self) -> Optional[Path]:
        """
        Technology LEF file – describes metal layers, via rules, etc.
        Required by: floorplanner, placer, router.

        Returns:
            Absolute Path to tech.lef, or None if not found.
        """
        lef_dir = self.pdk_root / "libs.ref" / Sky130Library.HD.value / "lef"
        candidates = [
            lef_dir / f"{Sky130Library.HD.value}.tlef",  # standard name
            lef_dir / "sky130_tech.lef",                 # alternate name
            lef_dir / "tech.lef",                        # generic fallback
        ]
        for c in candidates:
            if c.exists():
                return c
        self.logger.warning("tech.lef not found in PDK")
        return None

    def get_cell_lef(
        self,
        library: Sky130Library = Sky130Library.HD,
    ) -> Optional[Path]:
        """
        Merged cell-abstract LEF for an entire library.
        Used by placement tools to know cell sizes and pin positions.

        Args:
            library: Which Sky130 library to use.

        Returns:
            Path to merged .lef, or None if not found.
        """
        lef_dir  = self.pdk_root / "libs.ref" / library.value / "lef"
        lef_file = lef_dir / f"{library.value}.lef"
        if lef_file.exists():
            return lef_file
        self.logger.warning(f"Cell LEF not found: {lef_file}")
        return None

    def get_timing_lib(
        self,
        library: Sky130Library = Sky130Library.HD,
        corner:  TimingCorner  = TimingCorner.TT,
    ) -> Optional[Path]:
        """
        Liberty (.lib) timing file for one library+corner combination.
        Used by: OpenSTA, any STA engine.

        Args:
            library: Standard-cell library enum.
            corner:  PVT corner enum.

        Returns:
            Path to .lib, or None if not found.
        """
        return self._resolve_lib_file(library.value, corner.value)

    def get_all_timing_libs(
        self,
        library: Sky130Library = Sky130Library.HD,
    ) -> Dict[str, Path]:
        """
        All available timing libs for a library, keyed by corner name.
        Convenient when you want to pass every corner to a tool at once.

        Args:
            library: Standard-cell library enum.

        Returns:
            Dict  corner_string → Path.  Only contains found files.
        """
        libs: Dict[str, Path] = {}
        for corner in TimingCorner:
            p = self.get_timing_lib(library, corner)
            if p:
                libs[corner.value] = p
        return libs

    def get_gds_library(
        self,
        library: Sky130Library = Sky130Library.HD,
    ) -> Optional[Path]:
        """
        Merged GDS file for a library – contains all cell layouts.
        Used during final GDSII assembly (merging design + cells).

        Args:
            library: Standard-cell library enum.

        Returns:
            Path to merged .gds, or None if not found.
        """
        gds_path = (
            self.pdk_root / "libs.ref" / library.value
            / "gds" / f"{library.value}.gds"
        )
        if gds_path.exists():
            return gds_path
        self.logger.warning(f"GDS library not found: {gds_path}")
        return None

    # ──────────────────────────────────────────────────────────────────────
    # PATH RESOLUTION – verification rule decks
    # ──────────────────────────────────────────────────────────────────────

    def get_klayout_drc_rules(self) -> Optional[Path]:
        """
        KLayout DRC rule deck for Sky130.
        Used by: klayout_interface.py → drc_checker.py.

        Returns:
            Path to .lydrc / .drc file, or None.
        """
        base = self.pdk_root / "libs.tech" / "klayout"
        candidates = [
            base / "sky130A.lydrc",
            base / "drc" / "sky130A.lydrc",
            base / "drc" / "sky130.drc",
        ]
        for c in candidates:
            if c.exists():
                return c
        self.logger.warning("KLayout DRC rules not found")
        return None

    def get_klayout_lvs_rules(self) -> Optional[Path]:
        """
        KLayout LVS rule deck for Sky130.
        Used by: klayout_interface.py → lvs_checker.py.

        Returns:
            Path to .lylvs / .lvs file, or None.
        """
        base = self.pdk_root / "libs.tech" / "klayout"
        candidates = [
            base / "sky130A.lylvs",
            base / "lvs" / "sky130A.lvs",
            base / "lvs" / "sky130A.lylvs",
        ]
        for c in candidates:
            if c.exists():
                return c
        self.logger.warning("KLayout LVS rules not found")
        return None

    def get_openlane_config_dir(self) -> Optional[Path]:
        """
        OpenROAD / OpenLane config directory for Sky130 HD library.
        Contains pre-built constraint files and PDN configs.

        Returns:
            Path to openlane/<library> directory, or None.
        """
        candidates = [
            self.pdk_root / "libs.tech" / "openlane" / Sky130Library.HD.value,
            self.pdk_root / "libs.tech" / "openlane",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def get_spice_models(
        self,
        library: Sky130Library = Sky130Library.HD,
    ) -> List[Path]:
        """
        All SPICE / CDL netlists for a library.
        Used by LVS tools (Netgen) to compare against extracted netlist.

        Args:
            library: Standard-cell library enum.

        Returns:
            List of .spice / .cdl paths (may be empty).
        """
        spice_dir = self.pdk_root / "libs.ref" / library.value / "spice"
        if not spice_dir.exists():
            return []
        return (
            list(spice_dir.glob("*.spice")) +
            list(spice_dir.glob("*.cdl"))
        )

    # ──────────────────────────────────────────────────────────────────────
    # CELL LOOKUP
    # ──────────────────────────────────────────────────────────────────────

    def list_cells(
        self,
        library:       Sky130Library = Sky130Library.HD,
        filter_prefix: Optional[str] = None,
    ) -> List[str]:
        """
        Enumerate every standard cell available in a library.

        Args:
            library:       Library to query.
            filter_prefix: Optional prefix filter (e.g. "sky130_fd_sc_hd__and")
                           to get only AND gates.

        Returns:
            Sorted list of cell name strings.
        """
        lef_dir = self.pdk_root / "libs.ref" / library.value / "lef"
        if not lef_dir.exists():
            return []

        cells: List[str] = []

        # ── strategy A: one .lef file per cell ───────────────────────
        individual = list(lef_dir.glob("*.lef"))
        # Filter out the merged library lef (same name as library)
        individual = [
            p for p in individual if p.stem != library.value
        ]
        if individual:
            cells = [p.stem for p in individual]

        # ── strategy B: parse merged .lef ─────────────────────────────
        if not cells:
            merged = lef_dir / f"{library.value}.lef"
            if merged.exists():
                cells = self._parse_macro_names(merged)

        # ── apply prefix filter ────────────────────────────────────────
        if filter_prefix:
            cells = [c for c in cells if c.startswith(filter_prefix)]

        return sorted(cells)

    def get_cell_info(
        self,
        cell_name: str,
        library:   Sky130Library = Sky130Library.HD,
    ) -> Optional[CellInfo]:
        """
        Return path information for a specific standard cell.

        Args:
            cell_name: Full cell name, e.g. "sky130_fd_sc_hd__and2_1".
            library:   Library enum.

        Returns:
            CellInfo dataclass, or None if the cell is not found.
        """
        cache_key = f"{library.value}::{cell_name}"
        if cache_key in self._cell_cache:
            return self._cell_cache[cache_key]   # fast return from cache

        base     = self.pdk_root / "libs.ref" / library.value
        lef_path = base / "lef"   / f"{cell_name}.lef"
        gds_path = base / "gds"   / f"{cell_name}.gds"
        spice    = base / "spice" / f"{cell_name}.spice"

        # If there's no per-cell LEF, check whether the cell name appears
        # inside the merged library LEF before accepting it as a valid cell.
        if not lef_path.exists():
            merged = base / "lef" / f"{library.value}.lef"
            if not merged.exists():
                return None
            # Confirm the cell name actually exists in the merged file
            known_cells = self._parse_macro_names(merged)
            if cell_name not in known_cells:
                return None   # cell is not defined anywhere in this library
            lef_path = merged   # per-cell info lives inside the merged file

        # Collect Liberty paths for every timing corner
        lib_paths: Dict[str, Path] = {}
        for corner in TimingCorner:
            p = self._resolve_lib_file(library.value, corner.value)
            if p:
                lib_paths[corner.value] = p

        info = CellInfo(
            name       = cell_name,
            library    = library.value,
            lef_path   = lef_path,
            gds_path   = gds_path   if gds_path.exists()  else None,
            spice_path = spice      if spice.exists()      else None,
            lib_paths  = lib_paths,
        )
        self._cell_cache[cache_key] = info   # store for next call
        return info

    # ──────────────────────────────────────────────────────────────────────
    # ENVIRONMENT VARIABLES
    # ──────────────────────────────────────────────────────────────────────

    def get_env_vars(self) -> Dict[str, str]:
        """
        Build the environment-variable dictionary that physical-design
        tools (OpenROAD, Magic, KLayout) expect to find.

        Call this before subprocess.run() invocations:
            env = {**os.environ, **pdk.get_env_vars()}
            subprocess.run(cmd, env=env)

        Returns:
            Dict of variable-name → value strings.
        """
        return {
            "PDK_ROOT":          str(self.pdk_root.parent),  # parent of sky130A
            "PDK":               self.variant,
            "STD_CELL_LIBRARY":  Sky130Library.HD.value,
            "OPENLANE_ROOT":     str(
                self.pdk_root / "libs.tech" / "openlane"
            ),
        }

    # ──────────────────────────────────────────────────────────────────────
    # INSTALLATION HELPER
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_install_instructions() -> str:
        """
        Return step-by-step Sky130 install guide for Windows (PowerShell).

        Returns:
            Multi-line string with numbered steps.
        """
        return r"""
Sky130 PDK – Windows Installation Guide
═════════════════════════════════════════════════════════════════

Option A  –  volare (recommended, Python-based, ~2 GB HD only)
───────────────────────────────────────────────────────────────
1.  pip install volare

2.  volare enable --pdk sky130 --pdk-root C:\pdk `
        bdc9412b3e468c102d01b7cf6337be06ec6e9c9a

3.  Set the PDK_ROOT env var permanently:
    [System.Environment]::SetEnvironmentVariable(
        "PDK_ROOT", "C:\pdk", "User")

4.  Verify (new PowerShell window):
    python -c "from python.pdk_manager import PDKManager; PDKManager().print_summary()"

Option B  –  Full clone (Git LFS, ~8 GB)
───────────────────────────────────────────────────────────────
1.  winget install GitHub.GitLFS
    git lfs install

2.  git clone https://github.com/google/skywater-pdk C:\pdk\skywater-pdk
    cd C:\pdk\skywater-pdk
    git submodule update --init libraries\sky130_fd_sc_hd\latest

Option C  –  Via OpenLane Docker (includes PDK inside container)
───────────────────────────────────────────────────────────────
1.  Install Docker Desktop from https://www.docker.com/
2.  docker pull efabless/openlane:latest
    (PDK is baked into the image – nothing else to download)

Notes
─────
• PDK root expected at:  C:\pdk\sky130A
• Override with env var: $env:PDK_ROOT = "D:\my_pdk"
• Minimum install (HD library only): ~2 GB
• Full install (all libraries):       ~8 GB
"""

    # ──────────────────────────────────────────────────────────────────────
    # SUMMARY DISPLAY
    # ──────────────────────────────────────────────────────────────────────

    def print_summary(self) -> None:
        """
        Print a human-readable status table to stdout.
        Useful for a quick sanity-check at the start of a session.
        """
        v = self.validate()

        lines = [
            "",
            "═" * 62,
            "  Sky130 PDK  –  RTL-Gen AI Configuration",
            "═" * 62,
            f"  Root      : {self.pdk_root}",
            f"  Variant   : {self.variant}",
            f"  Status    : {'✅  VALID' if v.is_valid else '❌  INVALID'}",
            "",
            "  Detected libraries:",
        ]
        for lib in v.found_libraries:
            lines.append(f"    ✅  {lib}")
        if not v.found_libraries:
            lines.append("    (none)")

        if v.errors:
            lines.append(f"\n  Errors ({len(v.errors)}):")
            for e in v.errors:
                lines.append(f"    ❌  {e}")

        if v.warnings:
            lines.append(f"\n  Warnings ({len(v.warnings)}):")
            for w in v.warnings:
                lines.append(f"    ⚠   {w}")

        lines.append("\n  Key file paths:")
        lines.append(f"    Tech LEF   : {self.get_tech_lef() or 'not found'}")
        lines.append(f"    Cell LEF   : {self.get_cell_lef() or 'not found'}")
        lines.append(
            f"    Timing TT  : "
            f"{self.get_timing_lib(corner=TimingCorner.TT) or 'not found'}"
        )
        lines.append(f"    GDS Lib    : {self.get_gds_library() or 'not found'}")
        lines.append("═" * 62 + "\n")

        print("\n".join(lines))

    # ──────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ──────────────────────────────────────────────────────────────────────

    def _auto_detect_pdk(self) -> Optional[Path]:
        """
        Search common Windows locations for an existing Sky130 install.
        Checks (in order):
          1. PDK_ROOT environment variable
          2. Standard Windows paths
          3. User home folder

        Returns:
            Detected Path, or None if nothing found.
        """
        # Environment variable is the authoritative override
        env_root = os.environ.get("PDK_ROOT")
        if env_root:
            candidate = Path(env_root) / self.variant
            if candidate.exists():
                return candidate
            # Maybe PDK_ROOT already points inside sky130A
            candidate2 = Path(env_root)
            if (candidate2 / "libs.ref").exists():
                return candidate2

        # Hard-coded common Windows install paths
        standard_paths = [
            Path(r"C:\pdk")             / self.variant,
            Path(r"C:\openpdk")         / self.variant,
            Path(r"C:\eda\pdk")         / self.variant,
            Path.home() / "pdk"         / self.variant,
            Path.home() / ".pdk"        / self.variant,
        ]
        for p in standard_paths:
            if p.exists() and (p / "libs.ref").exists():
                return p

        return None

    def _resolve_lib_file(
        self, library_name: str, corner_name: str
    ) -> Optional[Path]:
        """
        Build the expected path to a Liberty (.lib) file and verify it exists.

        Liberty files follow the naming convention:
            <library>__<corner>.lib
        e.g.
            sky130_fd_sc_hd__tt_025C_1v80.lib

        Args:
            library_name: e.g. "sky130_fd_sc_hd"
            corner_name:  e.g. "tt_025C_1v80"

        Returns:
            Path to .lib if found, else None.
        """
        lib_dir = self.pdk_root / "libs.ref" / library_name / "lib"
        if not lib_dir.exists():
            return None

        # Standard two-underscore naming
        candidate = lib_dir / f"{library_name}__{corner_name}.lib"
        if candidate.exists():
            return candidate

        # Alternate: corner name only
        alt = lib_dir / f"{corner_name}.lib"
        if alt.exists():
            return alt

        return None

    def _parse_macro_names(self, lef_path: Path) -> List[str]:
        """
        Read a LEF file and collect all MACRO block names.
        Each MACRO in a LEF corresponds to one standard cell.

        Args:
            lef_path: Path to a (possibly large) merged .lef file.

        Returns:
            List of macro/cell name strings.
        """
        cells: List[str] = []
        try:
            with open(lef_path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped.startswith("MACRO "):
                        parts = stripped.split()
                        if len(parts) >= 2:
                            cells.append(parts[1])
        except OSError as exc:
            self.logger.warning(f"Could not parse LEF {lef_path}: {exc}")
        return cells
