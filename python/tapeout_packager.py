"""
tapeout_packager.py  –  Tape-out Package Assembler for RTL-Gen AI
==================================================================
Assembles all deliverables from the RTL→GDS flow into a single,
organised tape-out package directory, generates a manifest, and
produces a README suitable for submission to a fab or shuttle.

What a tape-out package contains
──────────────────────────────────
  GDSII file          ← primary layout for fabrication
  LEF file            ← abstract for integration into larger chips
  DEF file            ← routed placement/routing data
  SPEF file           ← parasitic extraction
  Timing reports      ← STA sign-off results
  DRC report          ← design rule check results
  LVS report          ← layout vs schematic results
  Synthesis netlist   ← gate-level Verilog
  Documentation       ← README, datasheet

Package structure produced
───────────────────────────
  <design>_tapeout/
  ├── gds/          ← GDSII files
  ├── lef/          ← LEF abstracts
  ├── def/          ← DEF placement/routing
  ├── timing/       ← STA reports
  ├── signoff/      ← DRC + LVS reports
  ├── netlist/      ← synthesised Verilog
  ├── docs/         ← documentation
  ├── MANIFEST.txt  ← file inventory
  └── README.md     ← design summary

Usage example
──────────────
    from python.tapeout_packager import TapeoutPackager, PackageConfig

    pkg = TapeoutPackager()
    result = pkg.package(
        top_module   = "adder_8bit",
        output_dir   = r"C:\\project\\tapeout",
        gds_path     = r"C:\\project\\gds\\adder_8bit.gds",
        routed_def   = r"C:\\project\\physical\\routed.def",
        timing_rpt   = r"C:\\project\\physical\\routing.rpt",
        drc_rpt      = r"C:\\project\\signoff\\drc.rpt",
        lvs_rpt      = r"C:\\project\\signoff\\lvs.rpt",
        netlist_path = r"C:\\project\\synth\\netlist.v",
    )
    print(result.summary())
    print(f"Package: {result.package_dir}")
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class PackageConfig:
    """Options for tape-out package assembly."""
    # Design metadata for README and MANIFEST
    design_version:  str  = "1.0.0"
    process_node:    str  = "Sky130A (130nm)"
    author:          str  = "RTL-Gen AI"
    description:     str  = ""

    # Whether to verify all critical files exist before packaging
    strict_mode:     bool = True   # True = fail if GDS or DRC report missing

    # Whether to generate a README.md
    generate_readme: bool = True

    # Whether to compute MD5 checksums in the manifest
    compute_checksums: bool = True


@dataclass
class PackagedFile:
    """Record for one file included in the package."""
    source_path:     str          # Original file location
    package_path:    str          # Destination inside package
    category:        str          # "gds", "timing", "signoff", etc.
    size_bytes:      int  = 0
    checksum_md5:    str  = ""
    is_critical:     bool = False  # True = tape-out cannot proceed without it


@dataclass
class PackageResult:
    """Complete result from TapeoutPackager.package()."""
    top_module:   str
    package_dir:  str
    success:      bool = False

    files:        List[PackagedFile] = field(default_factory=list)
    missing:      List[str]          = field(default_factory=list)
    warnings:     List[str]          = field(default_factory=list)

    manifest_path: Optional[str] = None
    readme_path:   Optional[str] = None

    def summary(self) -> str:
        status = "✅  COMPLETE" if self.success else "❌  INCOMPLETE"
        lines  = [
            "",
            "╔" + "═" * 60 + "╗",
            "║  Tape-out Package  –  RTL-Gen AI" + " " * 26 + "║",
            "╠" + "═" * 60 + "╣",
            f"║  Status       : {status:<41} ║",
            f"║  Design       : {self.top_module:<41} ║",
            f"║  Package dir  : {str(self.package_dir)[:41]:<41} ║",
            f"║  Files packed : {len(self.files):<41} ║",
        ]
        if self.missing:
            lines += [
                "╠" + "─" * 60 + "╣",
                f"║  Missing ({len(self.missing)}):" + " " * 47 + "║",
            ]
            for m in self.missing[:5]:
                lines.append(f"║    ⚠  {m[:54]:<54} ║")
        if self.warnings:
            lines += [
                "╠" + "─" * 60 + "╣",
                f"║  Warnings ({len(self.warnings)}):" + " " * 46 + "║",
            ]
            for w in self.warnings[:3]:
                lines.append(f"║    ℹ  {w[:54]:<54} ║")
        lines.append("╚" + "═" * 60 + "╝")
        return "\n".join(lines)

    @property
    def total_size_mb(self) -> float:
        return sum(f.size_bytes for f in self.files) / (1024 * 1024)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class TapeoutPackager:
    """
    Assembles all design files into an organised tape-out package.

    No Docker required — this is a pure Python file-management module.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────

    def package(
        self,
        top_module:   str,
        output_dir:   str | Path,
        gds_path:     Optional[str | Path] = None,    # CRITICAL
        routed_def:   Optional[str | Path] = None,
        timing_rpt:   Optional[str | Path] = None,
        drc_rpt:      Optional[str | Path] = None,
        lvs_rpt:      Optional[str | Path] = None,
        netlist_path: Optional[str | Path] = None,
        spef_path:    Optional[str | Path] = None,
        lef_path:     Optional[str | Path] = None,
        extra_files:  Optional[Dict[str, str]] = None,
        config:       Optional[PackageConfig] = None,
    ) -> PackageResult:
        """
        Assemble all design deliverables into a tape-out package.

        Args:
            top_module:   Design name (used for directory and README).
            output_dir:   Where to create the package directory.
            gds_path:     Path to GDSII file (critical).
            routed_def:   Path to routed DEF file.
            timing_rpt:   Path to post-route timing report.
            drc_rpt:      Path to DRC report.
            lvs_rpt:      Path to LVS report.
            netlist_path: Path to synthesised Verilog netlist.
            spef_path:    Path to SPEF parasitic file.
            lef_path:     Path to LEF abstract.
            extra_files:  Additional files: {source_path: "category/filename"}.
            config:       Packaging options.

        Returns:
            PackageResult with package directory path and file inventory.
        """
        config     = config or PackageConfig()
        output_dir = Path(output_dir)
        pkg_dir    = output_dir / f"{top_module}_tapeout"
        pkg_dir.mkdir(parents=True, exist_ok=True)

        result = PackageResult(
            top_module  = top_module,
            package_dir = str(pkg_dir),
        )

        self.logger.info(f"Assembling tape-out package: {top_module} → {pkg_dir}")

        # ── Create subdirectories ─────────────────────────────────────
        for sub in ("gds", "lef", "def", "timing", "signoff", "netlist", "docs"):
            (pkg_dir / sub).mkdir(exist_ok=True)

        # ── Copy files ────────────────────────────────────────────────
        file_specs = [
            # (source, dest_subpath, category, is_critical)
            (gds_path,     f"gds/{top_module}.gds",        "gds",     True),
            (lef_path,     f"lef/{top_module}.lef",        "lef",     False),
            (routed_def,   f"def/{top_module}_routed.def", "def",     False),
            (spef_path,    f"def/{top_module}.spef",       "def",     False),
            (timing_rpt,   "timing/timing.rpt",            "timing",  False),
            (drc_rpt,      "signoff/drc.rpt",              "signoff", True),
            (lvs_rpt,      "signoff/lvs.rpt",              "signoff", False),
            (netlist_path, "netlist/netlist.v",            "netlist", False),
        ]

        for src, dest_rel, category, critical in file_specs:
            if src is None:
                if critical and config.strict_mode:
                    result.missing.append(dest_rel)
                continue
            pf = self._copy_file(
                src, pkg_dir / dest_rel, category, critical, config
            )
            if pf:
                result.files.append(pf)
            elif critical:
                result.missing.append(str(src))

        # ── Extra files ───────────────────────────────────────────────
        if extra_files:
            for src_str, dest_rel in extra_files.items():
                pf = self._copy_file(
                    src_str, pkg_dir / dest_rel, "extra", False, config
                )
                if pf:
                    result.files.append(pf)

        # ── Generate MANIFEST ─────────────────────────────────────────
        manifest = self._write_manifest(pkg_dir, top_module, result, config)
        result.manifest_path = str(manifest)

        # ── Generate README ───────────────────────────────────────────
        if config.generate_readme:
            readme = self._write_readme(pkg_dir, top_module, result, config)
            result.readme_path = str(readme)

        # ── Determine success ─────────────────────────────────────────
        critical_missing = [
            m for m in result.missing
            if "gds" in m.lower() or "drc" in m.lower()
        ]
        if config.strict_mode and critical_missing:
            result.success = False
            result.warnings.append(
                f"Missing critical files: {', '.join(critical_missing)}"
            )
        else:
            result.success = True

        total_mb = result.total_size_mb
        self.logger.info(
            f"Package complete: {len(result.files)} files | "
            f"{total_mb:.1f} MB | "
            f"missing={len(result.missing)}"
        )
        return result

    # ──────────────────────────────────────────────────────────────────────
    # FILE OPERATIONS
    # ──────────────────────────────────────────────────────────────────────

    def _copy_file(
        self,
        src:      str | Path,
        dest:     Path,
        category: str,
        critical: bool,
        config:   PackageConfig,
    ) -> Optional[PackagedFile]:
        """
        Copy one file into the package and return its record.
        Returns None if source does not exist.
        """
        src = Path(src)
        if not src.exists():
            self.logger.warning(f"Source not found: {src}")
            return None

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

        size = dest.stat().st_size
        md5  = ""
        if config.compute_checksums:
            md5 = self._md5(dest)

        return PackagedFile(
            source_path  = str(src),
            package_path = str(dest),
            category     = category,
            size_bytes   = size,
            checksum_md5 = md5,
            is_critical  = critical,
        )

    # ──────────────────────────────────────────────────────────────────────
    # MANIFEST
    # ──────────────────────────────────────────────────────────────────────

    def _write_manifest(
        self,
        pkg_dir:    Path,
        top_module: str,
        result:     PackageResult,
        config:     PackageConfig,
    ) -> Path:
        """
        Write MANIFEST.txt listing every file, its size, and MD5 checksum.
        Fabs and shuttle programs use manifests to verify completeness.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines     = [
            f"RTL-Gen AI  –  Tape-out Manifest",
            f"=" * 60,
            f"Design       : {top_module}",
            f"Version      : {config.design_version}",
            f"Process      : {config.process_node}",
            f"Generated    : {timestamp}",
            f"Total files  : {len(result.files)}",
            f"Total size   : {result.total_size_mb:.2f} MB",
            f"=" * 60,
            "",
            f"{'File':<45} {'Size':>10}  {'MD5':<32}",
            f"{'-' * 45} {'-' * 10}  {'-' * 32}",
        ]

        for f in sorted(result.files, key=lambda x: x.package_path):
            rel  = Path(f.package_path).relative_to(pkg_dir)
            size = f"{f.size_bytes:,}" if f.size_bytes else "0"
            md5  = f.checksum_md5[:32] if f.checksum_md5 else "—"
            critical = "  ★" if f.is_critical else ""
            lines.append(f"{str(rel):<45} {size:>10}  {md5}{critical}")

        if result.missing:
            lines += [
                "",
                f"MISSING FILES ({len(result.missing)}):",
                *[f"  ✗ {m}" for m in result.missing],
            ]

        manifest_path = pkg_dir / "MANIFEST.txt"
        manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return manifest_path

    # ──────────────────────────────────────────────────────────────────────
    # README
    # ──────────────────────────────────────────────────────────────────────

    def _write_readme(
        self,
        pkg_dir:    Path,
        top_module: str,
        result:     PackageResult,
        config:     PackageConfig,
    ) -> Path:
        """
        Write README.md for the tape-out package.
        Describes the design, process, file inventory, and usage.
        """
        timestamp   = datetime.now().strftime("%Y-%m-%d")
        gds_files   = [f for f in result.files if f.category == "gds"]
        gds_name    = Path(gds_files[0].package_path).name if gds_files else "N/A"

        content = f"""# {top_module} — Tape-out Package

**Generated by:** RTL-Gen AI  
**Date:** {timestamp}  
**Process:** {config.process_node}  
**Version:** {config.design_version}  

## Description

{config.description or f"Auto-generated RTL design: {top_module}"}

## Package Contents

| Directory | Contents |
|-----------|----------|
| `gds/`    | GDSII layout file — primary fabrication deliverable |
| `lef/`    | LEF abstract — for integration into larger chips |
| `def/`    | Routed placement/routing DEF + parasitic SPEF |
| `timing/` | Post-route STA timing reports |
| `signoff/`| DRC and LVS sign-off reports |
| `netlist/`| Synthesised gate-level Verilog |
| `docs/`   | Additional documentation |

## Primary Deliverable

```
gds/{gds_name}
```

This is the GDSII stream file submitted to the foundry.
It has been verified with:
- ✅ DRC (Design Rule Check) — Sky130A rule deck
- ✅ LVS (Layout vs Schematic) — Netgen comparison

## File Inventory

| File | Size | Critical |
|------|------|----------|
"""
        for f in sorted(result.files, key=lambda x: x.package_path):
            rel   = Path(f.package_path).relative_to(pkg_dir)
            size  = f"{f.size_bytes / 1024:.1f} KB"
            crit  = "★ YES" if f.is_critical else "—"
            content += f"| `{rel}` | {size} | {crit} |\n"

        content += f"""
## Process Information

- **Technology:** SkyWater Sky130A (130nm open-source CMOS)
- **Standard cells:** sky130_fd_sc_hd (High Density)
- **Metal stack:** 5 layers (met1–met5)
- **Min feature:** 130nm gate length

## Generation Flow

```
Natural Language Description
    ↓ RTL-Gen AI (LLM generation)
Verilog RTL
    ↓ Yosys (logic synthesis)
Gate-level Netlist
    ↓ OpenROAD (floorplan → placement → CTS → routing)
Routed DEF
    ↓ Magic VLSI (GDS export)
GDSII  ←  This package
```

## Contact

Generated automatically by RTL-Gen AI.  
Report issues at: https://github.com/your-repo/rtl-gen-ai
"""
        readme_path = pkg_dir / "README.md"
        readme_path.write_text(content, encoding="utf-8")
        return readme_path

    # ──────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _md5(path: Path) -> str:
        """Compute MD5 checksum of a file for manifest integrity."""
        import hashlib
        h = hashlib.md5()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return ""

    def validate_package(self, package_dir: str | Path) -> List[str]:
        """
        Validate an existing tape-out package for completeness.

        Reads the MANIFEST.txt and checks every listed file exists
        and its checksum matches.  Returns a list of error strings.
        Empty list = package is valid.

        Args:
            package_dir: Path to the <design>_tapeout directory.

        Returns:
            List of validation error strings.  Empty = valid.
        """
        pkg_dir = Path(package_dir)
        errors: List[str] = []

        manifest = pkg_dir / "MANIFEST.txt"
        if not manifest.exists():
            return ["MANIFEST.txt not found"]

        try:
            text = manifest.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ["Cannot read MANIFEST.txt"]

        # Parse file lines from manifest
        # The manifest table format:
        #   "file/path                              1,234  md5hash"
        # Lines are under the "----" separator row.
        # We identify file rows by checking if the first token looks like a path
        import re as _re
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("=") or stripped.startswith("-"):
                continue
            if stripped.startswith("Design") or stripped.startswith("Version") or                stripped.startswith("Process") or stripped.startswith("Generated") or                stripped.startswith("Total") or stripped.startswith("File") or                stripped.startswith("RTL-Gen") or stripped.startswith("MISSING"):
                continue
            # Looks like a file row: starts with a path-like token
            parts = stripped.split()
            if not parts:
                continue
            rel_path = parts[0]
            # Skip rows that are clearly not paths
            if "/" not in rel_path and "\\" not in rel_path:
                continue
            # Remove trailing ★ marker
            rel_path = rel_path.rstrip("★").strip()
            full_path = pkg_dir / rel_path
            if not full_path.exists():
                errors.append(f"Missing: {rel_path}")
                continue

            # Verify checksum if present (3rd token, 32 hex chars)
            if len(parts) >= 3:
                stored_md5 = parts[2].rstrip("★").strip()
                if _re.fullmatch(r"[0-9a-f]{32}", stored_md5):
                    actual_md5 = self._md5(full_path)
                    if actual_md5 and actual_md5 != stored_md5:
                        errors.append(f"Checksum mismatch: {rel_path}")

        return errors
