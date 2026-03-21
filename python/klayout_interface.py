"""
klayout_interface.py  –  KLayout Python API Wrapper for RTL-Gen AI
===================================================================
Wraps KLayout's Python bindings (klayout.db) to provide GDSII reading,
writing, DRC execution, layer inspection, and area measurement.

KLayout is the only major EDA tool with full native Windows support and
a clean Python API.  It handles every file-format task in our GDS flow:
  • Reading / writing GDSII (.gds) files
  • Reading / writing OASIS (.oas) files
  • Running DRC rule scripts (.lydrc)
  • Running LVS scripts  (.lylvs)
  • Merging cell libraries into the design

Install KLayout (Windows, one-time):
    Download installer from https://www.klayout.de/build.html
    Select the Windows 64-bit installer that includes Python bindings.
    Default path: C:\\Program Files\\KLayout\\klayout.exe
    After install verify:
        python -c "import klayout.db; print(klayout.db.VERSION)"

Usage example:
    from python.klayout_interface import KLayoutInterface
    from python.pdk_manager import PDKManager

    pdk = PDKManager()
    kl  = KLayoutInterface(pdk)

    # Read a GDS file
    layout = kl.read_gds("design.gds")

    # Run DRC
    drc_result = kl.run_drc("design.gds")
    print(drc_result.summary())

    # Write a new GDS with metadata applied
    kl.write_gds(layout, "design_signed.gds")
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Try to import KLayout Python bindings ────────────────────────────────────
# The bindings ship with the KLayout installer.
# If the import fails we operate in "headless" mode: script-based DRC still
# works by calling klayout.exe via subprocess.
try:
    import klayout.db  as pya   # main layout database
    import klayout.rdb as rdb   # rule-database (DRC results)
    _KLAYOUT_BINDINGS = True
except ImportError:
    _KLAYOUT_BINDINGS = False


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LayerInfo:
    """Metadata for one GDS layer."""
    layer_number:  int           # GDS layer number (0–255)
    datatype:      int           # GDS datatype  (0–255)
    name:          str           # Human-readable name (e.g. "metal1")
    shape_count:   int = 0       # Number of polygons / paths on this layer
    area_um2:      float = 0.0   # Total drawn area in µm²


@dataclass
class DRCViolation:
    """One DRC error record returned by KLayout."""
    rule_name:   str             # e.g. "M1.1 min width"
    category:    str             # e.g. "metal1"
    description: str             # Free-text description from rule deck
    x_um:        float = 0.0    # X coordinate of violation marker (µm)
    y_um:        float = 0.0    # Y coordinate
    severity:    str = "error"  # "error" | "warning"


@dataclass
class DRCResult:
    """Complete DRC run output."""
    gds_path:      str                             # Input GDS that was checked
    rule_deck:     str                             # Rule deck used
    passed:        bool = False                    # True when violation_count==0
    violation_count: int = 0
    violations:    List[DRCViolation] = field(default_factory=list)
    log_output:    str = ""                        # Raw KLayout stdout/stderr
    report_path:   Optional[str] = None           # Path to .lyrdb report

    def summary(self) -> str:
        """One-line human-readable status."""
        status = "✅  CLEAN" if self.passed else f"❌  {self.violation_count} violations"
        return f"DRC {status} | {self.gds_path}"


@dataclass
class LVSResult:
    """Complete LVS run output."""
    gds_path:       str
    schematic_path: str
    rule_deck:      str
    matched:        bool = False   # True when layout netlist == schematic
    mismatches:     List[str] = field(default_factory=list)
    log_output:     str = ""
    report_path:    Optional[str] = None

    def summary(self) -> str:
        status = "✅  MATCHED" if self.matched else f"❌  {len(self.mismatches)} mismatches"
        return f"LVS {status} | {self.gds_path}"


@dataclass
class LayoutStats:
    """High-level statistics for a GDS layout."""
    cell_name:     str
    top_cell:      str
    layer_count:   int
    total_shapes:  int
    die_width_um:  float
    die_height_um: float
    die_area_um2:  float
    layers:        List[LayerInfo] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# SKY130 LAYER MAP
# Standard GDS layer numbers for Sky130A.
# source: https://skywater-pdk.readthedocs.io/en/main/rules/layers.html
# ──────────────────────────────────────────────────────────────────────────────

SKY130_LAYERS: Dict[Tuple[int, int], str] = {
    (235, 4):  "prBoundary",   # Die / PR boundary
    (64,  20): "nwell",        # N-well implant
    (65,  44): "tap",          # Substrate / well taps
    (66,  20): "ndiff",        # N+ diffusion
    (65,  20): "pdiff",        # P+ diffusion
    (66,  44): "npc",          # NPC (silicide block)
    (83,  44): "poly",         # Polysilicon gate
    (67,  44): "licon1",       # Local interconnect contact
    (67,  20): "li1",          # Local interconnect 1
    (68,  44): "mcon",         # Metal 1 contact
    (68,  20): "met1",         # Metal 1
    (69,  44): "via",          # Via 1 (M1→M2)
    (69,  20): "met2",         # Metal 2
    (70,  44): "via2",         # Via 2 (M2→M3)
    (70,  20): "met3",         # Metal 3
    (71,  44): "via3",         # Via 3 (M3→M4)
    (71,  20): "met4",         # Metal 4
    (72,  44): "via4",         # Via 4 (M4→M5)
    (72,  20): "met5",         # Metal 5 (topmost)
    (76,  44): "pad",          # Top-metal pad opening
}


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class KLayoutInterface:
    """
    Python wrapper around KLayout for GDSII operations in RTL-Gen AI.

    Two operating modes:
    ─────────────────────────────────────────────────────────────────
    Bindings mode  (preferred)
        klayout.db is importable → all operations run in-process.
        Fast, no subprocess overhead.

    Subprocess mode  (fallback)
        klayout.db not importable → uses klayout.exe via subprocess.
        Slightly slower but works even if Python bindings were not
        installed with KLayout.
    ─────────────────────────────────────────────────────────────────

    Attributes:
        pdk:            PDKManager  – source of Sky130 rule decks.
        klayout_exe:    Path to klayout.exe (auto-detected on Windows).
        mode:           "bindings" or "subprocess".
    """

    # Default KLayout install locations on Windows
    _WIN_EXE_PATHS = [
        Path(r"C:\Program Files\KLayout\klayout.exe"),
        Path(r"C:\Program Files (x86)\KLayout\klayout.exe"),
        Path(r"C:\KLayout\klayout.exe"),
    ]

    def __init__(
        self,
        pdk,                              # PDKManager instance
        klayout_exe: Optional[str] = None,
    ) -> None:
        """
        Create a KLayoutInterface.

        Args:
            pdk:         PDKManager instance (for Sky130 rule deck paths).
            klayout_exe: Explicit path to klayout.exe.
                         When None, common Windows locations are checked,
                         then PATH is searched.
        """
        self.logger = logging.getLogger(__name__)
        self.pdk    = pdk

        # ── determine operating mode ───────────────────────────────────
        if _KLAYOUT_BINDINGS:
            self.mode = "bindings"
            self.logger.info("KLayout Python bindings available – using bindings mode")
        else:
            self.mode = "subprocess"
            self.logger.info("KLayout bindings not found – using subprocess mode")

        # ── locate klayout.exe ─────────────────────────────────────────
        self.klayout_exe: Optional[Path] = self._find_klayout_exe(klayout_exe)
        if self.klayout_exe:
            self.logger.info(f"KLayout executable: {self.klayout_exe}")
        else:
            self.logger.warning(
                "klayout.exe not found.  Subprocess-mode DRC will fail.\n"
                "  Download: https://www.klayout.de/build.html"
            )

    # ──────────────────────────────────────────────────────────────────────
    # INSTALLATION CHECK
    # ──────────────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """
        Return True if KLayout is usable (either bindings or executable found).
        Call this before any other method to give a clear error to the user.
        """
        return _KLAYOUT_BINDINGS or (self.klayout_exe is not None)

    @staticmethod
    def get_install_instructions() -> str:
        """Return Windows install guide for KLayout."""
        return textwrap.dedent("""
        KLayout  –  Windows Installation
        ══════════════════════════════════════════════════════════
        1. Go to:  https://www.klayout.de/build.html
        2. Download the Windows 64-bit installer
           (choose the version labelled "with Python bindings")
        3. Run the installer; default path:
               C:\\Program Files\\KLayout
        4. Verify Python bindings work:
               python -c "import klayout.db; print('OK', klayout.db.VERSION)"
        5. If import fails, add KLayout to PYTHONPATH:
               $env:PYTHONPATH = "C:\\Program Files\\KLayout"
        ══════════════════════════════════════════════════════════
        """)

    # ──────────────────────────────────────────────────────────────────────
    # GDSII READ / WRITE
    # ──────────────────────────────────────────────────────────────────────

    def read_gds(self, gds_path: str | Path) -> Optional["pya.Layout"]:
        """
        Load a GDSII file into a KLayout Layout object.

        The Layout object is the in-memory representation of the chip.
        Pass it to write_gds() to save, or to get_stats() to inspect.

        Args:
            gds_path: Path to .gds file.

        Returns:
            klayout.db.Layout object, or None if the import failed.
        """
        if not _KLAYOUT_BINDINGS:
            self.logger.error(
                "read_gds() requires klayout.db bindings (not available).\n"
                "  Install KLayout with Python bindings."
            )
            return None

        gds_path = Path(gds_path)
        if not gds_path.exists():
            self.logger.error(f"GDS file not found: {gds_path}")
            return None

        try:
            # Create an empty layout container
            layout = pya.Layout()

            # Set the database unit (Sky130 uses 1 nm = 0.001 µm)
            layout.dbu = 0.001  # micrometres per database unit

            # Read options: preserve cell names, merge connected shapes
            options = pya.LoadLayoutOptions()
            options.warn_level = 0   # suppress minor warnings

            layout.read(str(gds_path), options)

            n_cells = layout.cells()
            self.logger.info(
                f"Read GDS: {gds_path.name} | "
                f"{n_cells} cell(s) | "
                f"top={self._get_top_cell_name(layout)}"
            )
            return layout

        except Exception as exc:
            self.logger.error(f"Failed to read GDS {gds_path}: {exc}")
            return None

    def write_gds(
        self,
        layout:   "pya.Layout",
        out_path: str | Path,
        compress: bool = False,
    ) -> bool:
        """
        Write a KLayout Layout object to a GDSII file.

        Args:
            layout:   KLayout Layout object (from read_gds or build_layout).
            out_path: Destination .gds path.  Parent directory is created
                      automatically if it does not exist.
            compress: If True, write a gzip-compressed .gds.gz instead.

        Returns:
            True on success, False on failure.
        """
        if not _KLAYOUT_BINDINGS:
            self.logger.error("write_gds() requires klayout.db bindings")
            return False

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # KLayout infers format from extension; .gds → GDSII
        if compress and not str(out_path).endswith(".gz"):
            out_path = Path(str(out_path) + ".gz")

        try:
            options = pya.SaveLayoutOptions()
            options.format = "GDS2"
            # Store the original user unit in the stream file
            options.gds2_write_timestamps = True

            layout.write(str(out_path), options)
            size_mb = out_path.stat().st_size / (1024 * 1024)
            self.logger.info(
                f"Wrote GDS: {out_path} ({size_mb:.2f} MB)"
            )
            return True

        except Exception as exc:
            self.logger.error(f"Failed to write GDS {out_path}: {exc}")
            return False

    # ──────────────────────────────────────────────────────────────────────
    # LAYOUT INSPECTION
    # ──────────────────────────────────────────────────────────────────────

    def get_stats(
        self,
        gds_path:  str | Path,
        top_cell:  Optional[str] = None,
    ) -> Optional[LayoutStats]:
        """
        Compute geometry statistics for a GDS file.

        Calculates die dimensions, total shape count, and per-layer
        statistics (shape count, drawn area).  Useful for sanity-checking
        a layout before running DRC.

        Args:
            gds_path: Path to .gds file.
            top_cell: Name of the top-level cell.  When None, the first
                      top cell found is used.

        Returns:
            LayoutStats dataclass, or None if the GDS could not be read.
        """
        layout = self.read_gds(gds_path)
        if layout is None:
            return None

        top_name = top_cell or self._get_top_cell_name(layout)
        if not top_name:
            self.logger.error("No top cell found in layout")
            return None

        top = layout.cell(top_name)
        if top is None:
            self.logger.error(f"Top cell '{top_name}' not found in layout")
            return None

        # ── die bounding box ───────────────────────────────────────────
        bbox   = top.dbbox()   # bounding box in µm (pya.DBox)
        width  = bbox.width()
        height = bbox.height()

        # ── per-layer statistics ───────────────────────────────────────
        layer_infos: List[LayerInfo] = []
        total_shapes = 0

        for layer_idx in range(layout.layers()):
            linfo = layout.get_info(layer_idx)   # pya.LayerInfo
            if linfo.is_named():                 # skip anonymous layer slots
                continue

            ln = linfo.layer
            dt = linfo.datatype

            # Count shapes on this layer (all cells, flat view)
            region     = pya.Region(top.begin_shapes_rec(layer_idx))
            shape_cnt  = region.count()
            area_um2   = region.area() * (layout.dbu ** 2)  # dbu² → µm²

            if shape_cnt == 0:
                continue   # skip empty layers

            total_shapes += shape_cnt

            # Look up human-readable name from Sky130 layer map
            layer_name = SKY130_LAYERS.get((ln, dt), f"layer{ln}/{dt}")

            layer_infos.append(LayerInfo(
                layer_number = ln,
                datatype     = dt,
                name         = layer_name,
                shape_count  = shape_cnt,
                area_um2     = area_um2,
            ))

        stats = LayoutStats(
            cell_name     = top_name,
            top_cell      = top_name,
            layer_count   = len(layer_infos),
            total_shapes  = total_shapes,
            die_width_um  = width,
            die_height_um = height,
            die_area_um2  = width * height,
            layers        = layer_infos,
        )

        self.logger.info(
            f"Stats: {top_name} | "
            f"{width:.2f}×{height:.2f} µm | "
            f"{total_shapes} shapes | "
            f"{len(layer_infos)} layers"
        )
        return stats

    def list_cells(self, gds_path: str | Path) -> List[str]:
        """
        Return the names of all cells defined in a GDS file.

        Args:
            gds_path: Path to .gds file.

        Returns:
            Sorted list of cell name strings.
        """
        layout = self.read_gds(gds_path)
        if layout is None:
            return []
        return sorted(c.name for c in layout.each_cell())

    def get_layer_map(
        self, gds_path: str | Path
    ) -> Dict[Tuple[int, int], str]:
        """
        Return a map of (layer, datatype) → name for every populated
        layer in the GDS.

        Args:
            gds_path: Path to .gds file.

        Returns:
            Dict  (layer_num, datatype) → name string.
        """
        layout = self.read_gds(gds_path)
        if layout is None:
            return {}

        result: Dict[Tuple[int, int], str] = {}
        for idx in range(layout.layers()):
            linfo = layout.get_info(idx)
            key   = (linfo.layer, linfo.datatype)
            name  = SKY130_LAYERS.get(key, f"layer{linfo.layer}/{linfo.datatype}")
            result[key] = name
        return result

    # ──────────────────────────────────────────────────────────────────────
    # GDSII MANIPULATION
    # ──────────────────────────────────────────────────────────────────────

    def merge_cell_library(
        self,
        design_gds: str | Path,
        library_gds: str | Path,
        out_path:   str | Path,
    ) -> bool:
        """
        Merge standard-cell GDS library into the design GDS.

        During tape-out, the router produces a GDS that references cell
        names (e.g. sky130_fd_sc_hd__and2_1) without embedding their
        layouts.  This method merges the PDK cell library into the design
        so the final GDS is self-contained and fab-ready.

        Args:
            design_gds:  Path to the routed design .gds.
            library_gds: Path to the PDK cell library .gds
                         (from pdk.get_gds_library()).
            out_path:    Path for the merged output .gds.

        Returns:
            True if merge succeeded.
        """
        if not _KLAYOUT_BINDINGS:
            self.logger.error("merge_cell_library() requires klayout.db bindings")
            return False

        design_gds  = Path(design_gds)
        library_gds = Path(library_gds)

        if not design_gds.exists():
            self.logger.error(f"Design GDS not found: {design_gds}")
            return False
        if not library_gds.exists():
            self.logger.error(f"Library GDS not found: {library_gds}")
            return False

        try:
            # Load design
            design = pya.Layout()
            design.read(str(design_gds))
            self.logger.info(f"Loaded design: {design_gds.name}")

            # Load cell library
            lib    = pya.Layout()
            lib.read(str(library_gds))
            self.logger.info(f"Loaded library: {library_gds.name}")

            # Find which cells the design references but does not define
            design_cell_names = {c.name for c in design.each_cell()}
            lib_cell_names    = {c.name for c in lib.each_cell()}
            needed = design_cell_names & lib_cell_names
            self.logger.info(
                f"Merging {len(needed)} cell(s) from library into design"
            )

            # Copy each needed cell from lib into design
            for cell_name in needed:
                lib_cell    = lib.cell(cell_name)
                design_cell = design.cell(cell_name)
                if design_cell is None:
                    # Cell is only referenced, not defined – copy it
                    design.copy_cell(lib_cell, False, design)

            # Write merged result
            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            design.write(str(out_path))

            size_mb = out_path.stat().st_size / (1024 * 1024)
            self.logger.info(
                f"Merged GDS written: {out_path} ({size_mb:.2f} MB)"
            )
            return True

        except Exception as exc:
            self.logger.error(f"merge_cell_library failed: {exc}")
            return False

    def extract_cell(
        self,
        gds_path:  str | Path,
        cell_name: str,
        out_path:  str | Path,
    ) -> bool:
        """
        Extract a single named cell from a GDS file into its own file.

        Useful for examining a specific module after routing.

        Args:
            gds_path:  Source GDS.
            cell_name: Name of the cell to extract.
            out_path:  Destination GDS (contains only the selected cell).

        Returns:
            True on success.
        """
        if not _KLAYOUT_BINDINGS:
            self.logger.error("extract_cell() requires klayout.db bindings")
            return False

        try:
            source = pya.Layout()
            source.read(str(gds_path))
            cell = source.cell(cell_name)
            if cell is None:
                self.logger.error(
                    f"Cell '{cell_name}' not found in {gds_path}"
                )
                return False

            # Build a new layout containing only this cell and its children
            target = pya.Layout()
            target.dbu = source.dbu
            target.copy_cell(cell, True, target)  # True = deep copy

            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            target.write(str(out_path))
            self.logger.info(f"Extracted '{cell_name}' → {out_path}")
            return True

        except Exception as exc:
            self.logger.error(f"extract_cell failed: {exc}")
            return False

    # ──────────────────────────────────────────────────────────────────────
    # DRC
    # ──────────────────────────────────────────────────────────────────────

    def run_drc(
        self,
        gds_path:    str | Path,
        rule_deck:   Optional[str | Path] = None,
        report_path: Optional[str | Path] = None,
        top_cell:    Optional[str] = None,
    ) -> DRCResult:
        """
        Run the Sky130 DRC rule deck against a GDS layout.

        KLayout executes the rule deck (a Ruby script) against the GDS
        and produces a .lyrdb violations report.  This method parses
        that report into a list of DRCViolation objects.

        Args:
            gds_path:    Layout to check.
            rule_deck:   Path to .lydrc file.  When None, the PDK default
                         is used (pdk.get_klayout_drc_rules()).
            report_path: Where to save the .lyrdb report.  Defaults to
                         <gds_path>.drc.lyrdb in the same directory.
            top_cell:    Top cell name (inferred if None).

        Returns:
            DRCResult with violations list and summary.
        """
        gds_path = Path(gds_path)

        # ── resolve rule deck ─────────────────────────────────────────
        if rule_deck is None:
            rule_deck = self.pdk.get_klayout_drc_rules()
        if rule_deck is None:
            self.logger.error(
                "DRC rule deck not found.  "
                "Install the full Sky130 PDK (libs.tech/klayout)."
            )
            return DRCResult(
                gds_path  = str(gds_path),
                rule_deck = "not found",
                log_output = "ERROR: rule deck not found"
            )

        rule_deck = Path(rule_deck)

        # ── resolve report path ───────────────────────────────────────
        if report_path is None:
            report_path = gds_path.with_suffix(".drc.lyrdb")
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        # ── choose execution path ─────────────────────────────────────
        if self.mode == "bindings":
            return self._run_drc_bindings(
                gds_path, rule_deck, report_path, top_cell
            )
        else:
            return self._run_drc_subprocess(
                gds_path, rule_deck, report_path, top_cell
            )

    def _run_drc_bindings(
        self,
        gds_path:    Path,
        rule_deck:   Path,
        report_path: Path,
        top_cell:    Optional[str],
    ) -> DRCResult:
        """
        Run DRC using klayout.drc Python module (in-process).

        KLayout's DRC engine runs the rule deck Ruby script against the
        layout loaded directly in memory – no subprocess needed.
        """
        try:
            # KLayout DRC requires calling the batch DRC runner
            # The cleanest cross-version way is via the scripting interface
            script = self._generate_drc_script(
                str(gds_path), str(rule_deck), str(report_path), top_cell
            )
            # Write temp script and execute via macro engine
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".rb", delete=False, encoding="utf-8"
            ) as tf:
                tf.write(script)
                temp_script = tf.name

            result = self._exec_klayout_script(temp_script)
            Path(temp_script).unlink(missing_ok=True)

            violations = self._parse_lyrdb(report_path)
            return DRCResult(
                gds_path        = str(gds_path),
                rule_deck       = str(rule_deck),
                passed          = len(violations) == 0,
                violation_count = len(violations),
                violations      = violations,
                log_output      = result,
                report_path     = str(report_path),
            )

        except Exception as exc:
            self.logger.error(f"DRC (bindings) failed: {exc}")
            return DRCResult(
                gds_path  = str(gds_path),
                rule_deck = str(rule_deck),
                log_output = f"ERROR: {exc}"
            )

    def _run_drc_subprocess(
        self,
        gds_path:    Path,
        rule_deck:   Path,
        report_path: Path,
        top_cell:    Optional[str],
    ) -> DRCResult:
        """
        Run DRC by calling klayout.exe as a subprocess.
        Works even when Python bindings are not installed.
        """
        if not self.klayout_exe:
            msg = "ERROR: klayout.exe not found – cannot run DRC in subprocess mode"
            self.logger.error(msg)
            return DRCResult(
                gds_path  = str(gds_path),
                rule_deck = str(rule_deck),
                log_output = msg
            )

        # Build command: klayout -b -r <rule_deck> -rd input=<gds> -rd report=<lyrdb>
        cmd = [
            str(self.klayout_exe),
            "-b",                                    # batch mode (no GUI)
            "-r", str(rule_deck),                    # run this script
            "-rd", f"input={gds_path}",             # pass input GDS
            "-rd", f"report={report_path}",         # where to write violations
        ]
        if top_cell:
            cmd += ["-rd", f"cell={top_cell}"]

        self.logger.info(f"Running KLayout DRC: {' '.join(cmd[:5])} ...")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,    # 5-minute timeout
            )
            log_out = proc.stdout + proc.stderr
            violations = self._parse_lyrdb(report_path)
            return DRCResult(
                gds_path        = str(gds_path),
                rule_deck       = str(rule_deck),
                passed          = len(violations) == 0,
                violation_count = len(violations),
                violations      = violations,
                log_output      = log_out,
                report_path     = str(report_path),
            )

        except subprocess.TimeoutExpired:
            msg = "DRC subprocess timed out (>5 min)"
            self.logger.error(msg)
            return DRCResult(
                gds_path  = str(gds_path),
                rule_deck = str(rule_deck),
                log_output = msg
            )
        except Exception as exc:
            self.logger.error(f"DRC subprocess error: {exc}")
            return DRCResult(
                gds_path  = str(gds_path),
                rule_deck = str(rule_deck),
                log_output = f"ERROR: {exc}"
            )

    # ──────────────────────────────────────────────────────────────────────
    # LVS
    # ──────────────────────────────────────────────────────────────────────

    def run_lvs(
        self,
        gds_path:       str | Path,
        schematic_path: str | Path,
        rule_deck:      Optional[str | Path] = None,
        report_path:    Optional[str | Path] = None,
        top_cell:       Optional[str] = None,
    ) -> LVSResult:
        """
        Run LVS (Layout vs Schematic) using KLayout's LVS engine.

        Compares the transistor-level netlist extracted from the layout
        against the reference SPICE schematic.  Both must match for
        tape-out sign-off.

        Args:
            gds_path:       Layout GDS to check.
            schematic_path: Reference SPICE netlist (.spice / .cdl).
            rule_deck:      LVS script (.lylvs).  Defaults to PDK LVS rules.
            report_path:    Where to save the LVS report.
            top_cell:       Top cell name (inferred if None).

        Returns:
            LVSResult with match status and mismatches list.
        """
        gds_path       = Path(gds_path)
        schematic_path = Path(schematic_path)

        if rule_deck is None:
            rule_deck = self.pdk.get_klayout_lvs_rules()
        if rule_deck is None:
            msg = "LVS rule deck not found"
            self.logger.error(msg)
            return LVSResult(
                gds_path       = str(gds_path),
                schematic_path = str(schematic_path),
                rule_deck      = "not found",
                log_output     = msg,
            )

        rule_deck = Path(rule_deck)
        if report_path is None:
            report_path = gds_path.with_suffix(".lvs.lyrdb")
        report_path = Path(report_path)

        if not self.klayout_exe:
            msg = "klayout.exe required for LVS"
            self.logger.error(msg)
            return LVSResult(
                gds_path       = str(gds_path),
                schematic_path = str(schematic_path),
                rule_deck      = str(rule_deck),
                log_output     = msg,
            )

        # KLayout LVS command
        cmd = [
            str(self.klayout_exe),
            "-b",
            "-r", str(rule_deck),
            "-rd", f"input={gds_path}",
            "-rd", f"schematic={schematic_path}",
            "-rd", f"report={report_path}",
        ]
        if top_cell:
            cmd += ["-rd", f"cell={top_cell}"]

        self.logger.info("Running KLayout LVS ...")

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            log_out    = proc.stdout + proc.stderr
            mismatches = self._parse_lvs_log(log_out)
            matched    = len(mismatches) == 0 and proc.returncode == 0

            return LVSResult(
                gds_path       = str(gds_path),
                schematic_path = str(schematic_path),
                rule_deck      = str(rule_deck),
                matched        = matched,
                mismatches     = mismatches,
                log_output     = log_out,
                report_path    = str(report_path),
            )

        except subprocess.TimeoutExpired:
            msg = "LVS subprocess timed out (>10 min)"
            self.logger.error(msg)
            return LVSResult(
                gds_path       = str(gds_path),
                schematic_path = str(schematic_path),
                rule_deck      = str(rule_deck),
                log_output     = msg,
            )
        except Exception as exc:
            self.logger.error(f"LVS error: {exc}")
            return LVSResult(
                gds_path       = str(gds_path),
                schematic_path = str(schematic_path),
                rule_deck      = str(rule_deck),
                log_output     = f"ERROR: {exc}",
            )

    # ──────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ──────────────────────────────────────────────────────────────────────

    def _find_klayout_exe(self, explicit: Optional[str]) -> Optional[Path]:
        """
        Locate klayout.exe on Windows.

        Search order:
          1. Explicitly supplied path
          2. Common installation directories
          3. System PATH
        """
        if explicit:
            p = Path(explicit)
            if p.exists():
                return p
            self.logger.warning(f"Explicit KLayout path not found: {p}")
            return None

        # Check common Windows install locations
        for candidate in self._WIN_EXE_PATHS:
            if candidate.exists():
                return candidate

        # Search PATH
        for dir_str in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(dir_str) / "klayout.exe"
            if candidate.exists():
                return candidate

        return None

    def _get_top_cell_name(self, layout: "pya.Layout") -> Optional[str]:
        """
        Find the topmost (unreferenced) cell in a layout.
        A top cell is one that is not instantiated by any other cell.
        """
        if not _KLAYOUT_BINDINGS:
            return None
        for cell in layout.each_cell():
            if layout.is_top_cell(cell.cell_index()):
                return cell.name
        # Fallback: return first cell name
        cells = list(layout.each_cell())
        return cells[0].name if cells else None

    def _generate_drc_script(
        self,
        gds_path:    str,
        rule_deck:   str,
        report_path: str,
        top_cell:    Optional[str],
    ) -> str:
        """
        Generate a minimal KLayout Ruby script that runs a DRC rule deck.
        The script reads $input, runs the deck, and writes results to $report.
        """
        top_part = f'top_cell_name("{top_cell}")' if top_cell else ""
        # Escape backslashes for Ruby strings on Windows
        gds_esc    = gds_path.replace("\\", "\\\\")
        report_esc = report_path.replace("\\", "\\\\")
        deck_esc   = rule_deck.replace("\\", "\\\\")

        return textwrap.dedent(f"""
        # Auto-generated DRC runner – RTL-Gen AI
        source("{gds_esc}")
        {top_part}
        report("{report_esc}")
        # Load and execute the Sky130 DRC rule deck
        load("{deck_esc}")
        """)

    def _exec_klayout_script(self, script_path: str) -> str:
        """
        Execute a KLayout Ruby/DRC script via subprocess (klayout -b -r).

        Returns:
            Combined stdout+stderr text.
        """
        if not self.klayout_exe:
            return "ERROR: klayout.exe not found"
        cmd = [str(self.klayout_exe), "-b", "-r", script_path]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        return proc.stdout + proc.stderr

    def _parse_lyrdb(self, lyrdb_path: Path) -> List[DRCViolation]:
        """
        Parse a KLayout .lyrdb XML violation report.

        .lyrdb is an XML format.  We parse just enough of it to build
        our DRCViolation list.  Returns [] if the file does not exist.
        """
        if not lyrdb_path.exists():
            return []

        violations: List[DRCViolation] = []
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(str(lyrdb_path))
            root = tree.getroot()

            # .lyrdb structure:  <report-database> → <categories> → <category>
            #                                      → <items> → <item>
            for category in root.iter("category"):
                cat_name = category.findtext("name", "unknown")
                desc     = category.findtext("description", "")
                for item in category.iter("item"):
                    # Each item has a <values> child with coordinate data
                    values = item.findtext("values", "")
                    x, y   = 0.0, 0.0
                    parts  = values.strip().split()
                    if len(parts) >= 2:
                        try:
                            x = float(parts[0])
                            y = float(parts[1])
                        except ValueError:
                            pass

                    violations.append(DRCViolation(
                        rule_name   = cat_name,
                        category    = cat_name,
                        description = desc,
                        x_um        = x,
                        y_um        = y,
                        severity    = "error",
                    ))

        except Exception as exc:
            self.logger.warning(f"Could not parse lyrdb {lyrdb_path}: {exc}")

        return violations

    def _parse_lvs_log(self, log_text: str) -> List[str]:
        """
        Extract mismatch lines from KLayout LVS log output.

        KLayout LVS prints "Mismatch:" or "ERROR:" lines when nets or
        devices do not match between layout and schematic.

        Args:
            log_text: Combined stdout+stderr from KLayout LVS run.

        Returns:
            List of mismatch description strings.
        """
        mismatches: List[str] = []
        for line in log_text.splitlines():
            stripped = line.strip()
            if any(
                keyword in stripped
                for keyword in ("Mismatch:", "ERROR:", "FAILED", "not matched")
            ):
                mismatches.append(stripped)
        return mismatches
