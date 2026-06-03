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


@dataclass
class TimingPath:
    startpoint:  str
    endpoint:    str
    path_type:   str   # max (setup) or min (hold)
    slack_ns:    float
    met:         bool
    cells:       List[Dict] = field(default_factory=list)
    total_delay: float = 0.0
    corner:      str = "TT"


def parse_sta_report(sta_path: str,
                     corner: str = "TT") -> List[TimingPath]:
    """
    Parse OpenSTA timing report.
    Extracts critical paths with cell-by-cell delays.
    """
    path = Path(sta_path)
    if not path.exists():
        return []

    content = path.read_text(errors="ignore")
    paths   = []

    # Find each path report block
    path_blocks = re.split(r'(?=Startpoint:)', content)

    for block in path_blocks[:5]:  # Max 5 paths
        if not block.strip():
            continue

        # Parse startpoint and endpoint
        start_m = re.search(r'Startpoint:\s+(.+?)(?:\s*\(|$)',
                             block, re.MULTILINE)
        end_m   = re.search(r'Endpoint:\s+(.+?)(?:\s*\(|$)',
                             block, re.MULTILINE)

        if not start_m or not end_m:
            continue

        startpoint = start_m.group(1).strip()
        endpoint   = end_m.group(1).strip()

        # Parse slack
        slack_m = re.search(
            r'([-\d.]+)\s+slack\s+\((MET|VIOLATED)\)',
            block
        )
        if not slack_m:
            continue

        slack_ns = float(slack_m.group(1))
        met      = slack_m.group(2) == "MET"

        # Parse cell delays in the path
        cells = []
        cell_pattern = re.compile(
            r'^\s+([\d.]+)\s+([\d.]+)\s+([v^])\s+'
            r'(\w+)(?:/(\w+))?\s+\((\w+)\)',
            re.MULTILINE
        )

        for cm in cell_pattern.finditer(block):
            cells.append({
                "delay":    float(cm.group(2)),
                "time":     float(cm.group(1)),
                "edge":     "rise" if cm.group(3)=='^'
                             else "fall",
                "net":      cm.group(4),
                "pin":      cm.group(5) or "",
                "cell":     cm.group(6)
            })

        total_delay = cells[-1]["time"] if cells else 0.0

        paths.append(TimingPath(
            startpoint=startpoint,
            endpoint=endpoint,
            path_type="max",
            slack_ns=slack_ns,
            met=met,
            cells=cells,
            total_delay=total_delay,
            corner=corner
        ))

    return paths


def render_timing_streamlit(results_dir: str,
                             design_name: str):
    """
    Render timing path viewer in Streamlit.
    Shows critical path with cell delays.
    """
    import streamlit as st

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ STATIC TIMING ANALYSIS — CRITICAL PATH VIEW
    </div>""", unsafe_allow_html=True)

    results = Path(results_dir)

    # Load all 3 corners
    corner_files = {
        "TT (25°C, 1.8V)":  "sta_final.txt",
        "SS (100°C, 1.6V)": "sta_ss.txt",
        "FF (-40°C, 1.95V)":"sta_ff.txt",
    }

    # Summary row
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    corner_paths = {}
    for i, (corner_name, fname) in enumerate(
        corner_files.items()
    ):
        f = results / fname
        if f.exists():
            content = f.read_text(errors="ignore")
            m = re.search(
                r'([-\d.]+)\s+slack\s+\((MET|VIOLATED)\)',
                content
            )
            if m:
                slack  = float(m.group(1))
                status = m.group(2)
                color  = "#00ff9d" if status=="MET" \
                          else "#ff3333"
                with cols[i]:
                    st.markdown(
                        f"""<div style="
                            background:#1c2128;
                            border:1px solid {'#00ff9d' if status=='MET' else '#ff3333'};
                            border-radius:4px;padding:10px;
                            text-align:center">
                            <div style="color:#8b949e;
                                font-size:0.7rem;
                                font-family:'Share Tech Mono',monospace">
                                {corner_name}
                            </div>
                            <div style="color:{color};
                                font-size:1.4rem;
                                font-family:'Share Tech Mono',monospace;
                                font-weight:bold">
                                {slack:.2f} ns
                            </div>
                            <div style="color:{color};
                                font-size:0.7rem">
                                {status}
                            </div>
                        </div>""",
                        unsafe_allow_html=True
                    )
                corner_paths[corner_name] = parse_sta_report(
                    str(f), corner_name
                )

    st.markdown("")

    # Detailed path view
    selected = st.selectbox(
        "View timing corner",
        list(corner_paths.keys())
    )

    if selected in corner_paths:
        paths = corner_paths[selected]
        if paths:
            path = paths[0]  # Most critical path

            st.markdown(
                f"**Critical Path:** "
                f"`{path.startpoint}` → `{path.endpoint}`"
            )
            st.markdown(
                f"**Total Delay:** {path.total_delay:.3f} ns  |  "
                f"**Slack:** {path.slack_ns:.3f} ns  |  "
                f"**Status:** "
                f"{'✅ MET' if path.met else '❌ VIOLATED'}"
            )

            # Waterfall chart of cell delays
            if path.cells:
                try:
                    import plotly.graph_objects as go

                    cells_to_show = path.cells[:20]
                    names  = [c.get('net','?')[:15]
                               for c in cells_to_show]
                    delays = [c.get('delay', 0)
                               for c in cells_to_show]
                    ctypes = [c.get('cell','?')
                               for c in cells_to_show]
                    times  = [c.get('time', 0)
                               for c in cells_to_show]

                    # Color by cell type
                    colors = []
                    for ct in ctypes:
                        if 'dff' in ct.lower() or 'ff' in ct:
                            colors.append('#4a90d9')
                        elif 'maj' in ct.lower():
                            colors.append('#e74c3c')
                        elif 'xor' in ct.lower():
                            colors.append('#f39c12')
                        else:
                            colors.append('#00d4ff')

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=names, y=delays,
                        marker_color=colors,
                        text=[f"{d:.3f}" for d in delays],
                        textposition='outside',
                        hovertemplate=(
                            '<b>%{x}</b><br>'
                            'Delay: %{y:.3f} ns<br>'
                            '<extra></extra>'
                        )
                    ))

                    fig.update_layout(
                        title="Cell Delay Breakdown",
                        paper_bgcolor='#0d1117',
                        plot_bgcolor='#161b22',
                        font=dict(
                            family='Share Tech Mono',
                            color='#c9d1d9',
                            size=9
                        ),
                        xaxis=dict(
                            gridcolor='#30363d',
                            tickangle=45
                        ),
                        yaxis=dict(
                            title="Delay (ns)",
                            gridcolor='#30363d'
                        ),
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)

                except ImportError:
                    # Text fallback
                    for cell in path.cells[:10]:
                        st.markdown(
                            f"`{cell.get('time',0):.3f}ns` "
                            f"+{cell.get('delay',0):.3f}ns "
                            f"→ `{cell.get('net','?')}`"
                        )
        else:
            st.info("No timing paths parsed from report")

        # Download button
        sta_file = results / corner_files.get(
            selected, "sta_final.txt"
        )
        if sta_file.exists():
            with open(sta_file) as f:
                st.download_button(
                    "⬇️ Download Full STA Report",
                    f.read(),
                    file_name=sta_file.name,
                    mime="text/plain"
                )
