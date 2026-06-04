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
              max_time:    int = 10000) -> Dict:
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

    # Render timing diagram using Plotly
    try:
        import plotly.graph_objects as go

        fig = go.Figure()

        # Sort signals: clk first, then reset, then others
        sig_order = []
        for name in signals:
            if 'clk' in name.lower():
                sig_order.insert(0, name)
            elif 'reset' in name.lower() or 'rst' in name.lower():
                sig_order.insert(1, name)
            else:
                sig_order.append(name)

        sig_order = sig_order[:16]  # max 16 signals

        bus_h = 0.35
        wire_h = 0.35

        for i, sig_name in enumerate(sig_order):
            sig = signals[sig_name]
            if not sig.values:
                continue

            yc = i * 1.5  # vertical spacing center

            # Color by signal type
            if 'clk' in sig_name.lower():
                color = '#00d4ff'  # Bright Cyan for clock
            elif 'reset' in sig_name.lower() or 'rst' in sig_name.lower():
                color = '#ff3333'  # Red for reset
            elif 'out' in sig_name.lower() or \
                 sig_name.startswith('sum') or \
                 sig_name.startswith('result') or \
                 sig_name.startswith('count'):
                color = '#00ff9d'  # Bright Green for outputs
            else:
                color = '#ffffff'  # White for inputs/internal

            # Create standard time change points up to max_time
            change_points = []
            for t, v in sig.values:
                if t > max_time:
                    break
                change_points.append((t, v))

            # Ensure we start at time 0
            if not change_points or change_points[0][0] > 0:
                initial_val = sig.values[0][1] if sig.values else '0'
                change_points.insert(0, (0, initial_val))

            # End at max_time
            change_points.append((max_time, change_points[-1][1]))

            # Render Multi-Bit Bus Signal (Vivado/Cadence style Hexagons)
            if sig.width > 1:
                # Group consecutive identical values to draw clean segments
                segments = []
                t_prev, val_prev = change_points[0]
                
                for idx in range(1, len(change_points)):
                    t_curr, val_curr = change_points[idx]
                    if val_curr != val_prev or t_curr == max_time:
                        segments.append((t_prev, t_curr, val_prev))
                        t_prev = t_curr
                        val_prev = val_curr

                # Draw each bus segment
                for t1, t2, val in segments:
                    if t2 <= t1:
                        continue

                    # Parse and format the value to Hexadecimal
                    try:
                        if 'x' in val.lower() or 'z' in val.lower():
                            txt = val.upper()
                        else:
                            int_val = int(val, 2)
                            txt = f"{hex(int_val)[2:].upper()}"
                    except Exception:
                        txt = val

                    # Crossover slope width (0.4ns or 10% of segment)
                    delta = min(0.3, (t2 - t1) / 3.0)

                    # Trace hexagonal shape
                    hx = [t1, t1 + delta, t2 - delta, t2, t2 - delta, t1 + delta, t1]
                    hy = [yc, yc + bus_h, yc + bus_h, yc, yc - bus_h, yc - bus_h, yc]

                    fig.add_trace(go.Scatter(
                        x=hx, y=hy,
                        fill="toself",
                        fillcolor="#111622",
                        line=dict(color='#e2e8f0', width=1.2),
                        mode='lines',
                        hoverinfo='text',
                        hovertext=f"{sig_name}: {txt} at {t1}-{t2} {timescale}",
                        name=sig_name,
                        showlegend=(t1 == 0)
                    ))

                    # Value Text inside the Hexagon
                    if (t2 - t1) > 2 * delta:
                        fig.add_trace(go.Scatter(
                            x=[(t1 + t2)/2], y=[yc],
                            text=[txt[:8]],
                            mode='text',
                            textfont=dict(color='#ffd700', size=8, family='Share Tech Mono', weight='bold'),
                            showlegend=False,
                            hoverinfo='none'
                        ))

            # Render Single-Bit Signal (Crisp step lines)
            else:
                times = []
                values = []
                
                for t, val in change_points:
                    try:
                        v_num = int(val, 2) if val not in ('x', 'z') else 0
                    except ValueError:
                        v_num = 0
                    
                    # Normalize y position
                    y_val = yc + wire_h if v_num == 1 else yc - wire_h
                    
                    if times:
                        # Hold previous value up to current change time (hv step)
                        times.append(t)
                        values.append(values[-1])
                        
                    times.append(t)
                    values.append(y_val)

                fig.add_trace(go.Scatter(
                    x=times, y=values,
                    mode='lines',
                    name=sig_name,
                    line=dict(color=color, width=1.8),
                    hoverinfo='text',
                    hovertext=f"{sig_name} at change points",
                    showlegend=True
                ))

        # Layout styling: Dark grid similar to Vivado Simulation view
        fig.update_layout(
            title=dict(
                text=f"Simulation Timing Diagram — {design_name}",
                font=dict(color='#c9d1d9', size=13, family='Share Tech Mono')
            ),
            paper_bgcolor='#080c14',
            plot_bgcolor='#0b0f19',
            font=dict(
                family='Share Tech Mono',
                color='#c9d1d9'
            ),
            xaxis=dict(
                title=f"Time ({timescale})",
                gridcolor='#1e293b',
                color='#8b949e',
                showgrid=True,
                zeroline=False,
                range=[0, max_time]
            ),
            yaxis=dict(
                title="Signals",
                gridcolor='#1e293b',
                tickvals=[i * 1.5 for i in range(len(sig_order))],
                ticktext=sig_order,
                color='#8b949e',
                showgrid=True,
                zeroline=False,
                range=[-1.0, len(sig_order) * 1.5 - 0.5]
            ),
            legend=dict(
                bgcolor='#080c14',
                bordercolor='#2d3748',
                font=dict(size=8, color='#8b949e')
            ),
            height=max(350, len(sig_order) * 45 + 100),
            margin=dict(l=50, r=20, t=50, b=50)
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
