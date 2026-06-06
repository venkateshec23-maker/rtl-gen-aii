"""
waveform_display.py
===================
Parse VCD waveform files and display as timing diagram.
Commercial equivalent: GTKWave / Cadence SimVision
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class WaveSignal:
    name:   str
    width:  int
    values: List[Tuple[int, str]]  # (time, value)


def parse_vcd(vcd_path: str,
              max_signals: int = 20,
              max_time:    int = 100000000) -> Dict:
    """
    Parse VCD (Value Change Dump) file.
    Returns signal dictionary with time-value pairs.
    """
    path = Path(vcd_path)
    if not path.exists():
        return {}

    content = path.read_text(errors="ignore")

    # Parse header
    timescale_m = re.search(r'\$timescale\s+(.*?)\s*\$end', content)
    timescale = timescale_m.group(1) if timescale_m else "1ns"

    # Parse variable declarations
    var_pattern = re.compile(
        r'\$var\s+(\w+)\s+(\d+)\s+(\S+)\s+(\S+)(?:\s+\[[\d:]+\])?\s*\$end'
    )
    id_to_signal = {}
    signals = {}

    for m in var_pattern.finditer(content):
        var_type  = m.group(1)
        width     = int(m.group(2))
        var_id    = m.group(3)
        var_name  = m.group(4)

        if var_name not in ('$dumpvars', '$end'):
            id_to_signal[var_id] = var_name
            signals[var_name] = WaveSignal(
                name=var_name,
                width=width,
                values=[]
            )

        if len(signals) >= max_signals:
            break

    # Parse value changes
    current_time = 0
    for line in content.split('\n'):
        line = line.strip()

        if line.startswith('#'):
            try:
                current_time = int(line[1:])
            except ValueError:
                pass
            if current_time > max_time:
                break

        elif line and line[0] in ('0', '1', 'x', 'z'):
            if len(line) >= 2:
                value = line[0]
                var_id = line[1:].strip()
                if var_id in id_to_signal:
                    sig_name = id_to_signal[var_id]
                    if sig_name in signals:
                        signals[sig_name].values.append(
                            (current_time, value)
                        )

        elif line.startswith('b'):
            parts = line.split()
            if len(parts) >= 2:
                value  = parts[0][1:]  # Remove 'b'
                var_id = parts[1]
                if var_id in id_to_signal:
                    sig_name = id_to_signal[var_id]
                    if sig_name in signals:
                        signals[sig_name].values.append(
                            (current_time, value)
                        )

    return {
        "timescale": timescale,
        "signals":   signals,
        "max_time":  current_time,
        "signal_count": len(signals)
    }


def find_vcd_for_design(
    results_dir: str,
    design_name: str
) -> str | None:
    """
    Find VCD file using multiple search strategies.
    VCD can be in: run dir, design dir, results dir,
    or any parent.
    """
    from pathlib import Path

    search_paths = [
        Path(results_dir),
        Path(results_dir).parent,
        Path(r"C:\tools\OpenLane\results"),
        Path(r"C:\tools\OpenLane\designs") / design_name,
        Path(r"C:\tools\OpenLane\designs") / design_name,
    ]

    # Also check runs directory for this design
    runs = Path(r"C:\tools\OpenLane\runs")
    if runs.exists():
        design_runs = sorted(
            [d for d in runs.glob(f"{design_name}*")
             if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        search_paths.extend(design_runs[:3])

    # Search all paths
    for search_path in search_paths:
        if not search_path.exists():
            continue
        # Direct search first
        for vcd_name in [
            "trace.vcd",
            f"{design_name}.vcd",
            "simulation.vcd",
            "waveform.vcd"
        ]:
            vcd = search_path / vcd_name
            if vcd.exists() and vcd.stat().st_size > 100:
                return str(vcd)
        # Recursive search (limited depth)
        for vcd in list(search_path.glob("*.vcd"))[:3]:
            if vcd.stat().st_size > 100:
                return str(vcd)

    return None


def _run_simulation_get_vcd(
    design_name: str,
    results_dir: str
) -> str | None:
    """
    Run RTL simulation to generate VCD.
    Used when VCD is missing from run directory.
    """
    import subprocess
    from pathlib import Path

    design_dir = Path(r"C:\tools\OpenLane\designs") / design_name
    rtl  = design_dir / f"{design_name}.v"
    tb   = design_dir / f"{design_name}_tb.v"

    if not rtl.exists() or not tb.exists():
        return None

    cmd = [
        "docker", "run", "--rm",
        "-v", r"C:\tools\OpenLane:/work",
        "efabless/openlane:latest",
        "bash", "-c",
        f"cd /work/designs/{design_name} && "
        f"iverilog -o /tmp/sim "
        f"{design_name}.v {design_name}_tb.v && "
        f"vvp /tmp/sim 2>&1"
    ]

    try:
        r = subprocess.run(
            cmd, capture_output=True,
            text=True, timeout=60
        )
        # VCD written to design dir
        vcd = design_dir / "trace.vcd"
        if vcd.exists() and vcd.stat().st_size > 100:
            return str(vcd)
    except Exception:
        pass
    return None


def _show_simulation_log(results_dir: str):
    """Show simulation log as fallback."""
    import streamlit as st
    from pathlib import Path

    log = Path(results_dir) / "simulation.log"
    if log.exists():
        content = log.read_text(errors="ignore")
        lines = content.split('\n')
        for line in lines:
            if 'PASS' in line:
                st.markdown(
                    f"<span style='color:#00ff9d;"
                    f"font-family:monospace'>"
                    f"✓ {line}</span>",
                    unsafe_allow_html=True
                )
            elif 'FAIL' in line:
                st.markdown(
                    f"<span style='color:#ff3333;"
                    f"font-family:monospace'>"
                    f"✗ {line}</span>",
                    unsafe_allow_html=True
                )
            elif line.strip():
                st.markdown(
                    f"<span style='color:#8b949e;"
                    f"font-family:monospace'>"
                    f"{line}</span>",
                    unsafe_allow_html=True
                )


def render_waveform_streamlit(results_dir: str,
                               design_name: str):
    """
    Render waveform viewer in Streamlit.
    Shows VCD signals as timing diagram.
    """
    import streamlit as st

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ SIMULATION WAVEFORMS — TIMING DIAGRAM
    </div>""", unsafe_allow_html=True)

    vcd_path = find_vcd_for_design(results_dir, design_name)

    if not vcd_path:
        # Generate a VCD by running simulation NOW
        st.info("No VCD found. Running simulation...")
        vcd_path = _run_simulation_get_vcd(
            design_name, results_dir
        )

    if not vcd_path:
        st.warning(
            "No simulation waveform available. "
            "This happens when:\n"
            "1. Design was loaded from cache\n"
            "2. Simulation was skipped\n\n"
            "Run the design again to generate waveforms."
        )
        # Show simulation log instead
        _show_simulation_log(results_dir)
        return

    st.caption(f"Source: {Path(vcd_path).name} "
               f"({Path(vcd_path).stat().st_size//1024} KB)")

    # Parse VCD
    with st.spinner("Parsing waveform..."):
        wavedata = parse_vcd(str(vcd_path))

    if not wavedata or not wavedata.get("signals"):
        st.warning("Could not parse waveform data")
        return

    signals  = wavedata["signals"]
    max_time = wavedata["max_time"]
    timescale= wavedata["timescale"]

    st.metric(
        "Simulation Time",
        f"{max_time} {timescale}"
    )

    # Render timing diagram using Plotly — Vivado / Cadence style
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        # ── Color scheme matching Vivado / Cadence waveform viewer ──
        BG_DARK   = '#0a0a1a'       # very dark navy
        BG_PLOT   = '#0d0d22'       # slightly lighter
        GRID_CLR  = '#1a1a3a'       # subtle grid
        GREEN     = '#00ff41'       # bright green (main signal)
        CLK_CLR   = '#22aaff'       # blue for clock
        RST_CLR   = '#ff3344'       # red for reset
        BUS_FILL  = '#0d1117'       # bus interior dark
        BUS_LINE  = '#00ff41'       # bus outline green
        BUS_TXT   = '#ffd700'       # gold hex value text
        LABEL_CLR = '#b0b8c8'       # signal name labels
        RULER_CLR = '#4a5568'       # time ruler ticks
        CURSOR_CLR= '#ffaa00'       # time cursor

        # Sort signals: clk first, reset, then alphabetical others
        sig_order = []
        for name in signals:
            if 'clk' in name.lower():
                sig_order.insert(0, name)
            elif 'reset' in name.lower() or 'rst' in name.lower():
                sig_order.insert(min(1, len(sig_order)), name)
            else:
                sig_order.append(name)
        sig_order = sig_order[:16]

        fig = go.Figure()
        shapes = []
        annotations = []

        ROW_H   = 1.8      # vertical spacing per signal
        WAVE_H  = 0.55     # waveform half-height
        BUS_H   = 0.4      # bus hexagon half-height

        # 1. Collect all unique time points where any signal changes
        all_times = set()
        for sig_name in sig_order:
            sig = signals[sig_name]
            change_points = []
            for t, v in sig.values:
                if t > max_time:
                    break
                change_points.append((t, v))
            if not change_points or change_points[0][0] > 0:
                initial_val = sig.values[0][1] if sig.values else '0'
                change_points.insert(0, (0, initial_val))
            change_points.append((max_time, change_points[-1][1]))
            
            for t, _ in change_points:
                all_times.add(t)
                
        all_times.add(0)
        all_times.add(max_time)
        
        # 2. Add intermediate sampling points for smooth cursor tracking
        step = max(1, max_time // 200)
        for t in range(0, max_time, step):
            all_times.add(t)
            
        sorted_times = sorted(list(all_times))

        # ── Draw horizontal separator lines for each signal row ──
        for i in range(len(sig_order)):
            yc = i * ROW_H
            shapes.append(dict(
                type='line',
                x0=0, y0=yc - ROW_H * 0.48,
                x1=max_time, y1=yc - ROW_H * 0.48,
                line=dict(color='#1a1a3a', width=0.5, dash='dot')
            ))

        # ── Render each signal ──────────────────────────────────
        for i, sig_name in enumerate(sig_order):
            sig = signals[sig_name]
            if not sig.values:
                continue

            yc = i * ROW_H  # vertical center for this signal

            # Pick color based on signal type
            if 'clk' in sig_name.lower():
                color = CLK_CLR
            elif 'reset' in sig_name.lower() or 'rst' in sig_name.lower():
                color = RST_CLR
            else:
                color = GREEN

            # Build change points
            change_points = []
            for t, v in sig.values:
                if t > max_time:
                    break
                change_points.append((t, v))
            if not change_points or change_points[0][0] > 0:
                initial_val = sig.values[0][1] if sig.values else '0'
                change_points.insert(0, (0, initial_val))
            change_points.append((max_time, change_points[-1][1]))

            # Map signal values onto sorted_times for aligned unified hover
            sig_times = []
            sig_values = []
            sig_labels = []
            val_idx = 0
            current_raw_val = '0'
            if sig.values:
                current_raw_val = sig.values[0][1]

            for t in sorted_times:
                while val_idx < len(sig.values) and sig.values[val_idx][0] <= t:
                    current_raw_val = sig.values[val_idx][1]
                    val_idx += 1

                sig_times.append(t)

                if sig.width == 1:
                    try:
                        v_num = int(current_raw_val, 2) if current_raw_val not in ('x', 'z') else 0
                    except ValueError:
                        v_num = 0
                    y_val = yc + WAVE_H if v_num == 1 else yc - WAVE_H
                    sig_values.append(y_val)
                    sig_labels.append(f"{current_raw_val}")
                else:
                    try:
                        if 'x' in current_raw_val.lower() or 'z' in current_raw_val.lower():
                            txt = current_raw_val.upper()
                        else:
                            int_val = int(current_raw_val, 2)
                            txt = f"0x{int_val:X}"
                    except Exception:
                        txt = current_raw_val
                    sig_labels.append(txt)

            # ── Multi-Bit Bus: Hexagonal segments ──────────────
            if sig.width > 1:
                # Add the continuous hover / legend trace FIRST (so it is drawn in the background)
                fig.add_trace(go.Scatter(
                    x=sig_times, y=[yc] * len(sig_times),
                    mode='lines',
                    name=sig_name,
                    line=dict(color=BUS_LINE, width=2),
                    customdata=sig_labels,
                    hovertemplate=f"<b>{sig_name}</b>: %{{customdata}}<extra></extra>",
                    showlegend=True
                ))

                segments = []
                t_prev, val_prev = change_points[0]
                for idx in range(1, len(change_points)):
                    t_curr, val_curr = change_points[idx]
                    if val_curr != val_prev or t_curr == max_time:
                        segments.append((t_prev, t_curr, val_prev))
                        t_prev = t_curr
                        val_prev = val_curr

                hx_all = []
                hy_all = []
                for t1, t2, val in segments:
                    if t2 <= t1:
                        continue
                    delta = min(0.4, (t2 - t1) / 3.0)
                    hx = [t1, t1 + delta, t2 - delta, t2, t2 - delta, t1 + delta, t1, None]
                    hy = [yc, yc + BUS_H, yc + BUS_H, yc, yc - BUS_H, yc - BUS_H, yc, None]
                    hx_all.extend(hx)
                    hy_all.extend(hy)

                # Draw bus outline (masks the center line)
                fig.add_trace(go.Scatter(
                    x=hx_all, y=hy_all,
                    fill='toself',
                    fillcolor=BUS_FILL,
                    line=dict(color=BUS_LINE, width=1.5),
                    mode='lines',
                    showlegend=False,
                    hoverinfo='skip'
                ))

                # Hex value text inside hexagon
                text_x = []
                text_y = []
                text_val = []
                for t1, t2, val in segments:
                    if t2 <= t1:
                        continue
                    try:
                        if 'x' in val.lower() or 'z' in val.lower():
                            txt = val.upper()
                        else:
                            int_val = int(val, 2)
                            txt = f"0x{int_val:X}"
                    except Exception:
                        txt = val

                    delta = min(0.4, (t2 - t1) / 3.0)
                    seg_w = t2 - t1
                    if seg_w > 2 * delta + 0.5:
                        text_x.append((t1 + t2) / 2)
                        text_y.append(yc)
                        text_val.append(txt[:8])

                if text_x:
                    fig.add_trace(go.Scatter(
                        x=text_x, y=text_y,
                        text=text_val,
                        mode='text',
                        textfont=dict(
                            color=BUS_TXT, size=9,
                            family='Consolas, monospace'
                        ),
                        showlegend=False, hoverinfo='none'
                    ))

            # ── Single-Bit Signal: Crisp step waveform ────────
            else:
                fig.add_trace(go.Scatter(
                    x=sig_times, y=sig_values,
                    mode='lines',
                    name=sig_name,
                    line=dict(color=color, width=2, shape='hv'),
                    customdata=sig_labels,
                    hovertemplate=f"<b>{sig_name}</b>: %{{customdata}}<extra></extra>",
                    showlegend=True
                ))

                # Fill under high regions for extra Vivado look
                fill_x = [sig_times[0]] + sig_times + [sig_times[-1], sig_times[0]]
                fill_y = [yc - WAVE_H] + sig_values + [yc - WAVE_H, yc - WAVE_H]

                fig.add_trace(go.Scatter(
                    x=fill_x, y=fill_y,
                    fill='toself',
                    fillcolor=f'rgba({int(color[1:3],16)},'
                              f'{int(color[3:5],16)},'
                              f'{int(color[5:7],16)},0.06)',
                    line=dict(width=0, shape='hv'),
                    mode='lines',
                    showlegend=False, hoverinfo='none'
                ))

        # ── Time cursor line at 60% ──────────────────────────
        cursor_t = max_time * 0.6
        shapes.append(dict(
            type='line',
            x0=cursor_t, y0=-1,
            x1=cursor_t, y1=len(sig_order) * ROW_H,
            line=dict(color=CURSOR_CLR, width=1, dash='dash')
        ))
        annotations.append(dict(
            x=cursor_t, y=len(sig_order) * ROW_H + 0.3,
            text=f"T={int(cursor_t)}",
            font=dict(color=CURSOR_CLR, size=9,
                      family='Consolas, monospace'),
            showarrow=False, xanchor='center'
        ))

        # ── Signal name labels on y-axis ─────────────────────
        tick_vals = [i * ROW_H for i in range(len(sig_order))]
        tick_text = []
        for name in sig_order:
            sig = signals[name]
            last_val = sig.values[-1][1] if sig.values else '?'
            if sig.width > 1:
                try:
                    if 'x' not in last_val.lower() and 'z' not in last_val.lower():
                        last_val = f"0x{int(last_val,2):X}"
                except Exception:
                    pass
            tick_text.append(f"{name}  [{last_val}]")

        # ── Layout: Professional Vivado / Cadence waveform look ─
        fig.update_layout(
            title=dict(
                text=(f"<b>Waveform Viewer</b> — {design_name}"
                      f"  <span style='color:#4a5568;font-size:11px'>"
                      f"({len(sig_order)} signals, "
                      f"{max_time} {timescale})</span>"),
                font=dict(color='#e2e8f0', size=14,
                          family='Consolas, monospace'),
                x=0.01
            ),
            paper_bgcolor=BG_DARK,
            plot_bgcolor=BG_PLOT,
            font=dict(family='Consolas, monospace',
                      color=LABEL_CLR),
            shapes=shapes,
            annotations=annotations,
            xaxis=dict(
                title=dict(
                    text=f"Time ({timescale})",
                    font=dict(color='#4a5568', size=10)
                ),
                gridcolor=GRID_CLR,
                gridwidth=0.5,
                color=RULER_CLR,
                showgrid=True,
                zeroline=False,
                range=[0, max_time],
                tickfont=dict(size=9, color=RULER_CLR,
                              family='Consolas'),
                minor=dict(
                    showgrid=True,
                    gridcolor='#12122a',
                    gridwidth=0.3
                ),
                side='top',
                dtick=max(1, max_time // 10),
                showspikes=True,
                spikethickness=1,
                spikedash='dash',
                spikemode='across',
                spikecolor='#ffaa00',
            ),
            yaxis=dict(
                gridcolor=GRID_CLR,
                gridwidth=0.3,
                tickvals=tick_vals,
                ticktext=tick_text,
                tickfont=dict(size=10, color=LABEL_CLR,
                              family='Consolas'),
                showgrid=False,
                zeroline=False,
                range=[-1.0, len(sig_order) * ROW_H + 0.5],
                fixedrange=True,
            ),
            legend=dict(
                bgcolor=BG_DARK,
                bordercolor='#1a1a3a',
                borderwidth=1,
                font=dict(size=9, color=LABEL_CLR,
                          family='Consolas'),
                x=1.01, y=1
            ),
            height=max(400, len(sig_order) * 55 + 120),
            margin=dict(l=140, r=10, t=55, b=35),
            dragmode='zoom',
            hovermode='x unified',
            spikedistance=-1,
        )

        st.plotly_chart(fig, use_container_width=True)



    except ImportError:
        # Fallback: ASCII waveform
        st.info("Install plotly for graphical waveforms: "
                "pip install plotly")
        st.markdown("**Signal Summary (text)**")
        for sig_name, sig in list(signals.items())[:10]:
            changes = len(sig.values)
            st.markdown(
                f"`{sig_name}`: {changes} transitions"
            )

    # Show simulation log
    sim_log = Path(results_dir) / "simulation.log"
    if sim_log.exists():
        st.markdown("**Simulation Results**")
        content = sim_log.read_text(errors="ignore")
        lines = content.split('\n')
        pass_lines = [l for l in lines
                      if 'PASS' in l or 'FAIL' in l
                      or 'RESULT' in l]
        if pass_lines:
            for line in pass_lines:
                color = 'green' if 'PASS' in line else 'red'
                st.markdown(
                    f"<span style='color:{color};"
                    f"font-family:monospace'>{line}</span>",
                    unsafe_allow_html=True
                )
        else:
            st.code(content[-1000:], language="text")
