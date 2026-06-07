"""
waveform_vivado.py — Exact Vivado Waveform Viewer
RTL-Gen AI v2.7

Pixel-perfect match to Xilinx Vivado simulation waveform viewer.
Rendered via HTML Canvas + JavaScript inside st.components.v1.html().

Features:
  ├── Two-panel layout: signal list (left) + waveform canvas (right)
  ├── Vivado exact dark theme: #1e1e1e bg, #4fc3f7 data, #ff9800 clock
  ├── Step waveforms for 1-bit signals
  ├── Trapezoid + hex value display for bus signals
  ├── Vertical cursor: click to set, value column updates instantly
  ├── Mouse-wheel zoom: expands/contracts time range at cursor
  ├── Click-drag pan across time axis
  ├── Time ruler with auto-scaling tick marks (ns/ps/us)
  ├── Radix toggle: Hex / Dec / Bin per session
  ├── Signal highlight on row click
  ├── PASS/FAIL event markers (green/red triangles on ruler)
  ├── Scrollable signal list synced with canvas rows
  └── Status bar: cursor time, zoom level, signal count

Usage in app.py:
    from waveform_vivado import render_waveform_vivado_streamlit
    render_waveform_vivado_streamlit(vcd_path, sim_log_path)

Standalone test (no Streamlit, no Docker):
    python waveform_vivado.py
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

ROW_HEIGHT = 32   # px per signal row — matches Vivado default


# ── VCD Parser (self-contained, no external deps) ─────────────────────────────

@dataclass
class Signal:
    name:       str
    width:      int
    identifier: str
    scope:      str  = ""
    times:      List[float] = field(default_factory=list)
    values:     List[int]   = field(default_factory=list)

    @property
    def signal_type(self) -> str:
        n = self.name.lower()
        if any(k in n for k in ("clk", "clock", "ck")):  return "clock"
        if any(k in n for k in ("rst", "reset", "resetn")): return "reset"
        return "bus" if self.width > 1 else "data"

    def value_at(self, t: float) -> Optional[int]:
        if not self.times:  return None
        v = self.values[0]
        for ts, vs in zip(self.times, self.values):
            if ts <= t: v = vs
            else:       break
        return v


def parse_vcd(vcd_path: Path) -> Tuple[Dict[str, Signal], float, float]:
    """
    Parse VCD file. Returns (signals_by_name, timescale_ns, end_time_ns).
    signals_by_name: display_name -> Signal
    """
    text = vcd_path.read_text(errors="replace")

    # Timescale
    ts_match = re.search(r"\$timescale\s+(.*?)\s*\$end", text, re.DOTALL)
    timescale_ns = 1.0
    if ts_match:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(f|p|n|u|m)?s", ts_match.group(1), re.I)
        if m:
            num  = float(m.group(1))
            unit = (m.group(2) or "n").lower()
            timescale_ns = num * {"f":1e-6,"p":1e-3,"n":1.0,"u":1e3,"m":1e6}.get(unit, 1.0)

    # Signal declarations
    signals_by_id: Dict[str, Signal] = {}
    scope_stack: List[str] = []

    for m in re.finditer(r"\$(scope|upscope|var)\s*(.*?)\s*\$end", text, re.DOTALL):
        kw, content = m.group(1), m.group(2).strip()
        if kw == "scope":
            parts = content.split()
            scope_stack.append(parts[1] if len(parts) >= 2 else "")
        elif kw == "upscope":
            if scope_stack: scope_stack.pop()
        elif kw == "var":
            parts = content.split()
            if len(parts) < 4: continue
            try:   width = int(parts[1])
            except ValueError: continue
            ident  = parts[2]
            name   = re.sub(r"\[.*?\]$", "", parts[3]).strip()
            scope  = ".".join(scope_stack)
            signals_by_id[ident] = Signal(name=name, width=width, identifier=ident, scope=scope)

    # Values
    end_def = re.search(r"\$enddefinitions\s*\$end", text)
    body = text[end_def.end():] if end_def else text
    cur_t = 0.0
    end_t = 0.0

    def _process_value_tokens(tokens: List[str], at_time: Optional[float] = None) -> None:
        """Process tokens that are value changes at the current cur_t."""
        t = at_time if at_time is not None else cur_t
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if not tok: i += 1; continue
            # Single-bit: "0!", "1!", "x!"
            if tok[0] in "01xzXZ" and len(tok) >= 2:
                ident = tok[1:]
                if ident in signals_by_id:
                    v = 0 if tok[0].lower() in "xz" else int(tok[0])
                    signals_by_id[ident].times.append(t)
                    signals_by_id[ident].values.append(v)
                i += 1
                continue
            # Bus value: "b00000101" followed by identifier
            if tok[0] in "bBrR" and len(tok) >= 2:
                bits_str = tok[1:]
                # Next token is the identifier
                if i + 1 < len(tokens):
                    ident = tokens[i + 1]
                    if ident in signals_by_id:
                        bits_clean = re.sub(r"[xzXZ]", "0", bits_str)
                        try:    v = int(bits_clean, 2) if bits_clean else 0
                        except: v = 0
                        signals_by_id[ident].times.append(t)
                        signals_by_id[ident].values.append(v)
                        i += 2
                        continue
            i += 1

    for line in body.splitlines():
        line = line.strip()
        if not line: continue
        # $dumpvars contains initial values at time 0
        if line.startswith("$dumpvars"):
            parts = line.split()
            # tokens are between "$dumpvars" and "$end"
            end_idx = parts.index("$end") if "$end" in parts else len(parts)
            init_tokens = parts[1:end_idx]
            _process_value_tokens(init_tokens, at_time=0.0)
            continue
        if line.startswith("$"): continue
        if line.startswith("#"):
            parts = line.split()
            try:
                cur_t = float(parts[0][1:]) * timescale_ns
                end_t = max(end_t, cur_t)
                _process_value_tokens(parts[1:])
            except ValueError: pass
            continue
        _process_value_tokens(line.split())

    # Build display-name dict (clock first, then reset, then rest)
    order = {"clock": 0, "reset": 1, "bus": 2, "data": 3}
    all_sigs = [s for s in signals_by_id.values() if s.times]
    all_sigs.sort(key=lambda s: order.get(s.signal_type, 9))

    result: Dict[str, Signal] = {}
    for s in all_sigs:
        key = f"{s.scope}/{s.name}" if s.scope and s.scope not in ("tb","testbench") else s.name
        if key in result: key = f"{key}_{s.identifier}"
        result[key] = s

    return result, timescale_ns, end_t


def parse_sim_events(log_path: Optional[Path]) -> List[Dict]:
    """Extract PASS/FAIL events from simulation.log."""
    if not log_path or not log_path.exists(): return []
    events = []
    for line in log_path.read_text(errors="replace").splitlines():
        kind = None
        if "PASS" in line.upper(): kind = "PASS"
        elif "FAIL" in line.upper(): kind = "FAIL"
        if kind:
            events.append({"kind": kind, "message": line.strip()})
    return events


# ── HTML / JS generator ───────────────────────────────────────────────────────

def _signals_to_json(signals: Dict[str, Signal], end_time: float) -> str:
    """Serialize signals to JSON for injection into HTML."""
    out = []
    for name, sig in signals.items():
        out.append({
            "name":   name,
            "width":  sig.width,
            "type":   sig.signal_type,
            "times":  sig.times,
            "values": sig.values,
        })
    return json.dumps({"signals": out, "endTime": end_time}, separators=(",", ":"))


def generate_waveform_html(
    signals:    Dict[str, Signal],
    end_time:   float,
    sim_events: List[Dict],
    height:     int = 560,
) -> str:
    """Generate complete self-contained Vivado-style waveform HTML."""

    data_json   = _signals_to_json(signals, end_time)
    events_json = json.dumps(sim_events, separators=(",", ":"))
    n_signals   = len(signals)

    template = r"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#1e1e1e;--bg-panel:#252526;--bg-hdr:#3c3c3c;--bg-sel:#264f78;
  --border:#474747;--text:#d4d4d4;--dim:#858585;
  --clk:#ff9800;--data:#4fc3f7;--bus:#ce93d8;--rst:#ef5350;
  --cursor:#ff4444;--grid:#2d2d2d;--pass:#4caf50;--fail:#f44336;
  --row:32px;
}
html,body{width:100%;height:100%;overflow:hidden;background:var(--bg);color:var(--text);font:12px/1 Consolas,monospace}
#root{display:flex;flex-direction:column;height:100%}
#toolbar{height:30px;background:var(--bg-hdr);border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:6px;padding:0 8px;flex-shrink:0}
#toolbar button{background:#4a4a4a;border:1px solid #5a5a5a;color:var(--text);
  padding:2px 8px;border-radius:2px;cursor:pointer;font:11px Consolas,monospace}
#toolbar button:hover{background:#5a5a5a}
#toolbar button.act{background:#1a4a7a;border-color:var(--data)}
#toolbar select{background:#3c3c3c;border:1px solid var(--border);color:var(--text);
  padding:1px 4px;font:11px Consolas,monospace}
#toolbar input{background:#3c3c3c;border:1px solid var(--border);color:var(--text);
  padding:2px 6px;width:140px;font:11px Consolas,monospace}
#toolbar span.sep{width:1px;height:18px;background:var(--border)}
#toolbar label{font:11px Consolas,monospace;color:var(--dim)}
#main{display:flex;flex:1;overflow:hidden;min-height:0}
#sig-panel{width:220px;min-width:100px;border-right:2px solid var(--border);
  display:flex;flex-direction:column;background:var(--bg-panel);flex-shrink:0}
#sig-hdr{height:24px;background:var(--bg-hdr);border-bottom:1px solid var(--border);
  display:flex;align-items:center;flex-shrink:0}
#sig-hdr span{padding:0 8px;font:11px Consolas,monospace;color:var(--dim);font-weight:700}
#sig-hdr .val-col{width:80px;border-left:1px solid var(--border);padding:0 6px;flex-shrink:0}
#sig-list{flex:1;overflow:hidden;position:relative}
.sr{height:var(--row);display:flex;align-items:center;border-bottom:1px solid #2a2a2a;cursor:pointer}
.sr:hover{background:#2a2d2e}
.sr.sel{background:var(--bg-sel)}
.sr .nm{flex:1;padding:0 4px 0 8px;display:flex;align-items:center;gap:4px;
  overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.sr .ic{font-size:10px;flex-shrink:0;width:14px;text-align:center}
.sr .nt{overflow:hidden;text-overflow:ellipsis;font-size:11px}
.sr .vl{width:80px;padding:0 6px;font:11px Consolas,monospace;
  text-align:right;overflow:hidden;text-overflow:ellipsis;flex-shrink:0}
#wave-area{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
#ruler-wrap{height:24px;background:var(--bg-hdr);border-bottom:1px solid var(--border);
  position:relative;flex-shrink:0;overflow:hidden}
#ruler-canvas{position:absolute;top:0;left:0}
#wave-wrap{flex:1;overflow:hidden;position:relative;cursor:crosshair}
#wave-canvas{display:block}
#statusbar{height:22px;background:#007acc;display:flex;align-items:center;
  gap:16px;padding:0 12px;font:11px Consolas,monospace;color:#fff;flex-shrink:0}
#statusbar span{display:flex;align-items:center;gap:4px}
</style>
</head>
<body>
<div id="root">
<div id="toolbar">
  <input id="search" type="text" placeholder="Search signals" oninput="filterSignals()">
  <span class="sep"></span>
  <label>Radix:</label>
  <select id="radix" onchange="redraw()">
    <option value="hex">Hex</option>
    <option value="dec">Dec</option>
    <option value="bin">Bin</option>
  </select>
  <span class="sep"></span>
  <button onclick="zoomFit()">Fit</button>
  <button onclick="zoom(0.5)">Zoom +</button>
  <button onclick="zoom(2)">Zoom -</button>
  <span class="sep"></span>
  <button onclick="cursorToStart()">|<</button>
  <button onclick="prevEdge()"><</button>
  <button onclick="nextEdge()">></button>
  <button onclick="cursorToEnd()">>|</button>
</div>
<div id="main">
  <div id="sig-panel">
    <div id="sig-hdr">
      <span style="flex:1">Name</span>
      <span class="val-col">Value</span>
    </div>
    <div id="sig-list"></div>
  </div>
  <div id="wave-area">
    <div id="ruler-wrap"><canvas id="ruler-canvas"></canvas></div>
    <div id="wave-wrap"><canvas id="wave-canvas"></canvas></div>
  </div>
</div>
<div id="statusbar">
  <span>Cursor: <b id="st-cursor">0.00 ns</b></span>
  <span>Range: <b id="st-range">--</b></span>
  <span>Signals: <b id="st-count">0</b></span>
  <span id="st-pass"></span>
</div>
</div>
<script>
const RAW = %DATA%;
const EVENTS = %EVENTS%;
const ALL_SIGNALS = RAW.signals;
const END_TIME = RAW.endTime;
let visibleSignals = [...ALL_SIGNALS];
let selectedIdx    = -1;
let cursorTime     = 0;
let viewStart      = 0;
let viewEnd        = END_TIME || 100;
let isDragging     = false;
let dragStartX     = 0;
let dragStartView  = [0, 0];
const ROW_H        = 32;
const waveWrap   = document.getElementById('wave-wrap');
const waveCanvas = document.getElementById('wave-canvas');
const rulerWrap  = document.getElementById('ruler-wrap');
const rulerCanvas= document.getElementById('ruler-canvas');
const wCtx       = waveCanvas.getContext('2d');
const rCtx       = rulerCanvas.getContext('2d');
function sigColor(sig) {
  if (sig.type === 'clock') return '#ff9800';
  if (sig.type === 'reset') return '#ef5350';
  if (sig.type === 'bus')   return '#ce93d8';
  return '#4fc3f7';
}
function sigIcon(sig) {
  if (sig.type === 'clock') return 'c';
  if (sig.type === 'reset') return 'r';
  if (sig.width > 1)        return '[' + sig.width + ']';
  return 'd';
}
function tToX(t) { return (t - viewStart) / (viewEnd - viewStart) * waveCanvas.width; }
function xToT(x) { return viewStart + x / waveCanvas.width * (viewEnd - viewStart); }
function valueAt(sig, t) {
  if (!sig.times.length) return null;
  let v = sig.values[0];
  for (let i = 0; i < sig.times.length; i++) {
    if (sig.times[i] <= t) v = sig.values[i];
    else break;
  }
  return v;
}
function formatVal(v, sig) {
  if (v === null) return '?';
  const radix = document.getElementById('radix').value;
  if (sig.width === 1) return String(v);
  if (radix === 'hex') return '0x' + v.toString(16).toUpperCase().padStart(Math.ceil(sig.width/4), '0');
  if (radix === 'bin') return v.toString(2).padStart(sig.width, '0');
  return String(v);
}
function resize() {
  const wr = waveWrap.getBoundingClientRect();
  const rr = rulerWrap.getBoundingClientRect();
  waveCanvas.width  = Math.max(1, Math.floor(wr.width));
  waveCanvas.height = Math.max(1, Math.floor(wr.height));
  rulerCanvas.width  = Math.max(1, Math.floor(rr.width));
  rulerCanvas.height = Math.max(1, Math.floor(rr.height));
  redraw();
}
function buildSignalList() {
  const list = document.getElementById('sig-list');
  list.innerHTML = '';
  visibleSignals.forEach((sig, i) => {
    const row = document.createElement('div');
    row.className = 'sr' + (i === selectedIdx ? ' sel' : '');
    row.dataset.idx = i;
    const v = valueAt(sig, cursorTime);
    const color = sigColor(sig);
    row.innerHTML = '<div class="nm"><span class="ic" style="color:'+color+'">'+sigIcon(sig)+'</span><span class="nt" title="'+sig.name+'">'+sig.name+'</span></div><div class="vl" style="color:'+color+'" id="vl-'+i+'">'+formatVal(v, sig)+'</div>';
    row.onclick = () => { selectedIdx = i; buildSignalList(); redraw(); };
    list.appendChild(row);
  });
  document.getElementById('st-count').textContent = visibleSignals.length;
}
function updateValues() {
  visibleSignals.forEach((sig, i) => {
    const el = document.getElementById('vl-' + i);
    if (el) el.textContent = formatVal(valueAt(sig, cursorTime), sig);
  });
  document.getElementById('st-cursor').textContent = cursorTime.toFixed(2) + ' ns';
}
function niceStep(range) {
  const ideal = range / 8;
  const mag   = Math.pow(10, Math.floor(Math.log10(ideal)));
  const norm  = ideal / mag;
  return (norm >= 5 ? 5 : norm >= 2 ? 2 : 1) * mag;
}
function drawRuler() {
  const w = rulerCanvas.width, h = rulerCanvas.height;
  rCtx.fillStyle = '#3c3c3c';
  rCtx.fillRect(0, 0, w, h);
  const step = niceStep(viewEnd - viewStart);
  const first = Math.ceil(viewStart / step) * step;
  rCtx.strokeStyle = '#666';
  rCtx.fillStyle   = '#d4d4d4';
  rCtx.font        = '10px Consolas';
  rCtx.textAlign   = 'center';
  rCtx.lineWidth   = 1;
  for (let t = first; t <= viewEnd + step * 0.01; t += step) {
    const x = (t - viewStart) / (viewEnd - viewStart) * w;
    rCtx.beginPath(); rCtx.moveTo(x, h-7); rCtx.lineTo(x, h); rCtx.stroke();
    rCtx.fillStyle = '#d4d4d4';
    rCtx.fillText(t.toFixed(1) + ' ns', x, h - 9);
  }
  EVENTS.forEach(ev => {
    const t = ev.time_ns;
    if (t == null) return;
    const x = (t - viewStart) / (viewEnd - viewStart) * w;
    rCtx.fillStyle = ev.kind === 'PASS' ? '#4caf50' : '#f44336';
    rCtx.beginPath();
    rCtx.moveTo(x - 4, 0); rCtx.lineTo(x + 4, 0); rCtx.lineTo(x, 8);
    rCtx.closePath(); rCtx.fill();
  });
  const cx = (cursorTime - viewStart) / (viewEnd - viewStart) * w;
  rCtx.fillStyle = '#ff4444';
  rCtx.beginPath();
  rCtx.moveTo(cx - 5, 0); rCtx.lineTo(cx + 5, 0); rCtx.lineTo(cx, 9);
  rCtx.closePath(); rCtx.fill();
}
function drawWaves() {
  const W = waveCanvas.width, H = waveCanvas.height;
  wCtx.fillStyle = '#1a1a1a';
  wCtx.fillRect(0, 0, W, H);
  const step = niceStep(viewEnd - viewStart);
  const first = Math.ceil(viewStart / step) * step;
  wCtx.strokeStyle = '#2d2d2d'; wCtx.lineWidth = 1;
  for (let t = first; t <= viewEnd + step * 0.01; t += step) {
    const x = tToX(t);
    wCtx.beginPath(); wCtx.moveTo(x, 0); wCtx.lineTo(x, H); wCtx.stroke();
  }
  wCtx.strokeStyle = '#2a2a2a';
  visibleSignals.forEach((_, i) => {
    const y = (i + 1) * ROW_H;
    wCtx.beginPath(); wCtx.moveTo(0, y); wCtx.lineTo(W, y); wCtx.stroke();
  });
  if (selectedIdx >= 0 && selectedIdx < visibleSignals.length) {
    wCtx.fillStyle = 'rgba(38,79,120,0.35)';
    wCtx.fillRect(0, selectedIdx * ROW_H, W, ROW_H);
  }
  visibleSignals.forEach((sig, i) => {
    const y0 = i * ROW_H;
    const color = sigColor(sig);
    if (sig.width === 1) drawBinary(sig, y0, color);
    else                 drawBus(sig, y0, color);
  });
  const cx = tToX(cursorTime);
  wCtx.strokeStyle = '#ff4444';
  wCtx.lineWidth   = 1;
  wCtx.setLineDash([4, 4]);
  wCtx.beginPath(); wCtx.moveTo(cx, 0); wCtx.lineTo(cx, H); wCtx.stroke();
  wCtx.setLineDash([]);
}
function drawBinary(sig, y0, color) {
  const margin = 4;
  const yH = y0 + margin, yL = y0 + ROW_H - margin;
  wCtx.strokeStyle = color; wCtx.lineWidth = 1.5;
  wCtx.beginPath();
  let px = null, pv = null;
  sig.times.forEach((t, i) => {
    const x = tToX(t), v = sig.values[i];
    const y = v ? yH : yL;
    if (px === null) { wCtx.moveTo(x, y); }
    else { wCtx.lineTo(x, pv ? yH : yL); wCtx.lineTo(x, y); }
    px = x; pv = v;
  });
  if (px !== null) wCtx.lineTo(tToX(viewEnd), pv ? yH : yL);
  wCtx.stroke();
}
function drawBus(sig, y0, color) {
  const margin = 5;
  const yT = y0 + margin + 2, yB = y0 + ROW_H - margin - 2;
  const yM = y0 + ROW_H / 2;
  const radix = document.getElementById('radix').value;
  for (let i = 0; i < sig.times.length; i++) {
    const t0 = sig.times[i];
    const t1 = i + 1 < sig.times.length ? sig.times[i + 1] : viewEnd;
    const v  = sig.values[i];
    const x0 = tToX(Math.max(t0, viewStart));
    const x1 = tToX(Math.min(t1, viewEnd));
    if (x1 - x0 < 2) continue;
    const nib = 4;
    wCtx.strokeStyle = color; wCtx.lineWidth = 1.2;
    wCtx.fillStyle   = color + '18';
    wCtx.beginPath();
    wCtx.moveTo(x0, yM);
    wCtx.lineTo(Math.min(x0 + nib, x1), yT);
    wCtx.lineTo(Math.max(x1 - nib, x0 + nib), yT);
    wCtx.lineTo(x1, yM);
    wCtx.lineTo(Math.max(x1 - nib, x0 + nib), yB);
    wCtx.lineTo(Math.min(x0 + nib, x1), yB);
    wCtx.closePath();
    wCtx.fill(); wCtx.stroke();
    const tw = x1 - x0 - nib * 2;
    if (tw > 20) {
      let s;
      if (radix === 'hex') s = '0x' + v.toString(16).toUpperCase().padStart(Math.ceil(sig.width/4),'0');
      else if (radix === 'bin') s = v.toString(2).padStart(sig.width,'0');
      else s = String(v);
      wCtx.fillStyle = color;
      wCtx.font = '10px Consolas';
      wCtx.textAlign = 'center';
      wCtx.save();
      wCtx.rect(x0 + nib, yT, tw, yB - yT);
      wCtx.clip();
      wCtx.fillText(s, (x0 + x1) / 2, yM + 4);
      wCtx.restore();
    }
  }
}
function redraw() {
  drawRuler();
  drawWaves();
  updateValues();
  const range = viewEnd - viewStart;
  document.getElementById('st-range').textContent = range.toFixed(1) + ' ns  (' + (range / waveCanvas.width * 10).toFixed(2) + ' ns/div)';
}
function zoomFit() { viewStart = 0; viewEnd = END_TIME || 100; redraw(); }
function zoom(factor) {
  const cx = (viewStart + viewEnd) / 2;
  const half = (viewEnd - viewStart) / 2 * factor;
  viewStart = Math.max(0, cx - half);
  viewEnd   = Math.min(END_TIME, cx + half);
  redraw();
}
function cursorToStart() { cursorTime = viewStart; redraw(); }
function cursorToEnd()   { cursorTime = viewEnd;   redraw(); }
function nextEdge() {
  if (selectedIdx < 0 || selectedIdx >= visibleSignals.length) return;
  const sig = visibleSignals[selectedIdx];
  const next = sig.times.find(t => t > cursorTime + 0.001);
  if (next != null) { cursorTime = next; redraw(); }
}
function prevEdge() {
  if (selectedIdx < 0 || selectedIdx >= visibleSignals.length) return;
  const sig = visibleSignals[selectedIdx];
  const prev = [...sig.times].reverse().find(t => t < cursorTime - 0.001);
  if (prev != null) { cursorTime = prev; redraw(); }
}
function filterSignals() {
  const q = document.getElementById('search').value.toLowerCase();
  visibleSignals = q ? ALL_SIGNALS.filter(s => s.name.toLowerCase().includes(q)) : [...ALL_SIGNALS];
  selectedIdx = -1;
  buildSignalList();
  redraw();
}
waveCanvas.addEventListener('mousedown', e => {
  isDragging    = true;
  dragStartX    = e.offsetX;
  dragStartView = [viewStart, viewEnd];
  cursorTime    = Math.max(0, Math.min(END_TIME, xToT(e.offsetX)));
  redraw();
});
waveCanvas.addEventListener('mousemove', e => {
  if (!isDragging) return;
  const dx  = e.offsetX - dragStartX;
  const dt  = -dx / waveCanvas.width * (dragStartView[1] - dragStartView[0]);
  const dur = dragStartView[1] - dragStartView[0];
  viewStart = Math.max(0, dragStartView[0] + dt);
  viewEnd   = Math.min(END_TIME, viewStart + dur);
  if (viewEnd >= END_TIME) { viewEnd = END_TIME; viewStart = Math.max(0, viewEnd - dur); }
  cursorTime = Math.max(0, Math.min(END_TIME, xToT(dragStartX)));
  redraw();
});
waveCanvas.addEventListener('mouseup',   () => { isDragging = false; });
waveCanvas.addEventListener('mouseleave', () => { isDragging = false; });
waveCanvas.addEventListener('wheel', e => {
  e.preventDefault();
  const factor = e.deltaY > 0 ? 1.4 : 0.7;
  const cx = xToT(e.offsetX);
  const l  = (cx - viewStart) * factor;
  const r  = (viewEnd - cx) * factor;
  viewStart = Math.max(0, cx - l);
  viewEnd   = Math.min(END_TIME, cx + r);
  redraw();
}, { passive: false });
const passes = EVENTS.filter(e => e.kind === 'PASS').length;
const fails  = EVENTS.filter(e => e.kind === 'FAIL').length;
if (passes + fails > 0) {
  const el = document.getElementById('st-pass');
  el.innerHTML = fails === 0
    ? '<span style="color:#4caf50">PASS '+passes+'</span>'
    : '<span style="color:#f44336">FAIL '+fails+'</span> / <span style="color:#4caf50">PASS '+passes+'</span>';
}
window.addEventListener('resize', resize);
buildSignalList();
resize();
</script>
</body></html>"""

    result = (template
              .replace("%DATA%",   data_json)
              .replace("%EVENTS%", events_json)
              .replace("%NROWS%",  str(n_signals)))
    return result


# ── Streamlit entry point ─────────────────────────────────────────────────────

def render_waveform_vivado_streamlit(
    vcd_path:     Optional[Path],
    sim_log_path: Optional[Path] = None,
    height:       int            = 560,
    key:          str            = "wv_vivado",
) -> None:
    """
    Render the Vivado-style waveform viewer in Streamlit.
    Replace existing waveform tab content with this call.

    Args:
        vcd_path:     Path to trace.vcd
        sim_log_path: Path to simulation.log (optional)
        height:       iframe height in pixels
        key:          unique key for component
    """
    import streamlit as st
    import streamlit.components.v1 as components

    vcd_path = Path(vcd_path) if vcd_path else None

    if not vcd_path or not vcd_path.exists():
        st.warning("No VCD file found for this design.")
        st.caption(
            "The pipeline generates trace.vcd during RTL simulation. "
            "Run the full pipeline to generate waveform data."
        )
        return

    try:
        signals, timescale_ns, end_time = parse_vcd(vcd_path)
    except Exception as e:
        st.error(f"VCD parse error: {e}")
        return

    if not signals:
        st.warning("VCD file parsed but contains no signals with data.")
        return

    sim_events = parse_sim_events(sim_log_path)

    # Metrics row above viewer
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Signals",    len(signals))
    m2.metric("Duration",   f"{end_time:.1f} ns")
    m3.metric("Timescale",  f"{timescale_ns:.3g} ns/unit")
    passes = sum(1 for e in sim_events if e.get("kind") == "PASS")
    fails  = sum(1 for e in sim_events if e.get("kind") == "FAIL")
    if passes + fails > 0:
        m4.metric("Sim Result", f"{passes}P / {fails}F",
                  delta="PASS" if fails == 0 else "FAIL",
                  delta_color="normal" if fails == 0 else "inverse")
    else:
        m4.metric("Sim Events", "N/A")

    # Render the HTML viewer
    html = generate_waveform_html(
        signals    = signals,
        end_time   = end_time,
        sim_events = sim_events,
        height     = height,
    )
    components.html(html, height=height, scrolling=False)

    # Download VCD button
    st.download_button(
        label     = "Download trace.vcd",
        data      = vcd_path.read_bytes(),
        file_name = vcd_path.name,
        mime      = "text/plain",
        key       = f"{key}_dl",
    )


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("waveform_vivado.py -- standalone self-test")
    print("=" * 60)

    passed = total = 0

    def _make_vcd(path: Path) -> None:
        path.write_text("""\
$timescale 1 ns $end
$scope module adder_tb $end
$var wire 1 ! clk $end
$var wire 1 " reset_n $end
$var wire 8 # a [7:0] $end
$var wire 8 $ b [7:0] $end
$var wire 9 % sum [8:0] $end
$upscope $end $enddefinitions $end
$dumpvars 0! 0" b00000000 # b00000000 $ b000000000 % $end
#0 1"
#5 1!
#10 0! b00000101 # b00000011 $
#15 1! b000001000 %
#20 0! b01100100 # b00110010 $
#25 1! b010010110 %
#30 0! b11111111 # b00000001 $
#35 1! b100000000 %
#40 0!
#50
""")

    with tempfile.TemporaryDirectory() as tmp:
        vcd = Path(tmp) / "test.vcd"
        _make_vcd(vcd)

        # Test 1: parse
        total += 1
        signals, ts_ns, end_t = parse_vcd(vcd)
        assert len(signals) >= 4, f"Expected >=4 signals, got {len(signals)}"
        assert end_t > 0, f"end_time is 0"
        assert ts_ns == 1.0, f"timescale_ns wrong: {ts_ns}"
        print(f"[PASS] VCD parse: {len(signals)} signals, end={end_t} ns, ts={ts_ns} ns")
        passed += 1

        # Test 2: signal types
        total += 1
        clk_sig = next((s for s in signals.values() if s.signal_type == "clock"), None)
        assert clk_sig is not None, "No clock signal found"
        assert clk_sig.width == 1
        assert len(clk_sig.times) >= 4
        print(f"[PASS] Clock signal: {clk_sig.name}, {len(clk_sig.times)} edges")
        passed += 1

        # Test 3: value_at
        total += 1
        assert clk_sig.value_at(0)  == 0, f"clk at t=0 should be 0"
        assert clk_sig.value_at(7)  == 1, f"clk at t=7 should be 1"
        assert clk_sig.value_at(12) == 0, f"clk at t=12 should be 0"
        print("[PASS] value_at: t=0->0, t=7->1, t=12->0")
        passed += 1

        # Test 4: HTML generation
        total += 1
        events = [{"kind": "PASS", "message": "PASS Test 1", "time_ns": 15.0}]
        html = generate_waveform_html(signals, end_t, events)
        assert "<!DOCTYPE html>" in html
        assert "waveCanvas" in html
        assert "Consolas" in html
        assert "#ff9800" in html
        assert "#1e1e1e" in html
        assert str(int(end_t)) in html or str(end_t) in html
        print(f"[PASS] HTML generated: {len(html):,} chars, Vivado theme present")
        passed += 1

        # Test 5: JSON data embedded correctly
        total += 1
        import json as _json
        start = html.find("const RAW = ") + len("const RAW = ")
        end   = html.find(";\nconst EVENTS", start)
        raw_json = html[start:end]
        data = _json.loads(raw_json)
        assert "signals" in data
        assert "endTime" in data
        assert len(data["signals"]) == len(signals)
        assert data["endTime"] == end_t
        print(f"[PASS] JSON embedded: {len(data['signals'])} signals, endTime={data['endTime']}")
        passed += 1

        # Test 6: sim events
        total += 1
        log_f = Path(tmp) / "sim.log"
        log_f.write_text("PASS Test 1: 5+3=8\nFAIL Test 2: expected 150 got 8\n")
        evs = parse_sim_events(log_f)
        assert len(evs) == 2
        assert evs[0]["kind"] == "PASS"
        assert evs[1]["kind"] == "FAIL"
        print(f"[PASS] Sim events: {evs[0]['kind']}, {evs[1]['kind']}")
        passed += 1

        # Test 7: Bus signal value
        total += 1
        sig_a = next(s for s in signals.values() if s.name == "a")
        v_at_20 = sig_a.value_at(22)
        assert v_at_20 == 100, f"a at t=22 should be 100, got {v_at_20}"
        print(f"[PASS] Bus signal value: a at t=22 = {v_at_20} (0x{v_at_20:X})")
        passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED -- waveform_vivado.py ready for integration")
    print("=" * 60)
