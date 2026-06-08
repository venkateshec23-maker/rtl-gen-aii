"""
schematic_enhanced.py — Vivado-Style RTL Schematic Viewer
RTL-Gen AI v2.5 — Phase 2

Features:
  ├── Clean rectangular cell blocks with bold gate-type labels (Vivado RTL style)
  ├── Distinct colours per gate family (AND=green, OR=gold, NAND=red, NOR=orange,
  │    XOR=purple, INV=rose, BUF=teal, DFF=blue, MUX=cyan, AOI/OAI=amber)
  ├── Pin annotations on block edges (input pins left, output pins right)
  ├── Instance name shown below each block
  ├── Left-to-right topological layout with orthogonal wire routing
  ├── Input/output port symbols at module boundaries
  ├── Hover: full cell type, all port→net mappings
  ├── Filter by gate family (checkboxes in sidebar)
  ├── Gate count summary header
  └── Click-highlight: single-click a node to highlight its fan-in/fan-out

Usage in app.py (Live Viewer → Schematic tab):
    from schematic_enhanced import render_schematic_enhanced_streamlit
    render_schematic_enhanced_streamlit(netlist_path, key_prefix="sch")

Standalone test:
    python schematic_enhanced.py
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import plotly.graph_objects as go

log = logging.getLogger(__name__)

# ── Gate family definitions ───────────────────────────────────────────────────

@dataclass
class GateFamily:
    label:       str         # short label displayed on node
    color:       str         # fill colour
    text_color:  str         # text colour
    border:      str         # border colour
    symbol:      str         # symbol drawn next to label (e.g. "&", "≥1", "=1")
    shape:       str         # Plotly marker symbol
    size:        int         # marker size

_GATE_FAMILIES: Dict[str, GateFamily] = {
    "nand": GateFamily("NAND", "#c0392b", "#ffffff", "#e74c3c", "&", "square", 28),
    "nor":  GateFamily("NOR",  "#d35400", "#ffffff", "#e67e22", "≥1","square", 28),
    "and":  GateFamily("AND",  "#27ae60", "#ffffff", "#2ecc71", "&", "square", 28),
    "or":   GateFamily("OR",   "#b7950b", "#ffffff", "#f1c40f", "≥1","square", 28),
    "xor":  GateFamily("XOR",  "#8e44ad", "#ffffff", "#9b59b6", "=1","square", 28),
    "xnor": GateFamily("XNOR", "#6c3483", "#ffffff", "#a569bd", "=1","square", 28),
    "inv":  GateFamily("INV",  "#922b21", "#ffffff", "#e74c3c", "1", "triangle-right", 26),
    "buf":  GateFamily("BUF",  "#0e6655", "#ffffff", "#1abc9c", "1", "triangle-right", 26),
    "dff":  GateFamily("DFF",  "#1a5276", "#ffffff", "#3498db", "DFF","square", 32),
    "mux":  GateFamily("MUX",  "#0b5345", "#ffffff", "#00ced1", "MUX","square", 28),
    "aoi":  GateFamily("AOI",  "#935116", "#ffffff", "#d4ac0d", "A/O","square", 28),
    "oai":  GateFamily("OAI",  "#7e5109", "#ffffff", "#d4ac0d", "O/A","square", 28),
    "conb": GateFamily("CONST","#566573", "#ffffff", "#808b96", "0/1","diamond", 20),
    "other":GateFamily("CELL", "#5d6d7e", "#ffffff", "#85929e", "?", "square", 24),
}

_PORT_SHAPES = {
    "input":  "triangle-right",
    "output": "triangle-left",
}

_PORT_COLORS = {
    "input":  "#00ff9d",
    "output": "#ff8800",
}

# Signal colours
_CLOCK_COLOR   = "#ff6b6b"
_RESET_COLOR   = "#ffd93d"
_DATA_COLOR    = "#6bcbff"
_DEFAULT_COLOR = "#4a5568"


# ── Netlist Parser ────────────────────────────────────────────────────────────

@dataclass
class CellNode:
    cell_id:    int
    cell_type:  str                # full Yosys type: sky130_fd_sc_hd__nand2_1
    instance:   str                # instance name: _19_
    family:     str                # gate family key: "nand", "dff", etc.
    ports:      Dict[str, str]     # port_name → net_name
    is_port:    bool = False
    direction:  str = ""           # "input" | "output" for module ports
    short_name: str = ""           # e.g. "NAND2", "DFF"

    @property
    def family_info(self) -> GateFamily:
        if self.is_port:
            return GateFamily(
                label=self.direction.upper(),
                color=_PORT_COLORS.get(self.direction, "#888"),
                text_color="#ffffff",
                border=_PORT_COLORS.get(self.direction, "#888"),
                symbol="",
                shape=_PORT_SHAPES.get(self.direction, "square"),
                size=18,
            )
        return _GATE_FAMILIES.get(self.family, _GATE_FAMILIES["other"])


@dataclass
class Net:
    name:  str
    width: int = 1


@dataclass
class Edge:
    source_id: int
    target_id: int
    source_port: str = ""
    target_port: str = ""
    net:       str = ""
    is_clock:  bool = False
    is_reset:  bool = False


def _classify_gate_family(cell_type: str) -> str:
    """Classify a full cell type into a gate family key."""
    ct = cell_type.lower()
    # DFF variants — any match means it's a flip-flop
    dff_keywords = ("dfxtp", "dfrtp", "dfstp", "dfbb", "dfxbp",
                    "dfrbp", "dfsbp", "dlxtp", "dlrtp", "dlrbp",
                    "dfxn", "dfrn", "dfsn")
    if any(k in ct for k in dff_keywords):
        return "dff"
    # Clocked buffers are still buffers
    if "clkbuf" in ct:
        return "buf"
    if "bufinv" in ct:
        return "inv"
    # Distinguish flip-flops by prefix pattern
    if ct.startswith("df") and len(ct) > 2 and ct[2] in "xrsbl":
        return "dff"
    if ct.startswith("dl") and len(ct) > 2 and ct[2] in "xrblp":
        return "dff"

    # Standard gates
    for key in ("nand", "nor", "and", "or", "xor", "xnor", "inv", "buf",
                 "mux", "aoi", "oai", "conb"):
        if key in ct:
            if key in ("inv", "buf") and "dff" in ct:
                return "dff"
            if key == "buf" and "clk" in ct:
                return "buf"
            return key
    # AOI/OAI with different naming
    if any(k in ct for k in ("aoi", "a2o", "a22o", "a21o", "a2bb")):
        return "aoi"
    if any(k in ct for k in ("oai", "o2a", "o22a", "o21a")):
        return "oai"
    if "fa" in ct or "ha" in ct:  # full-adder, half-adder
        return "xor"
    if "prodeq" in ct:
        return "and"
    return "other"


def _short_gate_name(cell_type: str) -> str:
    """Short human-readable name: sky130_fd_sc_hd__nand2_1 → NAND2"""
    ct = cell_type.replace("sky130_fd_sc_hd__", "")
    # Normalize DFF variants
    if any(k in ct for k in ("dfxtp", "dfrtp", "dfstp", "dfbbp",
                              "dfxbp", "dfrbp", "dfsbp",
                              "dlxtp", "dlrtp", "dlrbp",
                              "dfxn", "dfrn", "dfsn")):
        return "DFF"
    # Normalize AOI/OAI
    if any(k in ct for k in ("a2o2bbai", "a22o", "o2a", "o22a")):
        parts = ct.split("_")
        base = parts[0].upper() if parts else ct.upper()
        return base[:8]  # cap length
    # Normalize LPFLOW / special cells
    if "lpflow" in ct:
        return ct.upper()[:8]
    # Split on underscores
    parts = ct.split("_")
    if not parts:
        return ct[:10].upper()
    base = parts[0].upper()
    return base


def parse_synthesized_netlist(
    netlist_path: Path,
    max_cells: int = 200,
) -> Tuple[List[CellNode], List[Edge], Dict[str, int]]:
    """Parse a Yosys-synthesized Verilog netlist.

    Returns:
        nodes:  list of CellNode
        edges:  list of Edge
        stats:  dict of {gate_family_label: count}
    """
    content = netlist_path.read_text(errors="ignore")

    nodes:  List[CellNode] = []
    edges:  List[Edge]     = []
    stats:  Dict[str, int] = {}

    cell_id   = 0
    net_to_driver: Dict[str, int]    = {}
    pending_edges: List[dict]        = []
    port_nodes:    Dict[str, int]    = {}

    # ── Module ports ────────────────────────────────────────────────
    port_matches = re.findall(
        r'(input|output)\s+(?:wire\s+)?(?:\[\d+:\d+\]\s+)?(\w+)', content
    )
    for direction, pname in port_matches[:40]:
        nodes.append(CellNode(
            cell_id=cell_id, cell_type="port", instance=pname,
            family="port", is_port=True, direction=direction,
            short_name=pname,
            ports={"I": pname} if direction == "input" else {"O": pname},
        ))
        if direction == "input":
            net_to_driver[pname] = cell_id
        port_nodes[pname] = cell_id
        cell_id += 1

    # ── Cell instantiations ─────────────────────────────────────────
    cell_pattern = re.compile(
        r'(sky130_fd_sc_hd__\w+)\s+(\w+)\s*\(([^;]+)\);', re.DOTALL
    )

    for m in cell_pattern.finditer(content):
        if len(nodes) - len(port_nodes) >= max_cells:
            break

        cell_type_full = m.group(1)
        instance_name  = m.group(2)
        port_str       = m.group(3)

        family = _classify_gate_family(cell_type_full)
        short  = _short_gate_name(cell_type_full)

        conn_map: Dict[str, str] = {}
        for pm in re.finditer(r'\.(\w+)\s*\(\s*([\w\[\]]+)\s*\)', port_str):
            conn_map[pm.group(1)] = pm.group(2)

        nodes.append(CellNode(
            cell_id=cell_id, cell_type=cell_type_full,
            instance=instance_name, family=family,
            short_name=short, ports=conn_map,
        ))

        # Output pins → drives net
        out_pins = {"X", "Q", "Y", "COUT", "Z", "OUT"}
        for pname, net in conn_map.items():
            if pname.upper() in out_pins:
                net_to_driver[net] = cell_id

        # Input pins → pending edges
        for pname, net in conn_map.items():
            if pname.upper() not in out_pins:
                pending_edges.append({
                    "net": net, "to_id": cell_id, "port": pname,
                })

        # Update stats
        gf = _GATE_FAMILIES.get(family, _GATE_FAMILIES["other"])
        stats[gf.label] = stats.get(gf.label, 0) + 1

        cell_id += 1

    # ── Resolve edges ───────────────────────────────────────────────
    for pe in pending_edges:
        net_name = pe["net"]
        driver = net_to_driver.get(net_name)
        if driver is not None and driver != pe["to_id"]:
            is_clk = any(k in net_name.lower() for k in ("clk", "clock"))
            is_rst = any(k in net_name.lower() for k in ("reset", "rst", "r_b"))
            edges.append(Edge(
                source_id=driver, target_id=pe["to_id"],
                source_port="", target_port=pe["port"],
                net=net_name,
                is_clock=is_clk, is_reset=is_rst,
            ))
        # Port → cell edges
        if net_name in port_nodes:
            port_id = port_nodes[net_name]
            edges.append(Edge(
                source_id=port_id, target_id=pe["to_id"],
                source_port="", target_port=pe["port"],
                net=net_name,
            ))

    return nodes, edges, stats


# ── Layout engine ─────────────────────────────────────────────────────────────

def _compute_layout(
    nodes: List[CellNode],
    edges: List[Edge],
) -> Dict[int, Tuple[float, float]]:
    """Left-to-right topological layout with generous spacing for readable blocks."""
    import networkx as nx

    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n.cell_id)
    for e in edges:
        if G.has_node(e.source_id) and G.has_node(e.target_id):
            G.add_edge(e.source_id, e.target_id)

    pos: Dict[int, Tuple[float, float]] = {}

    try:
        layers = list(nx.topological_generations(G))
        for layer_idx, layer in enumerate(layers):
            ports   = [n for n in layer for nd in nodes if nd.cell_id == n and nd.is_port]
            cells   = [n for n in layer for nd in nodes if nd.cell_id == n and not nd.is_port]
            ordered = ports + cells
            n_total = len(ordered)
            for rank, node in enumerate(ordered):
                x = layer_idx * 4.0
                y = (rank - n_total / 2.0) * 2.8
                pos[node] = (x, y)
    except nx.NetworkXUnfeasible:
        pos = nx.spring_layout(G, seed=42, k=4.0, iterations=50)

    return pos


# ── Plotly figure builder ─────────────────────────────────────────────────────

# ── Gate block dimensions ───────────────────────────────────────────────


_GB = {
    "default": (1.6, 0.9),
    "dff":     (1.8, 1.0),
    "inv":     (1.2, 0.7),
    "buf":     (1.2, 0.7),
    "mux":     (1.8, 1.0),
    "conb":    (1.0, 0.6),
}

_GW = 1.6
_GH = 0.9

_GATE_SYMBOLS = {
    "and":   "&",  "nand": "&",
    "or":    "≥1","nor":  "≥1",
    "xor":   "=1","xnor": "=1",
    "inv":   "1",  "buf":  "1",
    "dff":   "DFF",
    "aoi":   "A/O","oai":  "O/A",
    "conb":  "01",
    "other": "?",
}

_GATE_LABELS = {
    "and":   "AND",   "nand": "NAND",
    "or":    "OR",    "nor":  "NOR",
    "xor":   "XOR",   "xnor": "XNOR",
    "inv":   "INV",   "buf":  "BUF",
    "dff":   "DFF",
    "aoi":   "AOI",   "oai":  "OAI",
    "conb":  "CONST",
    "other": "CELL",
}


def _node_dims(node: CellNode) -> Tuple[float, float]:
    gw, gh = _GB.get(node.family, _GB["default"])
    if node.family in ("inv", "buf", "conb"):
        gw = max(gw, 1.2)
        gh = max(gh, 0.7)
    return gw, gh


def _pin_positions(
    node: CellNode, pos: Dict[int, Tuple[float, float]]
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Return (in_pos, out_pos) — dicts of pin_name → y-coordinate on block edge."""
    x, y = pos[node.cell_id]
    gw, gh = _node_dims(node)
    hw, hh = gw / 2, gh / 2
    out_keywords = {"X", "Q", "Y", "COUT", "Z", "OUT"}
    in_pins, out_pins = [], []
    for pname in node.ports:
        if pname.upper() in out_keywords:
            out_pins.append(pname)
        else:
            in_pins.append(pname)
    n_in, n_out = len(in_pins), len(out_pins)
    in_pos = {}
    for pi, pname in enumerate(in_pins):
        py = y + hh * (1 - (pi + 1) * 2 / (n_in + 1)) if n_in > 0 else y
        in_pos[pname] = py
    out_pos = {}
    for pi, pname in enumerate(out_pins):
        py = y + hh * (1 - (pi + 1) * 2 / (n_out + 1)) if n_out > 0 else y
        out_pos[pname] = py
    return in_pos, out_pos


def build_schematic_figure(
    nodes: List[CellNode],
    edges: List[Edge],
    stats: Dict[str, int],
    highlight_node: Optional[int] = None,
) -> go.Figure:
    """Build interactive Plotly gate-level schematic."""
    fig    = go.Figure()
    pos    = _compute_layout(nodes, edges)

    highlighted_sources: set = set()
    highlighted_targets: set = set()
    if highlight_node is not None:
        for e in edges:
            if e.source_id == highlight_node:
                highlighted_targets.add(e.target_id)
            if e.target_id == highlight_node:
                highlighted_sources.add(e.source_id)

    # ── Precompute pin positions for every node ─────────────────────
    nodes_by_id: Dict[int, CellNode] = {n.cell_id: n for n in nodes}
    pin_in_pos:  Dict[int, Dict[str, float]] = {}
    pin_out_pos: Dict[int, Dict[str, float]] = {}
    for n in nodes:
        if n.cell_id in pos:
            inp, outp = _pin_positions(n, pos)
            pin_in_pos[n.cell_id] = inp
            pin_out_pos[n.cell_id] = outp

    # ── Group edges by source_layer→target_layer for staggering ─────
    # Compute layer index for each node
    try:
        import networkx as nx
        G = nx.DiGraph()
        for n in nodes:
            G.add_node(n.cell_id)
        for e in edges:
            if pos.get(e.source_id) and pos.get(e.target_id):
                G.add_edge(e.source_id, e.target_id)
        layers_map = {}
        for li, layer in enumerate(nx.topological_generations(G)):
            for nid in layer:
                layers_map[nid] = li
    except Exception:
        layers_map = {}

    edge_groups: Dict[Tuple[int, int], List[Tuple[int, Edge]]] = {}
    for ei, e in enumerate(edges):
        sl = layers_map.get(e.source_id, 0)
        tl = layers_map.get(e.target_id, 0)
        edge_groups.setdefault((sl, tl), []).append((ei, e))

    _STAGGER_SPACING = 0.20

    # ── Edges with pin-accurate routing ──────────────────────────────
    for e in edges:
        if e.source_id not in pos or e.target_id not in pos:
            continue
        src_n = nodes_by_id.get(e.source_id)
        tgt_n = nodes_by_id.get(e.target_id)
        if src_n is None or tgt_n is None:
            continue

        x0, y0 = pos[e.source_id]
        x1, y1 = pos[e.target_id]

        # Source block right-edge X
        gw_src, gh_src = _node_dims(src_n)
        hw_src = gw_src / 2
        src_edge_x = x0 + hw_src

        # Target block left-edge X
        gw_tgt, gh_tgt = _node_dims(tgt_n)
        hw_tgt = gw_tgt / 2
        tgt_edge_x = x1 - hw_tgt

        # Determine source Y from output pin position
        src_pins_out = pin_out_pos.get(e.source_id, {})
        src_edge_y = None
        if e.source_port and e.source_port in src_pins_out:
            src_edge_y = src_pins_out[e.source_port]
        else:
            # Use first output pin or center
            if src_pins_out:
                src_edge_y = list(src_pins_out.values())[0]
            else:
                src_edge_y = y0

        # Determine target Y from input pin position
        tgt_pins_in = pin_in_pos.get(e.target_id, {})
        tgt_edge_y = None
        if e.target_port and e.target_port in tgt_pins_in:
            tgt_edge_y = tgt_pins_in[e.target_port]
        else:
            if tgt_pins_in:
                tgt_edge_y = list(tgt_pins_in.values())[0]
            else:
                tgt_edge_y = y1

        # Stagger: compute a vertical offset for parallel edges
        sl = layers_map.get(e.source_id, 0)
        tl = layers_map.get(e.target_id, 0)
        group = edge_groups.get((sl, tl), [])
        stagger_idx = 0
        for gi, (gei, ge) in enumerate(group):
            if ge is e:
                stagger_idx = gi
                break
        stagger_off = (stagger_idx - (len(group) - 1) / 2) * _STAGGER_SPACING
        # Apply stagger to the vertical segment
        src_y_with_off = src_edge_y + stagger_off
        tgt_y_with_off = tgt_edge_y + stagger_off

        # Vertical segment X: midway between edges
        mid_x = (src_edge_x + tgt_edge_x) / 2

        # Wire style
        if e.is_clock:
            color, dash, width = _CLOCK_COLOR, "dot", 2.5
        elif e.is_reset:
            color, dash, width = _RESET_COLOR, "dash", 2.5
        else:
            color, dash, width = _DATA_COLOR, "solid", 2.0

        if highlight_node is not None:
            related = {highlight_node} | highlighted_sources | highlighted_targets
            opacity = 0.1 if (e.source_id not in related and e.target_id not in related) else 1.0
        else:
            opacity = 0.9

        # Route: source_edge → rightwards → vertical → leftwards → target_edge
        fig.add_trace(go.Scatter(
            x=[src_edge_x, mid_x, mid_x, tgt_edge_x, None],
            y=[src_y_with_off, src_y_with_off, tgt_y_with_off, tgt_y_with_off, None],
            mode="lines",
            line=dict(color=color, width=width, dash=dash),
            opacity=opacity,
            hoverinfo="skip",
            showlegend=False,
        ))

        # Connection dot at target pin
        dot_r = 0.10
        fig.add_shape(
            type="circle",
            x0=tgt_edge_x - dot_r, y0=tgt_y_with_off - dot_r,
            x1=tgt_edge_x + dot_r, y1=tgt_y_with_off + dot_r,
            fillcolor="#ffffff",
            line=dict(color=color, width=1.5),
            opacity=opacity,
            layer="above",
        )

        # Connection dot at source pin
        fig.add_shape(
            type="circle",
            x0=src_edge_x - dot_r, y0=src_y_with_off - dot_r,
            x1=src_edge_x + dot_r, y1=src_y_with_off + dot_r,
            fillcolor=color,
            line=dict(color="#ffffff", width=0.8),
            opacity=opacity,
            layer="above",
        )

        # Net name label on the horizontal segment
        net_label = e.net if e.net else (e.target_port if e.target_port else "")
        if net_label:
            label_x = (src_edge_x + mid_x) / 2
            fig.add_annotation(
                x=label_x, y=src_y_with_off + 0.20,
                text=net_label,
                showarrow=False,
                font=dict(size=8, color=color, family="monospace"),
                opacity=opacity,
                xanchor="center", yanchor="bottom",
            )

    # ── Nodes: Vivado-style rectangular blocks ────────────────────
    for n in nodes:
        if n.cell_id not in pos:
            continue
        x, y = pos[n.cell_id]
        info  = n.family_info

        is_highlighted = (
            highlight_node is None or
            n.cell_id == highlight_node or
            n.cell_id in highlighted_sources or
            n.cell_id in highlighted_targets
        )
        opacity = 1.0 if is_highlighted else 0.15

        if n.is_port:
            shape = "triangle-right" if n.direction == "input" else "triangle-left"
            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode="markers+text",
                marker=dict(
                    color=_PORT_COLORS.get(n.direction, "#888"),
                    size=16,
                    symbol=shape,
                    line=dict(color="#ffffff", width=1),
                ),
                text=[n.short_name],
                textposition="bottom center",
                textfont=dict(color="#dddddd", size=9, family="monospace"),
                hovertext=f"<b>{n.direction.upper()}</b>: {n.short_name}",
                hoverinfo="text",
                showlegend=False,
                opacity=opacity,
                customdata=[n.cell_id],
            ))
        else:
            family = n.family
            fc = info.color
            ec = info.border
            gw, gh = _GB.get(family, _GB["default"])
            # Clamp small gates to default width
            if family in ("inv", "buf", "conb"):
                gw = max(gw, 1.2)
                gh = max(gh, 0.7)
            hw = gw / 2
            hh = gh / 2

            # ── Gate body: rounded rectangle ────────────────────────
            r = 0.12
            fig.add_shape(
                type="rect",
                x0=x - hw, y0=y - hh, x1=x + hw, y1=y + hh,
                xref="x", yref="y",
                line=dict(color=ec, width=2),
                fillcolor=fc,
                opacity=opacity,
                layer="above",
            )

            # ── Gate symbol text (left side inside block) ──────────
            symbol = _GATE_SYMBOLS.get(family, "?")
            fig.add_annotation(
                x=x - hw * 0.35, y=y,
                text=symbol,
                showarrow=False,
                font=dict(
                    color=info.text_color,
                    size=14,
                    family="monospace",
                ),
                xanchor="center", yanchor="middle",
                opacity=opacity,
            )

            # ── Gate type label (right side inside block) ──────────
            gatelabel = _GATE_LABELS.get(family, family.upper())
            fig.add_annotation(
                x=x + hw * 0.25, y=y,
                text=gatelabel,
                showarrow=False,
                font=dict(
                    color=info.text_color,
                    size=10,
                    family="monospace",
                ),
                xanchor="center", yanchor="middle",
                opacity=opacity,
            )

            # ── Instance name below block ───────────────────────────
            fig.add_annotation(
                x=x, y=y - hh - 0.25,
                text=n.instance,
                showarrow=False,
                font=dict(color="#8888aa", size=8, family="monospace"),
                xanchor="center", yanchor="top",
                opacity=opacity,
            )

            # ── Short type name below block ─────────────────────────
            fig.add_annotation(
                x=x, y=y - hh - 0.45,
                text=n.short_name,
                showarrow=False,
                font=dict(color="#555577", size=7, family="monospace"),
                xanchor="center", yanchor="top",
                opacity=opacity,
            )

            # ── Pin annotations on block edges ─────────────────────
            in_pins  = []
            out_pins = []
            out_keywords = {"X", "Q", "Y", "COUT", "Z", "OUT"}
            for pname, pnet in n.ports.items():
                if pname.upper() in out_keywords:
                    out_pins.append((pname, pnet))
                else:
                    in_pins.append((pname, pnet))
            n_in = len(in_pins)
            n_out = len(out_pins)

            for pi, (pname, pnet) in enumerate(in_pins):
                py = y + hh * (1 - (pi + 1) * 2 / (n_in + 1)) if n_in > 0 else y
                # Pin connection dot on block edge
                fig.add_shape(
                    type="circle",
                    x0=x - hw - 0.04, y0=py - 0.04,
                    x1=x - hw + 0.04, y1=py + 0.04,
                    fillcolor="#88bbdd",
                    line=dict(color="#88bbdd", width=0.5),
                    opacity=opacity,
                    layer="above",
                )
                fig.add_annotation(
                    x=x - hw - 0.20, y=py,
                    text=f".{pname}",
                    showarrow=False,
                    font=dict(color="#99ccff", size=8, family="monospace"),
                    xanchor="right", yanchor="middle",
                    opacity=opacity,
                )

            for pi, (pname, pnet) in enumerate(out_pins):
                py = y + hh * (1 - (pi + 1) * 2 / (n_out + 1)) if n_out > 0 else y
                # Pin connection dot on block edge
                fig.add_shape(
                    type="circle",
                    x0=x + hw - 0.04, y0=py - 0.04,
                    x1=x + hw + 0.04, y1=py + 0.04,
                    fillcolor="#ddbb88",
                    line=dict(color="#ddbb88", width=0.5),
                    opacity=opacity,
                    layer="above",
                )
                fig.add_annotation(
                    x=x + hw + 0.20, y=py,
                    text=f".{pname}",
                    showarrow=False,
                    font=dict(color="#ffcc88", size=8, family="monospace"),
                    xanchor="left", yanchor="middle",
                    opacity=opacity,
                )

            # ── Hover data ──────────────────────────────────────────
            pin_lines = "<br>".join(f"  .{p} → {net}" for p, net in n.ports.items())
            hover = (
                f"<b>{n.short_name}</b>  ({n.family})<br>"
                f"  instance: {n.instance}<br>"
                f"  type: {n.cell_type}<br>"
                f"  pins:<br>{pin_lines}"
            )
            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode="markers",
                marker=dict(size=20, color="rgba(0,0,0,0)"),
                hovertext=hover,
                hoverinfo="text",
                showlegend=False,
                opacity=opacity,
                customdata=[n.cell_id],
            ))

    # ── Gate count annotations ──────────────────────────────────────
    y_ann = 1.0
    stats_text = "<b>Gate Count</b><br>"
    for label in ["DFF", "NAND", "NOR", "AND", "OR", "XOR", "XNOR",
                   "INV", "BUF", "MUX", "AOI", "OAI", "CONST", "CELL"]:
        cnt = stats.get(label, 0)
        if cnt:
            gf = _GATE_FAMILIES.get(
                label.lower(), _GATE_FAMILIES.get("other"))
            color = gf.color
            stats_text += (
                f'<span style="color:{color}">■</span> '
                f'{label}: {cnt}<br>'
            )
            y_ann -= 0.04

    fig.add_annotation(
        xref="paper", yref="paper",
        x=1.02, y=1.0,
        text=stats_text,
        showarrow=False,
        font=dict(size=10, color="#cccccc"),
        align="left",
        xanchor="left", yanchor="top",
        bgcolor="rgba(10,10,30,0.85)",
        bordercolor="#333366",
        borderwidth=1,
    )

    # ── Layout ──────────────────────────────────────────────────────
    fig.update_layout(
        paper_bgcolor="#0d0d18",
        plot_bgcolor="#111122",
        font=dict(family="monospace", size=10, color="#cccccc"),
        height=700,
        margin=dict(l=30, r=190, t=35, b=30),
        title=dict(
            text=f"Gate-Level Schematic — {len(nodes)} cells, {len(edges)} nets",
            font=dict(size=13, color="#ccccee"),
        ),
        xaxis=dict(
            showticklabels=False, showgrid=False, zeroline=False,
            range=None,
        ),
        yaxis=dict(
            showticklabels=False, showgrid=False, zeroline=False,
        ),
        hovermode="closest",
        dragmode="pan",
        modebar=dict(bgcolor="rgba(0,0,0,0)", color="#888888"),
        clickmode="event+select",
    )

    return fig


# ── Streamlit entry point ─────────────────────────────────────────────────────

def render_schematic_enhanced_streamlit(
    netlist_path: Optional[Path],
    key_prefix: str = "sch",
) -> None:
    """Interactive gate-level schematic for Streamlit."""
    import streamlit as st

    if not netlist_path or not Path(netlist_path).exists():
        st.warning("No synthesized netlist available for this design.")
        st.caption("Run the full pipeline (Step 2: Synthesis) to generate a netlist.")
        return

    netlist_path = Path(netlist_path)

    with st.spinner(f"Parsing {netlist_path.name} …"):
        nodes, edges, stats = parse_synthesized_netlist(netlist_path)

    if not nodes:
        st.warning("Netlist parsed but contains no cells.")
        return

    # ── Header ───────────────────────────────────────────────────────
    n_cells = sum(1 for n in nodes if not n.is_port)
    n_ports = sum(1 for n in nodes if n.is_port)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cells", n_cells)
    col2.metric("Ports", n_ports)
    col3.metric("Nets",  len(edges))
    col4.metric("Types", len(stats))

    # ── Gate family filter ───────────────────────────────────────────
    families_in_use: Dict[str, bool] = {}
    for n in nodes:
        if not n.is_port:
            families_in_use[n.family] = True

    with st.expander("Filter by gate type", expanded=False):
        cols = st.columns(5)
        filter_key = f"{key_prefix}_filters"
        if filter_key not in st.session_state:
            st.session_state[filter_key] = {f: True for f in families_in_use}
        for i, fam in enumerate(sorted(families_in_use.keys())):
            gf = _GATE_FAMILIES.get(fam, _GATE_FAMILIES["other"])
            checked = st.session_state[filter_key].get(fam, True)
            if cols[i % 5].checkbox(
                f"{gf.label} ({stats.get(gf.label, 0)})",
                value=checked,
                key=f"{key_prefix}_cb_{fam}",
            ):
                st.session_state[filter_key][fam] = True
            else:
                st.session_state[filter_key][fam] = False

    filtered_ids = {
        n.cell_id for n in nodes
        if n.is_port or st.session_state[filter_key].get(n.family, True)
    }
    filtered_nodes = [n for n in nodes if n.cell_id in filtered_ids]
    filtered_edges = [
        e for e in edges
        if e.source_id in filtered_ids and e.target_id in filtered_ids
    ]

    if not filtered_nodes:
        st.info("No cells match the current filter selection.")
        return

    # ── Click-to-highlight ──────────────────────────────────────────
    sel_key = f"{key_prefix}_sel"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = None

    fig = build_schematic_figure(
        filtered_nodes, filtered_edges, stats,
        highlight_node=st.session_state[sel_key],
    )

    # Handle click events
    ev = st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_chart",
                          on_select="rerun")
    if ev and hasattr(ev, "selection") and ev.selection:
        pts = ev.selection.get("points")
        if pts:
            cid = pts[0].get("customdata")
            if cid is not None:
                if st.session_state[sel_key] == cid:
                    st.session_state[sel_key] = None  # toggle off
                else:
                    st.session_state[sel_key] = cid
                st.rerun()

    # ── Clear highlight button ──────────────────────────────────────
    if st.session_state[sel_key] is not None:
        if st.button("Clear highlight", key=f"{key_prefix}_clear"):
            st.session_state[sel_key] = None
            st.rerun()

    # ── Cell detail panel ────────────────────────────────────────────
    if st.session_state[sel_key] is not None:
        sel_node = next(
            (n for n in nodes if n.cell_id == st.session_state[sel_key]), None
        )
        if sel_node:
            st.markdown("---")
            st.markdown(f"**Selected: {sel_node.short_name}** ({sel_node.family})")
            if not sel_node.is_port:
                st.code(
                    f"Instance: {sel_node.instance}\n"
                    f"Type:     {sel_node.cell_type}\n"
                    f"Family:   {sel_node.family}\n"
                    + "\n".join(f"  .{p} = {net}" for p, net in sel_node.ports.items())
                )
            else:
                st.info(f"Module port: {sel_node.direction} {sel_node.short_name}")

            # Show fan-in and fan-out
            fan_in  = [e for e in edges if e.target_id == sel_node.cell_id]
            fan_out = [e for e in edges if e.source_id == sel_node.cell_id]
            if fan_in:
                st.caption(f"Fan-in ({len(fan_in)}): " + ", ".join(
                    f"{e.net}→{e.target_port}" for e in fan_in[:8]
                ))
            if fan_out:
                st.caption(f"Fan-out ({len(fan_out)}): " + ", ".join(
                    f"{e.source_port}→{e.net}" for e in fan_out[:8]
                ))


# ── Standalone test ───────────────────────────────────────────────────────────

def _make_test_netlist(path: Path) -> None:
    """Create a synthetic Yosys-style netlist for testing."""
    content = r"""/* Generated by Yosys 0.38 */
module test_adder_8bit(clk, reset_n, a, b, sum);
  input clk;
  input reset_n;
  input [7:0] a;
  input [7:0] b;
  output [8:0] sum;
  wire _00_;
  wire _01_;
  wire _02_;
  wire _03_;
  wire _04_;
  wire _05_;
  wire _06_;
  wire _07_;
  wire _08_;
  wire _09_;
  wire _10_;
  wire _11_;
  wire _12_;
  wire _13_;
  wire _14_;
  wire _15_;
  wire _16_;
  wire _17_;
  wire _18_;

  sky130_fd_sc_hd__nand2_1 _19_ (
    .A(b[1]),
    .B(a[1]),
    .Y(_00_)
  );
  sky130_fd_sc_hd__nand2_1 _20_ (
    .A(b[0]),
    .B(a[0]),
    .Y(_01_)
  );
  sky130_fd_sc_hd__nor2_1 _21_ (
    .A(b[1]),
    .B(a[1]),
    .Y(_02_)
  );
  sky130_fd_sc_hd__lpflow_isobufsrc_1 _22_ (
    .A(_00_),
    .SLEEP(_02_),
    .X(_03_)
  );
  sky130_fd_sc_hd__a2o2bbai_1 _23_ (
    .A1(b[0]),
    .A2(a[0]),
    .B1(_03_),
    .B2(_01_),
    .Y(_04_)
  );
  sky130_fd_sc_hd__nand2_1 _24_ (
    .A(b[2]),
    .B(a[2]),
    .Y(_05_)
  );
  sky130_fd_sc_hd__nor2_1 _25_ (
    .A(b[2]),
    .B(a[2]),
    .Y(_06_)
  );
  sky130_fd_sc_hd__a21boi_1 _26_ (
    .A1(_04_),
    .A2(_05_),
    .B1_N(_06_),
    .Y(_07_)
  );
  sky130_fd_sc_hd__a2o2bbai_1 _27_ (
    .A1(b[3]),
    .A2(a[3]),
    .B1(_07_),
    .B2(_05_),
    .Y(_08_)
  );
  sky130_fd_sc_hd__nor2_1 _28_ (
    .A(b[3]),
    .B(a[3]),
    .Y(_09_)
  );
  sky130_fd_sc_hd__a21boi_1 _29_ (
    .A1(_08_),
    .A2(_09_),
    .B1_N(_09_),
    .Y(_10_)
  );
  sky130_fd_sc_hd__dfxtp_1 _30_ (
    .CLK(clk),
    .D(sum[0]),
    .Q(sum[0])
  );
  sky130_fd_sc_hd__dfxtp_1 _31_ (
    .CLK(clk),
    .D(sum[1]),
    .Q(sum[1])
  );
  sky130_fd_sc_hd__conb_1 _32_ (
    .HI(_17_),
    .LO(_18_)
  );
  sky130_fd_sc_hd__buf_1 _33_ (
    .A(_17_),
    .X(sum[8])
  );
endmodule
"""
    path.write_text(content)


if __name__ == "__main__":
    import sys
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("schematic_enhanced.py — standalone self-test")
    print("=" * 60)

    passed = total = 0

    # Test 1: netlist parsing
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        nl = Path(tmp) / "test_netlist.v"
        _make_test_netlist(nl)
        nodes, edges, stats = parse_synthesized_netlist(nl)
        assert len(nodes) > 0, "No nodes parsed"
        assert len(edges) > 0, "No edges parsed"
        cell_nodes = [n for n in nodes if not n.is_port]
        port_nodes = [n for n in nodes if n.is_port]
        print(f"[PASS] Parsed: {len(cell_nodes)} cells, {len(port_nodes)} ports, {len(edges)} edges")
        gate_types = set(n.family for n in cell_nodes)
        print(f"       Gate types: {sorted(gate_types)}")
        passed += 1

        # Test 2: gate family classification
        total += 1
        families_found = {n.family for n in cell_nodes}
        for expected in ("nand", "nor", "dff", "buf", "aoi"):
            assert expected in families_found, \
                f"Expected {expected} not found in {families_found}"
        print(f"[PASS] Gate families correct: {sorted(families_found)}")
        passed += 1

        # Test 3: short name extraction
        total += 1
        names = {n.short_name for n in cell_nodes}
        for expected in ("NAND2", "NOR2", "DFF", "BUF", "A2O2BBAI"):
            assert expected in names, \
                f"Expected {expected} not in {names}"
        print(f"[PASS] Short names: {sorted(names)}")
        passed += 1

        # Test 4: edge properties
        total += 1
        clk_edges = [e for e in edges if e.is_clock]
        assert len(clk_edges) > 0, "No clock edges found"
        print(f"[PASS] Clock edges: {len(clk_edges)}, "
              f"data edges: {len(edges) - len(clk_edges)}")
        passed += 1

        # Test 5: Plotly figure builds
        total += 1
        fig = build_schematic_figure(nodes, edges, stats)
        assert isinstance(fig, go.Figure), "Not a Plotly figure"
        assert len(fig.data) > 0, "Figure has no traces"
        n_shapes = len(fig.layout.shapes)
        n_cells_w_shape = sum(1 for n in cell_nodes if n.family not in ("port",))
        assert n_shapes >= n_cells_w_shape * 1, \
            f"Expected ≥{n_cells_w_shape} shapes, got {n_shapes}"
        trace_modes = [t.mode for t in fig.data if t.mode is not None]
        assert "lines" in " ".join(trace_modes), "No line traces"
        print(f"[PASS] Plotly figure: {len(fig.data)} traces, {n_shapes} gate shapes")
        passed += 1

        # Test 6: stats dict
        total += 1
        assert len(stats) > 0, "Empty stats"
        print(f"[PASS] Gate stats: {stats}")
        passed += 1

        # Test 7: highlight mode
        total += 1
        highlight_id = cell_nodes[0].cell_id if cell_nodes else 0
        fig_h = build_schematic_figure(nodes, edges, stats, highlight_node=highlight_id)
        assert isinstance(fig_h, go.Figure), "Highlight figure failed"
        print(f"[PASS] Highlight mode OK (node {highlight_id})")
        passed += 1

        # Test 8: empty netlist
        total += 1
        empty = Path(tmp) / "empty.v"
        empty.write_text("module empty(); endmodule")
        nodes_e, edges_e, stats_e = parse_synthesized_netlist(empty)
        print(f"[PASS] Empty netlist handled: {len(nodes_e)} nodes, {len(edges_e)} edges")
        passed += 1

        # Test 9: GateFamily definitions
        total += 1
        assert len(_GATE_FAMILIES) >= 10, f"Expected ≥10 families, got {len(_GATE_FAMILIES)}"
        for key in ("nand", "nor", "and", "or", "xor", "inv", "buf", "dff", "mux", "conb"):
            assert key in _GATE_FAMILIES, f"Missing family: {key}"
            gf = _GATE_FAMILIES[key]
            assert gf.color.startswith("#"), f"Bad color for {key}: {gf.color}"
            assert gf.size >= 16, f"Bad size for {key}: {gf.size}"
        print(f"[PASS] GateFamily definitions: {len(_GATE_FAMILIES)} families, all valid")
        passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED — schematic_enhanced.py ready for integration")
    else:
        print("SOME TESTS FAILED — check output above")
    print("=" * 60)
