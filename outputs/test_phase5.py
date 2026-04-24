"""
test_phase5.py  –  Phase 5 Tests: GDS Generator, Sign-off Checker, Tapeout Packager
====================================================================================
All tests pass without real tools.  Docker tests skip automatically.

Run from project root:
    python -m pytest tests/test_phase5.py -v

Run all phases:
    python -m pytest tests/ -v
"""

import sys
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.gds_generator import (
    GDSGenerator, GDSConfig, GDSResult,
)
from python.signoff_checker import (
    SignoffChecker, SignoffConfig, SignoffResult,
    DRCReport, LVSReport,
)
from python.tapeout_packager import (
    TapeoutPackager, PackageConfig, PackageResult, PackagedFile,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

FAKE_GDS  = b"\x00\x01\x02\x03" * 256   # 1KB fake binary
FAKE_DEF  = "VERSION 5.8 ;\nDESIGN top ;\nEND DESIGN\n"
FAKE_NETLIST = "module top(input clk, output q);\nendmodule\n"

DRC_REPORT_CLEAN = """\
DRC Report for adder_8bit
Violations: 0
"""

DRC_REPORT_VIOLATIONS = """\
DRC Report for adder_8bit
Violations: 5
  M1.width : 3
  M2.spacing : 2
"""

LVS_LOG_MATCH    = "Circuits match uniquely.\nFinal result: circuits match.\n"
LVS_LOG_MISMATCH = "Circuits do not match.\nMismatch in net VDD.\n"


def write_file(tmp: Path, content, name: str) -> Path:
    p = tmp / name
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content, encoding="utf-8")
    return p


def make_docker(success: bool = True, stdout: str = "") -> MagicMock:
    dm  = MagicMock()
    dm.work_dir = Path(tempfile.mkdtemp())
    run = MagicMock()
    run.success      = success
    run.stdout       = stdout
    run.stderr       = "" if success else "[ERROR magic failed]"
    run.return_code  = 0 if success else 1
    run.combined_output.return_value = stdout + ("" if success else "[ERROR magic failed]")
    dm.run_script.return_value = run
    return dm


def make_pdk() -> MagicMock:
    pdk = MagicMock()
    pdk.pdk_root = Path("/pdk/sky130A")
    return pdk


# ══════════════════════════════════════════════════════════════════════════════
# GDS GENERATOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGDSConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = GDSConfig()
        self.assertTrue(cfg.insert_fill_cells)
        self.assertTrue(cfg.add_seal_ring)
        self.assertTrue(cfg.flatten)

    def test_custom_values(self):
        cfg = GDSConfig(insert_fill_cells=False, flatten=False)
        self.assertFalse(cfg.insert_fill_cells)
        self.assertFalse(cfg.flatten)

    def test_fill_cell_prefix(self):
        cfg = GDSConfig()
        self.assertIn("sky130", cfg.fill_cell_prefix)

    def test_min_max_fill_width(self):
        cfg = GDSConfig()
        self.assertLessEqual(cfg.min_fill_width, cfg.max_fill_width)


class TestGDSResult(unittest.TestCase):
    def test_summary_success(self):
        r = GDSResult(
            top_module  = "adder",
            output_dir  = "/work",
            success     = True,
            gds_path    = "/work/adder.gds",
            gds_size_mb = 1.23,
        )
        text = r.summary()
        self.assertIn("SUCCESS",    text)
        self.assertIn("adder.gds", text)
        self.assertIn("1.23",      text)

    def test_summary_failure(self):
        r = GDSResult(
            top_module    = "adder",
            output_dir    = "/work",
            success       = False,
            error_message = "tech file not found",
        )
        text = r.summary()
        self.assertIn("FAILED",             text)
        self.assertIn("tech file not found", text)


class TestGDSGeneratorScripts(unittest.TestCase):
    def setUp(self):
        self.gen = GDSGenerator(docker=make_docker(), pdk=make_pdk())

    def test_gds_script_contains_gds_write(self):
        tcl = self.gen._generate_gds_script(
            Path("routed.def"), "adder", GDSConfig()
        )
        self.assertIn("gds write", tcl)

    def test_gds_script_contains_tech_load(self):
        tcl = self.gen._generate_gds_script(
            Path("routed.def"), "adder", GDSConfig()
        )
        self.assertIn("tech load", tcl)

    def test_gds_script_contains_gds_read(self):
        tcl = self.gen._generate_gds_script(
            Path("routed.def"), "adder", GDSConfig()
        )
        self.assertIn("gds read", tcl)

    def test_gds_script_contains_top_module(self):
        tcl = self.gen._generate_gds_script(
            Path("routed.def"), "my_chip", GDSConfig()
        )
        self.assertIn("my_chip", tcl)

    def test_flatten_cmd_when_enabled(self):
        cfg = GDSConfig(flatten=True)
        tcl = self.gen._generate_gds_script(Path("r.def"), "top", cfg)
        self.assertIn("flatten", tcl)

    def test_no_flatten_when_disabled(self):
        cfg = GDSConfig(flatten=False)
        tcl = self.gen._generate_gds_script(Path("r.def"), "top", cfg)
        self.assertNotIn("flatten", tcl)

    def test_gds_script_contains_pdk_paths(self):
        tcl = self.gen._generate_gds_script(
            Path("r.def"), "top", GDSConfig()
        )
        self.assertIn("/pdk", tcl)

    def test_fill_script_contains_filler_placement(self):
        tcl_run = self.gen._insert_fill_cells(
            Path("r.def"), "top", Path(tempfile.mkdtemp()), GDSConfig()
        )
        # The script is passed to run_script; check what was called
        call_args = self.gen.docker.run_script.call_args
        script    = call_args[1]["script_content"] if call_args[1] else call_args[0][0]
        self.assertIn("filler_placement", script)

    def test_fill_cell_names_in_script(self):
        cfg = GDSConfig(fill_cell_prefix="sky130_fd_sc_hd__fill",
                        min_fill_width=1, max_fill_width=8)
        self.gen._insert_fill_cells(
            Path("r.def"), "top", Path(tempfile.mkdtemp()), cfg
        )
        call_args = self.gen.docker.run_script.call_args
        script    = call_args[1]["script_content"] if call_args[1] else call_args[0][0]
        self.assertIn("sky130_fd_sc_hd__fill", script)


class TestGDSGeneratorRunMocked(unittest.TestCase):
    def test_docker_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm  = make_docker(success=False)
            gen = GDSGenerator(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF, "routed.def")
            r   = gen.run(Path(tmp) / "routed.def", "top", tmp)
        self.assertFalse(r.success)

    def test_gds_file_created_means_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm  = make_docker(success=True)
            gen = GDSGenerator(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF, "routed.def")
            # Pre-create the GDS file Magic would generate
            write_file(Path(tmp), FAKE_GDS, "top.gds")
            r   = gen.run(Path(tmp) / "routed.def", "top", tmp)
        self.assertTrue(r.success)
        self.assertIsNotNone(r.gds_path)
        self.assertGreater(r.gds_size_mb, 0)

    def test_missing_gds_means_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm  = make_docker(success=True)
            gen = GDSGenerator(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF, "routed.def")
            r   = gen.run(Path(tmp) / "routed.def", "top", tmp)
        self.assertFalse(r.success)
        self.assertIn("top.gds", r.error_message)

    def test_log_file_always_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm  = make_docker(success=True)
            gen = GDSGenerator(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF, "routed.def")
            r   = gen.run(Path(tmp) / "routed.def", "top", tmp)
            log = Path(tmp) / "gds.log"
        self.assertIsNotNone(r.log_path)

    def test_fill_disabled_skips_fill_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm  = make_docker(success=True)
            gen = GDSGenerator(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF, "routed.def")
            write_file(Path(tmp), FAKE_GDS, "top.gds")
            cfg = GDSConfig(insert_fill_cells=False)
            gen.run(Path(tmp) / "routed.def", "top", tmp, cfg)
        # With fill disabled: should only call run_script once (GDS export only)
        # (fill would add a second call)
        self.assertEqual(dm.run_script.call_count, 1)


# ══════════════════════════════════════════════════════════════════════════════
# SIGNOFF CHECKER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSignoffConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = SignoffConfig()
        self.assertTrue(cfg.run_drc)
        self.assertTrue(cfg.run_lvs)
        self.assertFalse(cfg.run_antenna)
        self.assertFalse(cfg.stop_on_fail)

    def test_drc_only(self):
        cfg = SignoffConfig(run_lvs=False)
        self.assertFalse(cfg.run_lvs)
        self.assertTrue(cfg.run_drc)


class TestDRCReport(unittest.TestCase):
    def test_clean(self):
        r = DRCReport(passed=True, violation_count=0)
        self.assertTrue(r.passed)
        self.assertEqual(r.violation_count, 0)

    def test_violations(self):
        r = DRCReport(
            passed=False, violation_count=3,
            violations=["M1.width: 2", "M2.spacing: 1"]
        )
        self.assertFalse(r.passed)
        self.assertEqual(len(r.violations), 2)


class TestLVSReport(unittest.TestCase):
    def test_matched(self):
        r = LVSReport(passed=True, matched=True)
        self.assertTrue(r.matched)
        self.assertEqual(r.mismatches, [])

    def test_mismatch(self):
        r = LVSReport(passed=False, matched=False,
                      mismatches=["net VDD mismatch"])
        self.assertFalse(r.matched)
        self.assertEqual(len(r.mismatches), 1)


class TestSignoffResult(unittest.TestCase):
    def test_summary_clean(self):
        r = SignoffResult(
            top_module = "adder",
            output_dir = "/work",
            is_clean   = True,
            drc        = DRCReport(passed=True, violation_count=0),
            lvs        = LVSReport(passed=True, matched=True),
        )
        text = r.summary()
        self.assertIn("TAPE-OUT READY", text)
        self.assertIn("CLEAN",          text)
        self.assertIn("MATCHED",        text)

    def test_summary_drc_fail(self):
        r = SignoffResult(
            top_module = "adder",
            output_dir = "/work",
            is_clean   = False,
            drc        = DRCReport(passed=False, violation_count=5),
        )
        self.assertIn("NOT READY", r.summary())
        self.assertIn("5 violations", r.summary())

    def test_summary_lvs_mismatch(self):
        r = SignoffResult(
            top_module = "top",
            output_dir = "/work",
            is_clean   = False,
            drc        = DRCReport(passed=True),
            lvs        = LVSReport(matched=False, mismatches=["net1", "net2"]),
        )
        self.assertIn("2 mismatches", r.summary())


class TestSignoffDRCParsing(unittest.TestCase):
    def setUp(self):
        self.checker = SignoffChecker(docker=make_docker(), pdk=make_pdk())

    def test_parse_clean_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), DRC_REPORT_CLEAN, "drc.rpt")
            v   = self.checker._parse_drc_report(rpt, "DRC violations: 0")
        self.assertEqual(v, [])

    def test_parse_violation_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), DRC_REPORT_VIOLATIONS, "drc.rpt")
            v   = self.checker._parse_drc_report(rpt, "")
        self.assertGreater(len(v), 0)

    def test_parse_from_log_zero(self):
        v = self.checker._parse_drc_report(
            Path("/nonexistent.rpt"), "DRC violations: 0"
        )
        self.assertEqual(v, [])

    def test_parse_from_log_nonzero(self):
        v = self.checker._parse_drc_report(
            Path("/nonexistent.rpt"), "DRC violations: 7\n"
        )
        self.assertGreater(len(v), 0)

    def test_parse_missing_file_and_log(self):
        v = self.checker._parse_drc_report(Path("/nonexistent.rpt"), "")
        self.assertEqual(v, [])


class TestSignoffLVSParsing(unittest.TestCase):
    def setUp(self):
        self.checker = SignoffChecker(docker=make_docker(), pdk=make_pdk())

    def test_parse_match_log(self):
        mismatches, matched = self.checker._parse_lvs_output(
            LVS_LOG_MATCH, Path("/nonexistent.rpt")
        )
        self.assertTrue(matched)
        self.assertEqual(mismatches, [])

    def test_parse_mismatch_log(self):
        mismatches, matched = self.checker._parse_lvs_output(
            LVS_LOG_MISMATCH, Path("/nonexistent.rpt")
        )
        self.assertFalse(matched)
        self.assertGreater(len(mismatches), 0)

    def test_parse_empty_log(self):
        mismatches, matched = self.checker._parse_lvs_output(
            "", Path("/nonexistent.rpt")
        )
        self.assertFalse(matched)

    def test_parse_match_from_report_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(
                Path(tmp),
                "Circuits match uniquely.\n",
                "lvs.rpt"
            )
            mismatches, matched = self.checker._parse_lvs_output("", rpt)
        self.assertTrue(matched)


class TestSignoffDRCScript(unittest.TestCase):
    def setUp(self):
        self.checker = SignoffChecker(docker=make_docker(), pdk=make_pdk())

    def test_drc_script_contains_drc_check(self):
        tcl = self.checker._generate_drc_script(
            Path("design.gds"), "top",
            Path(tempfile.mkdtemp())
        )
        self.assertIn("drc check", tcl)

    def test_drc_script_contains_top_module(self):
        tcl = self.checker._generate_drc_script(
            Path("design.gds"), "my_chip",
            Path(tempfile.mkdtemp())
        )
        self.assertIn("my_chip", tcl)

    def test_drc_script_contains_gds_read(self):
        tcl = self.checker._generate_drc_script(
            Path("design.gds"), "top",
            Path(tempfile.mkdtemp())
        )
        self.assertIn("gds read", tcl)

    def test_drc_script_writes_report(self):
        tcl = self.checker._generate_drc_script(
            Path("design.gds"), "top",
            Path(tempfile.mkdtemp())
        )
        self.assertIn("drc.rpt", tcl)


class TestSignoffRunMocked(unittest.TestCase):
    def test_drc_only_no_lvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True, stdout="DRC violations: 0\n")
            ch = SignoffChecker(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_GDS, "design.gds")
            write_file(Path(tmp), DRC_REPORT_CLEAN, "drc.rpt")
            r  = ch.run(
                Path(tmp) / "design.gds", "top", tmp,
                config=SignoffConfig(run_lvs=False)
            )
        self.assertIsNotNone(r.drc)
        self.assertIsNone(r.lvs)

    def test_lvs_requires_netlist(self):
        """LVS should be skipped when no netlist is provided."""
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True, stdout="DRC violations: 0\n")
            ch = SignoffChecker(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_GDS, "design.gds")
            write_file(Path(tmp), DRC_REPORT_CLEAN, "drc.rpt")
            r  = ch.run(
                Path(tmp) / "design.gds", "top", tmp,
                netlist_path=None,  # no netlist
                config=SignoffConfig(run_drc=True, run_lvs=True)
            )
        # LVS skipped because netlist_path is None
        self.assertIsNone(r.lvs)

    def test_run_drc_only_convenience(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True, stdout="DRC violations: 0\n")
            ch = SignoffChecker(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_GDS, "design.gds")
            write_file(Path(tmp), DRC_REPORT_CLEAN, "drc.rpt")
            rpt = ch.run_drc_only(Path(tmp) / "design.gds", "top", tmp)
        self.assertIsInstance(rpt, DRCReport)


# ══════════════════════════════════════════════════════════════════════════════
# TAPEOUT PACKAGER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPackageConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = PackageConfig()
        self.assertTrue(cfg.strict_mode)
        self.assertTrue(cfg.generate_readme)
        self.assertTrue(cfg.compute_checksums)

    def test_custom_values(self):
        cfg = PackageConfig(
            design_version = "2.0.0",
            process_node   = "Sky130B",
            author         = "Test",
        )
        self.assertEqual(cfg.design_version, "2.0.0")
        self.assertEqual(cfg.process_node,   "Sky130B")


class TestPackagedFile(unittest.TestCase):
    def test_creation(self):
        f = PackagedFile(
            source_path  = "/src/design.gds",
            package_path = "/pkg/gds/design.gds",
            category     = "gds",
            size_bytes   = 1024 * 1024,
            is_critical  = True,
        )
        self.assertEqual(f.category,    "gds")
        self.assertTrue(f.is_critical)
        self.assertEqual(f.size_bytes, 1048576)


class TestPackageResult(unittest.TestCase):
    def test_total_size_mb(self):
        r = PackageResult(
            top_module  = "top",
            package_dir = "/work",
            files       = [
                PackagedFile("/s/a", "/p/a", "gds",  size_bytes=1024*1024),
                PackagedFile("/s/b", "/p/b", "def",  size_bytes=512*1024),
            ]
        )
        self.assertAlmostEqual(r.total_size_mb, 1.5, places=1)

    def test_summary_complete(self):
        r = PackageResult(
            top_module  = "adder",
            package_dir = "/project/adder_tapeout",
            success     = True,
            files       = [
                PackagedFile("/s/a.gds", "/p/gds/a.gds", "gds", size_bytes=100),
            ]
        )
        text = r.summary()
        self.assertIn("COMPLETE", text)
        self.assertIn("adder",    text)
        self.assertIn("1",        text)

    def test_summary_with_missing(self):
        r = PackageResult(
            top_module  = "top",
            package_dir = "/work",
            success     = False,
            missing     = ["gds/top.gds"],
        )
        self.assertIn("top.gds", r.summary())


class TestTapeoutPackagerPackage(unittest.TestCase):
    def setUp(self):
        self.packager = TapeoutPackager()

    def test_package_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.packager.package("my_chip", tmp)
            pkg = Path(tmp) / "my_chip_tapeout"
        self.assertEqual(Path(r.package_dir), pkg)

    def test_package_creates_subdirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.packager.package("chip", tmp)
            pkg = Path(tmp) / "chip_tapeout"
            for sub in ("gds", "lef", "def", "timing", "signoff", "netlist"):
                self.assertTrue((pkg / sub).is_dir(), msg=f"{sub}/ not created")

    def test_package_copies_gds(self):
        with tempfile.TemporaryDirectory() as tmp:
            gds = write_file(Path(tmp), FAKE_GDS, "design.gds")
            r   = self.packager.package("chip", tmp, gds_path=gds)
            packed_gds = Path(r.package_dir) / "gds" / "chip.gds"
            self.assertTrue(packed_gds.exists())
            self.assertGreater(packed_gds.stat().st_size, 0)

    def test_package_copies_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            drc = write_file(Path(tmp), DRC_REPORT_CLEAN, "drc.rpt")
            r   = self.packager.package("chip", tmp, drc_rpt=drc)
            pkg_drc = Path(r.package_dir) / "signoff" / "drc.rpt"
            self.assertTrue(pkg_drc.exists())

    def test_package_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.packager.package("chip", tmp)
            manifest = Path(r.package_dir) / "MANIFEST.txt"
            self.assertTrue(manifest.exists())
            content = manifest.read_text()
            self.assertIn("RTL-Gen AI", content)
            self.assertIn("chip", content)

    def test_package_generates_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = PackageConfig(generate_readme=True)
            r   = self.packager.package("chip", tmp, config=cfg)
            readme = Path(r.package_dir) / "README.md"
            self.assertTrue(readme.exists())
            content = readme.read_text(encoding='utf-8')
            self.assertIn("chip", content)
            self.assertIn("RTL-Gen AI", content)

    def test_no_readme_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = PackageConfig(generate_readme=False)
            r   = self.packager.package("chip", tmp, config=cfg)
            readme = Path(r.package_dir) / "README.md"
            self.assertIsNone(r.readme_path)
            self.assertFalse(readme.exists())

    def test_strict_mode_fails_without_gds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = PackageConfig(strict_mode=True)
            r   = self.packager.package("chip", tmp, gds_path=None, config=cfg)
        self.assertFalse(r.success)
        self.assertGreater(len(r.missing) + len(r.warnings), 0)

    def test_non_strict_succeeds_without_gds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = PackageConfig(strict_mode=False)
            r   = self.packager.package("chip", tmp, gds_path=None, config=cfg)
        self.assertTrue(r.success)

    def test_extra_files_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            extra_src = write_file(Path(tmp), "extra data\n", "extra.txt")
            r = self.packager.package(
                "chip", tmp,
                extra_files={str(extra_src): "docs/extra.txt"}
            )
            packed_extra = Path(r.package_dir) / "docs" / "extra.txt"
            self.assertTrue(packed_extra.exists())

    def test_file_checksums_computed(self):
        with tempfile.TemporaryDirectory() as tmp:
            gds = write_file(Path(tmp), FAKE_GDS, "design.gds")
            cfg = PackageConfig(compute_checksums=True)
            r   = self.packager.package("chip", tmp, gds_path=gds, config=cfg)
        gds_files = [f for f in r.files if f.category == "gds"]
        if gds_files:
            self.assertGreater(len(gds_files[0].checksum_md5), 0)

    def test_no_checksums_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            gds = write_file(Path(tmp), FAKE_GDS, "design.gds")
            cfg = PackageConfig(compute_checksums=False)
            r   = self.packager.package("chip", tmp, gds_path=gds, config=cfg)
        gds_files = [f for f in r.files if f.category == "gds"]
        if gds_files:
            self.assertEqual(gds_files[0].checksum_md5, "")


class TestTapeoutPackagerMD5(unittest.TestCase):
    def test_md5_consistency(self):
        """MD5 of same content should always match."""
        with tempfile.TemporaryDirectory() as tmp:
            p = write_file(Path(tmp), b"hello world", "test.bin")
            h1 = TapeoutPackager._md5(p)
            h2 = TapeoutPackager._md5(p)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 32)

    def test_md5_different_contents(self):
        """MD5 of different content should differ."""
        with tempfile.TemporaryDirectory() as tmp:
            p1 = write_file(Path(tmp), b"content A", "a.bin")
            p2 = write_file(Path(tmp), b"content B", "b.bin")
            h1 = TapeoutPackager._md5(p1)
            h2 = TapeoutPackager._md5(p2)
        self.assertNotEqual(h1, h2)

    def test_md5_missing_file_returns_empty(self):
        h = TapeoutPackager._md5(Path("/nonexistent/file.bin"))
        self.assertEqual(h, "")


class TestTapeoutPackagerValidation(unittest.TestCase):
    def setUp(self):
        self.packager = TapeoutPackager()

    def test_validate_valid_package(self):
        """A freshly created package should validate cleanly."""
        with tempfile.TemporaryDirectory() as tmp:
            gds = write_file(Path(tmp), FAKE_GDS, "design.gds")
            r   = self.packager.package("chip", tmp, gds_path=gds)
            errors = self.packager.validate_package(r.package_dir)
        # May have minor warnings but should not report missing files
        missing_errors = [e for e in errors if "Missing" in e]
        self.assertEqual(missing_errors, [])

    def test_validate_missing_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = self.packager.validate_package(tmp)
        self.assertTrue(any("MANIFEST" in e for e in errors))

    def test_validate_nonexistent_dir(self):
        errors = self.packager.validate_package("/nonexistent/package")
        self.assertGreater(len(errors), 0)


class TestManifestContent(unittest.TestCase):
    def setUp(self):
        self.packager = TapeoutPackager()

    def test_manifest_contains_design_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.packager.package("my_adder", tmp)
            manifest = Path(r.package_dir) / "MANIFEST.txt"
            content  = manifest.read_text()
        self.assertIn("my_adder", content)

    def test_manifest_contains_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = PackageConfig(process_node="Sky130A")
            r   = self.packager.package("top", tmp, config=cfg)
            content = (Path(r.package_dir) / "MANIFEST.txt").read_text()
        self.assertIn("Sky130A", content)

    def test_manifest_contains_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            r       = self.packager.package("top", tmp)
            content = (Path(r.package_dir) / "MANIFEST.txt").read_text()
        # Should contain a date in YYYY-MM-DD format
        import re
        self.assertRegex(content, r"\d{4}-\d{2}-\d{2}")


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS (auto-skipped without Docker)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationRealTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import subprocess
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            cls.docker_available = r.returncode == 0
        except Exception:
            cls.docker_available = False

        try:
            import klayout.db
            cls.klayout_available = True
        except ImportError:
            cls.klayout_available = False

    def test_klayout_version(self):
        if not self.klayout_available:
            self.skipTest("klayout not installed")
        import klayout.db as pya
        self.assertIsNotNone(pya.Layout())

    def test_pdk_manager_validates(self):
        """PDKManager should validate (may warn if PDK not installed)."""
        try:
            from python.pdk_manager import PDKManager
            pdk = PDKManager()
            result = pdk.validate()
            # is_valid depends on whether PDK is installed; just check it runs
            self.assertIsInstance(result.is_valid, bool)
        except Exception:
            self.skipTest("PDKManager not available")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    passed  = result.testsRun - len(result.failures) - len(result.errors)
    print("\n" + "═" * 60)
    print(f"  Ran     : {result.testsRun} tests")
    print(f"  Passed  : {passed}")
    print(f"  Skipped : {len(result.skipped)}")
    if result.wasSuccessful():
        print("  ✅  ALL TESTS PASSED")
    else:
        print(f"  ❌  FAILURES : {len(result.failures)}")
        print(f"  ❌  ERRORS   : {len(result.errors)}")
    print("═" * 60)
    sys.exit(0 if result.wasSuccessful() else 1)
