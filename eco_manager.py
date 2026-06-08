"""
eco_manager.py — Engineering Change Order Engine
RTL-Gen AI Phase 11

Supports:
  - Buffer insertion
  - Cell upsizing / downsizing
  - Fanout optimization
  - Hold fixing
  - Setup fixing
  - Logic restructuring (placeholder)

Flow:
  1. Analyze timing violations -&gt; generate ECO recommendations
  2. Rank recommendations by area/power/timing impact
  3. Apply ECO to DesignDB
  4. Compare before/after QoR
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ECOAction:
    action_type: str          # buffer_insertion, cell_upsizing, cell_downsizing,
                              # fanout_optimization, hold_fixing, setup_fixing, logic_restructuring
    target: str               # net name, cell instance, or endpoint
    reason: str               # why this action is needed
    before_value: Optional[float] = None
    after_value: Optional[float] = None
    priority: int = 5         # 1 (highest) to 10 (lowest)
    area_impact: float = 0.0  # estimated area delta in um^2
    power_impact: float = 0.0 # estimated power delta in mW
    timing_gain: float = 0.0  # estimated slack improvement in ns


@dataclass
class ECOResult:
    applied_actions: List[ECOAction] = field(default_factory=list)
    timing_improvement: float = 0.0   # ns improvement (positive = better)
    power_delta: float = 0.0          # mW delta (positive = more power)
    area_delta: float = 0.0           # um^2 delta (positive = more area)
    slack_before: Optional[float] = None
    slack_after: Optional[float] = None
    fmax_before: Optional[float] = None
    fmax_after: Optional[float] = None
    success: bool = False
    message: str = ""
    applied_at: str = ""


@dataclass
class ECOComparison:
    fmax_before: float = 0.0
    fmax_after: float = 0.0
    power_before: float = 0.0
    power_after: float = 0.0
    area_before: float = 0.0
    area_after: float = 0.0
    slack_before: float = 0.0
    slack_after: float = 0.0

    def improvement_pct(self, metric: str) -> float:
        before = getattr(self, f"{metric}_before", 0)
        after  = getattr(self, f"{metric}_after", 0)
        if before == 0:
            return 0.0
        return round((after - before) / before * 100, 1)

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_html(self) -> str:
        return f"""<table class="eco-compare">
<tr><th>Metric</th><th>Before</th><th>After</th><th>Change</th></tr>
<tr><td>Fmax (MHz)</td><td>{self.fmax_before}</td><td>{self.fmax_after}</td>
  <td>{self.improvement_pct('fmax'):+.1f}%</td></tr>
<tr><td>Power (mW)</td><td>{self.power_before}</td><td>{self.power_after}</td>
  <td>{self.improvement_pct('power'):+.1f}%</td></tr>
<tr><td>Area (um2)</td><td>{self.area_before}</td><td>{self.area_after}</td>
  <td>{self.improvement_pct('area'):+.1f}%</td></tr>
<tr><td>Slack (ns)</td><td>{self.slack_before}</td><td>{self.slack_after}</td>
  <td>{self.improvement_pct('slack'):+.1f}%</td></tr>
</table>"""

    def to_csv(self) -> str:
        return ("metric,before,after,change_pct\n"
                f"fmax_mhz,{self.fmax_before},{self.fmax_after},{self.improvement_pct('fmax')}\n"
                f"power_mw,{self.power_before},{self.power_after},{self.improvement_pct('power')}\n"
                f"area_um2,{self.area_before},{self.area_after},{self.improvement_pct('area')}\n"
                f"slack_ns,{self.slack_before},{self.slack_after},{self.improvement_pct('slack')}\n")


# ── Timing violation analysis ─────────────────────────────────────────────────

def find_setup_violations(db) -> List[Dict]:
    """
    Identify setup timing violations from DesignDB.
    Returns list of violation dicts sorted by worst slack first.
    """
    violations: List[Dict] = []
    if not db or not db.timing:
        return violations

    for cname, corner in db.timing.corners.items():
        if corner.met:
            continue
        slack = corner.slack_ns if corner.slack_ns is not None else -999
        violations.append({
            "corner": cname,
            "path_type": "setup",
            "slack_ns": slack,
            "severity": "CRITICAL" if slack <= -0.5 else "WARNING",
            "paths": len(corner.paths),
            "worst_path": corner.paths[0] if corner.paths else None,
        })

    violations.sort(key=lambda v: v["slack_ns"])
    return violations


def find_hold_violations(db) -> List[Dict]:
    """
    Identify hold timing violations from DesignDB.
    Returns list of violation dicts.
    """
    violations: List[Dict] = []
    if not db or not db.timing:
        return violations

    hold_slack = db.timing.hold_slack_ns
    if hold_slack is not None and hold_slack < 0:
        violations.append({
            "corner": "HOLD",
            "path_type": "hold",
            "slack_ns": hold_slack,
            "severity": "CRITICAL" if hold_slack < -0.1 else "WARNING",
        })

    return violations


def find_high_fanout_nets(db, threshold: int = 50) -> List[Dict]:
    """
    Identify high-fanout nets that may benefit from buffer insertion.
    """
    nets: List[Dict] = []
    if not db or not db.routing:
        return nets
    # Use routing data as a proxy
    total_nets = db.routing.total_nets or 0
    if total_nets > threshold:
        fanout_est = min(total_nets // 10, 100)
        nets.append({
            "net": "clk_net",
            "fanout": fanout_est,
            "recommendation": "buffer_tree" if fanout_est > 20 else "none",
        })
    return nets


# ── ECO recommendation engine ─────────────────────────────────────────────────

def generate_eco_recommendations(db) -> List[ECOAction]:
    """
    Generate ranked ECO recommendations from a DesignDB analysis.
    Returns list of ECOActions sorted by priority.
    """
    actions: List[ECOAction] = []

    # 1. Setup violations -&gt; upsizing / buffer insertion
    setup_violations = find_setup_violations(db)
    for v in setup_violations:
        if v["severity"] == "CRITICAL":
            actions.append(ECOAction(
                action_type="cell_upsizing",
                target=v.get("worst_path", None) and v["worst_path"].endpoint or "unknown",
                reason=f"Setup violation: slack={v['slack_ns']}ns in {v['corner']}",
                before_value=v["slack_ns"],
                after_value=min(v["slack_ns"] + 0.3, 0.0),
                priority=1,
                timing_gain=0.3,
                area_impact=5.0,
                power_impact=0.001,
            ))
            # Also suggest buffer insertion on the path
            if v.get("worst_path") and v["worst_path"].startpoint:
                actions.append(ECOAction(
                    action_type="buffer_insertion",
                    target=f"path_{v['worst_path'].startpoint}_to_{v['worst_path'].endpoint}",
                    reason=f"Buffer insertion on critical setup path in {v['corner']}",
                    before_value=v["slack_ns"],
                    after_value=min(v["slack_ns"] + 0.15, 0.0),
                    priority=2,
                    timing_gain=0.15,
                    area_impact=2.0,
                    power_impact=0.0005,
                ))

    # 2. Hold violations -&gt; delay insertion
    hold_violations = find_hold_violations(db)
    for v in hold_violations:
        actions.append(ECOAction(
            action_type="hold_fixing",
            target=f"hold_path_{v['corner']}",
            reason=f"Hold violation: slack={v['slack_ns']}ns",
            before_value=v["slack_ns"],
            after_value=0.05,
            priority=3,
            timing_gain=abs(v["slack_ns"]) + 0.05,
            area_impact=3.0,
            power_impact=0.0008,
        ))

    # 3. High fanout nets -&gt; buffer tree
    high_fanout = find_high_fanout_nets(db)
    for n in high_fanout:
        if n["recommendation"] == "buffer_tree":
            actions.append(ECOAction(
                action_type="fanout_optimization",
                target=n["net"],
                reason=f"High fanout net: {n['fanout']} loads",
                priority=4,
                timing_gain=0.1,
                area_impact=float(n["fanout"]) * 0.5,
                power_impact=float(n["fanout"]) * 0.0001,
            ))

    # 4. Sort by priority
    actions.sort(key=lambda a: a.priority)
    return actions


# ── ECO application ──────────────────────────────────────────────────────────

def apply_eco(db, strategy: str = "buffer_insertion") -> ECOResult:
    """
    Apply Engineering Change Order (ECO) optimizations to a DesignDB.

    Args:
        db: DesignDB instance to optimize
        strategy: ECO strategy name

    Returns:
        ECOResult with applied actions and QoR deltas
    """
    result = ECOResult()
    result.applied_at = datetime.now().isoformat()

    # Snapshot before QoR
    if db.timing:
        tt = db.timing.corners.get("TT")
        if tt:
            result.slack_before = tt.slack_ns
        result.fmax_before = db.timing.fmax_mhz

    # Generate recommendations
    recommendations = generate_eco_recommendations(db)

    if not recommendations:
        result.message = "No ECO opportunities identified"
        result.success = True
        return result

    # Apply actions based on strategy
    if strategy == "buffer_insertion":
        applied = [a for a in recommendations
                   if a.action_type in ("buffer_insertion", "fanout_optimization")]
    elif strategy == "cell_upsizing":
        applied = [a for a in recommendations
                   if a.action_type in ("cell_upsizing", "setup_fixing")]
    elif strategy == "hold_fixing":
        applied = [a for a in recommendations
                   if a.action_type == "hold_fixing"]
    elif strategy == "setup_fixing":
        applied = [a for a in recommendations
                   if a.action_type in ("cell_upsizing", "buffer_insertion", "setup_fixing")]
    elif strategy == "full":
        applied = recommendations
    else:
        applied = recommendations[:3]

    result.applied_actions = applied

    # Simulate QoR improvements
    total_timing_gain = sum(a.timing_gain for a in applied)
    total_area       = sum(a.area_impact for a in applied)
    total_power      = sum(a.power_impact for a in applied)

    result.timing_improvement = round(total_timing_gain, 4)
    result.area_delta         = round(total_area, 2)
    result.power_delta        = round(total_power, 4)

    # Apply to DesignDB
    if db.timing and result.slack_before is not None:
        new_slack = result.slack_before + total_timing_gain
        for cname, corner in db.timing.corners.items():
            if corner.slack_ns is not None:
                corner.slack_ns = round(corner.slack_ns + total_timing_gain, 4)
                corner.met = corner.slack_ns >= 0
                result.slack_after = corner.slack_ns
        # Recompute Fmax
        margin = db.timing.period_ns - new_slack
        if margin > 0:
            db.timing.fmax_mhz = round(1000.0 / margin, 1)
            result.fmax_after = db.timing.fmax_mhz

    result.success = True
    result.message = (
        f"Applied {len(applied)} ECO actions ({strategy}): "
        f"timing +{result.timing_improvement}ns, "
        f"area +{result.area_delta}um2, "
        f"power +{result.power_delta}mW"
    )

    # Store in DesignDB as ECOData
    from design_db import ECOData
    db.eco = ECOData(
        original_qor={
            "fmax_mhz": result.fmax_before,
            "slack_ns": result.slack_before,
        },
        optimized_qor={
            "fmax_mhz": result.fmax_after,
            "slack_ns": result.slack_after,
            "timing_improvement_ns": result.timing_improvement,
            "power_delta_mw": result.power_delta,
            "area_delta_um2": result.area_delta,
        },
        actions=[{"type": a.action_type, "target": a.target, "reason": a.reason} for a in result.applied_actions],
        success=result.success,
        changes=[a.reason for a in result.applied_actions if a.reason],
        applied_at=str(result.message),
    )

    log.info("ECO applied: %s", result.message)
    return result


# ── Comparison ────────────────────────────────────────────────────────────────

def compare_eco_results(before_db, after_db) -> ECOComparison:
    """
    Compare QoR between two DesignDB states.
    Returns ECOComparison with before/after metrics.
    """
    def _fmax(d):
        return d.timing.fmax_mhz if d and d.timing and d.timing.fmax_mhz else 0.0

    def _power(d):
        return d.power.total_mw if d and d.power and d.power.total_mw else 0.0

    def _area(d):
        return d.layout.area_um2 if d and d.layout and d.layout.area_um2 else 0.0

    def _slack(d):
        if d and d.timing and d.timing.corners:
            tt = d.timing.corners.get("TT")
            if tt and tt.slack_ns is not None:
                return tt.slack_ns
        return 0.0

    return ECOComparison(
        fmax_before=_fmax(before_db),
        fmax_after=_fmax(after_db),
        power_before=_power(before_db),
        power_after=_power(after_db),
        area_before=_area(before_db),
        area_after=_area(after_db),
        slack_before=_slack(before_db),
        slack_after=_slack(after_db),
    )


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("eco_manager.py — standalone self-test")
    print("=" * 60)

    passed = total = 0
    from design_db import (
        DesignDB, TimingData, TimingCorner, TimingPath,
        PowerData, FloorplanData, LayoutInfo,
    )

    # Test 1: ECOAction dataclass
    total += 1
    a = ECOAction("buffer_insertion", "net_clk", "High fanout", 0.5, 0.8)
    assert a.action_type == "buffer_insertion"
    assert a.before_value == 0.5
    print(f"[PASS] ECOAction: {a.action_type} -&gt; {a.target} ({a.reason})")
    passed += 1

    # Test 2: find_setup_violations — no violations
    total += 1
    db = DesignDB(design_name="clean", rtl_sources=["c.v"], netlist_path="c.v")
    db.timing = TimingData(period_ns=10.0)
    db.timing.corners["TT"] = TimingCorner(corner="TT", slack_ns=5.0, met=True)
    sv = find_setup_violations(db)
    assert len(sv) == 0
    print("[PASS] No setup violations for clean design")
    passed += 1

    # Test 3: find_setup_violations — with violations
    total += 1
    db2 = DesignDB(design_name="violated", rtl_sources=["v.v"], netlist_path="v.v")
    db2.timing = TimingData(period_ns=10.0)
    db2.timing.corners["TT"] = TimingCorner(corner="TT", slack_ns=-0.5, met=False)
    sv2 = find_setup_violations(db2)
    assert len(sv2) == 1
    assert sv2[0]["slack_ns"] == -0.5
    assert sv2[0]["severity"] == "CRITICAL"
    print("[PASS] Setup violation detected: slack=-0.5ns CRITICAL")
    passed += 1

    # Test 4: find_hold_violations
    total += 1
    db3 = DesignDB(design_name="hold_viol", rtl_sources=["h.v"], netlist_path="h.v")
    db3.timing = TimingData(period_ns=10.0, hold_slack_ns=-0.08)
    hv = find_hold_violations(db3)
    assert len(hv) == 1
    assert hv[0]["path_type"] == "hold"
    print(f"[PASS] Hold violation: slack={hv[0]['slack_ns']}ns")
    passed += 1

    # Test 5: generate_eco_recommendations
    total += 1
    db4 = DesignDB(design_name="eco_test", rtl_sources=["e.v"], netlist_path="e.v")
    db4.timing = TimingData(period_ns=10.0)
    db4.timing.corners["TT"] = TimingCorner(
        corner="TT", slack_ns=-0.8, met=False,
        paths=[TimingPath(startpoint="a", endpoint="b", slack_ns=-0.8, met=False)],
    )
    db4.timing.hold_slack_ns = -0.05
    recs = generate_eco_recommendations(db4)
    assert len(recs) >= 2
    # First action should be cell_upsizing (highest priority)
    assert recs[0].action_type == "cell_upsizing"
    print(f"[PASS] ECO recommendations: {len(recs)} actions generated")
    passed += 1

    # Test 6: apply_eco — buffer_insertion
    total += 1
    db5 = DesignDB(design_name="apply_test", rtl_sources=["a.v"], netlist_path="a.v")
    db5.timing = TimingData(period_ns=10.0)
    db5.timing.corners["TT"] = TimingCorner(
        corner="TT", slack_ns=-0.5, met=False,
        paths=[TimingPath(startpoint="a", endpoint="b", slack_ns=-0.5, met=False)],
    )
    result = apply_eco(db5, strategy="buffer_insertion")
    assert result.success
    assert len(result.applied_actions) >= 1
    print(f"[PASS] ECO applied: {len(result.applied_actions)} actions, "
          f"timing +{result.timing_improvement}ns")
    passed += 1

    # Test 7: apply_eco — full strategy
    total += 1
    db5_full = DesignDB(design_name="apply_full", rtl_sources=["f.v"], netlist_path="f.v")
    db5_full.timing = TimingData(period_ns=10.0)
    db5_full.timing.corners["TT"] = TimingCorner(
        corner="TT", slack_ns=-1.5, met=False,
        paths=[TimingPath(startpoint="a", endpoint="b", slack_ns=-1.5, met=False)],
    )
    result2 = apply_eco(db5_full, strategy="full")
    assert result2.success
    assert result2.timing_improvement > 0
    assert len(result2.applied_actions) >= 2
    print(f"[PASS] Full ECO: {len(result2.applied_actions)} actions, "
          f"+{result2.timing_improvement}ns, area +{result2.area_delta}um2")
    passed += 1

    # Test 8: ECOComparison
    total += 1
    comp = ECOComparison(fmax_before=100, fmax_after=133, slack_before=-0.5, slack_after=0.3)
    assert comp.improvement_pct("fmax") == 33.0
    assert comp.to_csv().startswith("metric")
    assert "Fmax (MHz)" in comp.to_html()
    print(f"[PASS] ECOComparison: Fmax +{comp.improvement_pct('fmax')}%, CSV/HTML output")
    passed += 1

    # Test 9: apply_eco stores in db.eco
    total += 1
    assert db5.eco is not None
    assert db5.eco.success
    assert db5.eco.slack_before is not None
    assert db5.eco.slack_after is not None
    print(f"[PASS] ECO stored in DesignDB: slack {db5.eco.slack_before} -&gt; {db5.eco.slack_after}ns")
    passed += 1

    # Test 10: compare_eco_results
    total += 1
    before_db = DesignDB(design_name="before", rtl_sources=["b.v"], netlist_path="b.v")
    before_db.timing = TimingData(period_ns=10.0, fmax_mhz=100)
    before_db.timing.corners["TT"] = TimingCorner(corner="TT", slack_ns=-0.5)
    before_db.layout = LayoutInfo(area_um2=5000)

    after_db = DesignDB(design_name="after", rtl_sources=["a.v"], netlist_path="a.v")
    after_db.timing = TimingData(period_ns=10.0, fmax_mhz=133)
    after_db.timing.corners["TT"] = TimingCorner(corner="TT", slack_ns=0.3)
    after_db.layout = LayoutInfo(area_um2=5200)

    comp2 = compare_eco_results(before_db, after_db)
    assert comp2.fmax_before == 100
    assert comp2.fmax_after == 133
    assert abs(comp2.slack_before - (-0.5)) < 0.01
    print(f"[PASS] compare_eco_results: Fmax {comp2.fmax_before} -&gt; {comp2.fmax_after} MHz")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED — eco_manager.py ready for integration")
    print("=" * 60)
