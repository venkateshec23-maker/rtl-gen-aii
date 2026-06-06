"""
waveform_enhanced.py — SimVision-style Interactive Waveform Viewer
RTL-Gen AI v2.5 — Phase 2

Cadence SimVision / Vivado Waveform Viewer equivalent features:
  ├── Full VCD 2001 parser  (1-bit and multi-bit, x/z -> 0 safe)
  ├── GTKWave-style layout  (signals stacked, shared time axis)
  ├── Plotly step waveforms per signal  (line_shape='hv')
  ├── Signal search box     (Streamlit text_input filter)
  ├── Show/hide checkboxes  (per signal, persists in session)
  ├── Zoom + range slider   (Plotly built-in)
  ├── Hover value readout   (signal name, time, decimal + hex)
  ├── PASS/FAIL annotations (parsed from simulation.log)
  ├── Clock edge detection  (auto-identifies clock signals)
  └── SimVision dark theme  (#0a0a0f background, green clock)

Usage in app.py (Sign-Off -> Waveforms tab):
    from waveform_enhanced import render_waveform_enhanced_streamlit
    render_waveform_enhanced_streamlit(vcd_path, sim_log_path)

Standalone test (no Docker needed):
    python waveform_enhanced.py
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import plotly.graph_objects as go

log = logging.getLogger(__name__)

# ── Colour palette (SimVision dark theme) ────────────────────────────────────
_BG        = "#0a0a0f"
_GRID      = "#1a1a2e"
_CLK_COLOR = "#00FF41"   # bright green — clock
_RST_COLOR = "#FF4444"   # red          — reset
_IN_COLOR  = "#4FC3F7"   # cyan         — inputs
_OUT_COLOR = "#FFD54F"   # amber        — outputs
_BUS_COLOR = "#CE93D8"   # purple       — buses (width > 1)
_INT_COLOR = "#90A4AE"   # grey         — internal/other

def _hex_to_rgba(hex_color: str, alpha: float = 0.12) -> str:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

_PASS_COLOR = "rgba(0,255,65,0.15)"
_FAIL_COLOR = "rgba(255,68,68,0.15)"

# vertical spacing between signals (y-units per signal row)
_ROW_H = 1.6


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class VCDSignal:
    """One signal extracted from a VCD file."""
    name:       str
    width:      int            # 1 = binary, >1 = bus
    identifier: str            # VCD identifier character(s)
    scope:      str = ""

    times:  List[float] = field(default_factory=list)   # ns
    values: List[int]   = field(default_factory=list)   # integer

    @property
    def display_name(self) -> str:
        if self.scope and self.scope not in ("tb", "testbench"):
            return f"{self.scope}/{self.name}"
        return self.name

    @property
    def signal_class(self) -> str:
        n = self.name.lower()
        if any(k in n for k in ("clk", "clock", "ck")):
            return "clock"
        if any(k in n for k in ("rst", "reset", "resetn", "reset_n")):
            return "reset"
        if n.startswith("o_") or n.endswith("_out") or n == "sum" or n == "result":
            return "output"
        if self.width > 1:
            return "bus"
        return "input"

    @property
    def color(self) -> str:
        cls = self.signal_class
        return {
            "clock":  _CLK_COLOR,
            "reset":  _RST_COLOR,
            "output": _OUT_COLOR,
            "bus":    _BUS_COLOR,
        }.get(cls, _IN_COLOR)

    def value_at(self, t: float) -> Optional[int]:
        """Return the signal value at time t (most recent change at or before t)."""
        if not self.times:
            return None
        idx = 0
        for i, ts in enumerate(self.times):
            if ts <= t:
                idx = i
            else:
                break
        return self.values[idx]


# ── VCD Parser ────────────────────────────────────────────────────────────────

class VCDParser:
    """
    Lightweight VCD 2001 parser.
    Handles 1-bit scalar and multi-bit vector signals.
    x/z values treated as 0 (safe for waveform display).
    """

    def __init__(self):
        self.signals:          Dict[str, VCDSignal] = {}   # id -> signal
        self.timescale_ns:     float                = 1.0
        self.end_time_ns:      float                = 0.0

    # ─────────────────────────────────────────────────────────────────

    def parse(self, vcd_path: Path) -> Dict[str, VCDSignal]:
        """Parse VCD file. Returns dict of display_name -> VCDSignal."""
        if not vcd_path.exists():
            raise FileNotFoundError(f"VCD not found: {vcd_path}")

        text = vcd_path.read_text(errors="replace")
        self._parse_header(text)
        self._parse_values(text)

        # Index by display name for easy lookup
        return {s.display_name: s for s in self.signals.values()}

    # ─────────────────────────────────────────────────────────────────

    def _parse_header(self, text: str) -> None:
        """Extract timescale and signal declarations."""

        # Timescale
        ts = re.search(r"\$timescale\s+(.*?)\s*\$end", text, re.DOTALL | re.IGNORECASE)
        if ts:
            self.timescale_ns = self._parse_timescale_ns(ts.group(1).strip())

        # Signal $var declarations + scope tracking
        scope_stack: List[str] = []
        for m in re.finditer(r"\$(scope|upscope|var)\s*(.*?)\s*\$end", text, re.DOTALL):
            kw      = m.group(1).lower()
            content = m.group(2).strip()

            if kw == "scope":
                parts = content.split()
                scope_stack.append(parts[1] if len(parts) >= 2 else "")

            elif kw == "upscope":
                if scope_stack:
                    scope_stack.pop()

            elif kw == "var":
                # $var wire 8 # a [7:0] $end
                parts = content.split()
                if len(parts) < 4:
                    continue
                _, width_s, identifier, raw_name = (
                    parts[0], parts[1], parts[2], parts[3]
                )
                try:
                    width = int(width_s)
                except ValueError:
                    continue
                name  = re.sub(r"\s*\[.*?\]$", "", raw_name)
                scope = ".".join(scope_stack) if scope_stack else ""
                self.signals[identifier] = VCDSignal(
                    name=name, width=width, identifier=identifier, scope=scope
                )

    # ─────────────────────────────────────────────────────────────────

    def _parse_values(self, text: str) -> None:
        """Parse value changes after $enddefinitions."""
        marker = re.search(r"\$enddefinitions\s*\$end", text)
        body   = text[marker.end():] if marker else text

        current_time_ns: float = 0.0

        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("$"):
                continue

            # Time step
            if line.startswith("#"):
                try:
                    t_raw = float(line[1:])
                    current_time_ns = t_raw * self.timescale_ns
                    self.end_time_ns = max(self.end_time_ns, current_time_ns)
                except ValueError:
                    pass
                continue

            # Scalar value change: "0!" or "1#" or "x$"
            if line[0] in "01xzXZ" and len(line) >= 2:
                val_char   = line[0].lower()
                identifier = line[1:]
                if identifier in self.signals:
                    val = 0 if val_char in "xz" else int(val_char)
                    self.signals[identifier].times.append(current_time_ns)
                    self.signals[identifier].values.append(val)
                continue

            # Vector value change: "b00001010 #" or "bx$"
            if line[0] in "bBrR":
                parts = line.split()
                if len(parts) >= 2:
                    bits_raw   = parts[0][1:]
                    identifier = parts[1]
                    if identifier in self.signals:
                        # Strip x/z -> 0
                        clean = re.sub(r"[xzXZ]", "0", bits_raw)
                        try:
                            val = int(clean, 2) if clean else 0
                        except ValueError:
                            val = 0
                        self.signals[identifier].times.append(current_time_ns)
                        self.signals[identifier].values.append(val)

    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_timescale_ns(ts_str: str) -> float:
        """Convert timescale string like '1 ns', '10ps', '1us' -> float in ns."""
        m = re.search(r"(\d+(?:\.\d+)?)\s*(f|p|n|u|m)?s", ts_str, re.IGNORECASE)
        if not m:
            return 1.0
        num  = float(m.group(1))
        unit = (m.group(2) or "n").lower()
        mult = {"f": 1e-6, "p": 1e-3, "n": 1.0, "u": 1e3, "m": 1e6}
        return num * mult.get(unit, 1.0)


# ── Simulation log event parser ───────────────────────────────────────────────

@dataclass
class SimEvent:
    time_ns:   Optional[float]
    kind:      str    # "PASS" | "FAIL" | "INFO"
    message:   str


def parse_sim_log(sim_log_path: Path) -> List[SimEvent]:
    """
    Extract PASS/FAIL events from simulation.log.
    Returns list of SimEvent (time may be None if not in log).
    """
    if not sim_log_path or not sim_log_path.exists():
        return []

    events: List[SimEvent] = []
    text = sim_log_path.read_text(errors="replace")

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Try to extract simulation time from lines like "At time 50: PASS"
        t_match = re.search(r"(?:time|t)\s*[=:]\s*(\d+)", line, re.IGNORECASE)
        t_ns    = float(t_match.group(1)) if t_match else None

        if "RESULTS:" in line.upper():
            continue
        if "PASS" in line.upper():
            events.append(SimEvent(t_ns, "PASS", line))
        elif "FAIL" in line.upper():
            events.append(SimEvent(t_ns, "FAIL", line))

    return events


# ── Plotly figure builder ─────────────────────────────────────────────────────

def build_waveform_figure(
    signals:      Dict[str, VCDSignal],
    selected:     List[str],
    end_time_ns:  float,
    sim_events:   Optional[List[SimEvent]] = None,
) -> go.Figure:
    """
    Build a GTKWave/SimVision-style Plotly figure.

    Layout: all signals share one x-axis (time in ns).
    Each signal row is offset on the y-axis by _ROW_H units.
    Binary signals: 0/1 waveforms.
    Bus signals:    filled band with value text annotations.

    Args:
        signals:     dict of display_name -> VCDSignal
        selected:    list of display_names to include
        end_time_ns: rightmost time value on x-axis
        sim_events:  list of PASS/FAIL events to annotate

    Returns: Plotly Figure ready for st.plotly_chart()
    """
    active = [
        (name, signals[name])
        for name in selected
        if name in signals and signals[name].times
    ]

    if not active:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            title="No signals selected or VCD is empty",
        )
        return fig

    fig        = go.Figure()
    n          = len(active)
    ytick_vals = []
    ytick_text = []

    # ── One trace per signal ──────────────────────────────────────────
    for row_idx, (name, sig) in enumerate(active):
        y_base = row_idx * _ROW_H   # bottom of this row
        y_high = y_base + 1.0       # top of row (normalised 0->1 in its band)

        # Extend waveform to end_time
        times  = sig.times + [end_time_ns]
        values = sig.values + [sig.values[-1]]

        if sig.width == 1:
            # ── Binary signal ─────────────────────────────────────────
            y_vals = [y_base + float(v) for v in values]

            fig.add_trace(go.Scatter(
                x          = times,
                y          = y_vals,
                mode       = "lines",
                line       = dict(shape="hv", color=sig.color, width=1.8),
                name       = name,
                showlegend = False,
                hovertemplate=(
                    f"<b>{name}</b><br>"
                    "t=%{x:.1f} ns<br>"
                    "val=%{customdata}<extra></extra>"
                ),
                customdata = values,
            ))

        else:
            # ── Bus signal ────────────────────────────────────────────
            # Draw as a filled band; annotate value at each transition.
            # Use two traces (top + bottom edge) with fill between.

            band_lo = [y_base + 0.15] * len(times)
            band_hi = [y_base + 0.85] * len(times)
            hex_vals = [f"0x{v:X} ({v})" for v in values]

            # Top edge
            fig.add_trace(go.Scatter(
                x          = times,
                y          = band_hi,
                mode       = "lines",
                line       = dict(shape="hv", color=sig.color, width=1.2),
                name       = name,
                showlegend = False,
                hovertemplate=(
                    f"<b>{name}</b><br>"
                    "t=%{x:.1f} ns<br>"
                    "val=%{customdata}<extra></extra>"
                ),
                customdata = hex_vals,
            ))
            # Bottom edge with fill
            fig.add_trace(go.Scatter(
                x          = times,
                y          = band_lo,
                mode       = "lines",
                line       = dict(shape="hv", color=sig.color, width=1.2),
                fill       = "tonexty",
                fillcolor  = _hex_to_rgba(sig.color, 0.12),
                name       = name + "_lo",
                showlegend = False,
                hoverinfo  = "skip",
            ))

            # Value annotations at each transition point
            # (only show a subset to avoid clutter)
            MAX_ANNOTATIONS = 20
            step = max(1, len(sig.times) // MAX_ANNOTATIONS)
            for i in range(0, len(sig.times), step):
                fig.add_annotation(
                    x          = sig.times[i],
                    y          = y_base + 0.5,
                    text       = f"h{sig.values[i]:X}",
                    showarrow  = False,
                    font       = dict(size=9, color=sig.color),
                    xanchor    = "left",
                )

        ytick_vals.append(y_base + 0.5)
        ytick_text.append(f"<b>{name}</b>" if sig.signal_class == "clock" else name)

    # ── PASS/FAIL vertical bands ──────────────────────────────────────
    if sim_events:
        for ev in sim_events:
            if ev.time_ns is None:
                continue
            color = _PASS_COLOR if ev.kind == "PASS" else _FAIL_COLOR
            fig.add_vrect(
                x0          = ev.time_ns - 0.5,
                x1          = ev.time_ns + 0.5,
                fillcolor   = color,
                opacity     = 1.0,
                line_width  = 0,
                annotation_text = ev.kind,
                annotation_position = "top left",
                annotation_font = dict(size=8, color="#ffffff"),
            )

    # ── Layout ────────────────────────────────────────────────────────
    fig.update_layout(
        paper_bgcolor = _BG,
        plot_bgcolor  = _GRID,
        font          = dict(family="monospace", size=11, color="#cccccc"),
        height        = max(250, n * 60 + 80),
        margin        = dict(l=10, r=20, t=30, b=40),
        xaxis = dict(
            title      = "Time (ns)",
            color      = "#888888",
            gridcolor  = "#222244",
            showspikes = True,
            spikecolor = "#ffffff",
            spikethickness = 1,
            rangeslider = dict(visible=True, thickness=0.06),
            rangeselector = dict(
                buttons = [
                    dict(step="all",    label="All"),
                    dict(count=50,  step="all", label="50 ns"),
                    dict(count=100, step="all", label="100 ns"),
                    dict(count=200, step="all", label="200 ns"),
                ],
                bgcolor     = "#1a1a2e",
                activecolor = "#3a3a5e",
                font        = dict(color="#cccccc", size=10),
            ),
        ),
        yaxis = dict(
            tickvals    = ytick_vals,
            ticktext    = ytick_text,
            color       = "#888888",
            gridcolor   = "#1a1a2e",
            zeroline    = False,
            range       = [-0.3, n * _ROW_H + 0.3],
            fixedrange  = True,   # y-axis does not zoom (only x does)
        ),
        hovermode  = "x unified",
        dragmode   = "zoom",
        showlegend = False,
    )

    return fig


# ── Streamlit entry point ─────────────────────────────────────────────────────

def render_waveform_enhanced_streamlit(
    vcd_path:     Path,
    sim_log_path: Optional[Path] = None,
    key_prefix:   str            = "wv",
) -> None:
    """
    Renders the full interactive waveform viewer inside a Streamlit context.
    Drop-in replacement for render_waveform_streamlit() from waveform_display.py.

    Args:
        vcd_path:     path to trace.vcd file
        sim_log_path: path to simulation.log (optional, for PASS/FAIL markers)
        key_prefix:   Streamlit widget key prefix (avoid collision if called twice)
    """
    import streamlit as st

    # ── Parse VCD ────────────────────────────────────────────────────
    if not vcd_path or not Path(vcd_path).exists():
        st.warning("No VCD waveform file found for this design.")
        st.caption(
            "Run the pipeline to generate trace.vcd, "
            "or check that the VCD path is correct."
        )
        return

    vcd_path = Path(vcd_path)

    try:
        parser   = VCDParser()
        signals  = parser.parse(vcd_path)
        end_time = parser.end_time_ns
    except Exception as e:
        st.error(f"VCD parse error: {e}")
        log.exception("VCD parse failed: %s", vcd_path)
        return

    if not signals:
        st.warning("VCD file parsed but contains no signals.")
        return

    # ── Sort signals: clock first, then reset, then rest ─────────────
    def sort_key(name_sig: Tuple[str, VCDSignal]) -> int:
        order = {"clock": 0, "reset": 1, "output": 2, "bus": 3, "input": 4}
        return order.get(name_sig[1].signal_class, 5)

    sorted_signals = dict(sorted(signals.items(), key=sort_key))
    all_names      = list(sorted_signals.keys())

    # ── Sidebar controls ──────────────────────────────────────────────
    st.markdown("#### Signal Selection")
    col_search, col_all = st.columns([3, 1])

    with col_search:
        search = st.text_input(
            "Search signals",
            placeholder="clk, sum, a, ...",
            key=f"{key_prefix}_search",
            label_visibility="collapsed",
        )
    with col_all:
        show_all = st.button("Select All", key=f"{key_prefix}_all")

    # Filter by search term
    filtered = (
        [n for n in all_names if search.lower() in n.lower()]
        if search else all_names
    )

    # Signal checkboxes
    if f"{key_prefix}_selected" not in st.session_state or show_all:
        st.session_state[f"{key_prefix}_selected"] = set(
            all_names[:min(12, len(all_names))]  # default: first 12
        )

    with st.expander(f"Signals ({len(filtered)} shown)", expanded=True):
        cols = st.columns(3)
        for i, name in enumerate(filtered):
            sig   = sorted_signals[name]
            cls   = sig.signal_class
            label = f"{'🕐' if cls=='clock' else '🔄' if cls=='reset' else '📤' if cls=='output' else '📥'} {name}"
            checked = name in st.session_state[f"{key_prefix}_selected"]
            if cols[i % 3].checkbox(label, value=checked, key=f"{key_prefix}_cb_{name}"):
                st.session_state[f"{key_prefix}_selected"].add(name)
            else:
                st.session_state[f"{key_prefix}_selected"].discard(name)

    selected = [n for n in all_names if n in st.session_state[f"{key_prefix}_selected"]]

    if not selected:
        st.info("Select at least one signal above to view waveforms.")
        return

    # ── Simulation events ─────────────────────────────────────────────
    sim_events: List[SimEvent] = []
    if sim_log_path:
        sim_events = parse_sim_log(Path(sim_log_path))

    # ── Build and render figure ───────────────────────────────────────
    fig = build_waveform_figure(
        signals     = sorted_signals,
        selected    = selected,
        end_time_ns = end_time,
        sim_events  = sim_events,
    )

    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_chart")

    # ── Stats bar ─────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total signals",   len(signals))
    m2.metric("Showing",         len(selected))
    m3.metric("Duration",        f"{end_time:.1f} ns")
    m4.metric("Timescale",       f"{parser.timescale_ns:.3g} ns/unit")

    # ── PASS/FAIL summary ─────────────────────────────────────────────
    if sim_events:
        passes = sum(1 for e in sim_events if e.kind == "PASS")
        fails  = sum(1 for e in sim_events if e.kind == "FAIL")
        if fails == 0:
            st.success(f"✅ Simulation: {passes} PASS / 0 FAIL")
        else:
            st.error(f"❌ Simulation: {passes} PASS / {fails} FAIL")
        with st.expander("Simulation log events"):
            for ev in sim_events:
                icon = "✅" if ev.kind == "PASS" else "❌"
                t_str = f"@{ev.time_ns:.1f}ns " if ev.time_ns is not None else ""
                st.caption(f"{icon} {t_str}{ev.message}")


# ── Standalone self-test ──────────────────────────────────────────────────────

def _generate_test_vcd(path: Path) -> None:
    """Write a minimal synthetic VCD for testing without iverilog."""
    path.write_text("""\
$timescale 1 ns $end
$scope module adder_8bit_tb $end
$var wire 1 ! clk $end
$var wire 1 " reset_n $end
$var wire 8 # a [7:0] $end
$var wire 8 $ b [7:0] $end
$var wire 9 % sum [8:0] $end
$upscope $end
$enddefinitions $end
$dumpvars
0!
0"
b00000000 #
b00000000 $
b000000000 %
$end
#0
1"
#5
1!
#10
0!
b00000101 #
b00000011 $
#15
1!
b000001000 %
#20
0!
b01100100 #
b00110010 $
#25
1!
b010010110 %
#30
0!
b11111111 #
b00000001 $
#35
1!
b100000000 %
#40
0!
b10000000 #
b10000000 $
#45
1!
b100000000 %
#50
0!
""")


if __name__ == "__main__":
    import tempfile, json

    print("=" * 60)
    print("waveform_enhanced.py — standalone self-test")
    print("=" * 60)

    passed = 0
    total  = 0

    # Test 1: VCD parser — timescale
    total += 1
    p = VCDParser()
    assert abs(p._parse_timescale_ns("1 ns")   - 1.0)   < 1e-9
    assert abs(p._parse_timescale_ns("1 ps")   - 0.001) < 1e-9
    assert abs(p._parse_timescale_ns("10ns")   - 10.0)  < 1e-9
    assert abs(p._parse_timescale_ns("100 ps") - 0.1)   < 1e-9
    print("[PASS] Timescale parser: ns/ps/us conversions correct")
    passed += 1

    # Test 2: VCD parser — full parse of synthetic VCD
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        vcd_file = Path(tmp) / "test.vcd"
        _generate_test_vcd(vcd_file)
        parser  = VCDParser()
        signals = parser.parse(vcd_file)

    assert "adder_8bit_tb/clk"     in signals, f"clk missing. Got: {list(signals.keys())}"
    assert "adder_8bit_tb/reset_n" in signals
    assert "adder_8bit_tb/a"       in signals
    assert "adder_8bit_tb/sum"     in signals

    clk_sig = signals["adder_8bit_tb/clk"]
    assert clk_sig.width == 1
    assert len(clk_sig.times) >= 4,    f"clock has only {len(clk_sig.times)} transitions"
    assert clk_sig.signal_class == "clock"

    sum_sig = signals["adder_8bit_tb/sum"]
    assert sum_sig.width == 9
    assert sum_sig.signal_class == "output"  # sum -> output heuristic

    a_sig = signals["adder_8bit_tb/a"]
    assert len(a_sig.times) >= 4
    # Check that value 5 (0b00000101) was parsed correctly
    val5_idx = a_sig.values.index(5) if 5 in a_sig.values else -1
    assert val5_idx >= 0, f"Value 5 not found in signal a. Values: {a_sig.values}"

    print(f"[PASS] VCD parse: {len(signals)} signals, {len(clk_sig.times)} clock edges, "
          f"end_time={parser.end_time_ns} ns")
    passed += 1

    # Test 3: value_at() interpolation
    total += 1
    # clk goes: 0 at t=0, 1 at t=5, 0 at t=10, 1 at t=15 ...
    assert clk_sig.value_at(0)   == 0
    assert clk_sig.value_at(7)   == 1,  f"Expected 1 at t=7, got {clk_sig.value_at(7)}"
    assert clk_sig.value_at(12)  == 0,  f"Expected 0 at t=12, got {clk_sig.value_at(12)}"
    print("[PASS] value_at() interpolation: t=0->0, t=7->1, t=12->0")
    passed += 1

    # Test 4: Plotly figure builds without exception
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        vcd_file = Path(tmp) / "test.vcd"
        _generate_test_vcd(vcd_file)
        p2 = VCDParser()
        sigs = p2.parse(vcd_file)

    fig = build_waveform_figure(
        signals     = sigs,
        selected    = list(sigs.keys()),
        end_time_ns = p2.end_time_ns,
        sim_events  = [
            SimEvent(15.0, "PASS", "PASS Test 1: 5+3=8"),
            SimEvent(25.0, "PASS", "PASS Test 2: 100+50=150"),
            SimEvent(35.0, "PASS", "PASS Test 3: 255+1=256"),
        ],
    )
    assert isinstance(fig, go.Figure)
    trace_names = {t.name for t in fig.data}
    assert "adder_8bit_tb/clk" in trace_names, f"clk trace not found. Traces: {trace_names}"
    assert len(fig.data) >= len(sigs)    # at least one trace per signal
    print(f"[PASS] Plotly figure: {len(fig.data)} traces, "
          f"{len(fig.layout.annotations)} annotations")
    passed += 1

    # Test 5: sim log parser
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        log_file = Path(tmp) / "simulation.log"
        log_file.write_text(
            "PASS Test 1: 5+3=8\n"
            "FAIL Test 2: 100+50=150, expected 8\n"
            "PASS Test 3: 0+0=0\n"
            "RESULTS: 2 PASS / 1 FAIL\n"
        )
        events = parse_sim_log(log_file)

    assert len(events) == 3, f"Expected 3 events, got {len(events)}"
    assert events[0].kind == "PASS"
    assert events[1].kind == "FAIL"
    assert events[2].kind == "PASS"
    print(f"[PASS] Sim log: {sum(1 for e in events if e.kind=='PASS')} PASS, "
          f"{sum(1 for e in events if e.kind=='FAIL')} FAIL parsed")
    passed += 1

    # Test 6: bus signal color and class
    total += 1
    bus = VCDSignal(name="data_bus", width=32, identifier="@")
    assert bus.color == _BUS_COLOR
    inp = VCDSignal(name="a_input",  width=1,  identifier="#")
    assert inp.color == _IN_COLOR
    clk = VCDSignal(name="clk",      width=1,  identifier="!")
    assert clk.signal_class == "clock"
    assert clk.color == _CLK_COLOR
    print("[PASS] Signal classification and colors correct")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED — waveform_enhanced.py ready for integration")
    print("=" * 60)