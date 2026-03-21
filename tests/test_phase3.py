"""
test_phase3.py  –  Phase 3 Tests: Placer, CTS Engine, Placement Optimizer
==========================================================================
All tests pass without real tools.  Docker tests skip automatically.

Run from project root:
    python -m pytest tests/test_phase3.py -v

Run all phases:
    python -m pytest tests/ -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.placer import (
    Placer, PlacementConfig, PlacementResult, PlacementStats,
)
from python.cts_engine import (
    CTSEngine, CTSConfig, CTSResult, CTSStats,
)
from python.placement_optimizer import (
    PlacementOptimizer, OptConfig, OptimizationResult,
    OptimizationLevel, IssueType, PlacementIssue,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

PLACEMENT_REPORT_CLEAN = """\
Design area 5000 u^2 63% utilization
Number of instances: 147
HPWL: 12345.6
Overflow: 0.0001
wns 0.00
tns 0.00
"""

PLACEMENT_REPORT_VIOLATIONS = """\
Design area 6200 u^2 88% utilization
Number of instances: 200
HPWL: 18000.0
Overflow: 0.1500
wns -0.73
tns -5.21
"""

CTS_REPORT_CLEAN = """\
Clock clk
Latency      CRPR       Skew
0.823        -0.012     0.045
Clock buffers inserted: 23
wns 0.12
tns 0.00
"""

CTS_REPORT_HIGH_SKEW = """\
Clock clk
Latency      CRPR       Skew
1.200        -0.050     0.350
Clock buffers inserted: 12
wns -0.08
tns -0.30
"""

FAKE_DEF = """\
VERSION 5.8 ;
DESIGN adder_8bit ;
UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 100000 100000 ) ;
END DESIGN
"""


def write_report(tmp: Path, content: str, name: str = "placement.rpt") -> Path:
    p = tmp / name
    p.write_text(content)
    return p


def write_def(tmp: Path, name: str = "placed.def") -> Path:
    p = tmp / name
    p.write_text(FAKE_DEF)
    return p


def make_docker(success: bool = True, stdout: str = "") -> MagicMock:
    dm  = MagicMock()
    dm.work_dir = Path(tempfile.mkdtemp())
    run = MagicMock()
    run.success      = success
    run.stdout       = stdout
    run.stderr       = "" if success else "[ERROR something failed]"
    run.return_code  = 0 if success else 1
    run.combined_output.return_value = run.stdout + run.stderr
    dm.run_script.return_value = run
    return dm


def make_pdk() -> MagicMock:
    pdk = MagicMock()
    pdk.pdk_root = Path("/pdk/sky130A")
    return pdk


# ══════════════════════════════════════════════════════════════════════════════
# PLACER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPlacementConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = PlacementConfig()
        self.assertEqual(cfg.density_target,  0.60)
        self.assertEqual(cfg.clock_period_ns, 10.0)
        self.assertTrue(cfg.run_detailed)
        self.assertTrue(cfg.timing_driven)

    def test_custom_values(self):
        cfg = PlacementConfig(density_target=0.50, clock_net="my_clk")
        self.assertEqual(cfg.density_target, 0.50)
        self.assertEqual(cfg.clock_net,      "my_clk")


class TestPlacementStats(unittest.TestCase):
    def test_defaults_zero(self):
        s = PlacementStats()
        self.assertEqual(s.hpwl_um,         0.0)
        self.assertEqual(s.cell_count,       0)
        self.assertEqual(s.utilization_pct,  0.0)
        self.assertEqual(s.overflow,         0.0)
        self.assertEqual(s.worst_slack_ns,   0.0)


class TestPlacementResult(unittest.TestCase):
    def test_summary_success(self):
        r = PlacementResult(
            top_module = "adder",
            output_dir = "/work",
            success    = True,
            stats      = PlacementStats(cell_count=100, hpwl_um=5000.0),
        )
        text = r.summary()
        self.assertIn("SUCCESS", text)
        self.assertIn("100",     text)

    def test_summary_failure(self):
        r = PlacementResult(
            top_module    = "adder",
            output_dir    = "/work",
            success       = False,
            error_message = "placement overflow",
        )
        text = r.summary()
        self.assertIn("FAILED",             text)
        self.assertIn("placement overflow", text)

    def test_summary_shows_def_path(self):
        r = PlacementResult(
            top_module = "top",
            output_dir = "/work",
            success    = True,
            placed_def = "/work/placed.def",
        )
        self.assertIn("placed.def", r.summary())


class TestPlacerTclGeneration(unittest.TestCase):
    def setUp(self):
        self.placer = Placer(docker=make_docker(), pdk=make_pdk())

    def test_script_contains_top_module(self):
        tcl = self.placer._generate_placement_script(
            Path("fp.def"), "my_adder", PlacementConfig()
        )
        self.assertIn("my_adder", tcl)

    def test_script_contains_global_placement(self):
        tcl = self.placer._generate_placement_script(
            Path("fp.def"), "top", PlacementConfig()
        )
        self.assertIn("global_placement", tcl)

    def test_script_contains_legalize(self):
        tcl = self.placer._generate_placement_script(
            Path("fp.def"), "top", PlacementConfig()
        )
        self.assertIn("legalize_placement", tcl)

    def test_detailed_placement_included_when_enabled(self):
        cfg = PlacementConfig(run_detailed=True)
        tcl = self.placer._generate_placement_script(Path("fp.def"), "top", cfg)
        self.assertIn("detailed_placement", tcl)

    def test_detailed_placement_excluded_when_disabled(self):
        cfg = PlacementConfig(run_detailed=False)
        tcl = self.placer._generate_placement_script(Path("fp.def"), "top", cfg)
        # detailed_placement should not appear in the non-detailed path
        # (it may appear in check_placement context so we check the specific command)
        self.assertNotIn("\ndetailed_placement\n", tcl)

    def test_script_contains_pdk_paths(self):
        tcl = self.placer._generate_placement_script(
            Path("fp.def"), "top", PlacementConfig()
        )
        self.assertIn("/pdk", tcl)
        self.assertIn("sky130_fd_sc_hd", tcl)

    def test_script_contains_write_def(self):
        tcl = self.placer._generate_placement_script(
            Path("fp.def"), "top", PlacementConfig()
        )
        self.assertIn("write_def /work/placed.def", tcl)

    def test_script_contains_density(self):
        cfg = PlacementConfig(density_target=0.55)
        tcl = self.placer._generate_placement_script(Path("fp.def"), "top", cfg)
        self.assertIn("0.55", tcl)

    def test_timing_flag_present_when_enabled(self):
        cfg = PlacementConfig(timing_driven=True)
        tcl = self.placer._generate_placement_script(Path("fp.def"), "top", cfg)
        self.assertIn("-timing_driven", tcl)

    def test_timing_flag_absent_when_disabled(self):
        cfg = PlacementConfig(timing_driven=False)
        tcl = self.placer._generate_placement_script(Path("fp.def"), "top", cfg)
        self.assertNotIn("-timing_driven", tcl)

    def test_global_only_script_shorter(self):
        cfg      = PlacementConfig()
        full     = self.placer._generate_placement_script(Path("fp.def"), "top", cfg)
        glob_    = self.placer._generate_global_only_script(Path("fp.def"), "top", cfg)
        self.assertLess(len(glob_), len(full))

    def test_clock_net_in_script(self):
        cfg = PlacementConfig(clock_net="sys_clk")
        tcl = self.placer._generate_placement_script(Path("fp.def"), "top", cfg)
        self.assertIn("sys_clk", tcl)


class TestPlacerReportParsing(unittest.TestCase):
    def setUp(self):
        self.placer = Placer(docker=make_docker(), pdk=make_pdk())

    def test_parse_clean_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_report(Path(tmp), PLACEMENT_REPORT_CLEAN)
            s   = self.placer._parse_report(rpt)
        self.assertAlmostEqual(s.utilization_pct, 63.0)
        self.assertEqual(s.cell_count, 147)
        self.assertAlmostEqual(s.hpwl_um, 12345.6)
        self.assertAlmostEqual(s.overflow, 0.0001)
        self.assertAlmostEqual(s.worst_slack_ns, 0.0)

    def test_parse_violation_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_report(Path(tmp), PLACEMENT_REPORT_VIOLATIONS)
            s   = self.placer._parse_report(rpt)
        self.assertAlmostEqual(s.worst_slack_ns, -0.73)
        self.assertAlmostEqual(s.utilization_pct, 88.0)

    def test_parse_missing_report_returns_zeros(self):
        s = self.placer._parse_report(Path("/nonexistent/placement.rpt"))
        self.assertEqual(s.hpwl_um,       0.0)
        self.assertEqual(s.cell_count,    0)
        self.assertEqual(s.overflow,      0.0)

    def test_extract_error_line(self):
        output = "reading...\n[ERROR routing failed]\nmore\n"
        e      = Placer._extract_error(output)
        self.assertIn("ERROR", e)

    def test_extract_error_no_error(self):
        e = Placer._extract_error("all good\n")
        self.assertIn("error", e.lower())


class TestPlacerRunMocked(unittest.TestCase):
    def test_docker_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=False)
            pl = Placer(docker=dm, pdk=make_pdk())
            write_def(Path(tmp))
            r  = pl.run(Path(tmp) / "placed.def", "adder", tmp)
        self.assertFalse(r.success)
        self.assertIn("ERROR", r.error_message)

    def test_missing_placed_def_means_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True)
            pl = Placer(docker=dm, pdk=make_pdk())
            write_def(Path(tmp), "floorplan.def")
            r  = pl.run(Path(tmp) / "floorplan.def", "top", tmp)
        # Docker succeeded but placed.def was not created
        self.assertFalse(r.success)
        self.assertIn("placed.def", r.error_message)

    def test_placed_def_created_means_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True)
            pl = Placer(docker=dm, pdk=make_pdk())
            write_def(Path(tmp), "floorplan.def")
            # Pre-create the output DEF that OpenROAD would write
            (Path(tmp) / "placed.def").write_text("DESIGN ;\n")
            r  = pl.run(Path(tmp) / "floorplan.def", "top", tmp)
        self.assertTrue(r.success)
        self.assertIsNotNone(r.placed_def)


# ══════════════════════════════════════════════════════════════════════════════
# CTS ENGINE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCTSConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = CTSConfig()
        self.assertEqual(cfg.clock_period_ns, 10.0)
        self.assertEqual(cfg.target_skew_ns,  0.1)
        self.assertTrue(cfg.repair_hold)
        self.assertIn("clkbuf_16", cfg.root_buf)

    def test_custom_clock_net(self):
        cfg = CTSConfig(clock_net="fast_clk", clock_period_ns=5.0)
        self.assertEqual(cfg.clock_net,        "fast_clk")
        self.assertEqual(cfg.clock_period_ns,  5.0)


class TestCTSStats(unittest.TestCase):
    def test_defaults_zero(self):
        s = CTSStats()
        self.assertEqual(s.max_skew_ns,      0.0)
        self.assertEqual(s.buf_count,        0)
        self.assertEqual(s.worst_slack_ns,   0.0)


class TestCTSResult(unittest.TestCase):
    def test_summary_success(self):
        r = CTSResult(
            top_module = "top",
            output_dir = "/work",
            success    = True,
            stats      = CTSStats(buf_count=23, max_skew_ns=0.045),
        )
        text = r.summary()
        self.assertIn("SUCCESS", text)
        self.assertIn("23",      text)

    def test_summary_failure(self):
        r = CTSResult(
            top_module    = "top",
            output_dir    = "/work",
            success       = False,
            error_message = "cts failed",
        )
        self.assertIn("FAILED",     r.summary())
        self.assertIn("cts failed", r.summary())


class TestCTSTclGeneration(unittest.TestCase):
    def setUp(self):
        self.cts = CTSEngine(docker=make_docker(), pdk=make_pdk())

    def test_script_contains_clock_tree_synthesis(self):
        tcl = self.cts._generate_cts_script(
            Path("placed.def"), "top", CTSConfig()
        )
        self.assertIn("clock_tree_synthesis", tcl)

    def test_script_contains_root_buf(self):
        tcl = self.cts._generate_cts_script(
            Path("placed.def"), "top", CTSConfig()
        )
        self.assertIn("clkbuf_16", tcl)

    def test_script_contains_hold_repair_when_enabled(self):
        cfg = CTSConfig(repair_hold=True)
        tcl = self.cts._generate_cts_script(Path("placed.def"), "top", cfg)
        self.assertIn("repair_timing", tcl)
        self.assertIn("-hold",         tcl)

    def test_script_no_hold_repair_when_disabled(self):
        cfg = CTSConfig(repair_hold=False)
        tcl = self.cts._generate_cts_script(Path("placed.def"), "top", cfg)
        # repair_timing -hold should not appear
        self.assertNotIn("-hold", tcl)

    def test_script_contains_write_def(self):
        tcl = self.cts._generate_cts_script(
            Path("placed.def"), "top", CTSConfig()
        )
        self.assertIn("write_def /work/cts.def", tcl)

    def test_script_contains_pdk_paths(self):
        tcl = self.cts._generate_cts_script(
            Path("placed.def"), "top", CTSConfig()
        )
        self.assertIn("/pdk", tcl)

    def test_script_contains_set_propagated_clock(self):
        tcl = self.cts._generate_cts_script(
            Path("placed.def"), "top", CTSConfig()
        )
        self.assertIn("set_propagated_clock", tcl)

    def test_clock_net_in_script(self):
        cfg = CTSConfig(clock_net="ref_clk")
        tcl = self.cts._generate_cts_script(Path("placed.def"), "top", cfg)
        self.assertIn("ref_clk", tcl)

    def test_skew_check_script_shorter(self):
        full  = self.cts._generate_cts_script(
            Path("placed.def"), "top", CTSConfig()
        )
        check = self.cts._generate_skew_check_script(
            Path("cts.def"), "top", CTSConfig()
        )
        self.assertLess(len(check), len(full))


class TestCTSReportParsing(unittest.TestCase):
    def setUp(self):
        self.cts = CTSEngine(docker=make_docker(), pdk=make_pdk())

    def test_parse_clean_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_report(Path(tmp), CTS_REPORT_CLEAN, "cts.rpt")
            s   = self.cts._parse_cts_report(rpt)
        self.assertAlmostEqual(s.max_skew_ns,    0.045, places=2)
        self.assertEqual(s.buf_count,            23)
        self.assertAlmostEqual(s.worst_slack_ns, 0.12)

    def test_parse_high_skew_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_report(Path(tmp), CTS_REPORT_HIGH_SKEW, "cts.rpt")
            s   = self.cts._parse_cts_report(rpt)
        self.assertGreater(s.max_skew_ns, 0.2)

    def test_parse_missing_returns_zeros(self):
        s = self.cts._parse_cts_report(Path("/nonexistent/cts.rpt"))
        self.assertEqual(s.buf_count,   0)
        self.assertEqual(s.max_skew_ns, 0.0)

    def test_parse_skew_output(self):
        output = "Clock clk\nSkew 0.078\n"
        s      = CTSEngine._parse_skew_output(output)
        self.assertAlmostEqual(s.max_skew_ns, 0.078)


class TestCTSRunMocked(unittest.TestCase):
    def test_docker_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=False)
            ct = CTSEngine(docker=dm, pdk=make_pdk())
            write_def(Path(tmp), "placed.def")
            r  = ct.run(Path(tmp) / "placed.def", "top", tmp)
        self.assertFalse(r.success)

    def test_cts_def_created_means_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True)
            ct = CTSEngine(docker=dm, pdk=make_pdk())
            write_def(Path(tmp), "placed.def")
            (Path(tmp) / "cts.def").write_text("DESIGN ;\n")
            r  = ct.run(Path(tmp) / "placed.def", "top", tmp)
        self.assertTrue(r.success)

    def test_missing_cts_def_means_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True)
            ct = CTSEngine(docker=dm, pdk=make_pdk())
            write_def(Path(tmp), "placed.def")
            r  = ct.run(Path(tmp) / "placed.def", "top", tmp)
        self.assertFalse(r.success)


# ══════════════════════════════════════════════════════════════════════════════
# PLACEMENT OPTIMIZER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestOptConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = OptConfig()
        self.assertEqual(cfg.level,            OptimizationLevel.STANDARD)
        self.assertLess(cfg.wns_threshold_ns,  0)
        self.assertGreater(cfg.overflow_threshold, 0)

    def test_level_none(self):
        cfg = OptConfig(level=OptimizationLevel.NONE)
        self.assertEqual(cfg.level, OptimizationLevel.NONE)


class TestOptimizationLevels(unittest.TestCase):
    def test_all_levels_defined(self):
        levels = [OptimizationLevel.NONE, OptimizationLevel.LIGHT,
                  OptimizationLevel.STANDARD, OptimizationLevel.AGGRESSIVE]
        self.assertEqual(len(levels), 4)

    def test_none_less_than_aggressive(self):
        self.assertLess(
            OptimizationLevel.NONE.value,
            OptimizationLevel.AGGRESSIVE.value
        )


class TestPlacementIssue(unittest.TestCase):
    def test_creation(self):
        iss = PlacementIssue(
            issue_type  = IssueType.SETUP_VIOLATION,
            severity    = "critical",
            description = "WNS = -0.73 ns",
            metric      = -0.73,
            threshold   = -0.05,
        )
        self.assertEqual(iss.issue_type, IssueType.SETUP_VIOLATION)
        self.assertEqual(iss.severity,   "critical")


class TestPlacementOptimizerMetrics(unittest.TestCase):
    def setUp(self):
        self.opt = PlacementOptimizer(docker=make_docker(), pdk=make_pdk())

    def test_read_clean_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_report(Path(tmp), PLACEMENT_REPORT_CLEAN)
            m   = self.opt._read_metrics(rpt)
        self.assertAlmostEqual(m["wns"],             0.0)
        self.assertAlmostEqual(m["utilization_pct"], 63.0)
        self.assertEqual(m["cell_count"],            147)

    def test_read_violation_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_report(Path(tmp), PLACEMENT_REPORT_VIOLATIONS)
            m   = self.opt._read_metrics(rpt)
        self.assertAlmostEqual(m["wns"],  -0.73)
        self.assertAlmostEqual(m["overflow"], 0.15)

    def test_read_missing_returns_zeros(self):
        m = self.opt._read_metrics(None)
        self.assertEqual(m["wns"],        0.0)
        self.assertEqual(m["cell_count"], 0)

    def test_read_nonexistent_file(self):
        m = self.opt._read_metrics("/nonexistent/report.rpt")
        self.assertEqual(m["wns"], 0.0)


class TestPlacementOptimizerIssues(unittest.TestCase):
    def setUp(self):
        self.opt = PlacementOptimizer(docker=make_docker(), pdk=make_pdk())
        self.cfg = OptConfig()

    def test_no_issues_on_clean_metrics(self):
        m      = {"wns": 0.0, "tns": 0.0, "utilization_pct": 65.0,
                  "overflow": 0.001, "cell_count": 100, "max_skew": 0.05}
        issues = self.opt._identify_issues(m, self.cfg)
        self.assertEqual(issues, [])

    def test_setup_violation_detected(self):
        m = {"wns": -0.73, "tns": -5.0, "utilization_pct": 65.0,
             "overflow": 0.001, "cell_count": 100, "max_skew": 0.05}
        issues = self.opt._identify_issues(m, self.cfg)
        types  = {i.issue_type for i in issues}
        self.assertIn(IssueType.SETUP_VIOLATION, types)

    def test_high_overflow_detected(self):
        m = {"wns": 0.0, "tns": 0.0, "utilization_pct": 65.0,
             "overflow": 0.20, "cell_count": 100, "max_skew": 0.05}
        issues = self.opt._identify_issues(m, self.cfg)
        types  = {i.issue_type for i in issues}
        self.assertIn(IssueType.HIGH_OVERFLOW, types)

    def test_high_utilization_detected(self):
        m = {"wns": 0.0, "tns": 0.0, "utilization_pct": 90.0,
             "overflow": 0.001, "cell_count": 100, "max_skew": 0.05}
        issues = self.opt._identify_issues(m, self.cfg)
        types  = {i.issue_type for i in issues}
        self.assertIn(IssueType.HIGH_UTILIZATION, types)

    def test_high_skew_detected(self):
        m = {"wns": 0.0, "tns": 0.0, "utilization_pct": 65.0,
             "overflow": 0.001, "cell_count": 100, "max_skew": 0.35}
        issues = self.opt._identify_issues(m, self.cfg)
        types  = {i.issue_type for i in issues}
        self.assertIn(IssueType.HIGH_SKEW, types)

    def test_critical_before_warning(self):
        m = {"wns": -1.5, "tns": -10.0, "utilization_pct": 92.0,
             "overflow": 0.25, "cell_count": 100, "max_skew": 0.5}
        issues = self.opt._identify_issues(m, self.cfg)
        if len(issues) > 1:
            # Critical issues should come first
            self.assertEqual(issues[0].severity, "critical")


class TestPlacementOptimizerDiagnosis(unittest.TestCase):
    def setUp(self):
        self.opt = PlacementOptimizer(docker=make_docker(), pdk=make_pdk())

    def test_clean_diagnosis_positive(self):
        d = self.opt._write_diagnosis(
            [],
            {"wns": 0.0, "utilization_pct": 63.0, "overflow": 0.001}
        )
        self.assertIn("good", d.lower())

    def test_violation_diagnosis_mentions_wns(self):
        issues = [PlacementIssue(
            IssueType.SETUP_VIOLATION, "critical",
            "WNS = -0.73 ns", -0.73, -0.05
        )]
        d = self.opt._write_diagnosis(
            issues, {"wns": -0.73, "utilization_pct": 65.0, "overflow": 0.001}
        )
        self.assertIn("critical", d.lower())


class TestPlacementOptimizerRecommendations(unittest.TestCase):
    def setUp(self):
        self.opt = PlacementOptimizer(docker=make_docker(), pdk=make_pdk())
        self.cfg = OptConfig()

    def test_recommends_density_reduction_on_overflow(self):
        issues = [PlacementIssue(
            IssueType.HIGH_OVERFLOW, "warning",
            "Overflow 0.20", 0.20, 0.10
        )]
        recs = self.opt._write_recommendations(
            issues, {"wns": 0.0, "utilization_pct": 70.0, "overflow": 0.20},
            self.cfg
        )
        self.assertTrue(any("density" in r.lower() for r in recs))

    def test_no_issues_recommend_proceed(self):
        recs = self.opt._write_recommendations(
            [],
            {"wns": 0.0, "utilization_pct": 65.0, "overflow": 0.001},
            self.cfg
        )
        self.assertTrue(any("routing" in r.lower() or "proceed" in r.lower()
                            for r in recs))

    def test_returns_list(self):
        recs = self.opt._write_recommendations([], {}, self.cfg)
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)


class TestPlacementOptimizerTclGeneration(unittest.TestCase):
    def setUp(self):
        self.opt = PlacementOptimizer(docker=make_docker(), pdk=make_pdk())
        self.cfg = OptConfig(level=OptimizationLevel.STANDARD)

    def test_script_contains_repair_timing_on_setup_issue(self):
        issues = {IssueType.SETUP_VIOLATION}
        tcl    = self.opt._generate_optimization_script(
            Path("placed.def"), "top", self.cfg, issues
        )
        self.assertIn("repair_timing", tcl)
        self.assertIn("-setup",        tcl)

    def test_script_no_repair_when_no_issues(self):
        tcl = self.opt._generate_optimization_script(
            Path("placed.def"), "top", self.cfg, set()
        )
        self.assertIn("No timing issues", tcl)

    def test_script_contains_write_def(self):
        tcl = self.opt._generate_optimization_script(
            Path("placed.def"), "top", self.cfg, set()
        )
        self.assertIn("optimized_placed.def", tcl)

    def test_aggressive_level_adds_full_repair(self):
        cfg = OptConfig(level=OptimizationLevel.AGGRESSIVE)
        tcl = self.opt._generate_optimization_script(
            Path("placed.def"), "top", cfg, set()
        )
        self.assertIn("-setup", tcl)
        self.assertIn("-hold",  tcl)


class TestPlacementOptimizerAnalyzeOnly(unittest.TestCase):
    def setUp(self):
        self.opt = PlacementOptimizer(docker=make_docker(), pdk=make_pdk())

    def test_analyze_only_no_docker(self):
        """analyze_only must not call Docker at all."""
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_report(Path(tmp), PLACEMENT_REPORT_VIOLATIONS)
            issues, recs = self.opt.analyze_only(rpt)

        self.opt.docker.run_script.assert_not_called()
        self.assertIsInstance(issues, list)
        self.assertIsInstance(recs,   list)
        self.assertGreater(len(issues), 0)

    def test_analyze_only_clean_report_no_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt    = write_report(Path(tmp), PLACEMENT_REPORT_CLEAN)
            issues, recs = self.opt.analyze_only(rpt)
        self.assertEqual(issues, [])

    def test_violation_report_produces_recommendations(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt    = write_report(Path(tmp), PLACEMENT_REPORT_VIOLATIONS)
            issues, recs = self.opt.analyze_only(rpt)
        self.assertGreater(len(recs), 0)


class TestPlacementOptimizerRunMocked(unittest.TestCase):
    def test_level_none_skips_docker(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm  = make_docker(success=True)
            opt = PlacementOptimizer(docker=dm, pdk=make_pdk())
            rpt = write_report(Path(tmp), PLACEMENT_REPORT_CLEAN)
            def_p = write_def(Path(tmp))
            r = opt.analyze_and_fix(
                def_p, "top", tmp,
                report_path=rpt,
                config=OptConfig(level=OptimizationLevel.NONE),
            )
        dm.run_script.assert_not_called()
        self.assertTrue(r.success)

    def test_optimized_def_created_means_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm  = make_docker(success=True)
            opt = PlacementOptimizer(docker=dm, pdk=make_pdk())
            rpt = write_report(Path(tmp), PLACEMENT_REPORT_VIOLATIONS)
            def_p = write_def(Path(tmp))
            # Pre-create the output file
            (Path(tmp) / "optimized_placed.def").write_text("DESIGN ;\n")
            r = opt.analyze_and_fix(
                def_p, "top", tmp,
                report_path=rpt,
                config=OptConfig(level=OptimizationLevel.STANDARD),
            )
        self.assertTrue(r.success)
        self.assertIsNotNone(r.optimized_def)

    def test_result_summary_contains_module_name(self):
        r = OptimizationResult(top_module="my_chip", success=True)
        self.assertIn("my_chip", r.summary())


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION – REAL DOCKER (auto-skipped)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationRealDocker(unittest.TestCase):
    """Skipped when Docker not running."""

    @classmethod
    def setUpClass(cls):
        try:
            import subprocess
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            cls.docker_available = r.returncode == 0
        except Exception:
            cls.docker_available = False

    def _skip(self):
        if not self.docker_available:
            self.skipTest("Docker not running")

    def test_openroad_version_accessible(self):
        self._skip()
        from python.docker_manager import DockerManager
        from pathlib import Path
        import tempfile
        dm     = DockerManager()
        with tempfile.TemporaryDirectory() as tmp:
            result = dm.run_openroad(
                work_dir = tmp,
                command  = "openroad --version",
            )
            if result.is_success:
                self.assertGreater(len(result.stdout), 0)


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
