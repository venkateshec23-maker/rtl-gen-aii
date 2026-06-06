"""
netlist_viewer.py
=================
Parse synthesized Verilog netlist and generate
schematic visualization using Streamlit + Graphviz.
Shows: cells, pin-to-pin connections, inputs, outputs.
Commercial equivalent: Cadence Schematic Viewer
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class NetlistCell:
    cell_type: str
    instance:  str
    ports:     Dict[str, str] = field(default_factory=dict)


@dataclass
class NetlistInfo:
    module_name: str
    inputs:      List[str]
    outputs:     List[str]
    wires:       List[str]
    cells:       List[NetlistCell]
    cell_counts: Dict[str, int]


def parse_netlist(netlist_path: str) -> NetlistInfo:
    """
    Parse Sky130A synthesized Verilog netlist.
    Extracts: ports, wires, cell instances, connections.
    """
    path = Path(netlist_path)
    if not path.exists():
        return None

    content = path.read_text(errors="ignore")

    # Extract module name
    mod_m = re.search(r'module\s+(\w+)\s*\(', content)
    module_name = mod_m.group(1) if mod_m else "unknown"

    # Extract inputs and outputs
    inputs  = re.findall(r'input\s+(?:\[[\d:]+\]\s+)?(\w+)', content)
    outputs = re.findall(r'output\s+(?:reg\s+)?(?:\[[\d:]+\]\s+)?(\w+)', content)
    wires   = re.findall(r'wire\s+(?:\[[\d:]+\]\s+)?(\w+)', content)

    # Extract cell instances (Sky130 standard cells)
    cells = []
    cell_counts = {}

    # Pattern: sky130_fd_sc_hd__cellname_X instance (.ports);
    cell_pattern = re.compile(
        r'(sky130_fd_sc_hd__\w+)\s+(\w+)\s*\('
        r'([\s\S]*?)\)\s*;',
        re.MULTILINE
    )

    for m in cell_pattern.finditer(content):
        cell_type = m.group(1)
        instance  = m.group(2)
        port_str  = m.group(3)

        # Parse ports: .PORT(net)
        ports = {}
        for pm in re.finditer(r'\.(\w+)\s*\(([^)]*)\)', port_str):
            ports[pm.group(1)] = pm.group(2).strip()

        cells.append(NetlistCell(cell_type, instance, ports))

        short_type = cell_type.replace('sky130_fd_sc_hd__', '')
        cell_counts[short_type] = cell_counts.get(short_type, 0) + 1

    return NetlistInfo(
        module_name=module_name,
        inputs=inputs,
        outputs=outputs,
        wires=wires,
        cells=cells,
        cell_counts=cell_counts
    )


def is_output_pin(pin_name: str) -> bool:
    """Check if pin is typically an output in Sky130 sc_hd library."""
    return pin_name.upper() in ("X", "Y", "Q", "CON", "COUT", "S", "S0", "S1")


def is_ignored_pin(pin_name: str) -> bool:
    """Check if pin is a power/ground pin."""
    return pin_name.upper() in ("VPWR", "VGND", "VPB", "VNB")


def safe_name(name: str) -> str:
    """Sanitize names to be valid Graphviz identifiers."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


def make_cell_html_label(cell_type: str, instance: str, inputs: List[str], outputs: List[str], bg_color: str) -> str:
    """Generate HTML-like label for a schematic cell block."""
    short_type = cell_type.replace('sky130_fd_sc_hd__', '')
    
    # Input pins column
    in_tds = "".join([f'<tr><td port="{pin}" align="left" border="0"><font color="#00d4ff" size="1">  {pin}  </font></td></tr>' for pin in inputs])
    in_table = f'<table border="0" cellborder="0" cellspacing="1" cellpadding="1">{in_tds}</table>' if inputs else ""
    
    # Output pins column
    out_tds = "".join([f'<tr><td port="{pin}" align="right" border="0"><font color="#00ff9d" size="1">  {pin}  </font></td></tr>' for pin in outputs])
    out_table = f'<table border="0" cellborder="0" cellspacing="1" cellpadding="1">{out_tds}</table>' if outputs else ""
    
    label = f"""<
    <table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="#1c2128" style="border-radius: 4px;">
      <tr>
        <!-- Inputs -->
        <td border="0" align="left" valign="middle">{in_table}</td>
        
        <!-- Cell Info Box -->
        <td bgcolor="{bg_color}" align="center" valign="middle">
          <font color="#000000" face="Helvetica" size="2"><b> {short_type} </b></font><br/>
          <font color="#586e75" face="Helvetica" size="1"> {instance} </font>
        </td>
        
        <!-- Outputs -->
        <td border="0" align="right" valign="middle">{out_table}</td>
      </tr>
    </table>
    >"""
    return label


def generate_graphviz_dot(info: NetlistInfo,
                           max_cells: int = 50) -> str:
    """
    Generate Graphviz DOT language for pin-level netlist schematic.
    Employs HTML-like tables and orthogonal splines for CAD-style schematics.
    """
    if not info:
        return 'digraph { label="No netlist found" }'

    lines = [
        'digraph netlist {',
        '  rankdir=LR;',
        '  splines=ortho;',
        '  nodesep=0.6;',
        '  ranksep=0.8;',
        '  node [fontname="Share Tech Mono" fontsize=9 shape=none];',
        '  edge [color="#8b949e" penwidth=1.0 arrowsize=0.6];',
        '',
        '  // Style background',
        '  graph [bgcolor="#0d1117" fontcolor="#c9d1d9"];',
        '',
    ]

    # 1. Input Ports Cluster
    lines.append('  subgraph cluster_inputs {')
    lines.append('    label="INPUTS"; style=filled;')
    lines.append('    fillcolor="#0a192f"; color="#00d4ff";')
    lines.append('    fontcolor="#00d4ff";')
    for inp in info.inputs[:12]:
        safe = safe_name(inp)
        lines.append(f'    in_{safe} [label="{inp}" shape=invtriangle style=filled fillcolor="#00d4ff" fontcolor="#000000" penwidth=1.5];')
    lines.append('  }')
    lines.append('')

    # 2. Output Ports Cluster
    lines.append('  subgraph cluster_outputs {')
    lines.append('    label="OUTPUTS"; style=filled;')
    lines.append('    fillcolor="#0c2014"; color="#00ff9d";')
    lines.append('    fontcolor="#00ff9d";')
    for out in info.outputs[:12]:
        safe = safe_name(out)
        lines.append(f'    out_{safe} [label="{out}" shape=triangle style=filled fillcolor="#00ff9d" fontcolor="#000000" penwidth=1.5];')
    lines.append('  }')
    lines.append('')

    # Cell styling colors
    cell_colors = {
        'dfxtp': '#4a90d9',   # flip-flop: blue
        'xor2':  '#e74c3c',   # XOR: red
        'xnor2': '#c0392b',   # XNOR: dark red
        'nand2': '#f39c12',   # NAND: orange
        'nor2':  '#d35400',   # NOR: dark orange
        'and2':  '#2ecc71',   # AND: green
        'or2':   '#2ecc71',   # OR: green
        'inv':   '#9b59b6',   # inverter: purple
        'mux2':  '#1abc9c',   # MUX: teal
        'clkbuf':'#3498db',   # clock buf: blue
    }

    displayed_cells = info.cells[:max_cells]
    
    # 3. Create Cells with HTML labels
    for cell in displayed_cells:
        # Categorize pins
        cell_inputs = []
        cell_outputs = []
        for pin in cell.ports.keys():
            if is_ignored_pin(pin):
                continue
            if is_output_pin(pin):
                cell_outputs.append(pin)
            else:
                cell_inputs.append(pin)
                
        # Determine BG color
        short = cell.cell_type.replace('sky130_fd_sc_hd__', '')
        color = '#7f8c8d'  # default
        for key, c in cell_colors.items():
            if key in short:
                color = c
                break
                
        safe_inst = safe_name(cell.instance)
        label_html = make_cell_html_label(cell.cell_type, cell.instance, cell_inputs, cell_outputs, color)
        lines.append(f'  {safe_inst} [label={label_html}];')

    lines.append('')

    # 4. Map nets to their driver ports to route wires correctly
    net_drivers = {} # net_name -> (node_id, port_id)

    # Input ports drive their respective nets
    for inp in info.inputs:
        safe_inp = safe_name(inp)
        net_drivers[inp] = (f"in_{safe_inp}", None)
        # Handle index variants
        net_drivers[safe_inp] = (f"in_{safe_inp}", None)

    # Outputs of cells drive internal nets
    for cell in displayed_cells:
        safe_inst = safe_name(cell.instance)
        for pin, net in cell.ports.items():
            if is_ignored_pin(pin) or not is_output_pin(pin):
                continue
            net_drivers[net] = (safe_inst, pin)
            # Standardize index mapping e.g. sum[0]
            net_clean = re.sub(r'[^a-zA-Z0-9_]', '_', net)
            net_drivers[net_clean] = (safe_inst, pin)

    # 5. Connect input pins of cells to their drivers
    connected = set()
    for cell in displayed_cells:
        safe_inst = safe_name(cell.instance)
        for pin, net in cell.ports.items():
            if is_ignored_pin(pin) or is_output_pin(pin):
                continue
            
            # Find driver
            driver = net_drivers.get(net)
            if not driver:
                # Try stripped brackets or clean net variants
                net_clean = re.sub(r'[^a-zA-Z0-9_]', '_', net)
                driver = net_drivers.get(net_clean)
                if not driver:
                    # Strip any bit index and try matching inputs
                    base_net = re.sub(r'\[\d+\]', '', net)
                    driver = net_drivers.get(base_net)
            
            if driver:
                driver_node, driver_port = driver
                port_suffix = f":{driver_port}" if driver_port else ""
                edge_key = f"{driver_node}{port_suffix}_{safe_inst}_{pin}"
                
                if edge_key not in connected:
                    lines.append(f'  {driver_node}{port_suffix} -> {safe_inst}:{pin} [color="#8b949e" penwidth=1.0];')
                    connected.add(edge_key)

    # 6. Connect output ports of module to their drivers
    for out in info.outputs:
        safe_out = safe_name(out)
        driver = net_drivers.get(out)
        if not driver:
            # Try matching with slices e.g. sum[0] -> sum
            for net_name, drv in net_drivers.items():
                if re.sub(r'\[\d+\]', '', net_name) == out:
                    driver = drv
                    break
        
        if driver:
            driver_node, driver_port = driver
            port_suffix = f":{driver_port}" if driver_port else ""
            edge_key = f"{driver_node}{port_suffix}_out_{safe_out}"
            
            if edge_key not in connected:
                lines.append(f'  {driver_node}{port_suffix} -> out_{safe_out} [color="#00ff9d" penwidth=1.2];')
                connected.add(edge_key)

    if len(info.cells) > max_cells:
        lines.append(
            f'  truncated [label="... {len(info.cells)-max_cells} more cells" '
            f'shape=note fillcolor="#ffd700" fontcolor="black"];'
        )

    lines.append('}')
    return '\n'.join(lines)


def render_netlist_plotly(info) -> None:
    """
    Render netlist as a professional Vivado / Cadence-style schematic.
    Light background, IEEE gate symbols, orthogonal wire routing.
    """
    import streamlit as st

    if not info or not info.cells:
        st.warning("No cells to display")
        return

    try:
        import plotly.graph_objects as go
        import re

        cells_to_show = info.cells[:40]

        # ── 1. Topological levelization ──────────────────────────
        net_drv = {}
        for inp in info.inputs:
            net_drv[inp] = ('input', inp, None)
            net_drv[re.sub(r'[^a-zA-Z0-9_]', '_', inp)] = ('input', inp, None)
        for cell in cells_to_show:
            for pin, net in cell.ports.items():
                if is_ignored_pin(pin):
                    continue
                if is_output_pin(pin):
                    net_drv[net] = ('cell', cell.instance, pin)
                    net_drv[re.sub(r'[^a-zA-Z0-9_]', '_', net)] = ('cell', cell.instance, pin)

        levels = {}
        for inp in info.inputs:
            levels[f"in_{inp}"] = 0

        remaining = list(cells_to_show)
        for _ in range(120):
            if not remaining:
                break
            nxt = []
            progress = False
            for cell in remaining:
                lvls = []
                for pin, net in cell.ports.items():
                    if is_ignored_pin(pin) or is_output_pin(pin):
                        continue
                    d = net_drv.get(net) or net_drv.get(
                        re.sub(r'[^a-zA-Z0-9_]', '_', net)) or net_drv.get(
                        re.sub(r'\[\d+\]', '', net))
                    if d:
                        dt, dn, _ = d
                        if dt == 'input':
                            lvls.append(0)
                        elif dn in levels:
                            lvls.append(levels[dn])
                if lvls:
                    levels[cell.instance] = max(lvls) + 1
                    progress = True
                else:
                    nxt.append(cell)
            if not progress and nxt:
                c = nxt.pop(0)
                levels[c.instance] = (max(levels.values()) if levels else 0) + 1
            remaining = nxt

        for c in remaining:
            levels[c.instance] = 1

        max_lvl = max(levels.values()) if levels else 0
        out_lvl = max_lvl + 2

        # Group by level
        lvl_grp = {}
        for inp in info.inputs:
            lvl_grp.setdefault(0, []).append(f"in_{inp}")
        for cell in cells_to_show:
            lv = levels.get(cell.instance, 1)
            lvl_grp.setdefault(lv, []).append(cell.instance)
        for out in info.outputs:
            lvl_grp.setdefault(out_lvl, []).append(f"out_{out}")

        # Compute coordinates
        coords = {}
        X_SP, Y_SP = 4.5, 2.2
        for lv, nodes in sorted(lvl_grp.items()):
            M = len(nodes)
            x = lv * X_SP
            for idx, nd in enumerate(nodes):
                y = (idx - (M - 1) / 2.0) * Y_SP
                coords[nd] = (x, y)

        # ── 2. Gate type → IEEE symbol category ──────────────────
        def gate_cat(short):
            s = short.lower()
            if 'dfxtp' in s or 'dff' in s or 'dlat' in s or 'sdf' in s:
                return 'ff'
            if 'and' in s and 'nand' not in s:
                return 'and'
            if 'nand' in s:
                return 'nand'
            if 'or' in s and 'nor' not in s and 'xor' not in s and 'xnor' not in s:
                return 'or'
            if 'nor' in s:
                return 'nor'
            if 'xor' in s:
                return 'xor'
            if 'xnor' in s:
                return 'xnor'
            if 'inv' in s or 'clkinv' in s:
                return 'inv'
            if 'buf' in s or 'clkbuf' in s:
                return 'buf'
            if 'mux' in s:
                return 'mux'
            if 'maj' in s:
                return 'and'
            return 'rect'

        # Gate outline color by category (Vivado palette)
        cat_color = {
            'ff':   '#2563eb', 'and':  '#16a34a', 'nand': '#16a34a',
            'or':   '#16a34a', 'nor':  '#16a34a', 'xor':  '#16a34a',
            'xnor': '#16a34a', 'inv':  '#7c3aed', 'buf':  '#7c3aed',
            'mux':  '#0891b2', 'rect': '#64748b',
        }
        cat_fill = {
            'ff':   '#dbeafe', 'and':  '#dcfce7', 'nand': '#dcfce7',
            'or':   '#dcfce7', 'nor':  '#dcfce7', 'xor':  '#dcfce7',
            'xnor': '#dcfce7', 'inv':  '#f3e8ff', 'buf':  '#f3e8ff',
            'mux':  '#e0f2fe', 'rect': '#f1f5f9',
        }

        fig = go.Figure()
        shapes = []
        annotations = []

        W, H = 1.2, 0.9   # cell half-width / half-height
        pin_coords = {}

        # ── 3. Draw cells ─────────────────────────────────────────
        cell_map = {c.instance: c for c in cells_to_show}
        for cell in cells_to_show:
            xc, yc = coords[cell.instance]
            short = cell.cell_type.replace('sky130_fd_sc_hd__', '')
            cat = gate_cat(short)
            col_line = cat_color.get(cat, '#64748b')
            col_fill = cat_fill.get(cat, '#f1f5f9')

            # Rectangle body
            shapes.append(dict(
                type='rect',
                x0=xc - W, y0=yc - H, x1=xc + W, y1=yc + H,
                line=dict(color=col_line, width=2),
                fillcolor=col_fill,
                layer='below'
            ))

            # Bubble for INV / NAND / NOR / XNOR
            if cat in ('inv', 'nand', 'nor', 'xnor'):
                shapes.append(dict(
                    type='circle',
                    x0=xc + W, y0=yc - 0.15, x1=xc + W + 0.3, y1=yc + 0.15,
                    line=dict(color=col_line, width=1.5),
                    fillcolor='white',
                    layer='below'
                ))

            # Clock triangle for FF
            if cat == 'ff':
                tri_sz = 0.2
                fig.add_trace(go.Scatter(
                    x=[xc - W, xc - W + tri_sz, xc - W, xc - W],
                    y=[yc - tri_sz, yc, yc + tri_sz, yc - tri_sz],
                    fill='toself', fillcolor=col_fill,
                    line=dict(color=col_line, width=1.2),
                    mode='lines', showlegend=False, hoverinfo='none'
                ))

            # Cell type label (bold, inside)
            annotations.append(dict(
                x=xc, y=yc + 0.2,
                text=f"<b>{short[:14]}</b>",
                font=dict(size=9, color='#1e293b', family='Arial'),
                showarrow=False, xanchor='center', yanchor='middle'
            ))
            # Instance label (gray, below type)
            annotations.append(dict(
                x=xc, y=yc - 0.25,
                text=cell.instance,
                font=dict(size=7, color='#94a3b8', family='Arial'),
                showarrow=False, xanchor='center', yanchor='middle'
            ))

            # Separate input/output pins
            c_in = [p for p in cell.ports if not is_ignored_pin(p) and not is_output_pin(p)]
            c_out = [p for p in cell.ports if not is_ignored_pin(p) and is_output_pin(p)]

            # Input pin stubs (left)
            xl = xc - W
            for idx, pin in enumerate(c_in):
                n = len(c_in)
                yp = yc + (idx - (n - 1) / 2.0) * (2 * H / max(n + 1, 2))
                pin_coords[(cell.instance, pin)] = (xl, yp)
                # Stub line
                shapes.append(dict(
                    type='line',
                    x0=xl - 0.35, y0=yp, x1=xl, y1=yp,
                    line=dict(color='#334155', width=1)
                ))
                # Pin label
                annotations.append(dict(
                    x=xl + 0.08, y=yp,
                    text=pin, font=dict(size=7, color='#475569', family='Arial'),
                    showarrow=False, xanchor='left', yanchor='middle'
                ))

            # Output pin stubs (right)
            xr = xc + W
            bub = 0.3 if cat in ('inv', 'nand', 'nor', 'xnor') else 0
            for idx, pin in enumerate(c_out):
                n = len(c_out)
                yp = yc + (idx - (n - 1) / 2.0) * (2 * H / max(n + 1, 2))
                pin_coords[(cell.instance, pin)] = (xr + bub, yp)
                shapes.append(dict(
                    type='line',
                    x0=xr + bub, y0=yp, x1=xr + bub + 0.35, y1=yp,
                    line=dict(color='#334155', width=1)
                ))
                annotations.append(dict(
                    x=xr + bub - 0.08, y=yp,
                    text=pin, font=dict(size=7, color='#475569', family='Arial'),
                    showarrow=False, xanchor='right', yanchor='middle'
                ))

        # ── 4. I/O port symbols ───────────────────────────────────
        for inp in info.inputs:
            x, y = coords[f"in_{inp}"]
            pin_coords[('INPUT', inp)] = (x, y)
            # Green port rectangle
            shapes.append(dict(
                type='rect',
                x0=x - 0.6, y0=y - 0.3, x1=x + 0.1, y1=y + 0.3,
                line=dict(color='#16a34a', width=1.5),
                fillcolor='#bbf7d0',
            ))
            # Arrow tip
            fig.add_trace(go.Scatter(
                x=[x + 0.1, x + 0.5, x + 0.1], y=[y + 0.25, y, y - 0.25],
                fill='toself', fillcolor='#bbf7d0',
                line=dict(color='#16a34a', width=1.5),
                mode='lines', showlegend=False, hoverinfo='none'
            ))
            annotations.append(dict(
                x=x - 0.25, y=y,
                text=f"<b>{inp}</b>",
                font=dict(size=8, color='#15803d', family='Arial'),
                showarrow=False, xanchor='center', yanchor='middle'
            ))

        for out in info.outputs:
            x, y = coords[f"out_{out}"]
            pin_coords[('OUTPUT', out)] = (x, y)
            shapes.append(dict(
                type='rect',
                x0=x - 0.1, y0=y - 0.3, x1=x + 0.6, y1=y + 0.3,
                line=dict(color='#16a34a', width=1.5),
                fillcolor='#bbf7d0',
            ))
            fig.add_trace(go.Scatter(
                x=[x - 0.1, x - 0.5, x - 0.1], y=[y + 0.25, y, y - 0.25],
                fill='toself', fillcolor='#bbf7d0',
                line=dict(color='#16a34a', width=1.5),
                mode='lines', showlegend=False, hoverinfo='none'
            ))
            annotations.append(dict(
                x=x + 0.25, y=y,
                text=f"<b>{out}</b>",
                font=dict(size=8, color='#15803d', family='Arial'),
                showarrow=False, xanchor='center', yanchor='middle'
            ))

        # ── 5. Orthogonal wire routing ────────────────────────────
        wire_x, wire_y = [], []
        clk_x, clk_y = [], []

        def _find_drv(net):
            d = net_drv.get(net)
            if not d:
                d = net_drv.get(re.sub(r'[^a-zA-Z0-9_]', '_', net))
            if not d:
                d = net_drv.get(re.sub(r'\[\d+\]', '', net))
            return d

        def _route(p1, p2, is_clk=False):
            x1, y1 = p1
            x2, y2 = p2
            xm = (x1 + x2) / 2.0
            seg = [x1, xm, xm, x2]
            sgy = [y1, y1, y2, y2]
            if is_clk:
                clk_x.extend(seg + [None])
                clk_y.extend(sgy + [None])
            else:
                wire_x.extend(seg + [None])
                wire_y.extend(sgy + [None])

        for cell in cells_to_show:
            for pin, net in cell.ports.items():
                if is_ignored_pin(pin) or is_output_pin(pin):
                    continue
                d = _find_drv(net)
                if not d:
                    continue
                dt, dn, dp = d
                if dt == 'input':
                    drv_pt = pin_coords.get(('INPUT', dn))
                else:
                    drv_pt = pin_coords.get((dn, dp))
                snk_pt = pin_coords.get((cell.instance, pin))
                if drv_pt and snk_pt:
                    _route(drv_pt, snk_pt, 'clk' in net.lower())

        for out in info.outputs:
            d = _find_drv(out)
            if not d:
                for nn, drv in net_drv.items():
                    if re.sub(r'\[\d+\]', '', nn) == out:
                        d = drv
                        break
            if d:
                dt, dn, dp = d
                drv_pt = pin_coords.get(('INPUT', dn)) if dt == 'input' else pin_coords.get((dn, dp))
                snk_pt = pin_coords.get(('OUTPUT', out))
                if drv_pt and snk_pt:
                    _route(drv_pt, snk_pt)

        # Signal wires (dark gray)
        if wire_x:
            fig.add_trace(go.Scatter(
                x=wire_x, y=wire_y, mode='lines',
                line=dict(color='#334155', width=1.2),
                hoverinfo='none', showlegend=False
            ))
        # Clock wires (blue dashed)
        if clk_x:
            fig.add_trace(go.Scatter(
                x=clk_x, y=clk_y, mode='lines',
                line=dict(color='#2563eb', width=1.2, dash='dot'),
                hoverinfo='none', showlegend=False, name='CLK'
            ))

        # ── 6. Layout ────────────────────────────────────────────
        x_max = out_lvl * X_SP + 2
        y_vals = [c[1] for c in coords.values()]
        y_min, y_max = min(y_vals) - 2, max(y_vals) + 2

        fig.update_layout(
            title=dict(
                text=f"Schematic — {info.module_name}  ({len(info.cells)} cells)",
                font=dict(size=14, color='#1e293b', family='Arial')
            ),
            paper_bgcolor='#ffffff',
            plot_bgcolor='#f8fafc',
            showlegend=False,
            shapes=shapes,
            annotations=annotations,
            xaxis=dict(
                showgrid=True, gridcolor='#e2e8f0', gridwidth=0.5,
                showticklabels=False, zeroline=False,
                range=[-2, x_max], dtick=X_SP,
            ),
            yaxis=dict(
                showgrid=True, gridcolor='#e2e8f0', gridwidth=0.5,
                showticklabels=False, zeroline=False,
                range=[y_min, y_max]
            ),
            height=min(700, max(500, int((y_max - y_min) * 40))),
            margin=dict(l=10, r=10, t=45, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

        if len(info.cells) > 40:
            st.caption(f"Showing 40 of {len(info.cells)} cells")

    except ImportError:
        st.markdown("**Cell List**")
        import pandas as pd
        data = [{
            "Instance": c.instance,
            "Cell Type": c.cell_type.replace('sky130_fd_sc_hd__', ''),
            "Ports": len(c.ports)
        } for c in info.cells[:50]]
        st.dataframe(pd.DataFrame(data), use_container_width=True)



def render_netlist_streamlit(results_dir: str,
                              design_name: str):
    """
    Render netlist schematic in Streamlit.
    Call from app.py design detail view.
    """
    import streamlit as st

    results = Path(results_dir)
    netlist_path = results / f"{design_name}_sky130.v"

    if not netlist_path.exists():
        # Search for any netlist
        candidates = list(results.glob("*_sky130.v"))
        if candidates:
            netlist_path = candidates[0]
        else:
            st.warning("Synthesized netlist not found")
            return

    info = parse_netlist(str(netlist_path))
    if not info:
        st.warning("Could not parse netlist")
        return

    # Header metrics
    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ SYNTHESIZED NETLIST — SCHEMATIC VIEW
    </div>""", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Cells", len(info.cells))
    with col2:
        st.metric("Inputs", len(info.inputs))
    with col3:
        st.metric("Outputs", len(info.outputs))
    with col4:
        st.metric("Internal Wires", len(info.wires))

    # Cell type breakdown
    st.markdown("**Cell Type Distribution**")
    if info.cell_counts:
        # Sort by count
        sorted_cells = sorted(
            info.cell_counts.items(),
            key=lambda x: x[1], reverse=True
        )
        # Display as horizontal bar
        max_count = sorted_cells[0][1] if sorted_cells else 1
        for cell_type, count in sorted_cells[:15]:
            pct = count / max_count * 100
            st.markdown(f"""
            <div style="margin:2px 0;font-family:'Share Tech Mono',monospace;font-size:0.8rem">
                <span style="color:#8b949e;width:200px;display:inline-block">
                    {cell_type[:30]}
                </span>
                <span style="display:inline-block;
                    width:{pct:.0f}%;background:#00d4ff;
                    height:12px;vertical-align:middle;
                    border-radius:2px;max-width:200px">
                </span>
                <span style="color:#c9d1d9;margin-left:6px">
                    {count}
                </span>
            </div>""", unsafe_allow_html=True)

    st.markdown("**Netlist Schematic**")
    render_netlist_plotly(info)

    # Download netlist
    with open(netlist_path, "rb") as f:
        st.download_button(
            " Download Synthesized Netlist",
            f,
            file_name=netlist_path.name,
            mime="text/plain"
        )
