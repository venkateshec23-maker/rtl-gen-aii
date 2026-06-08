"""
congestion_enhanced.py — Routing Congestion Analysis & Heatmap
RTL-Gen AI v2.5 — PrimeTime/Cadence-style congestion visualization

Features:
  ├── Parse OpenROAD congestion report  (route_congestion + design_area)
  ├── Interactive Plotly heatmap (simulated grid from overflow/% density)
  ├── Metric gauges for H overflow, V overflow, max density, utilization
  ├── Streamlit renderer with tabbed views
  ├── Standalone self-test with synthetic data

Usage in app.py (Sign-Off → Congestion):
    from congestion_enhanced import render_congestion_enhanced_streamlit
    render_congestion_enhanced_streamlit(results_dir)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import plotly.graph_objects as go

from parsers.congestion_parser import parse_congestion_report, CongestionSummary

log = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class CongestionResult:
    h_overflow_pct:  Optional[float] = None
    v_overflow_pct:  Optional[float] = None
    max_density_pct: Optional[float] = None
    utilization_pct: Optional[float] = None
    total_nets:      Optional[int] = None
    unrouted_nets:   int = 0
    h_congestion_grid: Optional[list] = None
    v_congestion_grid: Optional[list] = None
    grid_data:       Optional[list] = None

    def has_data(self) -> bool:
        return any(v is not None for v in
                   [self.h_overflow_pct, self.v_overflow_pct, self.max_density_pct])

    def score(self) -> float:
        """Composite congestion score 0-100 (0=perfect)."""
        s = 0.0
        if self.h_overflow_pct is not None:
            s += min(self.h_overflow_pct * 10, 40)
        if self.v_overflow_pct is not None:
            s += min(self.v_overflow_pct * 10, 40)
        if self.max_density_pct is not None:
            s += max(0, (self.max_density_pct - 50) * 0.5)
        return round(min(s, 100), 1)


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_congestion_data(results_dir: Path) -> CongestionResult:
    """Read congestion data from a results directory.
    Tries multiple possible report file locations.
    """
    candidates = [
        results_dir / "congestion_report.txt",
        results_dir / "routing" / "congestion.rpt",
        results_dir / "reports" / "congestion.rpt",
    ]
    for c in candidates:
        if c.exists() and c.stat().st_size > 50:
            text = c.read_text(errors="replace")
            result = _parse_congestion_text(text)
            if result.has_data():
                return result

    # Fallback: try to extract from run.db / database
    return CongestionResult()


def _parse_congestion_text(text: str) -> CongestionResult:
    """Parse OpenROAD congestion report text.
    Delegates to parsers.congestion_parser and converts to CongestionResult.
    """
    cs = parse_congestion_report(text)
    result = CongestionResult(
        h_overflow_pct=cs.h_overflow_pct,
        v_overflow_pct=cs.v_overflow_pct,
        max_density_pct=cs.max_density_pct,
        utilization_pct=cs.utilization_pct,
        total_nets=cs.total_nets,
        unrouted_nets=cs.unrouted_nets,
    )

    # Parse per-layer routing congestion grid (OpenROAD detailed routing)
    h_grid = _parse_routing_grid(text, "H")
    v_grid = _parse_routing_grid(text, "V")
    if h_grid:
        result.h_congestion_grid = h_grid
    if v_grid:
        result.v_congestion_grid = v_grid
    if h_grid or v_grid:
        result.grid_data = h_grid or v_grid

    return result


def _parse_routing_grid(text: str, direction: str) -> Optional[list]:
    """Parse per-direction routing congestion grid from OpenROAD report.
    Looks for tabular congestion data like:
      Layer 1: cap=xx used=xx overflow=xx
    or grid rows of density values.
    """
    rows = []
    grid_section = False
    for line in text.splitlines():
        l = line.strip()
        if f"{direction} congestion" in l.lower() or f"{direction} routing" in l.lower():
            grid_section = True
            continue
        if grid_section and l.startswith(("V congestion", "Layer", "---")):
            if l.startswith("V") and direction == "H":
                break
            if l.startswith("H") and direction == "V":
                break
            continue
        if grid_section:
            nums = re.findall(r"[\d.]+", l)
            if len(nums) >= 3:
                row = [float(x) for x in nums[:max(1, len(nums) // 2)]]
                rows.append(row)
            elif not nums and l:
                grid_section = False
    if rows:
        return rows
    return None


# ── Heatmap generation ─────────────────────────────────────────────────────────

def _build_congestion_heatmap(result: CongestionResult, grid_size: int = 16) -> go.Figure:
    """Build a congestion heatmap from real routing data when available,
    falling back to a density-based representation from aggregate metrics.
    """
    import numpy as np

    h_ov = result.h_overflow_pct or 0.0
    v_ov = result.v_overflow_pct or 0.0
    base = result.max_density_pct or 40.0

    if hasattr(result, 'grid_data') and result.grid_data is not None:
        grid = np.array(result.grid_data)
    elif hasattr(result, 'h_congestion_grid') and result.h_congestion_grid:
        grid = np.array(result.h_congestion_grid)
    else:
        np.random.seed(42)
        grid = np.ones((grid_size, grid_size)) * (base / 100.0)
        rng = np.random.default_rng(42)
        noise = rng.normal(0, 0.05, (grid_size, grid_size))
        grid = np.clip(grid + noise, 0.05, 0.95)

        h_sev = int(round(h_ov * grid_size * 3))
        v_sev = int(round(v_ov * grid_size * 3))
        for _ in range(h_sev):
            ri = rng.integers(0, grid_size)
            ci = rng.integers(0, grid_size)
            grid[ri, ci] = min(grid[ri, ci] + rng.uniform(0.05, 0.25), 1.0)
        for _ in range(v_sev):
            ri = rng.integers(0, grid_size)
            ci = rng.integers(0, grid_size)
            grid[ri, ci] = min(grid[ri, ci] + rng.uniform(0.05, 0.25), 1.0)

    fig = go.Figure(data=go.Heatmap(
        z=grid,
        colorscale=[
            [0.0, "#1a3a1a"],
            [0.3, "#2e7d32"],
            [0.5, "#f9a825"],
            [0.7, "#e65100"],
            [0.85, "#c62828"],
            [1.0, "#b71c1c"],
        ],
        zmin=0.0, zmax=1.0,
        hovertemplate="X: %{x}<br>Y: %{y}<br>Density: %{z:.1%}<extra></extra>",
        colorbar=dict(title=dict(text="Density", side="right"), len=0.8),
    ))
    fig.update_layout(
        title=f"Routing Congestion Heatmap (score={result.score():.1f})",
        xaxis=dict(showticklabels=False, gridcolor="#30363d", title=""),
        yaxis=dict(showticklabels=False, gridcolor="#30363d", title="", autorange="reversed"),
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        font=dict(family="Share Tech Mono", color="#c9d1d9", size=9),
        height=500,
        margin=dict(l=20, r=60, t=40, b=20),
    )
    return fig


def _build_gauge(value: Optional[float], title: str, max_val: float = 100.0, green_until: float = 10.0) -> go.Figure:
    """Build a single gauge chart for a congestion metric."""
    v = value if value is not None else 0
    color = "#00ff9d" if v <= green_until else "#ffd700" if v <= green_until * 2 else "#ff3333"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=v,
        number=dict(suffix="%", font=dict(color=color, size=24)),
        title=dict(text=title, font=dict(color="#8b949e", size=12)),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor="#8b949e", ticklen=4),
            bar=dict(color=color, thickness=0.4),
            bgcolor="#1c2128",
            borderwidth=1, bordercolor="#30363d",
            steps=[
                dict(range=[0, green_until], color="rgba(0,255,157,0.1)"),
                dict(range=[green_until, green_until * 2], color="rgba(255,215,0,0.1)"),
                dict(range=[green_until * 2, max_val], color="rgba(255,51,51,0.1)"),
            ],
        ),
    ))
    fig.update_layout(
        paper_bgcolor="#0d1117", font=dict(family="Share Tech Mono", color="#c9d1d9"),
        height=200, margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


# ── Streamlit renderer ─────────────────────────────────────────────────────────

def render_congestion_enhanced_streamlit(results_dir: Path) -> None:
    """Render congestion analysis in Streamlit."""
    import streamlit as st

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ ROUTING CONGESTION ANALYSIS
    </div>""", unsafe_allow_html=True)

    result = parse_congestion_data(results_dir)

    if not result.has_data():
        st.info("No congestion report data available. Run the full RTL→GDS flow first.")
        return

    # ── Summary metrics ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    def _m(col, label, value, fmt=".2f"):
        v_str = f"{value:{fmt}}%" if value is not None else "—"
        col.metric(label, v_str)

    _m(c1, "H Overflow", result.h_overflow_pct)
    _m(c2, "V Overflow", result.v_overflow_pct)
    _m(c3, "Max Density", result.max_density_pct, ".1f")
    _m(c4, "Utilization", result.utilization_pct, ".1f")

    extra1, extra2 = st.columns(2)
    extra1.metric("Unrouted Nets", result.unrouted_nets)
    extra2.metric("Congestion Score", f"{result.score():.1f} / 100")

    # ── Heatmap + Gauges tabs ────────────────────────────────────────
    tab_hm, tab_ga = st.tabs(["🗺️ Heatmap", "📊 Gauges"])

    with tab_hm:
        fig = _build_congestion_heatmap(result)
        st.plotly_chart(fig, use_container_width=True)

        if result.grid_data is not None:
            st.caption(
                "Heatmap from real routing congestion data. "
                "Red regions indicate high routing density/overflow."
            )
        else:
            st.caption(
                "Heatmap approximated from aggregate congestion metrics. "
                "Red regions indicate high routing density/overflow."
            )

    with tab_ga:
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.plotly_chart(
                _build_gauge(result.h_overflow_pct, "H Overflow", max_val=20.0, green_until=2.0),
                use_container_width=True,
            )
        with g2:
            st.plotly_chart(
                _build_gauge(result.v_overflow_pct, "V Overflow", max_val=20.0, green_until=2.0),
                use_container_width=True,
            )
        with g3:
            st.plotly_chart(
                _build_gauge(result.max_density_pct, "Max Density", max_val=100.0, green_until=60.0),
                use_container_width=True,
            )
        with g4:
            st.plotly_chart(
                _build_gauge(result.utilization_pct, "Utilization", max_val=100.0, green_until=50.0),
                use_container_width=True,
            )

    # ── Guidance ─────────────────────────────────────────────────────
    score = result.score()
    if score < 10:
        st.success("Congestion is low. No routing issues expected.")
    elif score < 30:
        st.warning("Moderate congestion. Consider adjusting core utilization or adding routing layers.")
    else:
        st.error(f"High congestion (score={score:.1f}). Increase die area or reduce cell density.")


def render_congestion_from_db(db) -> None:
    """Render congestion data from a DesignDB instance (no file I/O)."""
    import streamlit as st

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ ROUTING CONGESTION — FROM DESIGN DATABASE
    </div>""", unsafe_allow_html=True)

    if not db.congestion:
        st.info("No congestion data in DesignDB.")
        return

    c = db.congestion
    col1, col2, col3, col4 = st.columns(4)
    def _m(col, label, val, fmt=".2f"):
        col.metric(label, f"{val:{fmt}}%" if val is not None else "—")
    _m(col1, "H Overflow", c.h_overflow_pct)
    _m(col2, "V Overflow", c.v_overflow_pct)
    _m(col3, "Max Density", c.max_density_pct, ".1f")
    _m(col4, "Utilization", c.utilization_pct, ".1f")

    c1, c2 = st.columns(2)
    c1.metric("Unrouted Nets", c.unrouted_nets)
    c2.metric("Score", f"{c.score:.1f}" if c.score is not None else "—")

    fig = _build_congestion_heatmap(
        CongestionResult(
            h_overflow_pct=c.h_overflow_pct,
            v_overflow_pct=c.v_overflow_pct,
            max_density_pct=c.max_density_pct,
            utilization_pct=c.utilization_pct,
            unrouted_nets=c.unrouted_nets,
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    s = c.score or 0
    if s < 10:
        st.success("Low congestion.")
    elif s < 30:
        st.warning("Moderate congestion.")
    else:
        st.error(f"High congestion ({s:.1f}).")


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("congestion_enhanced.py — standalone self-test")
    print("=" * 60)

    passed = total = 0

    # Test 1: parse congested report
    total += 1
    text1 = """
=== CONGESTION START ===
H overflow  : 2 (0.05%)
V overflow  : 5 (0.12%)
Max H density  : 52.30%
Max V density  : 48.10%
Design area 3460.00 um^2 30.20% utilization.
=== CONGESTION END ===
"""
    r = _parse_congestion_text(text1)
    assert r.h_overflow_pct == 0.05, f"H overflow: {r.h_overflow_pct}"
    assert r.v_overflow_pct == 0.12, f"V overflow: {r.v_overflow_pct}"
    assert r.max_density_pct == 52.30, f"Max density: {r.max_density_pct}"
    assert r.utilization_pct == 30.20, f"Utilization: {r.utilization_pct}"
    print(f"[PASS] Parsed congestion: H={r.h_overflow_pct}% V={r.v_overflow_pct}% Max={r.max_density_pct}% Util={r.utilization_pct}%")
    passed += 1

    # Test 2: parse clean report
    total += 1
    text2 = """
=== CONGESTION START ===
H overflow  : 0 (0.00%)
V overflow  : 0 (0.00%)
Max H density  : 35.10%
Max V density  : 32.80%
Design area 3460.00 um^2 28.50% utilization.
=== CONGESTION END ===
"""
    r2 = _parse_congestion_text(text2)
    assert r2.h_overflow_pct == 0.0
    assert r2.v_overflow_pct == 0.0
    assert abs(r2.max_density_pct - 35.10) < 0.1
    print(f"[PASS] Clean report parsed: H={r2.h_overflow_pct}% V={r2.v_overflow_pct}%")
    passed += 1

    # Test 3: empty text
    total += 1
    r3 = _parse_congestion_text("No data")
    assert not r3.has_data()
    print("[PASS] Empty text handled")
    passed += 1

    # Test 4: heatmap figure builds
    total += 1
    fig_hm = _build_congestion_heatmap(r)
    assert isinstance(fig_hm, go.Figure)
    assert len(fig_hm.data) > 0
    print("[PASS] Heatmap figure built")
    passed += 1

    # Test 5: gauge figure builds
    total += 1
    fig_ga = _build_gauge(25.0, "Test Gauge")
    assert isinstance(fig_ga, go.Figure)
    print("[PASS] Gauge figure built")
    passed += 1

    # Test 6: score calculation
    total += 1
    cr = CongestionResult(h_overflow_pct=0.0, v_overflow_pct=0.0, max_density_pct=35.0)
    assert cr.score() < 10, f"Score too high: {cr.score()}"
    cr_bad = CongestionResult(h_overflow_pct=5.0, v_overflow_pct=3.0, max_density_pct=85.0)
    assert cr_bad.score() > 40, f"Bad score too low: {cr_bad.score()}"
    print(f"[PASS] Score: good={cr.score()} bad={cr_bad.score()}")
    passed += 1

    # Test 7: file-based parse
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "congestion_report.txt"
        p.write_text(text1)
        rf = parse_congestion_data(Path(tmp))
        assert rf.has_data()
        assert rf.h_overflow_pct == 0.05
    print("[PASS] File-based parsing")
    passed += 1

    # Test 8: missing file
    total += 1
    rf2 = parse_congestion_data(Path(r"C:\nonexistent"))
    assert not rf2.has_data()
    print("[PASS] Missing file handled")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED — congestion_enhanced.py ready")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)
