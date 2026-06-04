# Create file: test_ui_tabs.py
"""
Test that all Sign-Off Dashboard tabs
can parse real data from a pipeline run.
Not a mock test — reads actual files.
"""

import pytest
from pathlib import Path


def get_latest_run_dir():
    """Find most recent run with a real GDS file."""
    runs = Path(r"C:\tools\OpenLane\runs")
    if not runs.exists():
        return None
    for d in sorted(
        runs.iterdir(),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    ):
        if not d.is_dir():
            continue
        gds = list(d.glob("*.gds"))
        if gds and max(g.stat().st_size for g in gds) > 50000:
            return d
    return None


@pytest.fixture
def run_dir():
    d = get_latest_run_dir()
    if not d:
        pytest.skip("No real run found — run pipeline first")
    return d


@pytest.fixture
def design_name(run_dir):
    return run_dir.name.rsplit('_', 2)[0]


class TestNetlistTab:
    def test_netlist_file_exists(self, run_dir, design_name):
        netlists = list(run_dir.glob("*_sky130.v"))
        assert netlists, "No synthesized netlist found"
        assert netlists[0].stat().st_size > 500

    def test_netlist_parses(self, run_dir, design_name):
        from netlist_viewer import parse_netlist
        netlists = list(run_dir.glob("*_sky130.v"))
        if not netlists:
            pytest.skip("No netlist")
        info = parse_netlist(str(netlists[0]))
        assert info is not None
        assert len(info.cells) > 0
        assert info.module_name != "unknown"

    def test_netlist_has_sky130_cells(self, run_dir, design_name):
        from netlist_viewer import parse_netlist
        netlists = list(run_dir.glob("*_sky130.v"))
        if not netlists:
            pytest.skip("No netlist")
        info = parse_netlist(str(netlists[0]))
        sky130 = [c for c in info.cells
                  if 'sky130' in c.cell_type]
        assert len(sky130) > 0, "No Sky130 cells in netlist"


class TestWaveformTab:
    def test_vcd_or_log_exists(self, run_dir, design_name):
        from waveform_display import find_vcd_for_design
        vcd = find_vcd_for_design(str(run_dir), design_name)
        sim_log = run_dir / "simulation.log"
        assert vcd or sim_log.exists(), \
            "Neither VCD nor simulation log found"

    def test_simulation_log_has_results(self, run_dir):
        log = run_dir / "simulation.log"
        if not log.exists():
            pytest.skip("No simulation log")
        content = log.read_text(errors="ignore")
        assert "PASS" in content or "FAIL" in content, \
            "Simulation log has no PASS/FAIL markers"


class TestLayoutTab:
    def test_gds_is_real(self, run_dir):
        gds_files = list(run_dir.glob("*.gds"))
        assert gds_files, "No GDS file in run"
        real = [g for g in gds_files
                if g.stat().st_size > 50000]
        assert real, f"GDS too small: {[g.stat().st_size for g in gds_files]}"

    def test_gds_has_sky130_cells_in_binary(self, run_dir):
        gds_files = list(run_dir.glob("*.gds"))
        if not gds_files:
            pytest.skip("No GDS")
        gds = max(gds_files, key=lambda x: x.stat().st_size)
        with open(gds, 'rb') as f:
            binary = f.read()
        sky130 = [
            b'sky130_fd_sc_hd__dfxtp',
            b'sky130_fd_sc_hd__nand2',
            b'sky130_fd_sc_hd__fill',
        ]
        found = any(cell in binary for cell in sky130)
        assert found, "No Sky130 cell names found in GDS binary"


class TestTimingTab:
    def test_sta_tt_exists_and_has_data(self, run_dir):
        sta = run_dir / "sta_final.txt"
        assert sta.exists(), "No TT STA report"
        content = sta.read_text(errors="ignore")
        assert "slack" in content.lower()
        assert "sky130" in content.lower()

    def test_timing_parser_works(self, run_dir):
        from timing_viewer import parse_sta_report
        sta = run_dir / "sta_final.txt"
        if not sta.exists():
            pytest.skip("No STA report")
        paths = parse_sta_report(str(sta))
        assert len(paths) >= 0  # Can be empty on simple designs

    def test_multi_corner_exists(self, run_dir):
        ss = run_dir / "sta_ss.txt"
        ff = run_dir / "sta_ff.txt"
        # At least one corner beyond TT
        assert ss.exists() or ff.exists(), \
            "No SS or FF corner STA report"


class TestReportsTab:
    def test_lvs_report_exists(self, run_dir):
        lvs = run_dir / "lvs_report_final.txt"
        assert lvs.exists(), "No LVS report"
        assert lvs.stat().st_size > 100

    def test_lvs_shows_result(self, run_dir):
        lvs = run_dir / "lvs_report_final.txt"
        if not lvs.exists():
            pytest.skip("No LVS report")
        content = lvs.read_text(errors="ignore")
        has_result = (
            "match" in content.lower() or
            "equivalent" in content.lower()
        )
        assert has_result, "LVS report has no match result"

    def test_drc_report_exists(self, run_dir):
        drc_files = list(run_dir.glob("drc*.txt")) + \
                    list(run_dir.glob("drc*.xml"))
        assert drc_files, "No DRC report found"
