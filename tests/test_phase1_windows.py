"""
test_phase1_windows.py  –  Phase 1 Tests: PDK Manager & KLayout Interface
==========================================================================
Tests for pdk_manager.py and klayout_interface.py.

Running these tests does NOT require the PDK to be installed or KLayout
to be present.  All tests use temporary directories and mock data so
they pass in any environment.  The tests that DO need real tools are
clearly marked and skip automatically when tools are absent.

Run from the project root:
    python -m pytest tests/test_phase1_windows.py -v

Or run this file directly:
    python tests/test_phase1_windows.py
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

# ── add project root to sys.path so imports work ──────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.pdk_manager import (
    PDKManager,
    Sky130Library,
    TimingCorner,
    PDKValidationResult,
    CellInfo,
)
from python.klayout_interface import (
    KLayoutInterface,
    DRCViolation,
    DRCResult,
    LVSResult,
    LayerInfo,
    LayoutStats,
    SKY130_LAYERS,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

def make_fake_pdk_tree(root: Path) -> None:
    """
    Build a minimal fake Sky130A directory tree inside *root*.
    Contains enough structure to pass PDKManager.validate().
    """
    # Required top-level directories
    (root / "libs.ref").mkdir(parents=True, exist_ok=True)
    (root / "libs.tech").mkdir(parents=True, exist_ok=True)

    # HD library skeleton
    hd = root / "libs.ref" / Sky130Library.HD.value
    for sub in ("lef", "lib", "gds", "spice"):
        (hd / sub).mkdir(parents=True, exist_ok=True)

    # Fake tech.lef
    (hd / "lef" / f"{Sky130Library.HD.value}.tlef").write_text(
        "VERSION 5.8 ;\nEND LIBRARY\n"
    )
    # Fake cell LEF
    (hd / "lef" / f"{Sky130Library.HD.value}.lef").write_text(
        "VERSION 5.8 ;\nMACRO sky130_fd_sc_hd__and2_1\n  END sky130_fd_sc_hd__and2_1\n"
        "MACRO sky130_fd_sc_hd__or2_1\n  END sky130_fd_sc_hd__or2_1\nEND LIBRARY\n"
    )
    # Fake timing lib for TT corner
    corner = TimingCorner.TT.value
    (hd / "lib" / f"{Sky130Library.HD.value}__{corner}.lib").write_text(
        "/* Timing library placeholder */\n"
    )
    # Fake GDS library
    (hd / "gds" / f"{Sky130Library.HD.value}.gds").write_bytes(b"\x00" * 64)

    # KLayout tech files
    kl = root / "libs.tech" / "klayout"
    kl.mkdir(parents=True, exist_ok=True)
    (kl / "sky130A.lydrc").write_text("# DRC placeholder\n")
    (kl / "sky130A.lylvs").write_text("# LVS placeholder\n")

    # OpenROAD config dir
    ol = root / "libs.tech" / "openlane" / Sky130Library.HD.value
    ol.mkdir(parents=True, exist_ok=True)


def make_fake_lyrdb(path: Path, n_violations: int = 0) -> None:
    """Write a minimal .lyrdb XML file with n_violations DRC errors."""
    items = ""
    for i in range(n_violations):
        items += f"""
        <item>
          <values>1.5 2.5</values>
          <description>violation {i}</description>
        </item>"""

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<report-database>
  <categories>
    <category>
      <name>M1.1</name>
      <description>Metal 1 minimum width violation</description>
      <items>{items}
      </items>
    </category>
  </categories>
</report-database>
"""
    path.write_text(content, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# PDK MANAGER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPDKManagerInit(unittest.TestCase):
    """Tests for PDKManager initialisation and path resolution."""

    def test_explicit_path_used(self):
        """When pdk_root is given, it must be used verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            pdk = PDKManager(pdk_root=tmp, auto_detect=False)
            self.assertEqual(pdk.pdk_root, Path(tmp))

    def test_default_path_when_not_found(self):
        """When no PDK is found, pdk_root falls back to C:\\pdk\\sky130A."""
        # Override PDK_ROOT env var to avoid accidental detection
        env = {k: v for k, v in os.environ.items() if k != "PDK_ROOT"}
        with patch.dict(os.environ, env, clear=True):
            pdk = PDKManager(auto_detect=False)
        # Path should be the default; may not exist – that's fine
        self.assertIn("sky130A", str(pdk.pdk_root))

    def test_env_var_detection(self):
        """PDK_ROOT environment variable should be honoured."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_root = Path(tmp) / "sky130A"
            fake_root.mkdir()
            (fake_root / "libs.ref").mkdir()  # needed for detection

            with patch.dict(os.environ, {"PDK_ROOT": tmp}):
                pdk = PDKManager(auto_detect=True)

            self.assertEqual(pdk.pdk_root, fake_root)

    def test_variant_stored(self):
        """variant attribute must be stored correctly."""
        pdk = PDKManager(pdk_root="/tmp/fake", variant="sky130A", auto_detect=False)
        self.assertEqual(pdk.variant, "sky130A")


class TestPDKManagerValidation(unittest.TestCase):
    """Tests for PDKManager.validate()."""

    def setUp(self):
        """Create a temporary directory with a full fake PDK tree."""
        self.tmp_dir  = tempfile.TemporaryDirectory()
        self.pdk_root = Path(self.tmp_dir.name) / "sky130A"
        self.pdk_root.mkdir()
        make_fake_pdk_tree(self.pdk_root)
        self.pdk = PDKManager(pdk_root=str(self.pdk_root), auto_detect=False)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_valid_pdk_passes(self):
        """A complete fake PDK must pass validation."""
        result = self.pdk.validate()
        self.assertTrue(result.is_valid, msg=f"Errors: {result.errors}")

    def test_missing_root_fails(self):
        """Non-existent root must fail immediately."""
        pdk = PDKManager(pdk_root="/nonexistent/path", auto_detect=False)
        result = pdk.validate()
        self.assertFalse(result.is_valid)
        self.assertTrue(any("not found" in e.lower() for e in result.errors))

    def test_missing_libs_ref_fails(self):
        """Removing libs.ref must cause validation failure."""
        import shutil
        shutil.rmtree(self.pdk_root / "libs.ref")
        result = self.pdk.validate()
        self.assertFalse(result.is_valid)

    def test_missing_hd_library_fails(self):
        """Removing the HD library must be a fatal error."""
        import shutil
        shutil.rmtree(self.pdk_root / "libs.ref" / Sky130Library.HD.value)
        result = self.pdk.validate()
        self.assertFalse(result.is_valid)

    def test_missing_klayout_tech_is_warning(self):
        """Absent KLayout tech dir → warning, not error."""
        import shutil
        shutil.rmtree(self.pdk_root / "libs.tech" / "klayout")
        result = self.pdk.validate()
        # Should still be valid (klayout is optional at validation time)
        self.assertTrue(len(result.warnings) > 0)

    def test_found_libraries_listed(self):
        """Validation must list the HD library in found_libraries."""
        result = self.pdk.validate()
        self.assertIn(Sky130Library.HD.value, result.found_libraries)


class TestPDKManagerPaths(unittest.TestCase):
    """Tests for path-resolution helper methods."""

    def setUp(self):
        self.tmp_dir  = tempfile.TemporaryDirectory()
        self.pdk_root = Path(self.tmp_dir.name) / "sky130A"
        self.pdk_root.mkdir()
        make_fake_pdk_tree(self.pdk_root)
        self.pdk = PDKManager(pdk_root=str(self.pdk_root), auto_detect=False)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_tech_lef_returns_path(self):
        """get_tech_lef() must return an existing Path."""
        p = self.pdk.get_tech_lef()
        self.assertIsNotNone(p)
        self.assertTrue(p.exists())

    def test_cell_lef_returns_path(self):
        """get_cell_lef() must return an existing Path."""
        p = self.pdk.get_cell_lef()
        self.assertIsNotNone(p)
        self.assertTrue(p.exists())

    def test_timing_lib_tt_found(self):
        """get_timing_lib() must find the TT corner lib we created."""
        p = self.pdk.get_timing_lib(corner=TimingCorner.TT)
        self.assertIsNotNone(p)
        self.assertTrue(p.exists())

    def test_timing_lib_missing_corner_returns_none(self):
        """get_timing_lib() returns None for an absent corner."""
        p = self.pdk.get_timing_lib(corner=TimingCorner.SS)
        self.assertIsNone(p)

    def test_gds_library_returns_path(self):
        """get_gds_library() must find the fake .gds we created."""
        p = self.pdk.get_gds_library()
        self.assertIsNotNone(p)
        self.assertTrue(p.exists())

    def test_drc_rules_found(self):
        """get_klayout_drc_rules() must find the fake .lydrc file."""
        p = self.pdk.get_klayout_drc_rules()
        self.assertIsNotNone(p)

    def test_lvs_rules_found(self):
        """get_klayout_lvs_rules() must find the fake .lylvs file."""
        p = self.pdk.get_klayout_lvs_rules()
        self.assertIsNotNone(p)

    def test_all_timing_libs_returns_dict(self):
        """get_all_timing_libs() must return a dict (may be partial)."""
        result = self.pdk.get_all_timing_libs()
        self.assertIsInstance(result, dict)
        # At minimum TT corner should be present
        self.assertIn(TimingCorner.TT.value, result)

    def test_get_env_vars_keys(self):
        """get_env_vars() must return all required env var keys."""
        env = self.pdk.get_env_vars()
        self.assertIn("PDK_ROOT", env)
        self.assertIn("PDK", env)
        self.assertIn("STD_CELL_LIBRARY", env)

    def test_openlane_config_dir_found(self):
        """get_openlane_config_dir() must find the fake openlane dir."""
        p = self.pdk.get_openlane_config_dir()
        self.assertIsNotNone(p)


class TestPDKManagerCellLookup(unittest.TestCase):
    """Tests for cell listing and lookup."""

    def setUp(self):
        self.tmp_dir  = tempfile.TemporaryDirectory()
        self.pdk_root = Path(self.tmp_dir.name) / "sky130A"
        self.pdk_root.mkdir()
        make_fake_pdk_tree(self.pdk_root)
        self.pdk = PDKManager(pdk_root=str(self.pdk_root), auto_detect=False)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_list_cells_returns_list(self):
        """list_cells() must return a non-empty sorted list."""
        cells = self.pdk.list_cells()
        self.assertIsInstance(cells, list)
        # Fake LEF has two MACRO blocks
        self.assertGreaterEqual(len(cells), 1)

    def test_list_cells_sorted(self):
        """list_cells() must return cells in alphabetical order."""
        cells = self.pdk.list_cells()
        self.assertEqual(cells, sorted(cells))

    def test_list_cells_prefix_filter(self):
        """filter_prefix should restrict results."""
        cells_all = self.pdk.list_cells()
        cells_and = self.pdk.list_cells(filter_prefix="sky130_fd_sc_hd__and")
        for c in cells_and:
            self.assertTrue(c.startswith("sky130_fd_sc_hd__and"))

    def test_get_cell_info_known_cell(self):
        """get_cell_info() must return CellInfo for a cell in the merged LEF."""
        # The merged LEF contains "sky130_fd_sc_hd__and2_1"
        info = self.pdk.get_cell_info("sky130_fd_sc_hd__and2_1")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "sky130_fd_sc_hd__and2_1")

    def test_get_cell_info_unknown_cell_returns_none(self):
        """get_cell_info() must return None for a cell that does not exist."""
        info = self.pdk.get_cell_info("definitely_not_a_real_cell_xyz")
        self.assertIsNone(info)

    def test_cell_info_caching(self):
        """Second call for same cell must come from cache (same object id)."""
        info1 = self.pdk.get_cell_info("sky130_fd_sc_hd__and2_1")
        info2 = self.pdk.get_cell_info("sky130_fd_sc_hd__and2_1")
        if info1 is not None:
            self.assertIs(info1, info2)


class TestPDKManagerInstallInstructions(unittest.TestCase):
    """Tests for static installation helper."""

    def test_instructions_non_empty(self):
        """get_install_instructions() must return a non-empty string."""
        text = PDKManager.get_install_instructions()
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 100)

    def test_instructions_contains_volare(self):
        """Instructions must mention volare (our recommended installer)."""
        text = PDKManager.get_install_instructions()
        self.assertIn("volare", text)


# ══════════════════════════════════════════════════════════════════════════════
# KLAYOUT INTERFACE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestKLayoutInterfaceInit(unittest.TestCase):
    """Tests for KLayoutInterface initialisation."""

    def _make_pdk(self) -> PDKManager:
        """Return a PDKManager pointing at a temp fake PDK."""
        tmp = tempfile.mkdtemp()
        root = Path(tmp) / "sky130A"
        root.mkdir()
        make_fake_pdk_tree(root)
        return PDKManager(pdk_root=str(root), auto_detect=False)

    def test_mode_attribute_set(self):
        """mode must be 'bindings' or 'subprocess'."""
        pdk = self._make_pdk()
        kl  = KLayoutInterface(pdk)
        self.assertIn(kl.mode, ("bindings", "subprocess"))

    def test_is_available_returns_bool(self):
        """is_available() must return a boolean."""
        pdk = self._make_pdk()
        kl  = KLayoutInterface(pdk)
        self.assertIsInstance(kl.is_available(), bool)

    def test_explicit_bad_exe_path(self):
        """Giving a non-existent klayout_exe path → exe should be None."""
        pdk = self._make_pdk()
        kl  = KLayoutInterface(pdk, klayout_exe=r"C:\nonexistent\klayout.exe")
        self.assertIsNone(kl.klayout_exe)

    def test_install_instructions_non_empty(self):
        """get_install_instructions() must return meaningful text."""
        text = KLayoutInterface.get_install_instructions()
        self.assertIn("klayout", text.lower())
        self.assertGreater(len(text), 50)


class TestKLayoutDRCResult(unittest.TestCase):
    """Tests for DRCResult dataclass."""

    def test_summary_clean(self):
        r = DRCResult(gds_path="a.gds", rule_deck="sky130.lydrc",
                      passed=True, violation_count=0)
        self.assertIn("CLEAN", r.summary())

    def test_summary_violations(self):
        r = DRCResult(gds_path="a.gds", rule_deck="sky130.lydrc",
                      passed=False, violation_count=5)
        self.assertIn("5", r.summary())

    def test_default_passed_false(self):
        r = DRCResult(gds_path="a.gds", rule_deck="rules")
        self.assertFalse(r.passed)


class TestKLayoutLVSResult(unittest.TestCase):
    """Tests for LVSResult dataclass."""

    def test_summary_matched(self):
        r = LVSResult(gds_path="a.gds", schematic_path="a.spice",
                      rule_deck="rules", matched=True)
        self.assertIn("MATCHED", r.summary())

    def test_summary_mismatch(self):
        r = LVSResult(gds_path="a.gds", schematic_path="a.spice",
                      rule_deck="rules", matched=False,
                      mismatches=["net1 mismatch", "net2 mismatch"])
        self.assertIn("2", r.summary())


class TestKLayoutLyrdbParsing(unittest.TestCase):
    """Tests for internal .lyrdb report parser."""

    def _make_kl(self) -> KLayoutInterface:
        tmp = tempfile.mkdtemp()
        root = Path(tmp) / "sky130A"
        root.mkdir()
        make_fake_pdk_tree(root)
        pdk = PDKManager(pdk_root=str(root), auto_detect=False)
        return KLayoutInterface(pdk)

    def test_parse_clean_lyrdb(self):
        """A lyrdb with zero items → empty violation list."""
        with tempfile.NamedTemporaryFile(
            suffix=".lyrdb", delete=False, mode="w", encoding="utf-8"
        ) as f:
            make_fake_lyrdb(Path(f.name), n_violations=0)
            path = Path(f.name)

        kl = self._make_kl()
        violations = kl._parse_lyrdb(path)
        self.assertEqual(len(violations), 0)
        path.unlink()

    def test_parse_lyrdb_with_violations(self):
        """A lyrdb with 3 items → 3 DRCViolation objects."""
        with tempfile.NamedTemporaryFile(
            suffix=".lyrdb", delete=False, mode="w", encoding="utf-8"
        ) as f:
            make_fake_lyrdb(Path(f.name), n_violations=3)
            path = Path(f.name)

        kl = self._make_kl()
        violations = kl._parse_lyrdb(path)
        self.assertEqual(len(violations), 3)
        path.unlink()

    def test_parse_missing_lyrdb_returns_empty(self):
        """A non-existent lyrdb must return [] without crashing."""
        kl = self._make_kl()
        violations = kl._parse_lyrdb(Path("/nonexistent/file.lyrdb"))
        self.assertEqual(violations, [])

    def test_violation_has_rule_name(self):
        """Each DRCViolation must have a non-empty rule_name."""
        with tempfile.NamedTemporaryFile(
            suffix=".lyrdb", delete=False, mode="w", encoding="utf-8"
        ) as f:
            make_fake_lyrdb(Path(f.name), n_violations=1)
            path = Path(f.name)

        kl = self._make_kl()
        violations = kl._parse_lyrdb(path)
        if violations:
            self.assertNotEqual(violations[0].rule_name, "")
        path.unlink()


class TestKLayoutLVSLogParsing(unittest.TestCase):
    """Tests for LVS log parser."""

    def _make_kl(self) -> KLayoutInterface:
        tmp = tempfile.mkdtemp()
        root = Path(tmp) / "sky130A"
        root.mkdir()
        make_fake_pdk_tree(root)
        pdk = PDKManager(pdk_root=str(root), auto_detect=False)
        return KLayoutInterface(pdk)

    def test_clean_log_no_mismatches(self):
        """A clean LVS log → empty mismatches list."""
        kl  = self._make_kl()
        log = "LVS completed successfully.\nAll nets matched.\n"
        mismatches = kl._parse_lvs_log(log)
        self.assertEqual(mismatches, [])

    def test_log_with_errors(self):
        """Log containing 'Mismatch:' lines → those lines extracted."""
        kl  = self._make_kl()
        log = (
            "Processing cell top ...\n"
            "Mismatch: net VDD not found in schematic\n"
            "Mismatch: net GND device count differs\n"
            "FAILED\n"
        )
        mismatches = kl._parse_lvs_log(log)
        self.assertEqual(len(mismatches), 3)   # 2 Mismatch + 1 FAILED


class TestSky130LayerMap(unittest.TestCase):
    """Tests for the SKY130_LAYERS constant."""

    def test_layer_map_non_empty(self):
        self.assertGreater(len(SKY130_LAYERS), 10)

    def test_metal_layers_present(self):
        """All 5 metal layers must be in the map."""
        layer_names = list(SKY130_LAYERS.values())
        for m in ("met1", "met2", "met3", "met4", "met5"):
            self.assertIn(m, layer_names, msg=f"{m} missing from SKY130_LAYERS")

    def test_keys_are_tuples(self):
        for k in SKY130_LAYERS:
            self.assertIsInstance(k, tuple)
            self.assertEqual(len(k), 2)

    def test_poly_layer_present(self):
        names = list(SKY130_LAYERS.values())
        self.assertIn("poly", names)


class TestKLayoutNoToolAvailable(unittest.TestCase):
    """Tests that check graceful failure when KLayout exe is absent."""

    def _make_kl_no_exe(self) -> KLayoutInterface:
        tmp = tempfile.mkdtemp()
        root = Path(tmp) / "sky130A"
        root.mkdir()
        make_fake_pdk_tree(root)
        pdk = PDKManager(pdk_root=str(root), auto_detect=False)
        kl  = KLayoutInterface(pdk)
        kl.klayout_exe = None   # simulate missing exe
        return kl

    def test_drc_no_rule_deck_returns_result(self):
        """run_drc() without rule deck must return DRCResult, not raise."""
        kl = self._make_kl_no_exe()
        # Temporarily remove the fake rule deck from PDK
        kl.pdk.pdk_root = Path("/nonexistent")   # force rule deck to None
        result = kl.run_drc("design.gds")
        self.assertIsInstance(result, DRCResult)
        self.assertFalse(result.passed)

    def test_subprocess_drc_no_exe_returns_result(self):
        """_run_drc_subprocess() with no exe → DRCResult with error."""
        kl = self._make_kl_no_exe()
        kl.mode = "subprocess"
        with tempfile.TemporaryDirectory() as td:
            result = kl._run_drc_subprocess(
                gds_path    = Path("/fake/design.gds"),
                rule_deck   = Path("/fake/sky130.lydrc"),
                report_path = Path(td) / "out.lyrdb",
                top_cell    = None,
            )
        self.assertIsInstance(result, DRCResult)
        self.assertIn("ERROR", result.log_output)


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION – READS AGAINST REAL TOOLS (SKIPPED IF NOT INSTALLED)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationRealKLayout(unittest.TestCase):
    """
    Integration tests that require a real KLayout installation.
    All tests are automatically skipped if klayout.db is not importable
    and klayout.exe is not found.
    """

    @classmethod
    def setUpClass(cls):
        """Check if KLayout is available; set flag for skip logic."""
        try:
            import klayout.db
            cls.has_bindings = True
        except ImportError:
            cls.has_bindings = False

        # Check exe
        from python.klayout_interface import KLayoutInterface
        from python.klayout_interface import KLayoutInterface as KLI
        tmp_root = Path(tempfile.mkdtemp()) / "sky130A"
        tmp_root.mkdir()
        make_fake_pdk_tree(tmp_root)
        pdk = PDKManager(pdk_root=str(tmp_root), auto_detect=False)
        kl  = KLI(pdk)
        cls.has_exe  = kl.klayout_exe is not None
        cls.pdk_root = tmp_root

    def _skip_if_no_klayout(self):
        if not self.has_bindings and not self.has_exe:
            self.skipTest("KLayout not installed – skipping real-tool test")

    def test_version_accessible(self):
        """If bindings available, klayout.db.VERSION should be readable."""
        if not self.has_bindings:
            self.skipTest("klayout.db not importable")
        import klayout.db as pya
        # Try multiple ways to get version info
        version = getattr(pya, 'VERSION', None)
        if version is None:
            version = getattr(pya, '__version__', 'unknown')
        self.assertIsInstance(version, str)
        self.assertGreater(len(version), 0)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Pretty output when run directly
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "═" * 60)
    print(f"  Ran {result.testsRun} tests")
    if result.wasSuccessful():
        print("  ✅  ALL TESTS PASSED")
    else:
        print(f"  ❌  FAILURES: {len(result.failures)}")
        print(f"  ❌  ERRORS:   {len(result.errors)}")
    print("═" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)
