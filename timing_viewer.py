"""
timing_viewer.py
================
Parse OpenSTA timing reports and visualize paths.
Commercial equivalent: PrimeTime path analysis
"""

import re
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, field

from parsers.sta_parser import parse_sta_corner, STAPath, STAPathCell


@dataclass
class TimingPath:
    startpoint:  str
    endpoint:    str
    path_type:   str
    slack_ns:    float
    met:         bool
    cells:       List[Dict] = field(default_factory=list)
    total_delay: float = 0.0
    corner:      str = "TT"


def parse_sta_report(sta_path: str,
                     corner: str = "TT") -> List[TimingPath]:
    """
    Parse OpenSTA timing report.
    Delegates to parsers.sta_parser and converts to TimingPath.
    """
    path = Path(sta_path)
    if not path.exists():
        return []

    content = path.read_text(errors="ignore")
    sta_corner = parse_sta_corner(content, corner)

    paths = []
    for sp in sta_corner.paths[:5]:
        cells = []
        for c in sp.cells:
            cells.append({
                "delay": c.delay,
                "time": c.time,
                "edge": "rise" if c.edge == "^" else "fall" if c.edge == "v" else c.edge,
                "net": c.net,
                "pin": c.pin,
                "cell": c.cell,
            })

        # If path has no cells, try inline parsing for alternate STA format
        if not cells:
            cells = _parse_cells_inline(content, sp.startpoint)

        total_delay = cells[-1]["time"] if cells else 0.0

        # Strip parenthetical from startpoint/endpoint
        startpoint = sp.startpoint.split(" (")[0].strip() if " (" in sp.startpoint else sp.startpoint
        endpoint = sp.endpoint.split(" (")[0].strip() if " (" in sp.endpoint else sp.endpoint

        # Use corner-level slack if path slack is 0 and corner has slack
        slack_ns = sp.slack_ns
        if slack_ns == 0.0 and sta_corner.slack_ns is not None:
            slack_ns = sta_corner.slack_ns

        paths.append(TimingPath(
            startpoint=startpoint,
            endpoint=endpoint,
            path_type=sp.path_type,
            slack_ns=slack_ns,
            met=sp.met if sp.slack_ns != 0.0 or not sta_corner.paths else (sta_corner.slack_ns is not None and sta_corner.slack_ns >= 0),
            cells=cells,
            total_delay=total_delay,
            corner=corner,
        ))

    return paths


def _parse_cells_inline(content: str, startpoint: str) -> List[Dict]:
    """Parse cell delays from STA report in delay/time/edge/net(cell) format."""
    cells = []
    cell_pattern = re.compile(
        r'^\s+([\d.]+)\s+([\d.]+)\s+([v^])\s+'
        r'(\S+?)(?:/(\S+?))?\s+\((\w+)\)',
        re.MULTILINE
    )
    path_blocks = re.split(r'(?=Startpoint:)', content)
    for block in path_blocks[:5]:
        if startpoint not in block:
            continue
        for cm in cell_pattern.finditer(block):
            cells.append({
                "delay": float(cm.group(2)),
                "time": float(cm.group(1)),
                "edge": "rise" if cm.group(3) == '^' else "fall",
                "net": cm.group(4),
                "pin": cm.group(5) or "",
                "cell": cm.group(6),
            })
        break
    return cells


def render_timing_streamlit(results_dir: str,
                             design_name: str):
    """
    Render timing path viewer in Streamlit.
    Shows critical path with cell delays (PrimeTime-style).
    """
    import streamlit as st
    import plotly.graph_objects as go

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ STATIC TIMING ANALYSIS — PRIMETIME-STYLE PATH VIEW
    </div>""", unsafe_allow_html=True)

    results = Path(results_dir)

    corner_files = {
        "TT (25°C, 1.8V)":  "sta_final.txt",
        "SS (100°C, 1.6V)": "sta_ss.txt",
        "FF (-40°C, 1.95V)":"sta_ff.txt",
    }

    # Summary row: 3-corner slack cards
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    corner_paths = {}
    for i, (corner_name, fname) in enumerate(corner_files.items()):
        f = results / fname
        if f.exists():
            content = f.read_text(errors="ignore")
            m = re.search(r'([-\d.]+)\s+slack\s+\((MET|VIOLATED)\)', content)
            if m:
                slack  = float(m.group(1))
                status = m.group(2)
                color  = "#00ff9d" if status == "MET" else "#ff3333"
                with cols[i]:
                    st.markdown(f"""<div style="background:#1c2128;border:1px solid {color};
                        border-radius:4px;padding:10px;text-align:center">
                        <div style="color:#8b949e;font-size:0.7rem;font-family:monospace">{corner_name}</div>
                        <div style="color:{color};font-size:1.4rem;font-family:monospace;font-weight:bold">{slack:.2f} ns</div>
                        <div style="color:{color};font-size:0.7rem">{status}</div>
                    </div>""", unsafe_allow_html=True)
                corner_paths[corner_name] = parse_sta_report(str(f), corner_name)

    st.markdown("")

    selected = st.selectbox("View timing corner", list(corner_paths.keys()))

    if selected not in corner_paths:
        st.info("No timing data for this corner.")
        return

    paths = corner_paths[selected]
    if not paths:
        st.info("No timing paths parsed from report")
        return

    # ── Path selector ───────────────────────────────────────────────
    path_labels = [f"Path {i+1}: {p.startpoint} → {p.endpoint} (slack={p.slack_ns:.3f}ns)" for i, p in enumerate(paths)]
    sel_idx = st.selectbox("Select path", range(len(path_labels)), format_func=lambda i: path_labels[i])
    path = paths[sel_idx]

    st.markdown(
        f"**Total Delay:** {path.total_delay:.3f} ns  |  "
        f"**Slack:** {path.slack_ns:.3f} ns  |  "
        f"**Status:** {'✅ MET' if path.met else '❌ VIOLATED'}"
    )

    # ── Waterfall chart: cumulative delay through path ──────────────
    if path.cells:
        cells = path.cells[:30]
        names = [c.get('net', '?')[:16] for c in cells]
        delays = [c.get('delay', 0) for c in cells]
        ctypes = [c.get('cell', '?') for c in cells]
        cum_times = [c.get('time', 0) for c in cells]

        colors = []
        for ct in ctypes:
            if any(k in ct.lower() for k in ('dff', 'ff', 'dfx', 'dfr', 'dfs')):
                colors.append('#4a90d9')
            elif any(k in ct.lower() for k in ('nand', 'and', 'or', 'nor')):
                colors.append('#e74c3c')
            elif any(k in ct.lower() for k in ('xor', 'xnor')):
                colors.append('#f39c12')
            elif 'inv' in ct.lower() or 'buf' in ct.lower():
                colors.append('#2ecc71')
            else:
                colors.append('#00d4ff')

        fig = go.Figure()
        # Cumulative delay step line
        fig.add_trace(go.Scatter(
            x=list(range(len(cells))), y=cum_times,
            mode="lines+markers",
            line=dict(color="#58a6ff", width=2),
            marker=dict(size=6, color="#58a6ff"),
            name="Cumulative delay",
            hovertemplate="Stage %{x}<br>Cumulative: %{y:.3f} ns<extra></extra>",
        ))
        # Individual delay bars
        fig.add_trace(go.Bar(
            x=list(range(len(cells))), y=delays,
            marker_color=colors,
            name="Cell delay",
            text=[f"{d:.3f}" for d in delays],
            textposition="outside",
            textfont=dict(size=8),
            hovertemplate="<b>%{text}</b><br>Net: %{customdata[0]}<br>Cell: %{customdata[1]}<extra></extra>",
            customdata=list(zip(names, ctypes)),
        ))

        fig.update_layout(
            title=f"Path Delay Breakdown — slack={path.slack_ns:.3f}ns",
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            font=dict(family="Share Tech Mono", color="#c9d1d9", size=9),
            xaxis=dict(title="Stage (left=startpoint, right=endpoint)", gridcolor="#30363d"),
            yaxis=dict(title="Delay (ns)", gridcolor="#30363d"),
            barmode="group", height=380,
            legend=dict(orientation="h", y=1.12),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Cell table ──────────────────────────────────────────────
        with st.expander("📋 Cell-by-cell path detail"):
            rows = []
            for c in cells:
                rows.append({
                    "Net": c.get("net", "?"),
                    "Cell": c.get("cell", "?"),
                    "Delay": f"{c.get('delay', 0):.3f}",
                    "Cumulative": f"{c.get('time', 0):.3f}",
                    "Edge": c.get("edge", "?"),
                })
            st.table(rows)

    else:
        st.info("No cell-level detail in timing path")

    # ── Slack distribution histogram (if multiple paths) ────────────
    if len(paths) > 1:
        st.markdown("---")
        slacks = [p.slack_ns for p in paths]
        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=slacks,
            nbinsx=min(len(slacks), 12),
            marker_color="#58a6ff",
            hovertemplate="Slack: %{x:.3f} ns<br>Count: %{y}<extra></extra>",
        ))
        fig2.update_layout(
            title="Slack Distribution",
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            font=dict(family="Share Tech Mono", color="#c9d1d9", size=9),
            xaxis=dict(title="Slack (ns)", gridcolor="#30363d"),
            yaxis=dict(title="Number of paths", gridcolor="#30363d"),
            height=250,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── All paths table ─────────────────────────────────────────────
    with st.expander("📋 All timing paths"):
        rows = []
        for i, p in enumerate(paths):
            rows.append({
                "Path": f"#{i + 1}",
                "Startpoint": p.startpoint[:40],
                "Endpoint": p.endpoint[:40],
                "Slack": f"{p.slack_ns:.3f}",
                "Delay": f"{p.total_delay:.3f}",
                "Cells": len(p.cells),
                "Status": "MET" if p.met else "VIOLATED",
            })
        st.table(rows)

    # ── Download button ─────────────────────────────────────────────
    sta_file = results / corner_files.get(selected, "sta_final.txt")
    if sta_file.exists():
        with open(sta_file) as f:
            st.download_button(
                "⬇️ Download Full STA Report",
                f.read(),
                file_name=sta_file.name,
                mime="text/plain"
            )


def render_timing_from_db(db) -> None:
    """Render timing data from a DesignDB instance (no file I/O)."""
    import streamlit as st
    import plotly.graph_objects as go

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ TIMING ANALYSIS — FROM DESIGN DATABASE
    </div>""", unsafe_allow_html=True)

    if not db.timing or not db.timing.corners:
        st.info("No timing data in DesignDB.")
        return

    td = db.timing

    # ── Corner cards ──────────────────────────────────────────────────
    cols = st.columns(len(td.corners))
    for i, (cname, tc) in enumerate(td.corners.items()):
        if i < len(cols):
            color = "#00ff9d" if tc.met else "#ff3333"
            cols[i].markdown(f"""<div style="background:#1c2128;border:1px solid {color};
                border-radius:4px;padding:10px;text-align:center">
                <div style="color:#8b949e;font-size:0.7rem;font-family:monospace">{cname}</div>
                <div style="color:{color};font-size:1.4rem;font-family:monospace;font-weight:bold">{tc.slack_ns or 0:.2f} ns</div>
                <div style="color:{color};font-size:0.7rem">{'MET' if tc.met else 'VIOLATED'}</div>
            </div>""", unsafe_allow_html=True)

    st.metric("Fmax", f"{td.fmax_mhz} MHz" if td.fmax_mhz else "N/A")
    if td.hold_slack_ns is not None:
        st.metric("Hold Slack", f"{td.hold_slack_ns:.3f} ns")

    # ── Path waterfall ────────────────────────────────────────────────
    tt = td.corners.get("TT") or next(iter(td.corners.values()))
    if tt and tt.paths:
        sel = st.selectbox("Select path", range(len(tt.paths)),
            format_func=lambda i: f"Path {i+1}: {tt.paths[i].startpoint} → {tt.paths[i].endpoint}")
        path = tt.paths[sel]

        if path.cells:
            cells = path.cells[:30]
            delays = [c.delay for c in cells]
            times = [c.time for c in cells]
            names = [c.net[:16] for c in cells]
            ctypes = [c.cell for c in cells]

            colors = []
            for ct in ctypes:
                if any(k in ct.lower() for k in ('dff', 'ff')):
                    colors.append('#4a90d9')
                elif any(k in ct.lower() for k in ('nand', 'and', 'nor')):
                    colors.append('#e74c3c')
                elif any(k in ct.lower() for k in ('xor', 'xnor')):
                    colors.append('#f39c12')
                else:
                    colors.append('#00d4ff')

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(range(len(cells))), y=times,
                mode="lines+markers", line=dict(color="#58a6ff", width=2),
                marker=dict(size=6), name="Cumulative",
            ))
            fig.add_trace(go.Bar(
                x=list(range(len(cells))), y=delays,
                marker_color=colors, name="Cell delay",
                text=[f"{d:.3f}" for d in delays],
                textposition="outside", textfont=dict(size=8),
            ))
            fig.update_layout(
                title=f"Path Delay — slack={path.slack_ns:.3f}ns",
                paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
                font=dict(family="Share Tech Mono", color="#c9d1d9", size=9),
                xaxis=dict(gridcolor="#30363d", title="Stage"),
                yaxis=dict(gridcolor="#30363d", title="Delay (ns)"),
                height=380,
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Slack histogram
        slacks = [p.slack_ns for p in tt.paths if len(tt.paths) > 1]
        if len(slacks) > 1:
            fig2 = go.Figure(go.Histogram(
                x=slacks, nbinsx=min(len(slacks), 12), marker_color="#58a6ff",
            ))
            fig2.update_layout(
                title="Slack Distribution",
                paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
                font=dict(family="Share Tech Mono", color="#c9d1d9", size=9),
                xaxis=dict(title="Slack (ns)", gridcolor="#30363d"),
                yaxis=dict(title="Count", gridcolor="#30363d"),
                height=250,
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No timing path details in DesignDB.")
