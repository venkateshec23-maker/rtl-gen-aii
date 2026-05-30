# visualizer.py
# Cadence-style live viewers for Streamlit:
#   - GDS Layout   (layer-by-layer chip view)
#   - VCD Waveform (GTKWave-style digital signals)
#   - Netlist Schematic (gate connectivity graph)
#   - Downloads panel (all artifacts)

import re
import struct
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ============================================================
# GDS READER — pure Python, no C dependencies
# Reads GDS binary format and extracts polygons per layer
# ============================================================

# Sky130 layer colour map (layer number -> (name, colour))
SKY130_LAYERS = {
    0:  ("Comment",    "#888888"),
    4:  ("NWell",      "#CC99FF"),
    5:  ("DNWell",     "#AA66FF"),
    6:  ("LVTN",       "#FFCCCC"),
    17: ("N+diff",     "#FF8800"),
    18: ("P+diff",     "#FF4444"),
    30: ("Poly",       "#FF2222"),
    44: ("LiPo",       "#CC4400"),
    47: ("LiDiff",     "#FF6600"),
    65: ("M1",         "#4488FF"),
    66: ("M1 Label",   "#6699FF"),
    67: ("Via1",       "#AAAAAA"),
    68: ("M2",         "#88CCFF"),
    69: ("M2 Label",   "#AADDFF"),
    70: ("Via2",       "#CCCCCC"),
    71: ("M3",         "#FFFF44"),
    74: ("Via3",       "#DDDDDD"),
    75: ("M4",         "#FF88FF"),
    76: ("Via4",       "#EEEEEE"),
    77: ("M5",         "#88FFFF"),
    236: ("Pad",       "#FFFFFF"),
}

def _gds_read_short(data, pos):
    return struct.unpack_from(">H", data, pos)[0]

def _gds_read_int(data, pos):
    return struct.unpack_from(">i", data, pos)[0]

def parse_gds_layers(gds_path: str) -> Dict[int, List[List[Tuple[float, float]]]]:
    """
    Read a GDS file and return polygons grouped by layer.
    Returns: {layer_num: [[(x,y), ...], ...]}
    Uses pure Python struct unpacking — no C compiler needed.
    """
    data = Path(gds_path).read_bytes()
    polygons: Dict[int, List] = {}
    pos = 0
    current_layer = None
    in_boundary = False
    coords = []

    while pos < len(data) - 4:
        try:
            length = _gds_read_short(data, pos)
            if length < 4:
                pos += 2
                continue
            record_type = data[pos + 2]
            data_type   = data[pos + 3]
            payload     = data[pos + 4: pos + length]
            pos += length

            # BOUNDARY start
            if record_type == 0x08:
                in_boundary = True
                coords = []
                current_layer = None

            # LAYER
            elif record_type == 0x0D and in_boundary:
                current_layer = _gds_read_short(payload, 0)

            # XY coordinates
            elif record_type == 0x10 and in_boundary and current_layer is not None:
                n_pairs = len(payload) // 8
                pts = []
                for i in range(n_pairs):
                    x = _gds_read_int(payload, i * 8) / 1000.0   # nm -> um
                    y = _gds_read_int(payload, i * 8 + 4) / 1000.0
                    pts.append((x, y))
                coords = pts

            # ENDEL (end of element)
            elif record_type == 0x11 and in_boundary:
                if current_layer is not None and coords:
                    polygons.setdefault(current_layer, []).append(coords)
                in_boundary = False
                coords = []
                current_layer = None
        except Exception:
            pos += 2
            continue

    return polygons


def _hex_to_rgba(hex_color: str, alpha: float = 0.3) -> str:
    """Convert #RRGGBB to rgba(r,g,b,alpha) for Plotly compatibility."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    return f"rgba(128,128,128,{alpha})"


def make_gds_figure(gds_path: str, max_polys_per_layer: int = 500):
    """
    Build a Plotly figure of the GDS layout.
    Returns a plotly Figure or None if file unreadable.
    """
    import plotly.graph_objects as go

    try:
        polygons = parse_gds_layers(gds_path)
    except Exception as e:
        return None

    if not polygons:
        return None

    fig = go.Figure()
    legend_added = set()

    for layer_num, poly_list in sorted(polygons.items()):
        name, color = SKY130_LAYERS.get(layer_num, (f"Layer {layer_num}", "#AAAAAA"))
        fill_rgba = _hex_to_rgba(color, 0.35)
        shown = poly_list[:max_polys_per_layer]
        show_legend = layer_num not in legend_added
        legend_added.add(layer_num)

        for pi, poly in enumerate(shown):
            xs = [p[0] for p in poly] + [poly[0][0]]
            ys = [p[1] for p in poly] + [poly[0][1]]
            try:
                fig.add_trace(go.Scatter(
                    x=xs, y=ys,
                    fill="toself",
                    fillcolor=fill_rgba,
                    line=dict(color=color, width=0.5),
                    name=name,
                    legendgroup=name,
                    showlegend=(show_legend and pi == 0),
                    hoverinfo="name",
                    mode="lines",
                ))
            except Exception:
                continue

    total_polys = sum(len(v) for v in polygons.values())
    fig.update_layout(
        title=dict(
            text=f"GDS Layout — {Path(gds_path).name}  ({total_polys:,} polygons, {len(polygons)} layers)",
            font=dict(color="#00ff9d")
        ),
        paper_bgcolor="#0a0a1a",
        plot_bgcolor="#0e0e1e",
        font=dict(color="#cccccc"),
        xaxis=dict(title="X (µm)", showgrid=True, gridcolor="#222244",
                   zeroline=False, scaleanchor="y"),
        yaxis=dict(title="Y (µm)", showgrid=True, gridcolor="#222244",
                   zeroline=False),
        legend=dict(bgcolor="#111122", bordercolor="#333355"),
        height=600,
        margin=dict(l=60, r=20, t=60, b=60),
    )
    return fig


# ============================================================
# VCD WAVEFORM PARSER + PLOTTER
# Parses .vcd files and renders as interactive digital waveforms
# ============================================================

def parse_vcd(vcd_path: str) -> Dict:
    """
    Parse a VCD file into signal data.
    Returns: {
        "timescale": "1ns",
        "signals": {name: {"id": id, "width": int, "values": [(time, value), ...]}},
        "end_time": int
    }
    """
    content = Path(vcd_path).read_text(errors="ignore")
    result = {
        "timescale": "1ns",
        "signals": {},
        "end_time": 0
    }

    # --- Header parsing ---
    ts_m = re.search(r'\$timescale\s+(.*?)\s*\$end', content, re.DOTALL)
    if ts_m:
        result["timescale"] = ts_m.group(1).strip()

    # Find all variable declarations
    id_to_name: Dict[str, str] = {}
    id_to_width: Dict[str, int] = {}
    for m in re.finditer(
        r'\$var\s+\w+\s+(\d+)\s+(\S+)\s+(\S+)(?:\s+\[\d+:\d+\])?\s*\$end',
        content
    ):
        width, vid, name = int(m.group(1)), m.group(2), m.group(3)
        id_to_name[vid]  = name
        id_to_width[vid] = width
        result["signals"][name] = {"id": vid, "width": width, "values": []}

    # --- Value changes ---
    current_time = 0
    name_to_vals: Dict[str, List] = {n: [] for n in result["signals"]}

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("$"):
            continue
        if line.startswith("#"):
            try:
                current_time = int(line[1:])
                result["end_time"] = max(result["end_time"], current_time)
            except ValueError:
                pass
        elif line[0] in "01xXzZ" and len(line) > 1:
            val = 1 if line[0] == "1" else 0
            vid = line[1:]
            if vid in id_to_name:
                name_to_vals[id_to_name[vid]].append((current_time, val))
        elif line.startswith("b") and " " in line:
            parts = line.split()
            if len(parts) >= 2:
                bval = parts[0][1:]
                vid  = parts[1]
                try:
                    val = int(bval, 2)
                except ValueError:
                    val = 0
                if vid in id_to_name:
                    name_to_vals[id_to_name[vid]].append((current_time, val))

    for name, vals in name_to_vals.items():
        result["signals"][name]["values"] = vals

    return result


def make_waveform_figure(vcd_path: str, max_signals: int = 20):
    """
    Build a Plotly figure of digital waveforms from a VCD file.
    Shows each signal as a separate row (like GTKWave in a browser).
    """
    import plotly.graph_objects as go

    try:
        vcd = parse_vcd(vcd_path)
    except Exception as e:
        return None

    signals = {
        name: data for name, data in vcd["signals"].items()
        if data["values"]
    }

    if not signals:
        return None

    signal_names = list(signals.keys())[:max_signals]
    n = len(signal_names)
    end_t = vcd["end_time"] or 1000

    # Each signal occupies a vertical band
    fig = go.Figure()
    SPACING = 2.5       # vertical units per signal
    AMPLITUDE = 1.8     # height of a "1"

    colors = [
        "#00ff9d", "#4488ff", "#ff8800", "#ff4466",
        "#88ffcc", "#ffcc00", "#cc88ff", "#00ccff",
    ]

    for idx, name in enumerate(signal_names):
        data   = signals[name]
        vals   = data["values"]
        width  = data["width"]
        color  = colors[idx % len(colors)]
        base_y = (n - idx - 1) * SPACING

        # Build step waveform
        times  = [0]
        levels = [0]
        for t, v in sorted(vals):
            if v > 1:
                norm = min(v / (2 ** width), 1.0)
            else:
                norm = float(v)
            times.append(t)
            levels.append(levels[-1])    # horizontal run
            times.append(t)
            levels.append(norm)          # vertical edge
        times.append(end_t)
        levels.append(levels[-1])

        ys = [base_y + lv * AMPLITUDE for lv in levels]

        fig.add_trace(go.Scatter(
            x=times, y=ys,
            mode="lines",
            line=dict(color=color, width=2),
            name=name,
            hovertemplate=f"<b>{name}</b><br>Time: %{{x}}<br>Value: %{{customdata}}<extra></extra>",
            customdata=[lv for lv in levels],
        ))

        # Add signal name as annotation on left
        fig.add_annotation(
            x=0, y=base_y + AMPLITUDE / 2,
            text=f"<b>{name}</b>",
            showarrow=False,
            xanchor="right",
            font=dict(color=color, size=11),
            xshift=-5,
        )

    # Timescale ticks every ~10% of total time
    tick_step = max(1, end_t // 10)

    fig.update_layout(
        title=dict(
            text=f"Waveform — {Path(vcd_path).name}  |  Timescale: {vcd['timescale']}  |  Duration: {end_t}",
            font=dict(color="#00ff9d")
        ),
        paper_bgcolor="#0a0a1a",
        plot_bgcolor="#0e0e1e",
        font=dict(color="#cccccc"),
        xaxis=dict(
            title=f"Time ({vcd['timescale']})",
            showgrid=True, gridcolor="#222244",
            dtick=tick_step,
            zeroline=False,
            range=[0, end_t],
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=[-0.5, n * SPACING],
        ),
        height=max(300, n * 60 + 100),
        margin=dict(l=120, r=20, t=60, b=60),
        showlegend=False,
    )

    # Marker at time=0
    fig.add_vline(x=0, line=dict(color="#555577", width=1, dash="dot"))

    return fig


# ============================================================
# NETLIST SCHEMATIC — parse synthesized Verilog → gate graph
# ============================================================

def parse_netlist_cells(netlist_path: str) -> Tuple[List, List]:
    """
    Parse a synthesized Verilog netlist.
    Returns (nodes, edges) for Plotly graph.
    nodes: [{"id": n, "label": label, "type": cell_type, "color": c}]
    edges: [{"from": n1, "to": n2, "net": wire_name}]
    """
    content = Path(netlist_path).read_text(errors="ignore")
    nodes   = []
    edges   = []
    node_id = 0
    net_to_driver: Dict[str, int] = {}   # net name → driving node id

    # Module ports
    port_matches = re.findall(
        r'(input|output)\s+(?:wire\s+)?(?:\[\d+:\d+\]\s+)?(\w+)', content
    )
    port_nodes: Dict[str, int] = {}
    for direction, pname in port_matches[:30]:  # cap at 30 ports
        color = "#00ff9d" if direction == "input" else "#ff8800"
        shape = "triangle-up" if direction == "input" else "triangle-down"
        nodes.append({"id": node_id, "label": pname, "type": direction,
                      "color": color, "shape": shape})
        if direction == "input":
            net_to_driver[pname] = node_id
        port_nodes[pname] = node_id
        node_id += 1

    # Cell instantiations
    cell_pattern = re.compile(
        r'(sky130_fd_sc_hd__\w+)\s+(\w+)\s*\(([^;]+)\);', re.DOTALL
    )
    cell_color = {
        "buf":    "#4488ff",
        "inv":    "#ff4466",
        "and":    "#88ccff",
        "or":     "#ffcc44",
        "xor":    "#cc88ff",
        "nand":   "#ff8888",
        "nor":    "#ff88cc",
        "mux":    "#44ffcc",
        "dff":    "#ffaa00",
        "conb":   "#888888",
    }

    for m in cell_pattern.finditer(content):
        cell_type_full = m.group(1)
        # Get short type for color
        short = "buf"
        for k in cell_color:
            if k in cell_type_full:
                short = k
                break
        color = cell_color.get(short, "#aaaaaa")

        # Parse ports from (.PORT(NET), ...)
        port_str = m.group(3)
        conn_map: Dict[str, str] = {}
        for pm in re.finditer(r'\.(\w+)\s*\(\s*(\w+[\w\[\]:]*)\s*\)', port_str):
            conn_map[pm.group(1)] = pm.group(2)

        label = cell_type_full.replace("sky130_fd_sc_hd__", "").split("_")[0]
        nodes.append({
            "id":    node_id,
            "label": label,
            "type":  cell_type_full,
            "color": color,
            "shape": "circle"
        })

        # Output ports drive nets
        for pname, net in conn_map.items():
            if pname.upper() in ("X", "Q", "Y", "COUT"):
                net_to_driver[net] = node_id

        # Input ports consume nets → create edges later
        for pname, net in conn_map.items():
            if pname.upper() not in ("X", "Q", "Y", "COUT"):
                edges.append({"from_net": net, "to_id": node_id, "port": pname})

        node_id += 1

    # Resolve edges: from_net → (driver_id → to_id)
    resolved_edges = []
    for e in edges:
        driver = net_to_driver.get(e["from_net"])
        if driver is not None and driver != e["to_id"]:
            resolved_edges.append({
                "from": driver,
                "to":   e["to_id"],
                "net":  e["from_net"]
            })
        # Output port → port node
        if e["from_net"] in port_nodes:
            port_id = port_nodes[e["from_net"]]
            resolved_edges.append({
                "from": port_id,
                "to":   e["to_id"],
                "net":  e["from_net"]
            })

    return nodes, resolved_edges


def make_schematic_figure(netlist_path: str, max_cells: int = 80):
    """
    Build a Plotly figure of the gate-level schematic.
    Uses a layered left-to-right layout.
    """
    import plotly.graph_objects as go
    import networkx as nx

    try:
        nodes, edges = parse_netlist_cells(netlist_path)
    except Exception:
        return None

    if not nodes:
        return None

    # Cap
    nodes = nodes[:max_cells + 20]  # +20 for ports

    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"], **n)
    for e in edges:
        if G.has_node(e["from"]) and G.has_node(e["to"]):
            G.add_edge(e["from"], e["to"], net=e["net"])

    # Layered layout using topological sort
    try:
        layers = list(nx.topological_generations(G))
        pos = {}
        for layer_idx, layer in enumerate(layers):
            n_in_layer = len(layer)
            for rank, node in enumerate(sorted(layer)):
                x = layer_idx * 3.0
                y = (rank - n_in_layer / 2.0) * 2.0
                pos[node] = (x, y)
    except nx.NetworkXUnfeasible:
        # Fallback: spring layout
        pos = nx.spring_layout(G, seed=42)

    fig = go.Figure()

    # Draw edges
    for src, dst, data in G.edges(data=True):
        if src in pos and dst in pos:
            x0, y0 = pos[src]
            x1, y1 = pos[dst]
            fig.add_trace(go.Scatter(
                x=[x0, x1, None], y=[y0, y1, None],
                mode="lines",
                line=dict(color="#334466", width=1),
                hoverinfo="skip",
                showlegend=False,
            ))

    # Draw nodes
    for ndata in nodes:
        nid = ndata["id"]
        if nid not in pos:
            continue
        x, y = pos[nid]
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            marker=dict(
                color=ndata["color"],
                size=20,
                line=dict(color="#ffffff", width=1),
                symbol=ndata.get("shape", "circle"),
            ),
            text=[ndata["label"]],
            textposition="bottom center",
            textfont=dict(color="#cccccc", size=8),
            name=ndata["type"],
            hovertext=ndata["type"],
            hoverinfo="text",
            showlegend=False,
        ))

    n_cells = sum(1 for n in nodes if n.get("shape") == "circle")
    fig.update_layout(
        title=dict(
            text=f"Gate-Level Schematic — {Path(netlist_path).name}  ({n_cells} cells, {len(edges)} nets)",
            font=dict(color="#00ff9d")
        ),
        paper_bgcolor="#0a0a1a",
        plot_bgcolor="#0e0e1e",
        font=dict(color="#cccccc"),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        height=600,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig
