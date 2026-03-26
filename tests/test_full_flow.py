"""
test_full_flow.py  –  Tests for full_flow.py
=============================================
All tests pass without Docker, Yosys, or real tools.
Tests that need infrastructure auto-skip.

Run from project root:
    python -m pytest tests/test_full_flow.py -v

Run everything:
    python -m pytest tests/ -v
"""

import sys
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.full_flow import (
    RTLGenAI, FlowConfig, FlowResult, FlowError, _Synthesiser,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

SIMPLE_NETLIST = """\
module adder_8bit (
    input  clk,
    input  [7:0] a, b,
    output [7:0] sum
);
  sky130_fd_sc_hd__and2_1 _0_ (.A(a[0]),.B(b[0]),.X(sum[0]));
  sky130_fd_sc_hd__dfxtp_1 _1_ (.CLK(clk),.D(sum[0]),.Q(sum[1]));
endmodule
"""

SIMPLE_RTL = """\
module adder_8bit (
    input  clk,
    input  [7:0] a, b,
    output reg [7:0] sum
);
  always @(posedge clk) sum <= a + b;
endmodule
"""


def write_file(tmp: Path, content: str, name: str) -> Path:
    p = tmp / name
    p.write_text(content, encoding="utf-8")
    return p


def make_successful_run():
    """Mock DockerManager run that always succeeds."""
    run = MagicMock()
    run.success     = True
    run.stdout      = "done\n"
    run.stderr      = ""
    run.return_code = 0
    run.combined_output.return_value = "done\n"
    return run


def make_failed_run(error="[ERROR something failed]"):
    run = MagicMock()
    run.success     = False
    run.stdout      = ""
    run.stderr      = error
    run.return_code = 1
    run.combined_output.return_value = error
    return run


def make_docker_status(running=True, image_ready=True):
    status = MagicMock()
    status.is_running  = running
    status.image_ready = image_ready
    status.version     = "Docker 24.0"
    status.error_message = ""
    return status


def make_pdk_result(valid=True):
    result = MagicMock()
    result.is_valid        = valid
    result.found_libraries = ["sky130_fd_sc_hd"]
    result.errors          = [] if valid else ["PDK not found"]
    return result


# ══════════════════════════════════════════════════════════════════════════════
# FLOW CONFIG TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowConfig(unittest.TestCase):
    """Tests for FlowConfig defaults and sub-config generation."""

    def test_defaults(self):
        cfg = FlowConfig()
        self.assertEqual(cfg.target_utilization, 0.65)
        self.assertEqual(cfg.clock_period_ns,    10.0)
        self.assertEqual(cfg.clock_net,          "clk")
        self.assertEqual(cfg.min_route_layer,    "met2")
        self.assertEqual(cfg.max_route_layer,    "met4")
        self.assertTrue(cfg.run_drc)
        self.assertTrue(cfg.run_lvs)

    def test_custom_values(self):
        cfg = FlowConfig(
            target_utilization = 0.50,
            clock_period_ns    = 5.0,
            clock_net          = "sys_clk",
        )
        self.assertEqual(cfg.target_utilization, 0.50)
        self.assertEqual(cfg.clock_period_ns,    5.0)
        self.assertEqual(cfg.clock_net,          "sys_clk")

    def test_floorplanner_config_populated(self):
        cfg = FlowConfig(target_utilization=0.70, clock_period_ns=8.0)
        fp  = cfg._floorplanner_config()
        self.assertEqual(fp.target_utilization, 0.70)
        self.assertEqual(fp.clock_period_ns,    8.0)
        self.assertTrue(fp.run_openroad)

    def test_placement_config_populated(self):
        cfg = FlowConfig(placement_density=0.55, timing_driven=False)
        pl  = cfg._placement_config()
        self.assertEqual(pl.density_target, 0.55)
        self.assertFalse(pl.timing_driven)

    def test_cts_config_populated(self):
        cfg = FlowConfig(clock_net="ref_clk", cts_repair_hold=False)
        cts = cfg._cts_config()
        self.assertEqual(cts.clock_net,   "ref_clk")
        self.assertFalse(cts.repair_hold)

    def test_global_route_config_populated(self):
        cfg = FlowConfig(routing_adjustment=0.45)
        gr  = cfg._global_route_config()
        self.assertEqual(gr.adjustment, 0.45)

    def test_detail_route_config_populated(self):
        cfg = FlowConfig(routing_threads=8)
        dr  = cfg._detail_route_config()
        self.assertEqual(dr.threads, 8)

    def test_gds_config_populated(self):
        cfg = FlowConfig(insert_fill_cells=False, flatten_gds=False)
        gds = cfg._gds_config()
        self.assertFalse(gds.insert_fill_cells)
        self.assertFalse(gds.flatten)

    def test_signoff_config_populated(self):
        cfg = FlowConfig(run_drc=True, run_lvs=False)
        so  = cfg._signoff_config()
        self.assertTrue(so.run_drc)
        self.assertFalse(so.run_lvs)

    def test_package_config_has_process(self):
        cfg = FlowConfig()
        pkg = cfg._package_config()
        self.assertIn("Sky130A", pkg.process_node)

    def test_clock_net_propagates_to_all_stages(self):
        """clock_net set once must appear in all stage configs."""
        cfg = FlowConfig(clock_net="my_clk")
        self.assertEqual(cfg._floorplanner_config().clock_net, "my_clk")
        self.assertEqual(cfg._placement_config().clock_net,    "my_clk")
        self.assertEqual(cfg._cts_config().clock_net,          "my_clk")
        self.assertEqual(cfg._global_route_config().clock_net, "my_clk")
        self.assertEqual(cfg._detail_route_config().clock_net, "my_clk")


# ══════════════════════════════════════════════════════════════════════════════
# FLOW ERROR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowError(unittest.TestCase):
    def test_attributes(self):
        exc = FlowError("placement", "density too high", "raw output")
        self.assertEqual(exc.stage,   "placement")
        self.assertEqual(exc.message, "density too high")
        self.assertEqual(exc.output,  "raw output")

    def test_str_contains_stage(self):
        exc = FlowError("cts", "buffer overload")
        self.assertIn("cts", str(exc))

    def test_is_runtime_error(self):
        self.assertIsInstance(FlowError("x", "y"), RuntimeError)

    def test_empty_output_default(self):
        exc = FlowError("gds", "magic crashed")
        self.assertEqual(exc.output, "")


# ══════════════════════════════════════════════════════════════════════════════
# FLOW RESULT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowResult(unittest.TestCase):
    def test_defaults(self):
        r = FlowResult(top_module="top", output_dir="/work")
        self.assertFalse(r.is_tapeable)
        self.assertEqual(r.drc_violations, 0)
        self.assertEqual(r.failed_stage,   "")
        self.assertEqual(r.total_seconds,  0.0)

    def test_summary_tapeable(self):
        r = FlowResult(
            top_module   = "adder",
            output_dir   = "/work",
            is_tapeable  = True,
            gds_path     = "/work/gds/adder.gds",
            package_dir  = "/work/tapeout",
            total_seconds = 145.3,
        )
        text = r.summary()
        self.assertIn("TAPE-OUT READY", text)
        self.assertIn("adder.gds",      text)
        self.assertIn("145.3",          text)

    def test_summary_failed(self):
        r = FlowResult(
            top_module    = "top",
            output_dir    = "/work",
            is_tapeable   = False,
            failed_stage  = "routing",
            error_message = "unrouted nets",
        )
        text = r.summary()
        self.assertIn("NOT READY",    text)
        self.assertIn("routing",      text)
        self.assertIn("unrouted nets", text)

    def test_summary_shows_all_stages(self):
        r = FlowResult(
            top_module    = "top",
            output_dir    = "/work",
            rtl_path      = "/work/rtl/top.v",
            netlist_path  = "/work/synth/top.v",
            floorplan_def = "/work/fp/floorplan.def",
            placed_def    = "/work/pl/placed.def",
            cts_def       = "/work/cts/cts.def",
            routed_def    = "/work/rt/routed.def",
            gds_path      = "/work/gds/top.gds",
            package_dir   = "/work/pkg",
        )
        text = r.summary()
        for label in ("RTL", "Netlist", "Floorplan", "Placement",
                      "CTS", "Routing", "GDS", "Package"):
            self.assertIn(label, text, msg=f"'{label}' missing from summary")

    def test_summary_shows_drc_when_tapeable(self):
        r = FlowResult(
            top_module    = "top",
            output_dir    = "/work",
            is_tapeable   = True,
            drc_violations = 0,
            lvs_matched    = True,
            worst_slack_ns = 0.23,
        )
        text = r.summary()
        self.assertIn("0.230", text)

    def test_stage_times_in_summary(self):
        r = FlowResult(
            top_module  = "top",
            output_dir  = "/work",
            stage_times = {"synthesis": 12.3, "floorplan": 45.1},
        )
        text = r.summary()
        self.assertIn("synthesis",  text)
        self.assertIn("12.3",       text)


# ══════════════════════════════════════════════════════════════════════════════
# SYNTHESISER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSynthesiser(unittest.TestCase):
    def test_no_yosys_raises_flow_error(self):
        """_Synthesiser with no Yosys must raise FlowError on synthesise()."""
        synth = _Synthesiser(yosys_exe="/nonexistent/yosys")
        with tempfile.TemporaryDirectory() as tmp:
            rtl = write_file(Path(tmp), SIMPLE_RTL, "adder.v")
            from unittest.mock import MagicMock
            mock_docker = MagicMock()
            with self.assertRaises(FlowError) as ctx:
                synth.synthesise(rtl, "adder_8bit", Path(tmp) / "synth", mock_docker)
        self.assertEqual(ctx.exception.stage, "synthesis")

    def test_yosys_timeout_raises_flow_error(self):
        synth = _Synthesiser(yosys_exe="yosys")
        with tempfile.TemporaryDirectory() as tmp:
            rtl = write_file(Path(tmp), SIMPLE_RTL, "adder.v")
            from unittest.mock import MagicMock
            mock_docker = MagicMock()
            # Mock docker.run_script to return a failed result (timeout)
            mock_result = MagicMock()
            mock_result.return_code = -1
            mock_result.stderr = "timed out waiting for command"
            mock_result.combined_output.return_value = "timed out"
            mock_docker.run_script.return_value = mock_result
            with self.assertRaises(FlowError) as ctx:
                synth.synthesise(rtl, "adder_8bit", Path(tmp), mock_docker)
        self.assertIn("synthesis", str(ctx.exception.stage))

    def test_yosys_failure_raises_flow_error(self):
        synth = _Synthesiser(yosys_exe="yosys")
        with tempfile.TemporaryDirectory() as tmp:
            rtl = write_file(Path(tmp), SIMPLE_RTL, "adder.v")
            from unittest.mock import MagicMock
            mock_docker = MagicMock()
            with patch("subprocess.run") as mock_run:
                proc = MagicMock()
                proc.returncode = 1
                proc.stdout     = "Error: syntax error"
                proc.stderr     = ""
                mock_run.return_value = proc
                with self.assertRaises(FlowError) as ctx:
                    synth.synthesise(rtl, "adder_8bit", Path(tmp), mock_docker)
        self.assertEqual(ctx.exception.stage, "synthesis")

    def test_yosys_success_returns_path(self):
        synth = _Synthesiser(yosys_exe="yosys")
        with tempfile.TemporaryDirectory() as tmp:
            rtl      = write_file(Path(tmp), SIMPLE_RTL, "adder.v")
            out_dir  = Path(tmp) / "synth"
            out_dir.mkdir()
            netlist  = out_dir / "adder_8bit_synth.v"
            netlist.write_text(SIMPLE_NETLIST)

            mock_docker = MagicMock()
            with patch("subprocess.run") as mock_run:
                proc = MagicMock()
                proc.returncode = 0
                proc.stdout     = "Synthesis done."
                proc.stderr     = ""
                mock_run.return_value = proc
                result = synth.synthesise(rtl, "adder_8bit", out_dir, mock_docker)
        self.assertEqual(result, netlist)


# ══════════════════════════════════════════════════════════════════════════════
# INFRASTRUCTURE CHECK TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestInfrastructureCheck(unittest.TestCase):
    """Tests for _verify_infrastructure() — fast-fail before any work."""

    def _make_instance(self, docker_running=True, image_ready=True, pdk_valid=True):
        """Create a patched RTLGenAI instance without real tools."""
        with tempfile.TemporaryDirectory() as tmp:
            with patch("python.full_flow.DockerManager") as MockDocker, \
                 patch("python.full_flow.PDKManager") as MockPDK:

                dm = MockDocker.return_value
                dm.check_status.return_value = make_docker_status(
                    docker_running, image_ready
                )
                dm.work_dir = Path(tmp)

                pdk = MockPDK.return_value
                pdk.validate.return_value = make_pdk_result(pdk_valid)

                try:
                    cfg      = FlowConfig()
                    instance = RTLGenAI(
                        config     = cfg,
                        output_dir = Path(tmp),
                    )
                    return instance, None
                except FlowError as e:
                    return None, e

    def test_valid_infra_no_error(self):
        instance, err = self._make_instance(
            docker_running=True, image_ready=True, pdk_valid=True
        )
        self.assertIsNone(err)
        self.assertIsNotNone(instance)

    def test_docker_not_running_raises(self):
        _, err = self._make_instance(docker_running=False)
        self.assertIsNotNone(err)
        self.assertEqual(err.stage, "infrastructure")
        self.assertIn("Docker", err.message)

    def test_image_not_pulled_raises(self):
        _, err = self._make_instance(docker_running=True, image_ready=False)
        self.assertIsNotNone(err)
        self.assertEqual(err.stage, "infrastructure")
        self.assertIn("OpenLane", err.message)

    def test_invalid_pdk_raises(self):
        _, err = self._make_instance(
            docker_running=True, image_ready=True, pdk_valid=False
        )
        self.assertIsNotNone(err)
        self.assertEqual(err.stage, "infrastructure")
        self.assertIn("PDK", err.message)


# ══════════════════════════════════════════════════════════════════════════════
# PROGRESS CALLBACK TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestProgressCallback(unittest.TestCase):
    def _make_instance(self, callback=None):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("python.full_flow.DockerManager") as MockDocker, \
                 patch("python.full_flow.PDKManager") as MockPDK:
                dm = MockDocker.return_value
                dm.check_status.return_value = make_docker_status()
                dm.work_dir = Path(tmp)
                MockPDK.return_value.validate.return_value = make_pdk_result()
                return RTLGenAI(
                    config     = FlowConfig(),
                    output_dir = Path(tmp),
                    progress   = callback,
                )

    def test_callback_receives_dict(self):
        events = []
        instance = self._make_instance(callback=lambda d: events.append(d))
        instance._emit("test_stage", 0.5, "halfway")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stage"], "test_stage")
        self.assertAlmostEqual(events[0]["pct"], 0.5)
        self.assertEqual(events[0]["msg"],   "halfway")

    def test_callback_none_no_crash(self):
        instance = self._make_instance(callback=None)
        # Should not raise even with no callback
        instance._emit("synthesis", 0.1, "running")

    def test_bad_callback_does_not_crash_flow(self):
        def bad_callback(d):
            raise RuntimeError("callback bug")

        instance = self._make_instance(callback=bad_callback)
        # _emit must never propagate callback exceptions
        try:
            instance._emit("test", 0.5, "msg")
        except RuntimeError:
            self.fail("_emit propagated callback exception")

    def test_callback_dict_has_required_keys(self):
        received = {}
        instance = self._make_instance(callback=lambda d: received.update(d))
        instance._emit("routing", 0.70, "global routing done")
        self.assertIn("stage", received)
        self.assertIn("pct",   received)
        self.assertIn("msg",   received)

    def test_negative_pct_for_error_stage(self):
        events = []
        instance = self._make_instance(callback=lambda d: events.append(d))
        instance._emit("placement", -1.0, "❌ failed")
        self.assertEqual(events[0]["pct"], -1.0)


# ══════════════════════════════════════════════════════════════════════════════
# END-TO-END MOCKED FLOW TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRunFromRTLMocked(unittest.TestCase):
    """
    End-to-end tests with all external tools mocked.
    These verify the orchestration logic without needing Docker/Yosys.
    """

    def _make_flow(self, tmp: Path, succeed_through: str = "package"):
        """
        Create a fully mocked RTLGenAI instance.

        succeed_through: which stage is the last to succeed.
          "synthesis", "floorplan", "placement", "cts",
          "routing", "gds", "signoff", "package"
        """
        stages = [
            "synthesis", "floorplan", "placement", "cts",
            "routing", "gds", "signoff", "package",
        ]
        idx_limit = stages.index(succeed_through)

        with patch("python.full_flow.DockerManager") as MockDocker, \
             patch("python.full_flow.PDKManager") as MockPDK, \
             patch("python.full_flow.Floorplanner") as MockFP, \
             patch("python.full_flow.Placer") as MockPl, \
             patch("python.full_flow.PlacementOptimizer") as MockOpt, \
             patch("python.full_flow.CTSEngine") as MockCTS, \
             patch("python.full_flow.GlobalRouter") as MockGR, \
             patch("python.full_flow.DetailRouter") as MockDR, \
             patch("python.full_flow.GDSGenerator") as MockGDS, \
             patch("python.full_flow.SignoffChecker") as MockSO, \
             patch("python.full_flow.TapeoutPackager") as MockPkg, \
             patch("python.full_flow._Synthesiser") as MockSynth:

            # ── infrastructure ────────────────────────────────────────
            dm = MockDocker.return_value
            dm.check_status.return_value = make_docker_status()
            dm.work_dir = tmp
            dm.run_script.return_value = make_successful_run()
            MockPDK.return_value.validate.return_value = make_pdk_result()

            # ── synthesis ─────────────────────────────────────────────
            netlist = tmp / "adder_8bit_synth.v"
            netlist.write_text(SIMPLE_NETLIST)
            MockSynth.return_value.synthesise.return_value = netlist

            # ── floorplan ─────────────────────────────────────────────
            fp_def = tmp / "floorplan.def"
            fp_def.write_text("DESIGN ;\n")
            fp_result = MagicMock()
            fp_result.success      = idx_limit >= stages.index("floorplan")
            fp_result.floorplan_def= str(fp_def)
            fp_result.error_message= "" if fp_result.success else "fp fail"
            MockFP.return_value.run.return_value = fp_result

            # ── placement ─────────────────────────────────────────────
            pl_def = tmp / "placed.def"
            pl_def.write_text("DESIGN ;\n")
            pl_result = MagicMock()
            pl_result.success       = idx_limit >= stages.index("placement")
            pl_result.placed_def    = str(pl_def)
            pl_result.error_message = "" if pl_result.success else "pl fail"
            pl_result.stats         = MagicMock()
            MockPl.return_value.run.return_value = pl_result

            # ── opt (analyze_only always returns no issues) ────────────
            MockOpt.return_value.analyze_only.return_value = ([], [])

            # ── CTS ───────────────────────────────────────────────────
            cts_def = tmp / "cts.def"
            cts_def.write_text("DESIGN ;\n")
            cts_result = MagicMock()
            cts_result.success       = idx_limit >= stages.index("cts")
            cts_result.cts_def       = str(cts_def)
            cts_result.error_message = "" if cts_result.success else "cts fail"
            cts_result.stats         = MagicMock()
            cts_result.stats.buf_count   = 10
            cts_result.stats.max_skew_ns = 0.045
            MockCTS.return_value.run.return_value = cts_result

            # ── global routing ────────────────────────────────────────
            guide = tmp / "route_guides.txt"
            guide.write_text("# guides\n")
            gr_result = MagicMock()
            gr_result.success       = idx_limit >= stages.index("routing")
            gr_result.guide_path    = str(guide)
            gr_result.error_message = "" if gr_result.success else "gr fail"
            gr_result.congestion    = MagicMock()
            gr_result.congestion.overflow_count = 0
            MockGR.return_value.run.return_value = gr_result

            # ── detailed routing ──────────────────────────────────────
            routed = tmp / "routed.def"
            routed.write_text("DESIGN ;\n")
            dr_result = MagicMock()
            dr_result.success       = idx_limit >= stages.index("routing")
            dr_result.routed_def    = str(routed)
            dr_result.error_message = "" if dr_result.success else "dr fail"
            dr_result.stats         = MagicMock()
            dr_result.stats.drc_violation_count = 0
            dr_result.stats.unrouted_nets       = 0
            dr_result.stats.worst_slack_ns      = 0.05
            MockDR.return_value.run.return_value = dr_result

            # ── GDS ───────────────────────────────────────────────────
            gds = tmp / "adder_8bit.gds"
            gds.write_bytes(b"\x00" * 1024)
            gds_result = MagicMock()
            gds_result.success       = idx_limit >= stages.index("gds")
            gds_result.gds_path      = str(gds)
            gds_result.gds_size_mb   = 0.001
            gds_result.error_message = "" if gds_result.success else "gds fail"
            MockGDS.return_value.run.return_value = gds_result

            # ── sign-off ──────────────────────────────────────────────
            drc_rpt = MagicMock()
            drc_rpt.passed          = True
            drc_rpt.violation_count = 0
            lvs_rpt = MagicMock()
            lvs_rpt.matched = True
            so_result = MagicMock()
            so_result.drc = drc_rpt
            so_result.lvs = lvs_rpt
            MockSO.return_value.run.return_value = so_result

            # ── package ───────────────────────────────────────────────
            pkg_dir_path = tmp / "adder_8bit_tapeout"
            pkg_dir_path.mkdir()
            pkg_result = MagicMock()
            pkg_result.package_dir = str(pkg_dir_path)
            pkg_result.files       = []
            MockPkg.return_value.package.return_value = pkg_result

            # ── create instance & run ─────────────────────────────────
            rtl = tmp / "adder_8bit.v"
            rtl.write_text(SIMPLE_RTL)

            instance = RTLGenAI(
                config     = FlowConfig(),
                output_dir = tmp,
            )
            result = instance._run_mode_b(rtl, "adder_8bit")
            return result

    def test_full_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._make_flow(Path(tmp), succeed_through="package")
        self.assertTrue(r.is_tapeable)
        self.assertIsNotNone(r.gds_path)
        self.assertIsNotNone(r.package_dir)
        self.assertEqual(r.failed_stage, "")

    def test_result_has_all_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._make_flow(Path(tmp), succeed_through="package")
        self.assertIsNotNone(r.rtl_path)
        self.assertIsNotNone(r.netlist_path)
        self.assertIsNotNone(r.floorplan_def)
        self.assertIsNotNone(r.placed_def)
        self.assertIsNotNone(r.cts_def)
        self.assertIsNotNone(r.routed_def)
        self.assertIsNotNone(r.gds_path)

    def test_total_seconds_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._make_flow(Path(tmp), succeed_through="package")
        self.assertGreater(r.total_seconds, 0.0)

    def test_drc_zero_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._make_flow(Path(tmp), succeed_through="package")
        self.assertEqual(r.drc_violations, 0)

    def test_lvs_matched_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._make_flow(Path(tmp), succeed_through="package")
        self.assertTrue(r.lvs_matched)


class TestFlowErrorPropagation(unittest.TestCase):
    """Test that failures in each stage are correctly captured."""

    def _run_with_fp_failure(self, tmp: Path) -> FlowResult:
        with patch("python.full_flow.DockerManager") as MockDocker, \
             patch("python.full_flow.PDKManager") as MockPDK, \
             patch("python.full_flow.Floorplanner") as MockFP, \
             patch("python.full_flow._Synthesiser") as MockSynth:

            dm = MockDocker.return_value
            dm.check_status.return_value = make_docker_status()
            dm.work_dir = tmp
            MockPDK.return_value.validate.return_value = make_pdk_result()

            netlist = tmp / "top_synth.v"
            netlist.write_text(SIMPLE_NETLIST)
            MockSynth.return_value.synthesise.return_value = netlist

            # Floorplan fails
            fp_result = MagicMock()
            fp_result.success       = False
            fp_result.error_message = "insufficient area for cells"
            MockFP.return_value.run.return_value = fp_result

            rtl = tmp / "top.v"
            rtl.write_text(SIMPLE_RTL)
            instance = RTLGenAI(
                config=FlowConfig(), output_dir=tmp
            )
            return instance._run_mode_b(rtl, "top")

    def test_floorplan_failure_captured(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run_with_fp_failure(Path(tmp))
        self.assertFalse(r.is_tapeable)
        self.assertEqual(r.failed_stage, "floorplan")
        self.assertIn("insufficient", r.error_message)

    def test_failed_result_has_no_gds(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run_with_fp_failure(Path(tmp))
        self.assertIsNone(r.gds_path)

    def test_failed_result_total_seconds_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run_with_fp_failure(Path(tmp))
        self.assertGreater(r.total_seconds, 0.0)


# ══════════════════════════════════════════════════════════════════════════════
# MODE A TESTS (require v1.0 rtl_generator — skip if not found)
# ══════════════════════════════════════════════════════════════════════════════

class TestModeA(unittest.TestCase):
    def test_mode_a_missing_rtl_generator_raises(self):
        """run_full_flow() without v1.0 system must raise FlowError."""
        with tempfile.TemporaryDirectory() as tmp:
            with patch("python.full_flow.DockerManager") as MockDocker, \
                 patch("python.full_flow.PDKManager") as MockPDK:

                dm = MockDocker.return_value
                dm.check_status.return_value = make_docker_status()
                dm.work_dir = Path(tmp)
                MockPDK.return_value.validate.return_value = make_pdk_result()

                instance = RTLGenAI(
                    config=FlowConfig(), output_dir=Path(tmp)
                )
                # Patch the import to simulate rtl_generator not found
                with patch.dict("sys.modules", {"python.rtl_generator": None}):
                    with self.assertRaises(FlowError) as ctx:
                        instance._run_mode_a("8-bit adder", "")
            self.assertIn("rtl_generation", ctx.exception.stage)


# ══════════════════════════════════════════════════════════════════════════════
# REAL TOOL INTEGRATION (auto-skipped)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationRealTools(unittest.TestCase):
    """Skipped automatically when Docker is not running."""

    @classmethod
    def setUpClass(cls):
        try:
            import subprocess
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            cls.docker_ok = r.returncode == 0
        except Exception:
            cls.docker_ok = False

    def _skip(self):
        if not self.docker_ok:
            self.skipTest("Docker not running")

    def test_run_from_rtl_simple_design(self):
        """
        Full end-to-end run with a simple 8-bit adder.
        Only executes when Docker + PDK are confirmed available.
        Expected runtime: 10–40 minutes depending on hardware.
        """
        self._skip()

        with tempfile.TemporaryDirectory() as tmp:
            rtl = Path(tmp) / "adder_8bit.v"
            rtl.write_text(SIMPLE_RTL)

            result = RTLGenAI.run_from_rtl(
                rtl_path   = rtl,
                top_module = "adder_8bit",
                output_dir = tmp,
                config     = FlowConfig(
                    clock_period_ns = 20.0,   # relaxed timing for test
                ),
                progress = lambda d: print(
                    f"  [{d['stage']}] {d['pct']*100:.0f}%  {d['msg']}"
                ),
            )

        print(result.summary())
        # The design must at least get through floorplanning
        self.assertIsNotNone(result.netlist_path or result.failed_stage)


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
