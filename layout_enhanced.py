"""
layout_enhanced.py — Cadence Virtuoso-style Interactive Layout Viewer
RTL-Gen AI v2.5 — Phase 2

Uses KLayout Python API (klayout.db — already installed, no GUI needed)
to extract GDS polygons per layer and render as interactive Plotly figure.

Features matching Cadence Virtuoso:
  ├── Per-layer checkboxes with shape counts
  ├── "Routing Only" / "Show All" quick-select buttons
  ├── Filled polygon rendering with Sky130A colour scheme
  ├── Chip outline boundary marker
  ├── Hover: x/y coordinates in µm
  ├── Zoom / pan (Plotly native)
  ├── Design metrics header (size, area, layers, GDS KB)
  ├── Performance cap: MAX_POLYGONS_PER_LAYER with warning
  └── Download GDS button

Usage in app.py (Sign-Off → Layout tab):
    from layout_enhanced import render_layout_enhanced_streamlit
    render_layout_enhanced_streamlit(gds_path, key_prefix="signoff_ly")

Standalone test (does NOT require Docker or a real GDS — generates one):
    python layout_enhanced.py
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import plotly.graph_objects as go

log = logging.getLogger(__name__)

# ── KLayout availability guard ────────────────────────────────────────────────
try:
    import klayout.db as pya
    _KL_AVAILABLE = True
except ImportError:
    _KL_AVAILABLE = False
    log.warning("klayout.db not importable — run: pip install klayout")


# ── Sky130A layer definitions ──────────────────────────────────────────────────
# (layer_number, datatype) → (canonical_name, hex_colour, fill_opacity)
# Colours match the KLayout default Sky130A colour scheme.
_SKY130_LAYERS: Dict[Tuple[int, int], Tuple[str, str, float]] = {
    (64, 20): ("nwell",  "#CC9966", 0.20),
    (65, 20): ("diff",   "#66CC66", 0.45),
    (66, 20): ("tap",    "#339933", 0.45),
    (67, 20): ("nsdm",   "#AAFFAA", 0.20),
    (68, 20): ("psdm",   "#FFAA44", 0.20),
    (69, 20): ("poly",   "#FF3333", 0.55),
    (70, 20): ("licon1", "#AAAAAA", 0.70),
    (71, 20): ("li1",    "#AA33FF", 0.50),
    (72, 20): ("mcon",   "#777777", 0.80),
    (73, 20): ("met1",   "#3366FF", 0.50),
    (74, 20): ("via",    "#555555", 0.80),
    (75, 20): ("met2",   "#33AAAA", 0.50),
    (76, 20): ("via2",   "#555555", 0.80),
    (77, 20): ("met3",   "#EEEE33", 0.50),
    (78, 20): ("via3",   "#555555", 0.80),
    (79, 20): ("met4",   "#FF33FF", 0.50),
    (80, 20): ("via4",   "#555555", 0.80),
    (81, 20): ("met5",   "#FF8833", 0.50),
    (83, 44): ("pad",    "#FFFFFF", 0.30),
}

_DEFAULT_COLOUR  = "#888888"
_DEFAULT_OPACITY = 0.35

# Via layers — rendered as small marks rather than filled polygons
_VIA_LAYER_NUMS = {70, 72, 74, 76, 78, 80}

# Routing layers shown by default
_ROUTING_LAYERS = {"met1", "met2", "met3", "met4", "met5", "li1"}

# Perf cap — prevents browser freeze on dense layers
MAX_POLYGONS_PER_LAYER = 400


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class LayerData:
    layer_num:   int
    datatype:    int
    name:        str
    color:       str
    opacity:     float
    is_via:      bool                                      = False
    polygons:    List[List[Tuple[float, float]]]           = field(default_factory=list)
    shape_count: int                                       = 0   # total before cap

    @property
    def display_name(self) -> str:
        return self.name if self.name else f"L{self.layer_num}/{self.datatype}"

    @property
    def fill_rgba(self) -> str:
        r, g, b = int(self.color[1:3], 16), int(self.color[3:5], 16), int(self.color[5:7], 16)
        return f"rgba({r},{g},{b},{self.opacity})"

    @property
    def edge_rgba(self) -> str:
        r, g, b = int(self.color[1:3], 16), int(self.color[3:5], 16), int(self.color[5:7], 16)
        return f"rgba({r},{g},{b},0.95)"

    @property
    def truncated(self) -> bool:
        return self.shape_count > MAX_POLYGONS_PER_LAYER


# ── GDS loader ────────────────────────────────────────────────────────────────

def load_gds_layout(
    gds_path: Path,
) -> Tuple[Dict[str, LayerData], Dict]:
    """
    Load a GDS file with KLayout Python API.

    Returns
    -------
    layers : dict  display_name → LayerData  (empty if load fails)
    info   : dict  design stats or {"error": "..."}
    """
    if not _KL_AVAILABLE:
        return {}, {"error": "klayout.db not available — run: pip install klayout"}

    gds_path = Path(gds_path)
    if not gds_path.exists():
        return {}, {"error": f"GDS file not found: {gds_path}"}

    # ── Read GDS ─────────────────────────────────────────────────────
    try:
        layout = pya.Layout()
        layout.read(str(gds_path))
    except Exception as exc:
        return {}, {"error": f"KLayout read error: {exc}"}

    dbu = layout.dbu   # µm per database unit (Sky130A: 0.001 µm = 1 nm)

    # ── Top cell ──────────────────────────────────────────────────────
    try:
        top_cell = layout.top_cell()
    except Exception:
        if layout.cells() == 0:
            return {}, {"error": "GDS has no cells"}
        top_cell = layout.cell(0)

    bbox = top_cell.bbox()
    info = {
        "design_name": top_cell.name,
        "dbu_um":      dbu,
        "width_um":    round(bbox.width()  * dbu, 3),
        "height_um":   round(bbox.height() * dbu, 3),
        "area_um2":    round(bbox.width() * bbox.height() * dbu * dbu, 3),
        "cell_count":  layout.cells(),
        "gds_size_kb": round(gds_path.stat().st_size / 1024, 1),
        "origin_x":    round(bbox.left  * dbu, 3),
        "origin_y":    round(bbox.bottom* dbu, 3),
    }

    # ── Extract shapes per layer ──────────────────────────────────────
    layers: Dict[str, LayerData] = {}

    for layer_idx in layout.layer_indexes():
        lp  = layout.get_info(layer_idx)
        key = (lp.layer, lp.datatype)

        if key in _SKY130_LAYERS:
            name, color, opacity = _SKY130_LAYERS[key]
        else:
            name    = lp.name or f"L{lp.layer}/{lp.datatype}"
            color   = _DEFAULT_COLOUR
            opacity = _DEFAULT_OPACITY

        is_via   = lp.layer in _VIA_LAYER_NUMS
        ld       = LayerData(
            layer_num=lp.layer, datatype=lp.datatype,
            name=name, color=color, opacity=opacity, is_via=is_via,
        )

        # Recursive iterator — traverses entire cell hierarchy
        try:
            it = pya.RecursiveShapeIterator(layout, top_cell, layer_idx)
            while not it.at_end():
                shape      = it.shape()
                trans      = it.itrans()   # integer transformation in DBU
                ld.shape_count += 1

                if len(ld.polygons) < MAX_POLYGONS_PER_LAYER:
                    poly = None
                    if shape.is_polygon():
                        poly = shape.polygon.transformed(trans)
                    elif shape.is_box():
                        poly = pya.Polygon(shape.box).transformed(trans)
                    elif shape.is_path():
                        try:
                            poly = shape.path.polygon().transformed(trans)
                        except Exception:
                            pass

                    if poly is not None:
                        pts = [
                            (pt.x * dbu, pt.y * dbu)
                            for pt in poly.each_point_hull()
                        ]
                        if len(pts) >= 3:
                            ld.polygons.append(pts)

                it.next()
        except Exception as exc:
            log.debug("Layer %s/%s extraction warning: %s", lp.layer, lp.datatype, exc)

        if ld.shape_count > 0:
            # Use display_name as key (may collide if unnamed — append layer num)
            display = ld.display_name
            if display in layers:
                display = f"{display}_{lp.layer}"
            layers[display] = ld

    # ── Sort: routing first, then device, then vias ───────────────────
    _order = {n: i for i, n in enumerate(
        ["met5", "met4", "met3", "met2", "met1", "li1",
         "via4", "via3", "via2", "via", "mcon", "licon1",
         "poly", "diff", "tap", "nwell", "nsdm", "psdm", "pad"]
    )}
    layers = dict(
        sorted(layers.items(), key=lambda x: _order.get(x[1].name, 99))
    )

    log.info(
        "GDS loaded: %d layers, %.1f×%.1f µm, %d cells, %.1f KB",
        len(layers), info["width_um"], info["height_um"],
        info["cell_count"], info["gds_size_kb"],
    )
    return layers, info


# ── Plotly figure builder ─────────────────────────────────────────────────────

def build_layout_figure(
    layers:       Dict[str, LayerData],
    selected:     List[str],
    info:         Optional[Dict] = None,
    show_outline: bool           = True,
) -> go.Figure:
    """
    Build Plotly figure with selected layers rendered as filled polygons.

    All polygons for one layer are packed into ONE Scatter trace using
    None separators — keeps trace count low for fast rendering.
    """
    fig    = go.Figure()
    all_xs: List[float] = []
    all_ys: List[float] = []

    for name in selected:
        if name not in layers:
            continue
        ld = layers[name]
        if not ld.polygons:
            continue

        # Pack all polygons into one trace with None breaks
        px: List[Optional[float]] = []
        py: List[Optional[float]] = []

        for pts in ld.polygons:
            # Close polygon by repeating first point, then None separator
            xs = [p[0] for p in pts] + [pts[0][0], None]
            ys = [p[1] for p in pts] + [pts[0][1], None]
            px.extend(xs)
            py.extend(ys)
            all_xs.extend(p[0] for p in pts)
            all_ys.extend(p[1] for p in pts)

        trunc_note = f"/{ld.shape_count}⚠" if ld.truncated else ""
        legend_label = f"{ld.display_name} ({len(ld.polygons)}{trunc_note})"

        fig.add_trace(go.Scatter(
            x             = px,
            y             = py,
            mode          = "lines",
            fill          = "toself",
            fillcolor     = ld.fill_rgba,
            line          = dict(color=ld.edge_rgba, width=0.6),
            name          = legend_label,
            legendgroup   = name,
            showlegend    = True,
            hovertemplate = (
                f"<b>{ld.display_name}</b><br>"
                "x = %{x:.3f} µm<br>"
                "y = %{y:.3f} µm"
                "<extra></extra>"
            ),
        ))

    # Chip outline
    if show_outline and all_xs and all_ys:
        pad  = max((max(all_xs) - min(all_xs)) * 0.02, 0.5)
        fig.add_shape(
            type      = "rect",
            x0        = min(all_xs) - pad,
            y0        = min(all_ys) - pad,
            x1        = max(all_xs) + pad,
            y1        = max(all_ys) + pad,
            line      = dict(color="#ffffff", width=1, dash="dot"),
            fillcolor = "rgba(0,0,0,0)",
            layer     = "below",
        )

    # Empty-state message
    if not all_xs:
        fig.add_annotation(
            text      = "No polygons in selected layers",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow = False,
            font      = dict(size=14, color="#888888"),
        )

    design_name = info.get("design_name", "") if info else ""
    fig.update_layout(
        paper_bgcolor = "#0a0a0f",
        plot_bgcolor  = "#0f0f1a",
        font          = dict(family="monospace", size=10, color="#cccccc"),
        height        = 660,
        margin        = dict(l=10, r=10, t=35, b=10),
        title         = dict(
            text = f"{design_name} — GDS Layout Viewer (Sky130A)",
            font = dict(size=12, color="#aaaacc"),
        ),
        xaxis = dict(
            title      = "X (µm)",
            color      = "#888888",
            gridcolor  = "#1a1a2e",
            scaleanchor= "y",
            scaleratio = 1,
            showspikes = True,
            spikecolor = "#ffffff",
            spikethickness = 1,
        ),
        yaxis = dict(
            title     = "Y (µm)",
            color     = "#888888",
            gridcolor = "#1a1a2e",
        ),
        legend = dict(
            bgcolor     = "rgba(10,10,30,0.85)",
            bordercolor = "#333366",
            borderwidth = 1,
            font        = dict(size=9),
            itemsizing  = "constant",
        ),
        hovermode = "closest",
        dragmode  = "zoom",
        modebar   = dict(bgcolor="rgba(0,0,0,0)", color="#888888"),
    )

    return fig


# ── Streamlit entry point ─────────────────────────────────────────────────────

def render_layout_enhanced_streamlit(
    gds_path:   Optional[Path],
    key_prefix: str = "ly",
) -> None:
    """
    Full interactive layout viewer for Streamlit.
    Call from app.py Sign-Off → Layout tab.

    Args:
        gds_path:   Path to .gds file (can be None — shows warning)
        key_prefix: Unique prefix for Streamlit widget keys
    """
    import streamlit as st

    if not _KL_AVAILABLE:
        st.error(
            "KLayout Python bindings not installed.\n"
            "Run: `pip install klayout` then restart the app."
        )
        return

    if not gds_path or not Path(gds_path).exists():
        st.warning("No GDS file available for this design.")
        st.caption("Complete the full pipeline to generate a layout.")
        return

    gds_path = Path(gds_path)

    # ── Load ──────────────────────────────────────────────────────────
    with st.spinner(f"Loading {gds_path.name} via KLayout Python API…"):
        layers, info = load_gds_layout(gds_path)

    if "error" in info:
        st.error(f"Layout load failed: {info['error']}")
        return

    if not layers:
        st.warning("GDS loaded successfully but contains no polygon layers.")
        return

    # ── Design info bar ───────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Cell",     info.get("design_name", "—"))
    m2.metric("Width",    f"{info.get('width_um',  0):.2f} µm")
    m3.metric("Height",   f"{info.get('height_um', 0):.2f} µm")
    m4.metric("Layers",   len(layers))
    m5.metric("GDS Size", f"{info.get('gds_size_kb', 0)} KB")

    # ── Quick-select buttons ──────────────────────────────────────────
    st.markdown("#### Layer Controls")
    b1, b2, b3, b4 = st.columns(4)
    show_all_btn     = b1.button("Show All",      key=f"{key_prefix}_all")
    show_routing_btn = b2.button("Routing Only",   key=f"{key_prefix}_routing")
    show_device_btn  = b3.button("Device Layers",  key=f"{key_prefix}_device")
    show_outline_cb  = b4.checkbox("Chip outline", value=True, key=f"{key_prefix}_outline")

    # ── Session state: selected layers ────────────────────────────────
    sel_key = f"{key_prefix}_sel"
    if sel_key not in st.session_state:
        # Default: met1 + met2 + li1 + poly
        st.session_state[sel_key] = {
            n for n, ld in layers.items()
            if ld.name in {"met1", "met2", "li1", "poly"}
        }

    if show_all_btn:
        st.session_state[sel_key] = set(layers.keys())
    if show_routing_btn:
        st.session_state[sel_key] = {
            n for n, ld in layers.items()
            if ld.name in _ROUTING_LAYERS or ld.is_via
        }
    if show_device_btn:
        st.session_state[sel_key] = {
            n for n, ld in layers.items()
            if ld.name in {"poly", "diff", "tap", "nwell", "nsdm", "psdm"}
        }

    # ── Per-layer checkboxes ──────────────────────────────────────────
    with st.expander(f"All layers ({len(layers)} with shapes)", expanded=True):
        cols = st.columns(4)
        for i, (name, ld) in enumerate(layers.items()):
            checked  = name in st.session_state[sel_key]
            trunc_w  = " ⚠️" if ld.truncated else ""
            cb_label = f"{ld.display_name} ({ld.shape_count}{trunc_w})"

            if cols[i % 4].checkbox(cb_label, value=checked, key=f"{key_prefix}_cb_{name}"):
                st.session_state[sel_key].add(name)
            else:
                st.session_state[sel_key].discard(name)

    selected = [n for n in layers if n in st.session_state[sel_key]]

    if not selected:
        st.info("Select at least one layer above to display the layout.")
        return

    # Truncation warning
    trunc_layers = [n for n in selected if layers[n].truncated]
    if trunc_layers:
        st.caption(
            f"⚠️ Dense layers subsampled to {MAX_POLYGONS_PER_LAYER} polygons "
            f"for browser performance: {', '.join(trunc_layers)}"
        )

    # ── Render ────────────────────────────────────────────────────────
    fig = build_layout_figure(layers, selected, info=info, show_outline=show_outline_cb)
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_chart")

    # ── Layer stats table ─────────────────────────────────────────────
    with st.expander("Layer shape counts"):
        import pandas as pd
        rows = [
            {
                "Layer":  ld.display_name,
                "Shapes": ld.shape_count,
                "Shown":  len(ld.polygons),
                "Capped": "⚠️ yes" if ld.truncated else "✓ no",
                "Type":   "via" if ld.is_via else "polygon",
            }
            for ld in (layers[n] for n in selected)
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # ── Download ──────────────────────────────────────────────────────
    st.download_button(
        label     = f"⬇ Download {gds_path.name}",
        data      = gds_path.read_bytes(),
        file_name = gds_path.name,
        mime      = "application/octet-stream",
        key       = f"{key_prefix}_dl",
    )


# ── Standalone test (no Docker, no real GDS required) ────────────────────────

def _make_test_gds(path: Path) -> None:
    """Create a minimal synthetic Sky130A-style GDS for testing."""
    layout = pya.Layout()
    layout.dbu = 0.001          # 1 nm resolution (Sky130A standard)
    top = layout.create_cell("test_adder_8bit")

    def add_layer(layer_num: int, datatype: int,
                  boxes: List[Tuple[int, int, int, int]]) -> None:
        lyr = layout.layer(layer_num, datatype)
        for x0, y0, x1, y1 in boxes:
            top.shapes(lyr).insert(pya.Box(x0, y0, x1, y1))

    # nwell  — large background region
    add_layer(64, 20, [(0, 0, 80000, 60000)])
    # diff   — several active areas
    add_layer(65, 20, [(2000, 2000, 10000, 8000),
                       (15000, 2000, 25000, 8000),
                       (50000, 40000, 70000, 55000)])
    # poly   — gate stripes
    add_layer(69, 20, [(5000, 0, 6000, 10000),
                       (20000, 0, 21000, 10000),
                       (60000, 38000, 61000, 58000)])
    # li1    — local interconnect
    add_layer(71, 20, [(1000, 10000, 30000, 11500),
                       (1000, 20000, 30000, 21500),
                       (40000, 10000, 80000, 11500)])
    # met1   — first metal (horizontal routes)
    add_layer(73, 20, [(0, 15000, 80000, 16500),
                       (0, 30000, 80000, 31500),
                       (0, 45000, 80000, 46500)])
    # met2   — second metal (vertical routes)
    add_layer(75, 20, [(10000, 0, 11500, 60000),
                       (30000, 0, 31500, 60000),
                       (60000, 0, 61500, 60000)])
    # via    — via1 connections
    add_layer(74, 20, [(10200, 14800, 10800, 16700),
                       (30200, 14800, 30800, 16700),
                       (60200, 29800, 60800, 31700)])
    # met3   — third metal
    add_layer(77, 20, [(0, 25000, 80000, 26500)])

    layout.write(str(path))


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("layout_enhanced.py — standalone self-test")
    print("=" * 60)

    passed = total = 0

    # Test 0: KLayout available
    total += 1
    if not _KL_AVAILABLE:
        print("[FAIL] klayout.db not importable — run: pip install klayout")
        sys.exit(1)
    print("[PASS] klayout.db imported successfully")
    passed += 1

    with tempfile.TemporaryDirectory() as tmp:
        gds_file = Path(tmp) / "test_layout.gds"

        # Test 1: create synthetic GDS
        total += 1
        try:
            _make_test_gds(gds_file)
            assert gds_file.exists()
            assert gds_file.stat().st_size > 100
            print(f"[PASS] Synthetic GDS created: {gds_file.stat().st_size} bytes")
            passed += 1
        except Exception as e:
            print(f"[FAIL] GDS creation: {e}")
            sys.exit(1)

        # Test 2: load GDS
        total += 1
        layers, info = load_gds_layout(gds_file)
        assert "error" not in info, f"Load error: {info.get('error')}"
        assert len(layers) > 0, "No layers loaded"
        assert info["width_um"]  > 0
        assert info["height_um"] > 0
        print(f"[PASS] GDS loaded: {len(layers)} layers, "
              f"{info['width_um']:.1f}×{info['height_um']:.1f} µm, "
              f"{info['cell_count']} cell(s)")
        passed += 1

        # Test 3: expected layers present
        total += 1
        layer_names = {ld.name for ld in layers.values()}
        for expected in ("met1", "met2", "li1", "poly"):
            assert expected in layer_names, \
                f"Expected layer '{expected}' not found. Got: {layer_names}"
        print(f"[PASS] Expected layers present: {sorted(layer_names)}")
        passed += 1

        # Test 4: polygon extraction
        total += 1
        met1_entry = next((ld for ld in layers.values() if ld.name == "met1"), None)
        assert met1_entry is not None, "met1 not found"
        assert len(met1_entry.polygons) >= 3, \
            f"met1 has only {len(met1_entry.polygons)} polygons (expected ≥3)"
        assert met1_entry.shape_count >= 3
        # Verify polygon has valid coordinates
        first_poly = met1_entry.polygons[0]
        assert len(first_poly) >= 3, "Polygon has fewer than 3 points"
        assert all(isinstance(x, float) for x, y in first_poly)
        print(f"[PASS] Polygon extraction: met1 has {len(met1_entry.polygons)} polygons, "
              f"first polygon: {len(first_poly)} vertices")
        passed += 1

        # Test 5: LayerData properties
        total += 1
        ld_test = LayerData(layer_num=73, datatype=20,
                            name="met1", color="#3366FF", opacity=0.5)
        assert "rgba(51,102,255,0.5)" == ld_test.fill_rgba, \
            f"fill_rgba wrong: {ld_test.fill_rgba}"
        assert ld_test.display_name == "met1"
        assert not ld_test.truncated   # 0 polygons < cap
        print(f"[PASS] LayerData properties: fill_rgba={ld_test.fill_rgba}")
        passed += 1

        # Test 6: Plotly figure builds
        total += 1
        selected = list(layers.keys())[:4]
        fig = build_layout_figure(layers, selected, info=info, show_outline=True)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1, "Figure has no traces"
        print(f"[PASS] Plotly figure: {len(fig.data)} traces for "
              f"{len(selected)} layers")
        passed += 1

        # Test 7: sorting — met layers before via/nwell
        total += 1
        names = list(layers.keys())
        met1_pos  = next((i for i, n in enumerate(names) if layers[n].name == "met1"),  99)
        nwell_pos = next((i for i, n in enumerate(names) if layers[n].name == "nwell"), 99)
        assert met1_pos < nwell_pos, \
            f"Expected met1 before nwell, got met1@{met1_pos} nwell@{nwell_pos}"
        print(f"[PASS] Layer sort order: met1@{met1_pos} < nwell@{nwell_pos}")
        passed += 1

        # Test 8: missing GDS → graceful error
        total += 1
        _, bad_info = load_gds_layout(Path("/nonexistent/path.gds"))
        assert "error" in bad_info
        print(f"[PASS] Missing GDS graceful error: '{bad_info['error'][:40]}…'")
        passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED — layout_enhanced.py ready for integration")
    else:
        print("SOME TESTS FAILED — check output above")
    print("=" * 60)
