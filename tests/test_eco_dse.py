"""
Integration tests for ECO Engine and Design Space Exploration (Phase 11)
RTL-Gen AI — validates end-to-end ECO + DSE flows.
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from design_db import (
    DesignDB,
    TimingData,
    TimingCorner,
    TimingPath,
    PowerData,
    CongestionData,
    ECOData,
    DSEData,
    save_design_db,
    load_design_db,
)
from eco_manager import (
    ECOAction,
    ECOResult,
    apply_eco,
    find_setup_violations,
    find_hold_violations,
    generate_eco_recommendations,
    compare_eco_results,
    ECOComparison,
)
from dse_engine import (
    DSEPoint,
    DSEResult,
    run_design_space_exploration,
    generate_pareto_frontier,
    render_pareto_chart,
    simulate_point,
)


# ═══════════════════════════════════════════════════════════════════════════
# ECO Tests
# ═══════════════════════════════════════════════════════════════════════════

def make_test_db(
    slack_ns: float = -0.5,
    hold_slack: float = 0.0,
    fmax_mhz: float = 100.0,
    period_ns: float = 10.0,
) -> DesignDB:
    db = DesignDB(
        design_name="eco_test",
        rtl_sources=["eco_test.v"],
        netlist_path="eco_test.v",
    )
    db.timing = TimingData(
        period_ns=period_ns,
        fmax_mhz=fmax_mhz,
        hold_slack_ns=hold_slack,
        corners={
            "TT": TimingCorner(
                corner="TT",
                slack_ns=slack_ns,
                met=(slack_ns >= 0),
                paths=[
                    TimingPath(
                        startpoint="a",
                        endpoint="b",
                        slack_ns=slack_ns,
                        met=(slack_ns >= 0),
                    )
                ],
            )
        },
    )
    return db


class TestECO:
    """ECO Engine integration tests."""

    def test_buffer_insertion_eco(self):
        db = make_test_db(slack_ns=-0.5)
        result = apply_eco(db, strategy="buffer_insertion")
        assert result.success
        assert len(result.applied_actions) >= 1
        assert any(a.action_type == "buffer_insertion" for a in result.applied_actions)
        assert result.timing_improvement > 0

    def test_cell_upsizing_eco(self):
        db = make_test_db(slack_ns=-1.2)
        result = apply_eco(db, strategy="cell_upsizing")
        assert result.success
        assert any(a.action_type == "cell_upsizing" for a in result.applied_actions)
        assert result.area_delta > 0

    def test_hold_fixing_eco(self):
        db = make_test_db(slack_ns=0.5, hold_slack=-0.12)
        result = apply_eco(db, strategy="hold_fixing")
        assert result.success
        assert len(result.applied_actions) >= 1
        assert any(a.action_type == "hold_fixing" for a in result.applied_actions)

    def test_setup_fixing_eco(self):
        db = make_test_db(slack_ns=-1.0)
        result = apply_eco(db, strategy="setup_fixing")
        assert result.success
        assert len(result.applied_actions) >= 1
        assert any(a.action_type in ("cell_upsizing", "buffer_insertion")
                   for a in result.applied_actions)

    def test_find_setup_violations(self):
        db_clean = make_test_db(slack_ns=5.0)
        assert len(find_setup_violations(db_clean)) == 0

        db_viol = make_test_db(slack_ns=-0.8)
        viol = find_setup_violations(db_viol)
        assert len(viol) == 1
        assert viol[0]["severity"] == "CRITICAL"

    def test_find_hold_violations(self):
        db_clean = make_test_db(hold_slack=0.05)
        assert len(find_hold_violations(db_clean)) == 0

        db_viol = make_test_db(hold_slack=-0.08)
        viol = find_hold_violations(db_viol)
        assert len(viol) == 1
        assert viol[0]["path_type"] == "hold"

    def test_generate_recommendations(self):
        db = make_test_db(slack_ns=-1.5, hold_slack=-0.1)
        recs = generate_eco_recommendations(db)
        assert len(recs) >= 2

    def test_eco_comparison_report(self):
        before = make_test_db(slack_ns=-0.5, fmax_mhz=100)
        after = make_test_db(slack_ns=0.3, fmax_mhz=133)
        comp = compare_eco_results(before, after)
        assert comp.fmax_before == 100
        assert comp.fmax_after == 133
        assert comp.slack_before == -0.5
        assert comp.improvement_pct("fmax") == 33.0
        html = comp.to_html()
        assert "Fmax (MHz)" in html
        csv = comp.to_csv()
        assert csv.startswith("metric")


# ═══════════════════════════════════════════════════════════════════════════
# DSE Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDSE:
    """Design Space Exploration integration tests."""

    def test_dse_point_dataclass(self):
        pt = DSEPoint(
            clock_period_ns=5.0,
            utilization_pct=60,
            placement_density=0.65,
            fmax_mhz=200,
            area_um2=1500,
            power_mw=12.5,
            congestion_score=0.15,
        )
        d = pt.to_dict()
        assert d["clock_period_ns"] == 5.0
        assert d["fmax_mhz"] == 200
        assert d["is_pareto"] is False

    def test_simulate_point(self):
        qor = simulate_point(5.0, 60, 0.65)
        for key in ("fmax_mhz", "area_um2", "power_mw", "congestion_score", "slack_ns"):
            assert key in qor
        assert qor["fmax_mhz"] > 0

    def test_dse_generation(self):
        result = run_design_space_exploration()
        # 5 clock periods * 4 utilizations * 3 densities = 60 points
        assert len(result.points) == 60
        assert result.best_fmax is not None
        assert result.best_area is not None
        assert result.best_power is not None
        assert result.best_balanced is not None
        assert result.generated_at != ""

    def test_pareto_frontier(self):
        pts = [
            DSEPoint(5, 60, 0.65, fmax_mhz=200, area_um2=1000, power_mw=10, congestion_score=0.1),
            DSEPoint(4, 60, 0.65, fmax_mhz=250, area_um2=900,  power_mw=8,  congestion_score=0.08),
            DSEPoint(6, 60, 0.65, fmax_mhz=180, area_um2=1100, power_mw=12, congestion_score=0.12),
        ]
        frontier = generate_pareto_frontier(pts)
        assert len(frontier) >= 1
        assert frontier[0].fmax_mhz == 250

    def test_best_selection(self):
        result = run_design_space_exploration()
        assert result.best_fmax.fmax_mhz >= result.best_area.fmax_mhz
        assert result.best_area.area_um2 <= result.best_fmax.area_um2

    def test_dse_full_exploration_with_baseline(self):
        db = make_test_db(slack_ns=2.0, fmax_mhz=200)
        result = run_design_space_exploration(db)
        assert len(result.points) == 60
        assert result.best_fmax is not None

    def test_pareto_chart_renders(self):
        result = run_design_space_exploration()
        fig = render_pareto_chart(result, "area_um2", "fmax_mhz", "Test Chart")
        assert fig is not None
        # Should have at least 3 traces (non-pareto, pareto, + best highlights)
        assert len(fig.data) >= 4


# ═══════════════════════════════════════════════════════════════════════════
# DesignDB Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDesignDBIntegration:
    """DesignDB ECO/DSE persistence and migration tests."""

    def test_eco_serialization(self):
        db = DesignDB(
            design_name="eco_ser",
            rtl_sources=["e.v"],
            netlist_path="e.v",
        )
        db.eco = ECOData(
            original_qor={"fmax_mhz": 100.0, "power_mw": 10.0, "area_um2": 5000},
            optimized_qor={"fmax_mhz": 133.0, "power_mw": 10.5, "area_um2": 5200},
            actions=[{"action_type": "buffer_insertion", "target": "clk"}],
            success=True,
            applied_at="2026-01-15T12:00:00",
        )
        d = db.to_dict()
        assert "eco" in d
        assert d["eco"]["success"]
        db2 = DesignDB.from_dict(d)
        assert db2.eco is not None
        assert db2.eco.success
        assert len(db2.eco.actions) == 1

    def test_dse_serialization(self):
        db = DesignDB(
            design_name="dse_ser",
            rtl_sources=["d.v"],
            netlist_path="d.v",
        )
        db.dse = DSEData(
            points=[
                {"clock_period_ns": 5.0, "utilization_pct": 60, "fmax_mhz": 200},
                {"clock_period_ns": 10.0, "utilization_pct": 80, "fmax_mhz": 100},
            ],
            best_fmax={"clock_period_ns": 5.0, "fmax_mhz": 200},
            pareto_frontier_indices=[0],
            generated_at="2026-01-15T12:00:00",
        )
        d = db.to_dict()
        assert "dse" in d
        assert d["dse"]["best_fmax"]["fmax_mhz"] == 200
        db2 = DesignDB.from_dict(d)
        assert db2.dse is not None
        assert len(db2.dse.points) == 2

    def test_json_file_roundtrip(self):
        db = DesignDB(
            design_name="json_rt",
            rtl_sources=["j.v"],
            netlist_path="j.v",
        )
        db.eco = ECOData(
            original_qor={"fmax_mhz": 100.0},
            optimized_qor={"fmax_mhz": 133.0},
            actions=[],
            success=True,
        )
        db.dse = DSEData(
            points=[{"clock_period_ns": 5.0, "fmax_mhz": 200}],
            best_fmax={"fmax_mhz": 200},
            exploration_params={"total_configs": 48},
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "eco_dse_db.json"
            save_design_db(db, p)
            assert p.exists()
            loaded = load_design_db(p)
            assert loaded.eco is not None
            assert loaded.eco.success
            assert loaded.dse is not None
            assert loaded.dse.best_fmax["fmax_mhz"] == 200

    def test_migration_v1_0_to_v1_2(self):
        v10 = {
            "schema_version": "1.0",
            "design_name": "legacy_v10",
            "rtl_sources": ["l.v"],
            "netlist_path": "l.v",
            "timing": {"period_ns": 10.0, "fmax_mhz": 100},
        }
        db = DesignDB.from_dict(v10)
        assert db.schema_version == "1.2"
        assert db.timing is not None
        assert db.timing.fmax_mhz == 100
        assert db.eco is None
        assert db.dse is None

    def test_migration_v1_1_to_v1_2(self):
        v11 = {
            "schema_version": "1.1",
            "design_name": "legacy_v11",
            "rtl_sources": ["l.v"],
            "netlist_path": "l.v",
            "power": {"total_mw": 0.05},
        }
        db = DesignDB.from_dict(v11)
        assert db.schema_version == "1.2"
        assert db.power is not None
        assert abs(db.power.total_mw - 0.05) < 0.001
        assert db.eco is None
        assert db.dse is None
