"""
tests/test_parsers.py — RTL-Gen AI Phase 10 parser tests.
Tests all 6 parsers with real OpenROAD report samples.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from parsers.sta_parser import parse_sta_corner, parse_sta_report, STASummary, STACorner
from parsers.power_parser import parse_power_report, PowerSummary
from parsers.congestion_parser import parse_congestion_report, CongestionSummary
from parsers.drc_parser import parse_drc_report, parse_klayout_drc, DRCSummary
from parsers.lvs_parser import parse_lvs_report, LVSSummary
from parsers.metrics_parser import collect_all_metrics, AggregateMetrics


# ── STA Parser Tests ─────────────────────────────────────────────────────────

class TestSTAParser:
    STA_SAMPLE = """Startpoint: a[0]
Endpoint: sum[0]
Path type: max
-------------------------------------------------------------------------
  Cell type                   Delay  Time  Edge  Net  Pin
-------------------------------------------------------------------------
  sky130_fd_sc_hd__inv_2      0.012  0.012  r     a[0]  Y
  sky130_fd_sc_hd__nand2_1    0.008  0.020  f     n1    Y
  sky130_fd_sc_hd__xor3_1     0.045  0.065  r     sum[0]  X
slack (MET) 5.23
wns 0.00
tns 0.00
"""

    def test_parse_tt_corner(self):
        corner = parse_sta_corner(self.STA_SAMPLE, "TT")
        assert corner.corner == "TT"
        assert corner.wns_ns == 0.0
        assert corner.tns_ns == 0.0
        assert corner.met
        assert len(corner.paths) == 1
        assert corner.paths[0].startpoint == "a[0]"
        assert corner.paths[0].endpoint == "sum[0]"
        assert corner.paths[0].path_type == "max"

    def test_parse_wns_tns(self):
        text = "wns -0.15\ntns -1.23"
        corner = parse_sta_corner(text, "SS")
        assert corner.wns_ns == -0.15
        assert corner.tns_ns == -1.23
        assert not corner.met

    def test_parse_violated_slack(self):
        text = "slack (VIOLATED) -0.50"
        corner = parse_sta_corner(text, "FF")
        assert corner.slack_ns == -0.5
        assert not corner.met

    def test_parse_sta_summary(self):
        summary = parse_sta_report(self.STA_SAMPLE)
        assert "TT" in summary.corners
        tt = summary.corners["TT"]
        assert tt.wns_ns == 0.0

    def test_sta_degradation(self):
        preroute = "slack (MET) 6.00"
        postroute = "slack (MET) 5.50"
        signoff = "slack (MET) 5.23"
        summary = parse_sta_report("", preroute, postroute, signoff)
        assert summary.preroute is not None
        assert summary.postroute is not None
        assert summary.signoff is not None

    def test_empty_report(self):
        corner = parse_sta_corner("", "TT")
        assert corner.wns_ns is None
        assert corner.paths == []


# ── Power Parser Tests ───────────────────────────────────────────────────────

class TestPowerParser:
    POWER_SAMPLE = """-------------------------------------------------------------------------
  Group      Internal  Switching  Leakage   Total
  (power in W)
-------------------------------------------------------------------------
  Sequential 0.000000  0.000002  0.000000  0.000002
  Combinational 0.000010  0.000020  0.000000  0.000030
  Macro      0.000000  0.000000  0.000000  0.000000
Total        0.000010  0.000022  0.000000  0.000032
Design area 1234.56 u^2 45.0% utilization
"""

    def test_parse_power(self):
        ps = parse_power_report(self.POWER_SAMPLE)
        assert ps.total_power_mw == pytest.approx(0.032, rel=0.01)
        assert ps.dynamic_power_mw == pytest.approx(0.032, rel=0.01)
        assert ps.static_power_mw == pytest.approx(0.0, abs=0.001)
        assert ps.core_area_um2 == pytest.approx(1234.56)
        assert ps.utilization_pct == pytest.approx(45.0)

    def test_parse_power_groups(self):
        ps = parse_power_report(self.POWER_SAMPLE)
        assert len(ps.groups) == 3
        assert ps.groups[0].name == "Sequential"
        assert ps.groups[1].name == "Combinational"
        assert ps.groups[2].name == "Macro"

    def test_parse_power_fallback(self):
        text = "Total power = 0.032 mW"
        ps = parse_power_report(text)
        assert ps.total_power_mw == pytest.approx(0.032, rel=0.01)

    def test_parse_empty_power(self):
        ps = parse_power_report("")
        assert ps.total_power_mw is None
        assert ps.dynamic_power_mw is None


# ── Congestion Parser Tests ──────────────────────────────────────────────────

class TestCongestionParser:
    CONG_SAMPLE = """Overflow : 2.5%
Max density : 72.3%
Design area 1234.56 u^2 55.0% utilization
Unrouted nets : 0
"""

    def test_parse_congestion(self):
        cs = parse_congestion_report(self.CONG_SAMPLE)
        assert cs.available
        assert cs.h_overflow_pct == pytest.approx(2.5)
        assert cs.max_density_pct == pytest.approx(72.3)
        assert cs.utilization_pct == pytest.approx(55.0)
        assert cs.unrouted_nets == 0

    def test_congestion_not_available(self):
        cs = parse_congestion_report("CONGESTION_NOT_AVAILABLE")
        assert not cs.available

    def test_congestion_empty(self):
        cs = parse_congestion_report("")
        assert not cs.available

    def test_congestion_score(self):
        cs = parse_congestion_report(self.CONG_SAMPLE)
        assert cs.overflow_score is not None
        assert cs.overflow_score > 0


# ── DRC Parser Tests ─────────────────────────────────────────────────────────

class TestDRCParser:
    DRC_SAMPLE = """DRC violations: 0
"""

    DRC_VIOLATED = """DRC violations: 3
  met1.min_width : 2 violations
  met1.min_spacing : 1 violations
  Violation at (10.5, 20.3)
  Violation at (15.2, 25.1)
"""

    def test_parse_clean(self):
        ds = parse_drc_report(self.DRC_SAMPLE)
        assert ds.clean
        assert ds.total_violations == 0
        assert ds.engine == "magic"

    def test_parse_violations(self):
        ds = parse_drc_report(self.DRC_VIOLATED)
        assert not ds.clean
        assert ds.total_violations == 3
        assert "met1.min_width" in ds.by_category
        assert ds.by_category["met1.min_width"] == 2

    def test_parse_klayout_xml(self):
        xml = """<?xml version="1.0"?>
<drc-report>
  <violation rule="width" layer="met1" x="10.0" y="20.0" description="Min width violation"/>
  <violation rule="space" layer="met1" x="15.0" y="25.0" description="Min spacing violation"/>
</drc-report>"""
        ds = parse_klayout_drc(xml)
        assert ds.total_violations == 2
        assert not ds.clean
        assert ds.engine == "klayout"

    def test_parse_openroad_format(self):
        text = "Found 5 DRC violations"
        ds = parse_drc_report(text, engine="openroad")
        assert ds.total_violations == 5
        assert not ds.clean
        assert ds.engine == "openroad"

    def test_parse_coordinates(self):
        ds = parse_drc_report(self.DRC_VIOLATED)
        assert len(ds.coordinates) == 2
        assert ds.coordinates[0][0] == 10.5


# ── LVS Parser Tests ─────────────────────────────────────────────────────────

class TestLVSParser:
    LVS_MATCHED = """Netgen LVS results:
Circuits match uniquely.
Number of devices: 120 | Number of devices: 120
"""

    LVS_MISMATCH = """Netgen LVS results:
Netlists do not match.
Number of devices: 120 | Number of devices: 119
"""

    LVS_AMBIGUITY = """Netgen LVS results:
Cell pin lists for top cell altered to match.
Device classes are equivalent.
Number of devices: 120 | Number of devices: 120
"""

    def test_parse_matched(self):
        ls = parse_lvs_report(self.LVS_MATCHED)
        assert ls.matched
        assert ls.status == "MATCHED"
        assert ls.reason_code == "MATCHED"
        assert ls.total_devices_schematic == 120
        assert ls.total_devices_layout == 120

    def test_parse_mismatch(self):
        ls = parse_lvs_report(self.LVS_MISMATCH)
        assert not ls.matched
        assert ls.status == "UNMATCHED"

    def test_parse_ambiguity(self):
        ls = parse_lvs_report(self.LVS_AMBIGUITY)
        assert ls.matched  # pin ambiguity but devices equivalent = matched with warnings
        assert ls.status == "MATCHED_WITH_WARNINGS"

    def test_parse_empty(self):
        ls = parse_lvs_report("")
        assert ls.status == "INCOMPLETE"
        assert not ls.matched

    def test_parse_json_annotation(self):
        json_lvs = """{"lvs": {"matched": true, "matched_nets": 100, "unmatched_nets": 0, "device_mismatches": 0, "devices_schematic": 120, "devices_layout": 120}}"""
        ls = parse_lvs_report(json_lvs)
        assert ls.matched
        assert ls.total_devices_schematic == 120


# ── Metrics Collector Tests ──────────────────────────────────────────────────

class TestMetricsCollector:
    def test_collect_all_metrics_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            am = collect_all_metrics(tmp, "test_design")
            assert am.design_name == "test_design"
            assert am.sta is not None
            assert am.power is None
            assert am.drc is None

    def test_collect_all_metrics_with_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp)

            # DRC
            (rd / "drc_report.txt").write_text("DRC violations: 2\n")

            # LVS
            (rd / "lvs_report_final.txt").write_text("Circuits match uniquely.\n")

            # Power
            (rd / "power_report.txt").write_text("Total 0.00001 0.00002 0.00000 0.00003\n")

            # STA
            (rd / "sta_final.txt").write_text("slack (MET) 5.00\nwns 0.00\ntns 0.00")

            # Netlist
            (rd / "test_design_sky130.v").write_text(
                "sky130_fd_sc_hd__inv_1 sky130_fd_sc_hd__nand2_1\n"
            )

            am = collect_all_metrics(str(rd), "test_design")
            assert am.drc is not None
            assert am.drc.total_violations == 2
            assert am.lvs is not None
            assert am.lvs.matched
            assert am.power is not None
            assert am.sta is not None
            assert "TT" in am.sta.corners
            assert am.cell_count == 2
            assert am.sta.corners["TT"].slack_ns == 5.0


# ── Converter Consistency Tests ──────────────────────────────────────────────

class TestConverterConsistency:
    """Tests that parser outputs convert cleanly to DesignDB types."""

    def test_timing_conversion(self):
        from parsers.sta_parser import convert_to_design_db_timing
        text = "slack (MET) 5.23\nwns 0.00\ntns 0.00"
        summary = parse_sta_report(text)
        td = convert_to_design_db_timing(summary, period_ns=10.0)
        assert td.period_ns == 10.0
        assert "TT" in td.corners
        assert td.corners["TT"].slack_ns == 5.23
        assert td.corners["TT"].met
        assert td.fmax_mhz is not None

    def test_drc_to_design_db(self):
        from parsers.drc_parser import drc_to_design_db
        ds = parse_drc_report("DRC violations: 0\n")
        dc = drc_to_design_db(ds)
        assert dc.violations == 0
        assert dc.categories == {}

    def test_lvs_to_design_db(self):
        from parsers.lvs_parser import lvs_to_design_db
        ls = parse_lvs_report("Circuits match uniquely.\n")
        lc = lvs_to_design_db(ls)
        assert lc.status == "MATCHED"

    def test_congestion_to_design_db(self):
        from parsers.congestion_parser import congestion_to_design_db
        cs = parse_congestion_report("Overflow : 2.5%\n")
        cd = congestion_to_design_db(cs)
        assert cd is not None
        assert cd.h_overflow_pct == 2.5


# ── Edge Case Tests ──────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_sta_malformed_report(self):
        text = "random garbage\nno timing data\n"
        corner = parse_sta_corner(text, "TT")
        assert corner.slack_ns is None

    def test_power_malformed_report(self):
        ps = parse_power_report("not a power report")
        assert ps.total_power_mw is None

    def test_drc_malformed_openroad(self):
        ds = parse_drc_report("no violations here", engine="openroad")
        assert ds.total_violations == 0
        assert ds.clean

    def test_congestion_malformed(self):
        cs = parse_congestion_report("no data here")
        assert not cs.available

    def test_lvs_incomplete_report(self):
        ls = parse_lvs_report("some random text without LVS markers")
        assert ls.status == "INCOMPLETE"
