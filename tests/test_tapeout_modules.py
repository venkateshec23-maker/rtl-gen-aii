"""
tests/test_tapeout_modules.py — RTL-Gen AI Phase 10 integration tests.
Tests tapeout_manager, tapeout_score, design_compare, and spef_enhanced.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tapeout_manager import (
    TapeoutManifest, generate_tapeout_package, get_tapeout_readiness_score,
)
from tapeout_score import evaluate_tapeout_readiness, TapeoutScore
from design_compare import DesignSnapshot, compare_design_snapshots, ComparisonResult
from spef_enhanced import (
    parse_real_spef, parse_parasitic_report, RealSPEFResult, RealParasiticNet,
    plot_rc_histogram, plot_top_rc_nets,
)


# ── Tapeout Manager Tests ────────────────────────────────────────────────────

class TestTapeoutManager:
    def test_manifest_creation(self):
        m = TapeoutManifest(design_name="test", drc_clean=True, lvs_matched=True, timing_met=True)
        assert m.design_name == "test"
        assert m.drc_clean
        assert m.lvs_matched

    def test_readiness_score_perfect(self):
        m = TapeoutManifest(design_name="test", drc_clean=True, lvs_matched=True, timing_met=True,
                            total_power_mw=10.0, cell_count=500, files={
            "gds/test.gds": "150000",
            "spef/test.spef": "5000",
            "reports/drc/drc.txt": "200",
            "reports/lvs/lvs.txt": "300",
            "reports/sta/sta.txt": "400",
        })
        score = get_tapeout_readiness_score(m)
        assert score["tapeout_ready"]
        assert score["percentage"] >= 90

    def test_readiness_score_blockers(self):
        m = TapeoutManifest(design_name="fail", drc_clean=False, lvs_matched=False, timing_met=False)
        score = get_tapeout_readiness_score(m)
        assert not score["tapeout_ready"]
        assert len(score["blockers"]) >= 3

    def test_generate_package_minimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp) / "results"
            rd.mkdir()
            od = Path(tmp) / "tapeout"
            (rd / "test.gds").write_bytes(b"\x00" * 100)
            pkg = generate_tapeout_package("test", str(rd), str(od))
            assert Path(pkg).exists()
            assert (Path(pkg) / "manifest.json").exists()

    def test_generate_package_with_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp) / "results"
            rd.mkdir()
            od = Path(tmp) / "tapeout"
            (rd / "test.gds").write_bytes(b"\x00" * 100)
            (rd / "test_sky130.v").write_bytes(b"sky130 module\n")
            (rd / "drc_report.txt").write_bytes(b"DRC violations: 0\n")
            (rd / "lvs_report_final.txt").write_bytes(b"Circuits match uniquely.\n")
            (rd / "sta_final.txt").write_bytes(b"slack (MET) 5.0\n")
            pkg = generate_tapeout_package("test", str(rd), str(od))
            manifest = json.loads((Path(pkg) / "manifest.json").read_text())
            assert manifest["design_name"] == "test"
            assert "test.gds" in str(manifest["files"])


# ── Tapeout Score Tests ──────────────────────────────────────────────────────

class TestTapeoutScore:
    def test_score_perfect(self):
        from parsers.sta_parser import STASummary, STACorner
        from parsers.drc_parser import DRCSummary
        from parsers.lvs_parser import LVSSummary
        from parsers.power_parser import PowerSummary
        from parsers.congestion_parser import CongestionSummary
        sta = STASummary()
        sta.corners["TT"] = STACorner(corner="TT", slack_ns=5.0, met=True)
        drc = DRCSummary(total_violations=0, clean=True)
        lvs = LVSSummary(status="MATCHED", matched=True)
        pwr = PowerSummary(total_power_mw=15.0, dynamic_power_mw=12.0)
        cong = CongestionSummary(h_overflow_pct=2.0, available=True)

        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp)
            gds = rd / "test.gds"
            gds.write_bytes(b"\x00" * 60000)
            spef = rd / "test.spef"
            spef.write_text("*SPEF\n*D_NET clk 0.001\n*END\n")
            ts = evaluate_tapeout_readiness(
                design_name="test", results_dir=str(rd),
                sta_summary=sta, drc_summary=drc, lvs_summary=lvs,
                power_summary=pwr, congestion_summary=cong,
                gds_path=str(gds), spef_path=str(spef),
            )
            assert ts.tapeout_ready
            assert ts.percentage >= 80

    def test_score_failing(self):
        from parsers.sta_parser import STASummary, STACorner
        from parsers.drc_parser import DRCSummary
        from parsers.lvs_parser import LVSSummary
        sta = STASummary()
        sta.corners["TT"] = STACorner(corner="TT", slack_ns=-0.5, met=False)
        drc = DRCSummary(total_violations=10, clean=False)
        lvs = LVSSummary(status="UNMATCHED", matched=False)

        ts = evaluate_tapeout_readiness("fail", "/nonexistent",
                                        sta_summary=sta, drc_summary=drc, lvs_summary=lvs)
        assert not ts.tapeout_ready
        assert len(ts.blockers) >= 3
        assert ts.category_scores.get("drc", 0) == 0

    def test_score_from_results_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp)
            (rd / "drc_report.txt").write_text("DRC violations: 0\n")
            (rd / "lvs_report_final.txt").write_text("Circuits match uniquely.\n")
            (rd / "sta_final.txt").write_text("slack (MET) 5.0\nwns 0.00\ntns 0.00\n")
            (rd / "power_report.txt").write_text("Total 0.00001 0.00002 0.00000 0.00003\n")
            gds = rd / "test.gds"
            gds.write_bytes(b"\x00" * 60000)
            spef = rd / "test.spef"
            spef.write_text("*SPEF\n*D_NET test 0.001\n*END\n")

            from tapeout_score import score_from_results_dir
            ts = score_from_results_dir("test", str(rd))
            assert isinstance(ts, TapeoutScore)
            assert ts.category_scores.get("drc", 0) >= 20


# ── Design Compare Tests ─────────────────────────────────────────────────────

class TestDesignCompare:
    def test_delta_improvement(self):
        a = DesignSnapshot(label="old", fmax_mhz=100, total_power_mw=20, drc_violations=3)
        b = DesignSnapshot(label="new", fmax_mhz=133, total_power_mw=15, drc_violations=0)
        r = compare_design_snapshots(a, b)
        assert r.deltas["fmax_mhz"] == 33.0
        assert r.deltas["drc_violations"] == -3
        assert "Improvements" in r.summary

    def test_delta_degradation(self):
        a = DesignSnapshot(label="good", fmax_mhz=133, lvs_status="MATCHED")
        b = DesignSnapshot(label="bad", fmax_mhz=100, lvs_status="UNMATCHED")
        r = compare_design_snapshots(a, b)
        assert r.deltas["fmax_mhz"] < 0

    def test_equal_snapshots(self):
        a = DesignSnapshot(label="v1", fmax_mhz=100, cell_count=500)
        b = DesignSnapshot(label="v1_dup", fmax_mhz=100, cell_count=500)
        r = compare_design_snapshots(a, b)
        assert r.deltas["fmax_mhz"] == 0
        assert r.deltas["cell_count"] == 0

    def test_from_db(self):
        """Test DesignSnapshot.from_design_db with a mock DesignDB."""
        from design_db import DesignDB, TimingData, TimingCorner, PowerData
        db = DesignDB(design_name="test", rtl_sources=["test.v"], netlist_path="test.v")
        db.timing = TimingData(
            period_ns=10.0,
            corners={"TT": TimingCorner(corner="TT", slack_ns=5.0, met=True)},
            fmax_mhz=200.0,
        )
        db.power = PowerData(total_mw=15.0)
        snap = DesignSnapshot.from_design_db(db, label="test_snap")
        assert snap.fmax_mhz == 200.0
        assert snap.setup_slack_ns == 5.0
        assert snap.total_power_mw == 15.0


# ── SPEF Enhanced Tests ──────────────────────────────────────────────────────

class TestSPEFEnhanced:
    def test_parse_spef_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.spef"
            p.write_text("""*SPEF
*DESIGN adder
*D_NET clk 0.001200
*RES 1
1 *P 0 *P 1 12.50
*CAP 2
1 *P 0 0.000800
2 *P 1 0.000400 *C
*END
*D_NET a[0] 0.000950
*RES 1
1 *P 2 *P 3 8.30
*CAP 2
1 *P 2 0.000600
2 *P 3 0.000350 *C
*END
""")
            result = parse_real_spef(p)
            assert result.total_nets == 2
            assert result.nets[0].net_name == "clk"
            assert abs(result.nets[0].resistance_ohm - 12.5) < 0.01
            assert abs(result.nets[0].capacitance_pf - 0.0012) < 0.0001
            assert abs(result.nets[0].coupling_cap_pf - 0.0004) < 0.0001

    def test_parse_parasitic_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpt = Path(tmp) / "report.txt"
            rpt.write_text("""Design: adder_8bit
  Net: clk    | R=12.50 ohm | C=0.001200 pF | Cc=0.000400 pF
  Net: a[0]   | R=8.30 ohm  | C=0.000950 pF | Cc=0.000350 pF
  Net: sum[0] | R=15.20 ohm | C=0.002100 pF | Cc=0.000800 pF
Total resistance: 36.00 ohm
Total capacitance: 0.004250 pF
Total coupling cap: 0.001550 pF
""")
            result = parse_parasitic_report(rpt)
            assert result.total_nets == 3
            assert abs(result.total_resistance_ohm - 36.0) < 0.01
            assert abs(result.total_capacitance_pf - 0.00425) < 0.0001

    def test_histogram_plot(self):
        result = RealSPEFResult(design_name="test")
        result.nets = [RealParasiticNet(net_name=f"n{i}", resistance_ohm=i*10,
                                        capacitance_pf=i*0.001, coupling_cap_pf=i*0.0005)
                       for i in range(5)]
        fig = plot_rc_histogram(result)
        assert fig is not None
        assert len(fig.data) >= 1

    def test_top_nets_plot(self):
        result = RealSPEFResult(design_name="test")
        result.nets = [RealParasiticNet(net_name=f"n{i}", resistance_ohm=i*10,
                                        capacitance_pf=i*0.001, delay_impact_ps=i*50)
                       for i in range(5)]
        fig = plot_top_rc_nets(result, n=3)
        assert fig is not None

    def test_spef_generation_roundtrip(self):
        result = RealSPEFResult(design_name="test")
        result.nets = [RealParasiticNet(net_name="clk", resistance_ohm=10,
                                        capacitance_pf=0.001, coupling_cap_pf=0.0004)]
        spef = result.to_spef()
        assert "*SPEF" in spef
        assert "*D_NET clk" in spef
        assert "*C" in spef

    def test_empty_result(self):
        result = RealSPEFResult()
        assert result.total_nets == 0
        assert result.avg_resistance() == 0.0
