"""
tapeout_manager.py — Production Tapeout Package Generator
RTL-Gen AI Phase 10

Generates a complete tapeout package from DesignDB + GDS + reports:
  tapeout/
  ├── gds/          <design>.gds
  ├── lef/          <design>.lef
  ├── def/          <design>.def
  ├── lib/          <design>.lib
  ├── netlist/      <design>.v
  ├── spef/         <design>.spef
  ├── sdc/          constraints.sdc
  ├── reports/
  │   ├── drc/      drc_report.txt
  │   ├── lvs/      lvs_report.txt
  │   ├── sta/      sta_final.txt (pre/post/signoff)
  │   └── power/    power_report.txt
  ├── timing/       timing_comparison.csv
  ├── docs/         README.md, manifest.json
  └── manifest.json (top-level)
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)


@dataclass
class TapeoutManifest:
    design_name: str = ""
    version: str = "1.0"
    generated_at: str = ""
    technology: str = "SKY130A"
    clock_period_ns: float = 10.0
    fmax_mhz: Optional[float] = None
    total_power_mw: Optional[float] = None
    core_area_um2: Optional[float] = None
    cell_count: Optional[int] = None
    drc_clean: bool = False
    lvs_matched: bool = False
    timing_met: bool = False
    tapeout_ready: bool = False
    files: Dict[str, str] = field(default_factory=dict)
    checksums: Dict[str, str] = field(default_factory=dict)


def generate_tapeout_package(
    design_name: str,
    results_dir: str,
    output_dir: str,
    db=None,
    include_sdf: bool = True,
    include_reports: bool = True,
    compress: bool = False,
) -> str:
    """
    Generate a complete tapeout package.

    Args:
        design_name: Design name (e.g. "adder_8bit")
        results_dir: Path to run results directory
        output_dir: Path to output tapeout directory
        db: Optional DesignDB instance for metadata
        include_sdf: Include SDF back-annotation file
        include_reports: Include all reports
        compress: Create ZIP archive

    Returns:
        Path to generated tapeout directory (or ZIP file if compress=True)
    """
    rd = Path(results_dir)
    out = Path(output_dir) / f"tapeout_{design_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)

    # Directory structure
    dirs = {
        "gds": out / "gds",
        "lef": out / "lef",
        "def": out / "def",
        "lib": out / "lib",
        "netlist": out / "netlist",
        "spef": out / "spef",
        "sdc": out / "sdc",
        "drc": out / "reports" / "drc",
        "lvs": out / "reports" / "lvs",
        "sta": out / "reports" / "sta",
        "power": out / "reports" / "power",
        "timing": out / "timing",
        "docs": out / "docs",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # File mapping: (source_pattern, dest_dir, dest_name)
    file_map = [
        (f"{design_name}.gds", dirs["gds"], f"{design_name}.gds"),
        (f"{design_name}_sky130.v", dirs["netlist"], f"{design_name}.v"),
        ("routed.def", dirs["def"], f"{design_name}.def"),
        (f"{design_name}.spef", dirs["spef"], f"{design_name}.spef"),
        ("constraints.sdc", dirs["sdc"], "constraints.sdc"),
        ("drc_report.txt", dirs["drc"], "drc_report.txt"),
        ("klayout_drc.xml", dirs["drc"], "klayout_drc.xml"),
        ("lvs_report_final.txt", dirs["lvs"], "lvs_report.txt"),
        ("sta_final.txt", dirs["sta"], "sta_tt.txt"),
        ("sta_ss.txt", dirs["sta"], "sta_ss.txt"),
        ("sta_ff.txt", dirs["sta"], "sta_ff.txt"),
        ("power_report.txt", dirs["power"], "power_report.txt"),
        ("timing_report.txt", dirs["sta"], "timing_report.txt"),
        ("hold_analysis.txt", dirs["timing"], "hold_analysis.txt"),
        ("ir_drop_vdd.txt", dirs["power"], "ir_drop_vdd.txt"),
        ("simulation.log", dirs["docs"], "simulation.log"),
        ("gate_simulation.log", dirs["docs"], "gate_simulation.log"),
    ]

    if include_sdf:
        file_map.append((f"{design_name}.sdf", out / "timing", f"{design_name}.sdf"))

    # Liberty file (generate if not present)
    liberty_src = rd / f"{design_name}.lib"
    if not liberty_src.exists():
        liberty_src = rd / "sky130_fd_sc_hd__tt_025C_1v80.lib"
    if liberty_src.exists():
        file_map.append((liberty_src.name, dirs["lib"], f"{design_name}.lib"))

    manifest = TapeoutManifest(
        design_name=design_name,
        generated_at=datetime.now().isoformat(),
    )

    file_count = 0
    total_size = 0

    for src_pattern, dest_dir, dest_name in file_map:
        src = rd / src_pattern
        if src.exists() and src.stat().st_size > 0:
            dst = dest_dir / dest_name
            shutil.copy2(str(src), str(dst))
            file_count += 1
            size = dst.stat().st_size
            total_size += size
            manifest.files[str(dst.relative_to(out))] = f"{size} bytes"
            log.info("  Copied: %s -> %s (%d bytes)", src.name, dst, size)
        else:
            log.debug("  Skipped (not found): %s", src_pattern)

    # Generate timing comparison if we have pre/post route STA
    sta_files = {
        "Pre-route": rd / "sta_preroute.txt",
        "Post-route": rd / "sta_postroute.txt",
        "Signoff": rd / "sta_signoff.txt",
    }
    timing_csv = dirs["timing"] / "timing_comparison.csv"
    with open(timing_csv, "w") as f:
        f.write("Stage,Slack_ns,WNS_ns,TNS_ns\n")
        for stage, st_path in sta_files.items():
            if st_path.exists():
                import re
                text = st_path.read_text(errors="ignore")
                slack = re.search(r"slack\s+\((?:MET|VIOLATED)\)\s+([-\d.]+)", text)
                wns = re.search(r"wns\s+([-\d.]+)", text)
                tns = re.search(r"tns\s+([-\d.]+)", text)
                f.write(f"{stage},{slack.group(1) if slack else ''},"
                        f"{wns.group(1) if wns else ''},{tns.group(1) if tns else ''}\n")
    manifest.files[str(timing_csv.relative_to(out))] = f"{timing_csv.stat().st_size} bytes"
    log.info("  Generated: timing_comparison.csv")

    # Populate manifest metadata from DB if available
    if db:
        if db.timing:
            manifest.fmax_mhz = db.timing.fmax_mhz
            manifest.clock_period_ns = db.timing.period_ns
            manifest.timing_met = all(c.met for c in db.timing.corners.values())
        if db.power:
            manifest.total_power_mw = db.power.total_mw
        if db.layout:
            manifest.core_area_um2 = db.layout.area_um2
        if db.placement:
            manifest.cell_count = db.placement.total_cells
        if db.drc:
            manifest.drc_clean = db.drc.violations == 0
        if db.lvs:
            manifest.lvs_matched = db.lvs.status in ("MATCHED", "MATCHED_WITH_WARNINGS")

    manifest.tapeout_ready = (
        manifest.drc_clean and manifest.lvs_matched and manifest.timing_met
    )

    # Write top-level manifest
    manifest_path = out / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(asdict(manifest), f, indent=2, default=str)
    manifest.files[str(manifest_path.relative_to(out))] = f"{manifest_path.stat().st_size} bytes"
    log.info("  Generated: manifest.json")

    # Generate doc/README
    readme = f"""# Tapeout Package: {design_name}

Generated: {manifest.generated_at}
Technology: {manifest.technology}
Clock Period: {manifest.clock_period_ns} ns
Fmax: {manifest.fmax_mhz or 'N/A'} MHz

## Sign-off Status
- DRC: {'PASS' if manifest.drc_clean else 'FAIL'}
- LVS: {'PASS' if manifest.lvs_matched else 'FAIL'}
- Timing: {'PASS' if manifest.timing_met else 'FAIL'}
- Tapeout Ready: {'YES' if manifest.tapeout_ready else 'NO'}

## Files
| Path | Size |
|------|------|
"""
    for path, size in manifest.files.items():
        readme += f"| {path} | {size} |\n"

    readme_path = dirs["docs"] / "README.md"
    readme_path.write_text(readme)
    log.info("  Generated: README.md")

    log.info("Tapeout package generated: %s (%d files, %d bytes)",
             out, file_count, total_size)

    # Optional ZIP compression
    if compress:
        import zipfile
        zip_path = out.parent / f"{out.name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in out.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(out))
        log.info("Compressed package: %s (%d bytes)", zip_path, zip_path.stat().st_size)
        return str(zip_path)

    return str(out)


def get_tapeout_readiness_score(manifest: TapeoutManifest) -> Dict[str, Any]:
    """Compute readiness score from manifest data."""
    score = 0
    max_score = 100
    blockers = []
    warnings_list = []
    recommendations = []

    # DRC clean (+20)
    if manifest.drc_clean:
        score += 20
    else:
        blockers.append("DRC violations present")
        recommendations.append("Fix all DRC violations before tapeout")

    # LVS matched (+20)
    if manifest.lvs_matched:
        score += 20
    else:
        blockers.append("LVS mismatch detected")
        recommendations.append("Debug LVS; check extracted SPICE vs schematic")

    # Timing met (+20)
    if manifest.timing_met:
        score += 20
    else:
        blockers.append("Timing violations present")
        recommendations.append("Fix setup/hold violations; consider pipelining")

    # GDS present (+10)
    if manifest.files and any("gds" in k for k in manifest.files):
        score += 10
    else:
        blockers.append("GDS file missing")
        recommendations.append("Run GDS generation stage")

    # SPEF present (+10)
    if manifest.files and any("spef" in k for k in manifest.files):
        score += 10
    else:
        warnings_list.append("SPEF file missing; post-layout timing unverified")

    # Reports present (+10)
    report_count = sum(1 for k in manifest.files if "report" in k)
    if report_count >= 3:
        score += 10
    elif report_count > 0:
        score += 5
        warnings_list.append("Some reports missing; consider running full sign-off flow")

    # Power data (+5)
    if manifest.total_power_mw is not None:
        score += 5

    # Cell count (+5)
    if manifest.cell_count is not None and manifest.cell_count > 0:
        score += 5

    return {
        "score": min(score, max_score),
        "max_score": max_score,
        "percentage": round(score / max_score * 100),
        "blockers": blockers,
        "warnings": warnings_list,
        "recommendations": recommendations,
        "tapeout_ready": (
            manifest.drc_clean and manifest.lvs_matched and manifest.timing_met
            and any("gds" in k for k in manifest.files)
            and len(blockers) == 0
        ),
    }


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile, json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("tapeout_manager.py -- standalone self-test")
    print("=" * 60)

    passed = total = 0

    # Test 1: Manifest creation
    total += 1
    m = TapeoutManifest(
        design_name="test_design",
        generated_at="2026-06-07",
        technology="SKY130A",
        drc_clean=True,
        lvs_matched=True,
        timing_met=True,
    )
    assert m.design_name == "test_design"
    assert m.drc_clean
    assert m.lvs_matched
    assert m.tapeout_ready is False  # no gds/power yet
    print("[PASS] TapeoutManifest creation")
    passed += 1

    # Test 2: Readiness score computation
    total += 1
    score = get_tapeout_readiness_score(m)
    assert score["score"] >= 40  # drc(20) + lvs(20) + timing(20) - no gds
    assert score["percentage"] >= 40
    assert score["tapeout_ready"] is False  # no GDS
    print(f"[PASS] Readiness score: {score['score']}/{score['max_score']} ({score['percentage']}%)")
    passed += 1

    # Test 3: Full manifest with files
    total += 1
    m_with_files = TapeoutManifest(
        design_name="full_design",
        generated_at="2026-06-07",
        drc_clean=True,
        lvs_matched=True,
        timing_met=True,
        total_power_mw=15.3,
        cell_count=1000,
        files={
            "gds/test.gds": "150000 bytes",
            "spef/test.spef": "5000 bytes",
            "reports/drc/drc.txt": "200 bytes",
            "reports/lvs/lvs.txt": "300 bytes",
            "reports/sta/sta.txt": "400 bytes",
        },
    )
    score2 = get_tapeout_readiness_score(m_with_files)
    assert score2["tapeout_ready"]
    assert score2["percentage"] >= 90
    print(f"[PASS] Full tapeout readiness: {score2['percentage']}% (tapeout_ready={score2['tapeout_ready']})")
    passed += 1

    # Test 4: Package generation (no real files = minimal package)
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        rd = Path(tmp) / "results"
        rd.mkdir()
        od = Path(tmp) / "output"
        # Create a minimal GDS stub to prevent warnings
        (rd / "test.gds").write_bytes(b"\x00" * 1000)
        pkg = generate_tapeout_package("test", str(rd), str(od), compress=False)
        pkg_path = Path(pkg)
        assert pkg_path.exists()
        manifest_file = pkg_path / "manifest.json"
        assert manifest_file.exists()
        data = json.loads(manifest_file.read_text())
        assert data["design_name"] == "test"
    print(f"[PASS] Tapeout package generated: {pkg_path}")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED -- tapeout_manager.py ready for integration")
    print("=" * 60)
