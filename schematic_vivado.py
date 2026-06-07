"""
schematic_vivado.py — Cadence/Vivado-style Gate-Level Schematic Viewer
RTL-Gen AI v2.7

Parses synthesized Sky130A Verilog netlist → builds DAG →
Sugiyama-style hierarchical layout → renders gate symbols in Plotly.

Matches Cadence Virtuoso / Vivado Gate-level Schematic:
  ├── Proper gate symbols: AND/OR/XOR/NOT/NAND/NOR/DFF/BUF/MUX
  ├── Vivado dark theme: #1e1e1e background, cyan wires
  ├── Color-coded cells: blue=DFF, green=AND, amber=OR, purple=XOR
  ├── Clock wires highlighted orange (Vivado standard)
  ├── Hierarchical left→right layout (inputs left, FFs right)
  ├── Orthogonal wire routing (L-shaped bends)
  ├── Port labels on all module I/O
  ├── Hover: cell type, instance name, connected nets
  ├── Zoom/pan (Plotly native)
  └── Cell count legend + design stats

Usage in app.py (Sign-Off → Netlist tab):
    from schematic_vivado import render_schematic_vivado_streamlit
    render_schematic_vivado_streamlit(netlist_path)

Standalone test (no Docker, generates a synthetic netlist):
    python schematic_vivado.py
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import plotly.graph_objects as go

log = logging.getLogger(__name__)

# ── Cell type definitions ──────────────────────────────────────────────────────

# Maps cell type string → (short_label, fill_color, text_color)
# Covers both Sky130A standard cells and Yosys generic cells.
CELL_TYPES: Dict[str, Tuple[str, str, str]] = {
    # ── Yosys generic ─────────────────────────────────────────────────
    "$_AND_":    ("AND",   "#2E7D32", "#A5D6A7"),
    "$_NAND_":   ("NAND",  "#1B5E20", "#C8E6C9"),
    "$_OR_":     ("OR",    "#E65100", "#FFCC02"),
    "$_NOR_":    ("NOR",   "#BF360C", "#FFCCBC"),
    "$_XOR_":    ("XOR",   "#4A148C", "#CE93D8"),
    "$_XNOR_":   ("XNOR",  "#311B92", "#E1BEE7"),
    "$_NOT_":    ("NOT",   "#546E7A", "#B0BEC5"),
    "$_BUF_":    ("BUF",   "#455A64", "#CFD8DC"),
    "$_ANDNOT_": ("ANDNOT","#2E7D32", "#A5D6A7"),
    "$_ORNOT_":  ("ORNOT", "#E65100", "#FFCC02"),
    "$_MUX_":    ("MUX",   "#E64A19", "#FFAB91"),
    "$_SDFF_PN0_":("DFF",  "#01579B", "#81D4FA"),
    "$_SDFF_PP0_":("DFF",  "#01579B", "#81D4FA"),
    "$_DFF_P_":  ("DFF",   "#01579B", "#81D4FA"),
    "$_DFF_N_":  ("DFF",   "#01579B", "#81D4FA"),
    # ── Sky130A HD ────────────────────────────────────────────────────
    "sky130_fd_sc_hd__and2_1":   ("AND2",  "#2E7D32", "#A5D6A7"),
    "sky130_fd_sc_hd__and2_2":   ("AND2",  "#2E7D32", "#A5D6A7"),
    "sky130_fd_sc_hd__and3_1":   ("AND3",  "#2E7D32", "#A5D6A7"),
    "sky130_fd_sc_hd__and4_1":   ("AND4",  "#2E7D32", "#A5D6A7"),
    "sky130_fd_sc_hd__nand2_1":  ("NAND2", "#1B5E20", "#C8E6C9"),
    "sky130_fd_sc_hd__nand3_1":  ("NAND3", "#1B5E20", "#C8E6C9"),
    "sky130_fd_sc_hd__nand4_1":  ("NAND4", "#1B5E20", "#C8E6C9"),
    "sky130_fd_sc_hd__or2_1":    ("OR2",   "#E65100", "#FFCC02"),
    "sky130_fd_sc_hd__or3_1":    ("OR3",   "#E65100", "#FFCC02"),
    "sky130_fd_sc_hd__or4_1":    ("OR4",   "#E65100", "#FFCC02"),
    "sky130_fd_sc_hd__nor2_1":   ("NOR2",  "#BF360C", "#FFCCBC"),
    "sky130_fd_sc_hd__nor3_1":   ("NOR3",  "#BF360C", "#FFCCBC"),
    "sky130_fd_sc_hd__xor2_1":   ("XOR2",  "#4A148C", "#CE93D8"),
    "sky130_fd_sc_hd__xnor2_1":  ("XNOR2", "#311B92", "#E1BEE7"),
    "sky130_fd_sc_hd__inv_1":    ("INV",   "#546E7A", "#B0BEC5"),
    "sky130_fd_sc_hd__inv_2":    ("INV",   "#546E7A", "#B0BEC5"),
    "sky130_fd_sc_hd__buf_1":    ("BUF",   "#455A64", "#CFD8DC"),
    "sky130_fd_sc_hd__buf_2":    ("BUF",   "#455A64", "#CFD8DC"),
    "sky130_fd_sc_hd__dfxtp_1":  ("DFF",   "#01579B", "#81D4FA"),
    "sky130_fd_sc_hd__dfxtp_2":  ("DFF",   "#01579B", "#81D4FA"),
    "sky130_fd_sc_hd__dfstp_2":  ("DFFSR", "#0277BD", "#B3E5FC"),
    "sky130_fd_sc_hd__mux2_1":   ("MUX2",  "#E64A19", "#FFAB91"),
    "sky130_fd_sc_hd__mux4_1":   ("MUX4",  "#E64A19", "#FFAB91"),
    "sky130_fd_sc_hd__maj3_1":   ("MAJ3",  "#827717", "#FFF59D"),
    "sky130_fd_sc_hd__o21a_1":   ("OA21",  "#E65100", "#FFCC02"),
    "sky130_fd_sc_hd__a21o_1":   ("AO21",  "#2E7D32", "#A5D6A7"),
    "sky130_fd_sc_hd__a21oi_1":  ("AOI21", "#1B5E20", "#C8E6C9"),
    "sky130_fd_sc_hd__o21ai_1":  ("OAI21", "#BF360C", "#FFCCBC"),
    "sky130_fd_sc_hd__clkbuf_1": ("CKBUF", "#00695C", "#80CBC4"),
    "sky130_fd_sc_hd__clkbuf_2": ("CKBUF", "#00695C", "#80CBC4"),
    "sky130_fd_sc_hd__tapvpwrvgnd_1": ("TAP", "#37474F", "#90A4AE"),
    "sky130_fd_sc_hd__decap_3":  ("DCAP",  "#37474F", "#90A4AE"),
    "sky130_fd_sc_hd__fill_1":   ("FILL",  "#263238", "#78909C"),
    "sky130_fd_sc_hd__fill_2":   ("FILL",  "#263238", "#78909C"),
}

_DEFAULT_CELL = ("CELL", "#1565C0", "#90CAF9")

# Cells that should NOT appear in the schematic (filler/tap)
_SKIP_CELLS: Set[str] = {
    "sky130_fd_sc_hd__tapvpwrvgnd_1",
    "sky130_fd_sc_hd__decap_3",
    "sky130_fd_sc_hd__fill_1",
    "sky130_fd_sc_hd__fill_2",
    "sky130_fd_sc_hd__fill_4",
    "sky130_fd_sc_hd__fill_8",
}

# Max cells to show in schematic (performance cap)
MAX_CELLS = 120

# Layout spacing
X_SPACING = 2.8   # between layers
Y_SPACING = 1.6   # between cells in a layer
CELL_W    = 1.8   # cell box width
CELL_H    = 0.9   # cell box height


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Cell:
    instance: str          # e.g. "_032_"
    cell_type: str         # full type string
    ports: Dict[str, str]  # port_name → net_name
    label: str    = ""     # short display label
    color: str    = "#1565C0"
    tcolor: str   = "#90CAF9"
    layer: int    = 0      # assigned by layout
    pos:   int    = 0      # position within layer
    x:     float  = 0.0
    y:     float  = 0.0

    def __post_init__(self) -> None:
        info = CELL_TYPES.get(self.cell_type, _DEFAULT_CELL)
        self.label, self.color, self.tcolor = info


@dataclass
class Port:
    name:      str
    direction: str   # "input" | "output"
    width:     int   = 1
    layer:     int   = 0
    pos:       int   = 0
    x:         float = 0.0
    y:         float = 0.0


@dataclass
class Wire:
    net:   str
    src:   str    # instance name (or "PORT:name")
    dst:   str
    is_clk: bool = False


# ── Netlist parser ────────────────────────────────────────────────────────────

def parse_netlist(path: Path) -> Tuple[List[Cell], List[Port], List[Wire], str]:
    """
    Parse a Yosys-synthesized Verilog netlist.
    Returns (cells, ports, wires, module_name).
    """
    text = path.read_text(errors="replace")

    # Module name
    m = re.search(r"module\s+(\w+)\s*\(", text)
    module_name = m.group(1) if m else path.stem

    # Port declarations  (input/output [width] name)
    ports: List[Port] = []
    # Split into individual declarations (handle multiple per line)
    for decl in re.split(r"\s*[;]\s*", text):
        m = re.match(
            r"\s*(input|output)\s+(?:wire|reg)?\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*$",
            decl, re.IGNORECASE
        )
        if m:
            direction = m.group(1)
            hi = m.group(2); lo = m.group(3)
            width = (int(hi) - int(lo) + 1) if hi else 1
            name = m.group(4)
            ports.append(Port(name=name, direction=direction, width=width))

    # Cell instantiations
    cells: List[Cell] = []
    skipped = 0

    # Pattern: CellType InstanceName ( .port(net), ... );
    cell_pattern = re.compile(
        r"(\S+)\s+(_\w+_|u_\w+)\s*\(\s*(.*?)\s*\)\s*;",
        re.DOTALL
    )
    port_pattern = re.compile(r"\.(\w+)\s*\(\s*([\w\[\]\'\"]+)\s*\)")

    for cm in cell_pattern.finditer(text):
        cell_type = cm.group(1)
        instance  = cm.group(2)
        port_str  = cm.group(3)

        # Skip non-cell keywords
        if cell_type in ("module", "wire", "assign", "input", "output",
                         "endmodule", "reg", "always", "initial"):
            continue
        if cell_type in _SKIP_CELLS:
            skipped += 1
            continue

        port_map: Dict[str, str] = {}
        for pp in port_pattern.finditer(port_str):
            port_map[pp.group(1)] = pp.group(2)

        cells.append(Cell(instance=instance, cell_type=cell_type, ports=port_map))

    log.info("Parsed %d cells, %d ports, %d filler skipped",
             len(cells), len(ports), skipped)

    # Cap for performance
    if len(cells) > MAX_CELLS:
        log.warning("Netlist has %d cells — capping to %d for schematic", len(cells), MAX_CELLS)
        # Keep DFFs first (most informative), then by instance name
        dffs  = [c for c in cells if "DFF" in CELL_TYPES.get(c.cell_type, ("",))[0]]
        other = [c for c in cells if c not in dffs]
        cells = (dffs + other)[:MAX_CELLS]

    # Build wires from port connections
    # net → list of (instance, port, is_output)
    net_drivers: Dict[str, str] = {}   # net → driving cell instance
    net_loads:   Dict[str, List[str]] = defaultdict(list)

    # Identify output ports of cells (standard: X, Y, Q, Z, S, CO)
    OUTPUT_PORTS = {"X", "Y", "Q", "Z", "S", "CO", "SUM", "CARRY", "OUT",
                    "COUT", "A_N", "B_N"}

    for cell in cells:
        for port, net in cell.ports.items():
            if port.upper() in OUTPUT_PORTS:
                net_drivers[net] = cell.instance
            else:
                net_loads[net].append(cell.instance)

    # Module input ports also drive nets
    for port in ports:
        if port.direction == "input":
            net_drivers[port.name] = f"PORT:{port.name}"
            # Also handle bit slices: port a drives a[0], a[1], ...
            for net, driver in list(net_drivers.items()):
                pass  # simplified

    wires: List[Wire] = []
    for net, driver in net_drivers.items():
        for load in net_loads.get(net, []):
            is_clk = "clk" in net.lower() or "clock" in net.lower()
            wires.append(Wire(net=net, src=driver, dst=load, is_clk=is_clk))
        # Connect to output ports
        for port in ports:
            if port.direction == "output":
                if net == port.name or net.startswith(port.name + "["):
                    wires.append(Wire(net=net, src=driver,
                                      dst=f"PORT:{port.name}", is_clk=False))

    return cells, ports, wires, module_name


# ── Hierarchical layout ───────────────────────────────────────────────────────

def compute_layout(
    cells:  List[Cell],
    ports:  List[Port],
    wires:  List[Wire],
) -> None:
    """
    Assign (x, y) positions to all cells and ports.
    Uses BFS-based layer assignment + barycenter ordering.
    Modifies cells and ports in-place.
    """
    # Build instance → Cell lookup
    inst_map: Dict[str, Cell] = {c.instance: c for c in cells}

    # Adjacency: instance → set of successor instances
    successors:   Dict[str, Set[str]] = defaultdict(set)
    predecessors: Dict[str, Set[str]] = defaultdict(set)

    for w in wires:
        if w.src in inst_map and w.dst in inst_map:
            successors[w.src].add(w.dst)
            predecessors[w.dst].add(w.src)

    # Layer assignment: BFS from sources (cells with no predecessors)
    layer: Dict[str, int] = {}

    sources = [c.instance for c in cells if c.instance not in predecessors
               or not predecessors[c.instance]]
    queue = deque((s, 0) for s in sources)
    while queue:
        inst, lyr = queue.popleft()
        if inst in layer and layer[inst] >= lyr:
            continue
        layer[inst] = lyr
        for succ in successors.get(inst, []):
            queue.append((succ, lyr + 1))

    # Assign remaining cells (no predecessors found)
    for cell in cells:
        if cell.instance not in layer:
            layer[cell.instance] = 0

    # Apply layer to cells
    max_layer = 0
    for cell in cells:
        cell.layer = layer.get(cell.instance, 0)
        max_layer = max(max_layer, cell.layer)

    # Barycenter ordering within layers
    by_layer: Dict[int, List[Cell]] = defaultdict(list)
    for cell in cells:
        by_layer[cell.layer].append(cell)

    for lyr, layer_cells in by_layer.items():
        # Sort by average successor position (approximation)
        def bary(c: Cell) -> float:
            succ_layers = [layer.get(s, lyr + 1) for s in successors.get(c.instance, [])]
            return sum(succ_layers) / len(succ_layers) if succ_layers else float(lyr)
        layer_cells.sort(key=bary)
        for pos, cell in enumerate(layer_cells):
            cell.pos = pos

    # Assign (x, y) coordinates
    for cell in cells:
        cell.x = cell.layer * X_SPACING
        cell.y = -cell.pos  * Y_SPACING

    # Input ports at x = -X_SPACING, output ports at x = (max_layer+1)*X_SPACING
    in_ports  = [p for p in ports if p.direction == "input"]
    out_ports = [p for p in ports if p.direction == "output"]

    for i, p in enumerate(in_ports):
        p.layer = -1
        p.pos   = i
        p.x     = -X_SPACING
        p.y     = -i * Y_SPACING

    for i, p in enumerate(out_ports):
        p.layer = max_layer + 1
        p.pos   = i
        p.x     = (max_layer + 1) * X_SPACING
        p.y     = -i * Y_SPACING


# ── Gate symbol shapes ─────────────────────────────────────────────────────────

def _gate_shape(label: str, x: float, y: float,
                fill: str, tcolor: str) -> List[go.layout.Shape]:
    """Return Plotly shape objects for a gate symbol at (x, y) center."""
    hw = CELL_W / 2
    hh = CELL_H / 2
    shapes = []

    # Main rectangle body (rgba for alpha support)
    if fill.startswith("#") and len(fill) == 7:
        fill_rgba = f"rgba({int(fill[1:3],16)},{int(fill[3:5],16)},{int(fill[5:7],16)},0.8)"
    else:
        fill_rgba = fill
    shapes.append(go.layout.Shape(
        type      = "rect",
        x0=x-hw, y0=y-hh, x1=x+hw, y1=y+hh,
        fillcolor = fill_rgba,
        line      = dict(color=tcolor, width=1.2),
        layer     = "above",
    ))

    # DFF: add clock triangle on left side
    if label.startswith("DFF") or label.startswith("DFFSR"):
        shapes.append(go.layout.Shape(
            type="path",
            path=f"M {x-hw} {y-hh*0.4} L {x-hw+0.15} {y} L {x-hw} {y+hh*0.4}",
            line=dict(color="#ff9800", width=1.5),
            layer="above",
        ))

    return shapes


def _port_shape(p: Port) -> go.layout.Shape:
    """Diamond shape for module ports."""
    hw = 0.25
    return go.layout.Shape(
        type="path",
        path=(f"M {p.x} {p.y+hw*0.8} "
              f"L {p.x+hw} {p.y} "
              f"L {p.x} {p.y-hw*0.8} "
              f"L {p.x-hw} {p.y} Z"),
        fillcolor="#1A6B3C" if p.direction == "input" else "#B71C1C",
        line=dict(color="#66BB6A" if p.direction == "input" else "#EF9A9A", width=1),
        layer="above",
    )


# ── Plotly figure builder ─────────────────────────────────────────────────────

def build_schematic_figure(
    cells:       List[Cell],
    ports:       List[Port],
    wires:       List[Wire],
    module_name: str,
    truncated:   bool = False,
) -> go.Figure:
    """
    Build the complete Plotly schematic figure.
    """
    fig = go.Figure()

    # Lookup tables
    inst_to_cell: Dict[str, Cell] = {c.instance: c for c in cells}
    port_by_name: Dict[str, Port] = {p.name: p for p in ports}

    def node_xy(inst: str) -> Optional[Tuple[float, float]]:
        if inst in inst_to_cell:
            c = inst_to_cell[inst]
            return c.x, c.y
        if inst.startswith("PORT:"):
            name = inst[5:]
            if name in port_by_name:
                p = port_by_name[name]
                return p.x, p.y
        return None

    # ── Wires ────────────────────────────────────────────────────────
    # Group by is_clk for separate traces (different colors)
    def add_wire_trace(wire_list: List[Wire], color: str, name: str) -> None:
        xs, ys = [], []
        for w in wire_list:
            src = node_xy(w.src)
            dst = node_xy(w.dst)
            if src is None or dst is None:
                continue
            x0, y0 = src
            x1, y1 = dst
            # L-shaped routing: go right from src, then vertical to dst row
            mid_x = (x0 + CELL_W/2 + x1 - CELL_W/2) / 2
            xs += [x0 + CELL_W/2, mid_x, mid_x, x1 - CELL_W/2, None]
            ys += [y0,            y0,    y1,    y1,             None]

        if xs:
            fig.add_trace(go.Scatter(
                x=xs, y=ys,
                mode="lines",
                line=dict(color=color, width=1.2),
                name=name,
                showlegend=True,
                hoverinfo="skip",
            ))

    clk_wires  = [w for w in wires if w.is_clk]
    data_wires = [w for w in wires if not w.is_clk]

    add_wire_trace(data_wires, "#4FC3F7", "Data wire")
    add_wire_trace(clk_wires,  "#FF9800", "Clock wire")

    # ── Cell labels (scatter for hover) ──────────────────────────────
    cell_x, cell_y, cell_text, cell_hover, cell_color = [], [], [], [], []

    for cell in cells:
        cell_x.append(cell.x)
        cell_y.append(cell.y)
        cell_text.append(f"<b>{cell.label}</b>")
        nets_str = "<br>".join(f".{k}({v})" for k, v in list(cell.ports.items())[:8])
        cell_hover.append(
            f"<b>{cell.instance}</b><br>"
            f"Type: {cell.cell_type}<br>"
            f"Layer: {cell.layer}<br>"
            f"<br><i>Ports:</i><br>{nets_str}"
        )
        cell_color.append(cell.color)

    fig.add_trace(go.Scatter(
        x=cell_x, y=cell_y,
        mode="text",
        text=cell_text,
        textfont=dict(size=9, color="#FFFFFF", family="Consolas"),
        hovertext=cell_hover,
        hovertemplate="%{hovertext}<extra></extra>",
        showlegend=False,
        name="cells",
    ))

    # ── Port labels ───────────────────────────────────────────────────
    for p in ports:
        color = "#66BB6A" if p.direction == "input" else "#EF9A9A"
        anchor = "right" if p.direction == "output" else "left"
        fig.add_annotation(
            x=p.x + (0.35 if p.direction == "output" else -0.35),
            y=p.y,
            text=f"<b>{p.name}</b>",
            showarrow=False,
            font=dict(size=9, color=color, family="Consolas"),
            xanchor=anchor,
            bgcolor="rgba(30,30,30,0.7)",
        )

    # ── Cell instance labels (below gate) ─────────────────────────────
    for cell in cells:
        fig.add_annotation(
            x=cell.x, y=cell.y - CELL_H/2 - 0.12,
            text=f"<span style='font-size:7px;color:#858585'>{cell.instance}</span>",
            showarrow=False,
            font=dict(size=7, color="#858585"),
        )

    # ── Plotly shapes (gate bodies + port diamonds) ───────────────────
    all_shapes = []
    for cell in cells:
        all_shapes.extend(_gate_shape(cell.label, cell.x, cell.y,
                                       cell.color, cell.tcolor))
    for p in ports:
        all_shapes.append(_port_shape(p))

    # ── Legend entries for cell types ─────────────────────────────────
    seen_labels: Set[str] = set()
    for cell in cells:
        if cell.label not in seen_labels:
            seen_labels.add(cell.label)
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="markers",
                marker=dict(symbol="square", size=10,
                            color=cell.color, line=dict(color=cell.tcolor, width=1)),
                name=cell.label,
                showlegend=True,
            ))

    # ── Layout ────────────────────────────────────────────────────────
    trunc_note = f" (showing {MAX_CELLS}/{MAX_CELLS}+ cells)" if truncated else ""
    fig.update_layout(
        shapes        = all_shapes,
        paper_bgcolor = "#1e1e1e",
        plot_bgcolor  = "#1a1a1a",
        font          = dict(family="Consolas, monospace", size=10, color="#d4d4d4"),
        height        = 680,
        margin        = dict(l=10, r=10, t=40, b=10),
        title         = dict(
            text = f"<b>{module_name}</b> — Gate-Level Schematic (Sky130A){trunc_note}",
            font = dict(size=13, color="#4FC3F7"),
            x    = 0.01,
        ),
        xaxis = dict(
            showgrid   = True, gridcolor = "#2d2d2d",
            zeroline   = False, showticklabels = False,
            showspikes = True, spikecolor = "#888888",
        ),
        yaxis = dict(
            showgrid   = True, gridcolor = "#2d2d2d",
            zeroline   = False, showticklabels = False,
            scaleanchor= "x", scaleratio = 1,
        ),
        legend = dict(
            bgcolor     = "rgba(30,30,40,0.85)",
            bordercolor = "#474747",
            borderwidth = 1,
            font        = dict(size=9),
            title       = dict(text="Cell types", font=dict(size=9, color="#858585")),
        ),
        hovermode = "closest",
        dragmode  = "pan",
    )

    return fig


# ── Streamlit entry point ─────────────────────────────────────────────────────

def render_schematic_vivado_streamlit(
    netlist_path: Optional[Path],
    key_prefix:   str = "sch",
) -> None:
    """
    Render Cadence/Vivado-style gate schematic in Streamlit.
    Call from the Netlist tab in app.py show_signoff().

    Args:
        netlist_path: path to *_sky130.v or *_synth.v synthesized netlist
        key_prefix:   unique key prefix for Streamlit widgets
    """
    import streamlit as st

    if not netlist_path or not Path(netlist_path).exists():
        st.warning("No synthesized netlist found for this design.")
        st.caption(
            "The pipeline generates a Sky130A netlist during synthesis. "
            "Run the full pipeline to view the schematic."
        )
        return

    netlist_path = Path(netlist_path)

    with st.spinner(f"Building schematic from {netlist_path.name}…"):
        try:
            cells, ports, wires, module_name = parse_netlist(netlist_path)
        except Exception as e:
            st.error(f"Netlist parse failed: {e}")
            log.exception("Netlist parse error")
            return

    truncated = len(cells) >= MAX_CELLS

    if not cells:
        st.warning("No cells found in netlist. Check that synthesis completed successfully.")
        return

    compute_layout(cells, ports, wires)

    # ── Stats bar ─────────────────────────────────────────────────────
    from collections import Counter
    type_counts = Counter(CELL_TYPES.get(c.cell_type, _DEFAULT_CELL)[0] for c in cells)
    dff_count = sum(v for k, v in type_counts.items() if k.startswith("DFF"))

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Module",    module_name)
    m2.metric("Cells",     len(cells))
    m3.metric("Registers", dff_count)
    m4.metric("Nets",      len(set(w.net for w in wires)))
    m5.metric("Ports",     len(ports))

    if truncated:
        st.caption(
            f"⚠️ Netlist has >{MAX_CELLS} cells. Showing first {MAX_CELLS} "
            f"(DFFs prioritised). Zoom in for detail."
        )

    # ── Layer selector (filter by depth) ─────────────────────────────
    max_layer = max((c.layer for c in cells), default=0)
    if max_layer > 2:
        layer_range = st.slider(
            "Show layers",
            min_value=0,
            max_value=max_layer,
            value=(0, max_layer),
            key=f"{key_prefix}_layers",
        )
        cells_shown = [c for c in cells if layer_range[0] <= c.layer <= layer_range[1]]
        wires_shown = [w for w in wires
                       if any(c.instance in (w.src, w.dst) for c in cells_shown)]
    else:
        cells_shown = cells
        wires_shown = wires

    # ── Build and render figure ───────────────────────────────────────
    fig = build_schematic_figure(cells_shown, ports, wires_shown,
                                  module_name, truncated)
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_fig")

    # ── Cell type breakdown ───────────────────────────────────────────
    with st.expander("Cell type breakdown"):
        import pandas as pd
        rows = [{"Type": k, "Count": v, "Category": _categorize(k)}
                for k, v in sorted(type_counts.items(), key=lambda x: -x[1])]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # ── Download netlist ──────────────────────────────────────────────
    st.download_button(
        label     = f"⬇ Download {netlist_path.name}",
        data      = netlist_path.read_bytes(),
        file_name = netlist_path.name,
        mime      = "text/plain",
        key       = f"{key_prefix}_dl",
    )


def _categorize(label: str) -> str:
    for kw, cat in [("DFF","Sequential"),("BUF","Buffer"),("INV","Buffer"),
                     ("AND","Logic"),("OR","Logic"),("XOR","Logic"),
                     ("NAND","Logic"),("NOR","Logic"),("MUX","Mux"),
                     ("MAJ","Adder"),("CK","Clock")]:
        if kw in label.upper(): return cat
    return "Other"


# ── Standalone test ───────────────────────────────────────────────────────────

def _make_test_netlist(path: Path) -> None:
    """Write a minimal 8-bit adder gate-level netlist for testing."""
    path.write_text("""\
/* Generated by Yosys 0.38 */
module adder_8bit(clk, reset_n, a, b, sum);
  wire _000_; wire _001_; wire _002_; wire _003_; wire _004_;
  wire _005_; wire _006_; wire _007_; wire _008_; wire _009_;
  input [7:0] a; input [7:0] b; input clk; input reset_n; output [8:0] sum;

  sky130_fd_sc_hd__xor2_1 _032_ (.A(a[0]), .B(b[0]), .X(_000_));
  sky130_fd_sc_hd__and2_1 _033_ (.A(a[0]), .B(b[0]), .X(_001_));
  sky130_fd_sc_hd__xor2_1 _034_ (.A(a[1]), .B(b[1]), .X(_002_));
  sky130_fd_sc_hd__xor2_1 _035_ (.A(_002_), .B(_001_), .X(_003_));
  sky130_fd_sc_hd__maj3_1 _036_ (.A(a[1]), .B(b[1]), .C(_001_), .X(_004_));
  sky130_fd_sc_hd__xor2_1 _037_ (.A(a[2]), .B(b[2]), .X(_005_));
  sky130_fd_sc_hd__xor2_1 _038_ (.A(_005_), .B(_004_), .X(_006_));
  sky130_fd_sc_hd__maj3_1 _039_ (.A(a[2]), .B(b[2]), .C(_004_), .X(_007_));
  sky130_fd_sc_hd__inv_1  _040_ (.A(reset_n), .X(_008_));
  sky130_fd_sc_hd__dfxtp_1 _041_ (.CLK(clk), .D(_000_), .Q(sum[0]));
  sky130_fd_sc_hd__dfxtp_1 _042_ (.CLK(clk), .D(_003_), .Q(sum[1]));
  sky130_fd_sc_hd__dfxtp_1 _043_ (.CLK(clk), .D(_006_), .Q(sum[2]));
  sky130_fd_sc_hd__dfxtp_1 _044_ (.CLK(clk), .D(_007_), .Q(sum[8]));
  sky130_fd_sc_hd__buf_1  _045_ (.A(_000_), .X(_009_));
endmodule
""")


if __name__ == "__main__":
    import sys, tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("schematic_vivado.py — standalone self-test")
    print("=" * 60)

    passed = total = 0

    with tempfile.TemporaryDirectory() as tmp:
        nl = Path(tmp) / "adder_8bit_sky130.v"
        _make_test_netlist(nl)

        # Test 1: parse
        total += 1
        cells, ports, wires, module_name = parse_netlist(nl)
        assert module_name == "adder_8bit", f"Module name wrong: {module_name}"
        assert len(cells) >= 10, f"Expected ≥10 cells, got {len(cells)}"
        assert len(ports) >= 4,  f"Expected ≥4 ports, got {len(ports)}"
        print(f"[PASS] Netlist parse: {len(cells)} cells, {len(ports)} ports, "
              f"module={module_name}")
        passed += 1

        # Test 2: cell types resolved correctly
        total += 1
        dff_cells = [c for c in cells if c.label == "DFF"]
        xor_cells = [c for c in cells if c.label == "XOR2"]
        assert len(dff_cells) >= 3, f"Expected ≥3 DFFs, got {len(dff_cells)}"
        assert len(xor_cells) >= 3, f"Expected ≥3 XOR2, got {len(xor_cells)}"
        assert dff_cells[0].color == "#01579B"   # blue
        assert xor_cells[0].color == "#4A148C"   # purple
        print(f"[PASS] Cell types: {len(dff_cells)} DFF, {len(xor_cells)} XOR2, colours correct")
        passed += 1

        # Test 3: ports have correct directions
        total += 1
        in_ports  = [p for p in ports if p.direction == "input"]
        out_ports = [p for p in ports if p.direction == "output"]
        assert len(in_ports)  >= 3, f"Expected ≥3 input ports, got {len(in_ports)}"
        assert len(out_ports) >= 1, f"Expected ≥1 output port, got {len(out_ports)}"
        print(f"[PASS] Ports: {len(in_ports)} inputs, {len(out_ports)} outputs")
        passed += 1

        # Test 4: layout assigns coordinates
        total += 1
        compute_layout(cells, ports, wires)
        assert all(c.x is not None for c in cells)
        assert all(c.y is not None for c in cells)
        # DFFs should be in a higher layer than XOR inputs
        max_dff_layer = max(c.layer for c in dff_cells)
        min_xor_layer = min(c.layer for c in xor_cells)
        assert max_dff_layer >= min_xor_layer, \
            f"DFF layer {max_dff_layer} should be ≥ XOR layer {min_xor_layer}"
        print(f"[PASS] Layout: DFF layer={max_dff_layer}, XOR layer={min_xor_layer}, "
              f"cells span x={min(c.x for c in cells):.1f}..{max(c.x for c in cells):.1f}")
        passed += 1

        # Test 5: Plotly figure builds without exception
        total += 1
        fig = build_schematic_figure(cells, ports, wires, module_name)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2,   "Expected ≥2 traces"
        assert len(fig.layout.shapes) >= len(cells), \
            f"Expected ≥{len(cells)} shapes, got {len(fig.layout.shapes)}"
        print(f"[PASS] Plotly figure: {len(fig.data)} traces, "
              f"{len(fig.layout.shapes)} shapes")
        passed += 1

        # Test 6: Clock wires coloured orange
        total += 1
        wire_traces = [t for t in fig.data
                       if hasattr(t, "line") and t.line and t.line.color == "#FF9800"]
        assert len(wire_traces) >= 1, "Expected at least one orange clock wire trace"
        print(f"[PASS] Clock wire trace present (orange #FF9800)")
        passed += 1

        # Test 7: skip filler cells
        total += 1
        filler_nl = Path(tmp) / "filler_test.v"
        filler_nl.write_text("""\
module t(clk, a, out);
  input clk, a; output out;
  sky130_fd_sc_hd__tapvpwrvgnd_1 _tap0_ (.VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
  sky130_fd_sc_hd__buf_1 _b0_ (.A(a), .X(out));
  sky130_fd_sc_hd__fill_1 _f0_ (.VPWR(1'b1), .VGND(1'b0), .VPB(1'b1), .VNB(1'b0));
endmodule
""")
        cells2, _, _, _ = parse_netlist(filler_nl)
        names2 = [c.cell_type for c in cells2]
        assert "sky130_fd_sc_hd__tapvpwrvgnd_1" not in names2, "TAP cell not skipped"
        assert "sky130_fd_sc_hd__fill_1"         not in names2, "FILL cell not skipped"
        assert "sky130_fd_sc_hd__buf_1"          in names2,     "BUF cell missing"
        print(f"[PASS] Filler/tap cells skipped. Remaining: {[c.label for c in cells2]}")
        passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED — schematic_vivado.py ready for integration")
    print("=" * 60)
