"""
test_phase4.py  –  Phase 4 Tests: Global Router, Detail Router, Routing Optimizer
==================================================================================
All tests pass without real tools.  Docker tests skip automatically.

Run from project root:
    python -m pytest tests/test_phase4.py -v

Run all phases:
    python -m pytest tests/ -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.global_router import (
    GlobalRouter, GlobalRouteConfig, GlobalRouteResult, CongestionStats,
)
from python.detail_router import (
    DetailRouter, DetailRouteConfig, DetailRouteResult, RoutingStats,
)
from python.routing_optimizer import (
    RoutingOptimizer, RouteOptConfig, RouteAnalysisResult,
    RoutingIssueType, RoutingIssue, FixStrategy,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

CONGESTION_REPORT_CLEAN = """\
Global routing congestion report
Total overflow: 0
Max H congestion: 0.423
Max V congestion: 0.381
Avg H congestion: 0.210
Avg V congestion: 0.195
Wirelength: 45230.5
"""

CONGESTION_REPORT_OVERFLOW = """\
Global routing congestion report
Total overflow: 7
Max H congestion: 0.951
Max V congestion: 0.882
Avg H congestion: 0.510
Wirelength: 62100.0
"""

ROUTING_REPORT_CLEAN = """\
Total wire length: 52340.7
Total number of vias: 1823
Number of unrouted nets: 0
wns 0.00
tns 0.00
"""

ROUTING_REPORT_DRC = """\
Total wire length: 55000.0
Total number of vias: 2100
Number of unrouted nets: 0
Number of DRC violations: 4
wns -0.12
tns -0.45
"""

ROUTING_REPORT_UNROUTED = """\
Total wire length: 48000.0
Total number of vias: 1700
Number of unrouted nets: 3
Number of DRC violations: 0
wns 0.05
tns 0.00
"""

FAKE_DEF = "VERSION 5.8 ;\nDESIGN top ;\nEND DESIGN\n"
FAKE_GUIDES = "# Route guides\nnet1 met2 0 0 100 100\n"


def write_file(tmp: Path, content: str, name: str) -> Path:
    p = tmp / name
    p.write_text(content)
    return p


def make_docker(success: bool = True) -> MagicMock:
    dm  = MagicMock()
    dm.work_dir = Path(tempfile.mkdtemp())
    run = MagicMock()
    run.success     = success
    run.stdout      = "done\n"
    run.stderr      = "" if success else "[ERROR something failed]"
    run.return_code = 0 if success else 1
    run.combined_output.return_value = run.stdout + run.stderr
    dm.run_script.return_value = run
    return dm


def make_pdk() -> MagicMock:
    pdk = MagicMock()
    pdk.pdk_root = Path("/pdk/sky130A")
    return pdk


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL ROUTER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGlobalRouteConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = GlobalRouteConfig()
        self.assertEqual(cfg.min_layer,    "met2")
        self.assertEqual(cfg.max_layer,    "met4")
        self.assertEqual(cfg.adjustment,   0.30)
        self.assertIn("met1", cfg.layer_adjustments)

    def test_met1_zero_capacity(self):
        """met1 must be reserved for power rails (0% signal capacity)."""
        cfg = GlobalRouteConfig()
        self.assertEqual(cfg.layer_adjustments["met1"], 0.0)

    def test_met5_zero_capacity(self):
        """met5 must be reserved for power stripes."""
        cfg = GlobalRouteConfig()
        self.assertEqual(cfg.layer_adjustments["met5"], 0.0)

    def test_custom_adjustment(self):
        cfg = GlobalRouteConfig(adjustment=0.45)
        self.assertEqual(cfg.adjustment, 0.45)


class TestCongestionStats(unittest.TestCase):
    def test_defaults_zero(self):
        s = CongestionStats()
        self.assertEqual(s.max_congestion, 0.0)
        self.assertEqual(s.overflow_count, 0)

    def test_fields_settable(self):
        s = CongestionStats(max_congestion=0.75, overflow_count=3)
        self.assertEqual(s.max_congestion, 0.75)
        self.assertEqual(s.overflow_count, 3)


class TestGlobalRouteResult(unittest.TestCase):
    def test_summary_success(self):
        r = GlobalRouteResult(
            top_module  = "adder",
            output_dir  = "/work",
            success     = True,
            congestion  = CongestionStats(max_congestion=0.42, overflow_count=0),
        )
        text = r.summary()
        self.assertIn("SUCCESS", text)
        self.assertIn("0.420",   text)

    def test_summary_failure(self):
        r = GlobalRouteResult(
            top_module    = "adder",
            output_dir    = "/work",
            success       = False,
            error_message = "layer not found",
        )
        self.assertIn("FAILED",         r.summary())
        self.assertIn("layer not found", r.summary())

    def test_summary_shows_guide_path(self):
        r = GlobalRouteResult(
            top_module = "top",
            output_dir = "/work",
            success    = True,
            guide_path = "/work/route_guides.txt",
        )
        self.assertIn("route_guides.txt", r.summary())


class TestGlobalRouterTclGeneration(unittest.TestCase):
    def setUp(self):
        self.gr = GlobalRouter(docker=make_docker(), pdk=make_pdk())

    def test_script_contains_global_route(self):
        tcl = self.gr._generate_global_route_script(
            Path("cts.def"), "top", GlobalRouteConfig()
        )
        self.assertIn("global_route", tcl)

    def test_script_contains_write_guides(self):
        tcl = self.gr._generate_global_route_script(
            Path("cts.def"), "top", GlobalRouteConfig()
        )
        self.assertIn("route_guides.txt", tcl)

    def test_script_contains_adjustment(self):
        cfg = GlobalRouteConfig(adjustment=0.40)
        tcl = self.gr._generate_global_route_script(Path("cts.def"), "top", cfg)
        # Adjustment appears in layer commands
        self.assertIn("0.4", tcl)

    def test_script_contains_layer_bounds(self):
        tcl = self.gr._generate_global_route_script(
            Path("cts.def"), "top", GlobalRouteConfig()
        )
        self.assertIn("set_routing_layers", tcl)
        self.assertIn("met2", tcl)
        self.assertIn("met4", tcl)

    def test_script_contains_pdk_paths(self):
        tcl = self.gr._generate_global_route_script(
            Path("cts.def"), "top", GlobalRouteConfig()
        )
        self.assertIn("/pdk", tcl)

    def test_script_contains_congestion_report(self):
        tcl = self.gr._generate_global_route_script(
            Path("cts.def"), "top", GlobalRouteConfig()
        )
        self.assertIn("congestion.rpt", tcl)

    def test_script_contains_top_module(self):
        tcl = self.gr._generate_global_route_script(
            Path("cts.def"), "my_counter", GlobalRouteConfig()
        )
        self.assertIn("my_counter", tcl)

    def test_per_layer_adjustments_in_script(self):
        tcl = self.gr._generate_global_route_script(
            Path("cts.def"), "top", GlobalRouteConfig()
        )
        self.assertIn("set_global_routing_layer_adjustment", tcl)


class TestGlobalRouterCongestionParsing(unittest.TestCase):
    def setUp(self):
        self.gr = GlobalRouter(docker=make_docker(), pdk=make_pdk())

    def test_parse_clean_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), CONGESTION_REPORT_CLEAN, "congestion.rpt")
            s   = self.gr._parse_congestion_report(rpt)
        self.assertEqual(s.overflow_count, 0)
        self.assertAlmostEqual(s.max_congestion, 0.423)
        self.assertAlmostEqual(s.wirelength_um,  45230.5)

    def test_parse_overflow_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), CONGESTION_REPORT_OVERFLOW, "congestion.rpt")
            s   = self.gr._parse_congestion_report(rpt)
        self.assertEqual(s.overflow_count, 7)
        self.assertGreater(s.max_congestion, 0.9)

    def test_parse_missing_returns_zeros(self):
        s = self.gr._parse_congestion_report(Path("/nonexistent.rpt"))
        self.assertEqual(s.overflow_count, 0)
        self.assertEqual(s.max_congestion, 0.0)


class TestGlobalRouterSuggestions(unittest.TestCase):
    def setUp(self):
        self.gr  = GlobalRouter(docker=make_docker(), pdk=make_pdk())
        self.cfg = GlobalRouteConfig()

    def test_overflow_generates_suggestion(self):
        s    = CongestionStats(overflow_count=5, max_congestion=0.92)
        recs = self.gr.suggest_adjustments(s, self.cfg)
        self.assertTrue(any("overflow" in r.lower() or "utiliz" in r.lower()
                            for r in recs))

    def test_high_congestion_suggests_density(self):
        s    = CongestionStats(overflow_count=0, max_congestion=0.95)
        recs = self.gr.suggest_adjustments(s, self.cfg)
        self.assertTrue(any("congestion" in r.lower() or "dense" in r.lower()
                            for r in recs))

    def test_clean_suggests_proceed(self):
        s    = CongestionStats(overflow_count=0, max_congestion=0.40)
        recs = self.gr.suggest_adjustments(s, self.cfg)
        self.assertTrue(any("proceed" in r.lower() or "detail" in r.lower()
                            for r in recs))

    def test_returns_list(self):
        s    = CongestionStats()
        recs = self.gr.suggest_adjustments(s, self.cfg)
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)


class TestGlobalRouterRunMocked(unittest.TestCase):
    def test_docker_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=False)
            gr = GlobalRouter(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF, "cts.def")
            r  = gr.run(Path(tmp) / "cts.def", "top", tmp)
        self.assertFalse(r.success)

    def test_missing_guide_means_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True)
            gr = GlobalRouter(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF, "cts.def")
            r  = gr.run(Path(tmp) / "cts.def", "top", tmp)
        self.assertFalse(r.success)
        self.assertIn("route_guides", r.error_message)

    def test_guide_file_created_means_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True)
            gr = GlobalRouter(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF,   "cts.def")
            write_file(Path(tmp), FAKE_GUIDES, "route_guides.txt")
            r  = gr.run(Path(tmp) / "cts.def", "top", tmp)
        self.assertTrue(r.success)
        self.assertIsNotNone(r.guide_path)


# ══════════════════════════════════════════════════════════════════════════════
# DETAIL ROUTER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestDetailRouteConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = DetailRouteConfig()
        self.assertEqual(cfg.min_layer,          "met2")
        self.assertEqual(cfg.max_layer,          "met4")
        self.assertEqual(cfg.threads,            4)
        self.assertEqual(cfg.drc_repair_loops,   3)
        self.assertTrue(cfg.run_drc_check)
        self.assertTrue(cfg.run_sta)

    def test_custom_values(self):
        cfg = DetailRouteConfig(threads=8, run_sta=False)
        self.assertEqual(cfg.threads, 8)
        self.assertFalse(cfg.run_sta)


class TestRoutingStats(unittest.TestCase):
    def test_defaults_zero(self):
        s = RoutingStats()
        self.assertEqual(s.drc_violation_count,   0)
        self.assertEqual(s.unrouted_nets,          0)
        self.assertEqual(s.via_count,              0)
        self.assertEqual(s.total_wire_length_um,   0.0)

    def test_is_clean(self):
        s = RoutingStats(drc_violation_count=0, unrouted_nets=0)
        r = DetailRouteResult(
            top_module = "top", output_dir = "/work",
            success    = True,  stats       = s,
        )
        self.assertTrue(r.is_drc_clean())
        self.assertTrue(r.is_fully_routed())

    def test_not_clean_with_drc(self):
        s = RoutingStats(drc_violation_count=3)
        r = DetailRouteResult(
            top_module = "top", output_dir = "/work",
            success    = True,  stats       = s,
        )
        self.assertFalse(r.is_drc_clean())


class TestDetailRouteResult(unittest.TestCase):
    def test_summary_success_clean(self):
        r = DetailRouteResult(
            top_module = "adder",
            output_dir = "/work",
            success    = True,
            stats      = RoutingStats(
                via_count=1823, total_wire_length_um=52340.7
            ),
        )
        text = r.summary()
        self.assertIn("SUCCESS",  text)
        self.assertIn("1823",     text)
        self.assertIn("CLEAN",    text)

    def test_summary_with_violations(self):
        r = DetailRouteResult(
            top_module = "adder",
            output_dir = "/work",
            success    = True,
            stats      = RoutingStats(drc_violation_count=4),
        )
        self.assertIn("4 violations", r.summary())

    def test_summary_failure(self):
        r = DetailRouteResult(
            top_module    = "top",
            output_dir    = "/work",
            success       = False,
            error_message = "routing failed",
        )
        self.assertIn("FAILED", r.summary())


class TestDetailRouterTclGeneration(unittest.TestCase):
    def setUp(self):
        self.dr = DetailRouter(docker=make_docker(), pdk=make_pdk())

    def test_script_contains_detailed_route(self):
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"),
            "top", DetailRouteConfig()
        )
        self.assertIn("detailed_route", tcl)

    def test_script_contains_read_guides(self):
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"),
            "top", DetailRouteConfig()
        )
        self.assertIn("read_guides", tcl)

    def test_script_contains_output_drc(self):
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"),
            "top", DetailRouteConfig()
        )
        self.assertIn("drc_violations.txt", tcl)

    def test_script_contains_write_def(self):
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"),
            "top", DetailRouteConfig()
        )
        self.assertIn("routed.def", tcl)

    def test_script_contains_sta_when_enabled(self):
        cfg = DetailRouteConfig(run_sta=True)
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"), "top", cfg
        )
        self.assertIn("report_checks", tcl)

    def test_script_no_sta_when_disabled(self):
        cfg = DetailRouteConfig(run_sta=False)
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"), "top", cfg
        )
        self.assertNotIn("report_checks", tcl)

    def test_script_contains_top_module(self):
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"),
            "my_design", DetailRouteConfig()
        )
        self.assertIn("my_design", tcl)

    def test_script_contains_pdk_paths(self):
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"),
            "top", DetailRouteConfig()
        )
        self.assertIn("/pdk", tcl)

    def test_script_contains_layer_bounds(self):
        tcl = self.dr._generate_detail_route_script(
            Path("cts.def"), Path("route_guides.txt"),
            "top", DetailRouteConfig()
        )
        self.assertIn("set_routing_layers", tcl)


class TestDetailRouterReportParsing(unittest.TestCase):
    def setUp(self):
        self.dr = DetailRouter(docker=make_docker(), pdk=make_pdk())

    def test_parse_clean_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), ROUTING_REPORT_CLEAN, "routing.rpt")
            s   = self.dr._parse_routing_report(rpt)
        self.assertAlmostEqual(s.total_wire_length_um, 52340.7)
        self.assertEqual(s.via_count,                  1823)
        self.assertEqual(s.unrouted_nets,              0)
        self.assertAlmostEqual(s.worst_slack_ns,       0.0)

    def test_parse_drc_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), ROUTING_REPORT_DRC, "routing.rpt")
            s   = self.dr._parse_routing_report(rpt)
        self.assertAlmostEqual(s.worst_slack_ns, -0.12)

    def test_parse_unrouted_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), ROUTING_REPORT_UNROUTED, "routing.rpt")
            s   = self.dr._parse_routing_report(rpt)
        self.assertEqual(s.unrouted_nets, 3)

    def test_parse_missing_returns_zeros(self):
        s = self.dr._parse_routing_report(Path("/nonexistent.rpt"))
        self.assertEqual(s.via_count, 0)


class TestDetailRouterRunMocked(unittest.TestCase):
    def test_docker_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=False)
            dr = DetailRouter(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF,   "cts.def")
            write_file(Path(tmp), FAKE_GUIDES, "route_guides.txt")
            r  = dr.run(Path(tmp) / "cts.def", "top", tmp)
        self.assertFalse(r.success)

    def test_routed_def_created_means_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True)
            dr = DetailRouter(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF,   "cts.def")
            write_file(Path(tmp), FAKE_GUIDES, "route_guides.txt")
            (Path(tmp) / "routed.def").write_text("DESIGN ;\n")
            r  = dr.run(Path(tmp) / "cts.def", "top", tmp)
        self.assertTrue(r.success)
        self.assertIsNotNone(r.routed_def)

    def test_missing_routed_def_means_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dm = make_docker(success=True)
            dr = DetailRouter(docker=dm, pdk=make_pdk())
            write_file(Path(tmp), FAKE_DEF,   "cts.def")
            write_file(Path(tmp), FAKE_GUIDES, "route_guides.txt")
            r  = dr.run(Path(tmp) / "cts.def", "top", tmp)
        self.assertFalse(r.success)
        self.assertIn("routed.def", r.error_message)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING OPTIMIZER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRouteOptConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = RouteOptConfig()
        self.assertEqual(cfg.drc_threshold,      0)
        self.assertEqual(cfg.unrouted_threshold, 0)
        self.assertLess(cfg.wns_threshold_ns,    0)

    def test_custom_thresholds(self):
        cfg = RouteOptConfig(drc_threshold=5)
        self.assertEqual(cfg.drc_threshold, 5)


class TestRouteAnalysisResult(unittest.TestCase):
    def test_tapeable_when_clean(self):
        r = RouteAnalysisResult(
            top_module    = "top",
            is_tapeable   = True,
            drc_count     = 0,
            unrouted_count= 0,
        )
        text = r.summary()
        self.assertIn("TAPE-OUT READY", text)

    def test_not_tapeable_with_drc(self):
        r = RouteAnalysisResult(
            top_module    = "top",
            is_tapeable   = False,
            drc_count     = 3,
        )
        self.assertIn("NOT READY", r.summary())

    def test_summary_includes_all_metrics(self):
        r = RouteAnalysisResult(
            top_module    = "adder",
            drc_count     = 0,
            unrouted_count= 0,
            wns_ns        = -0.05,
            wire_length_um= 52000.0,
            via_count     = 1800,
        )
        text = r.summary()
        self.assertIn("52000.0",  text)
        self.assertIn("1800",     text)


class TestRoutingOptimizerParsing(unittest.TestCase):
    def setUp(self):
        self.opt = RoutingOptimizer(docker=make_docker(), pdk=make_pdk())

    def test_parse_clean_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), ROUTING_REPORT_CLEAN, "routing.rpt")
            m   = self.opt._parse_routing_report(rpt)
        self.assertAlmostEqual(m["wire_length_um"], 52340.7)
        self.assertEqual(m["via_count"],            1823)
        self.assertEqual(m["unrouted_count"],       0)

    def test_parse_drc_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = write_file(Path(tmp), ROUTING_REPORT_DRC, "routing.rpt")
            m   = self.opt._parse_routing_report(rpt)
        self.assertEqual(m["drc_count"],  4)
        self.assertAlmostEqual(m["wns_ns"], -0.12)

    def test_parse_nonexistent_returns_zeros(self):
        m = self.opt._parse_routing_report("/nonexistent/routing.rpt")
        self.assertEqual(m["drc_count"],  0)
        self.assertEqual(m["via_count"],  0)

    def test_count_drc_violations_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = tmp / Path("drc.txt")
            Path(f).write_text("# no violations\n")
            count = self.opt._count_drc_violations(f)
        self.assertEqual(count, 0)

    def test_count_drc_violations_missing_file(self):
        count = self.opt._count_drc_violations("/nonexistent/drc.txt")
        self.assertEqual(count, 0)


class TestRoutingOptimizerIssues(unittest.TestCase):
    def setUp(self):
        self.opt = RoutingOptimizer(docker=make_docker(), pdk=make_pdk())
        self.cfg = RouteOptConfig()

    def test_no_issues_when_clean(self):
        m = {"drc_count": 0, "unrouted_count": 0, "wns_ns": 0.0,
             "congestion": 0.3, "wire_length_um": 50000.0}
        issues = self.opt._identify_issues(m, self.cfg)
        self.assertEqual(issues, [])

    def test_drc_is_critical(self):
        m = {"drc_count": 3, "unrouted_count": 0, "wns_ns": 0.0,
             "congestion": 0.3, "wire_length_um": 50000.0}
        issues = self.opt._identify_issues(m, self.cfg)
        types  = {i.issue_type for i in issues}
        self.assertIn(RoutingIssueType.DRC_VIOLATION, types)
        drc_issue = next(i for i in issues if i.issue_type == RoutingIssueType.DRC_VIOLATION)
        self.assertEqual(drc_issue.severity, "critical")

    def test_unrouted_is_critical(self):
        m = {"drc_count": 0, "unrouted_count": 2, "wns_ns": 0.0,
             "congestion": 0.3, "wire_length_um": 50000.0}
        issues = self.opt._identify_issues(m, self.cfg)
        types  = {i.issue_type for i in issues}
        self.assertIn(RoutingIssueType.UNROUTED_NET, types)

    def test_timing_violation_detected(self):
        m = {"drc_count": 0, "unrouted_count": 0, "wns_ns": -0.30,
             "congestion": 0.3, "wire_length_um": 50000.0}
        issues = self.opt._identify_issues(m, self.cfg)
        types  = {i.issue_type for i in issues}
        self.assertIn(RoutingIssueType.TIMING_VIOLATION, types)

    def test_high_congestion_detected(self):
        m = {"drc_count": 0, "unrouted_count": 0, "wns_ns": 0.0,
             "congestion": 0.90, "wire_length_um": 50000.0}
        issues = self.opt._identify_issues(m, self.cfg)
        types  = {i.issue_type for i in issues}
        self.assertIn(RoutingIssueType.HIGH_CONGESTION, types)

    def test_critical_before_warning(self):
        m = {"drc_count": 2, "unrouted_count": 0, "wns_ns": -0.15,
             "congestion": 0.85, "wire_length_um": 50000.0}
        issues = self.opt._identify_issues(m, self.cfg)
        if len(issues) > 1:
            self.assertEqual(issues[0].severity, "critical")


class TestRoutingOptimizerActionPlan(unittest.TestCase):
    def setUp(self):
        self.opt = RoutingOptimizer(docker=make_docker(), pdk=make_pdk())

    def test_clean_plan_says_proceed(self):
        plan = self.opt._build_action_plan([], {})
        self.assertTrue(any("proceed" in p.lower() or "drc" in p.lower()
                            for p in plan))

    def test_drc_plan_mentions_reroute(self):
        issues = [RoutingIssue(
            RoutingIssueType.DRC_VIOLATION, "critical",
            "4 DRC violations", 4.0, 0.0, FixStrategy.REROUTE_NET
        )]
        plan = self.opt._build_action_plan(issues, {"drc_count": 4})
        self.assertTrue(any("drc" in p.lower() or "violation" in p.lower()
                            for p in plan))

    def test_unrouted_plan_mentions_utilization(self):
        issues = [RoutingIssue(
            RoutingIssueType.UNROUTED_NET, "critical",
            "3 unrouted", 3.0, 0.0, FixStrategy.CHANGE_CONFIG
        )]
        plan = self.opt._build_action_plan(
            issues, {"drc_count": 0, "unrouted_count": 3, "wns_ns": 0.0}
        )
        self.assertTrue(any("utiliz" in p.lower() or "space" in p.lower()
                            for p in plan))

    def test_returns_list(self):
        plan = self.opt._build_action_plan([], {})
        self.assertIsInstance(plan, list)
        self.assertGreater(len(plan), 0)


class TestRoutingOptimizerAnalyze(unittest.TestCase):
    def setUp(self):
        self.opt = RoutingOptimizer(docker=make_docker(), pdk=make_pdk())

    def test_analyze_clean_report_tapeable(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt    = write_file(Path(tmp), ROUTING_REPORT_CLEAN, "routing.rpt")
            result = self.opt.analyze(rpt, "top")
        self.assertTrue(result.is_tapeable)
        self.assertEqual(result.issues, [])

    def test_analyze_drc_report_not_tapeable(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt    = write_file(Path(tmp), ROUTING_REPORT_DRC, "routing.rpt")
            result = self.opt.analyze(rpt, "top")
        # DRC violations in report (via drc_count line)
        self.assertGreater(result.drc_count, 0)

    def test_analyze_from_result_clean(self):
        dr_stats  = RoutingStats(
            drc_violation_count = 0,
            unrouted_nets       = 0,
            worst_slack_ns      = 0.05,
        )
        dr_result = DetailRouteResult(
            top_module = "top", output_dir = "/work",
            success    = True,  stats       = dr_stats,
        )
        result = self.opt.analyze_from_result(dr_result)
        self.assertTrue(result.is_tapeable)

    def test_analyze_from_result_with_drc(self):
        dr_stats  = RoutingStats(drc_violation_count=2)
        dr_result = DetailRouteResult(
            top_module = "top", output_dir = "/work",
            success    = True,  stats       = dr_stats,
        )
        result = self.opt.analyze_from_result(dr_result)
        self.assertFalse(result.is_tapeable)
        types = {i.issue_type for i in result.issues}
        self.assertIn(RoutingIssueType.DRC_VIOLATION, types)

    def test_action_plan_not_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt    = write_file(Path(tmp), ROUTING_REPORT_CLEAN, "routing.rpt")
            result = self.opt.analyze(rpt, "top")
        self.assertGreater(len(result.action_plan), 0)


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS (auto-skipped without Docker)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationRealDocker(unittest.TestCase):
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

    def test_openroad_fastroute_accessible(self):
        self._skip()
        from python.docker_manager import DockerManager
        from pathlib import Path
        dm     = DockerManager()
        result = dm.run_openroad(
            work_dir = str(Path.home()),
            command  = "openroad -help 2>&1 | grep -i route | head -3",
        )
        # Just verify openroad is available; route commands may vary
        self.assertIsNotNone(result)


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
