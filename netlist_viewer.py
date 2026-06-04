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
    Render netlist using Plotly (no Graphviz needed).
    Shows cells as rectangular blocks, pins, and orthogonal routed wires
    similar to Cadence Schematic Viewer or Vivado RTL Schematic.
    """
    import streamlit as st

    if not info or not info.cells:
        st.warning("No cells to display")
        return

    try:
        import plotly.graph_objects as go
        import re

        # Display at most 45 cells to keep diagram clean and readable
        cells_to_show = info.cells[:45]

        # 1. Topological Sorting / Levelization
        net_drivers = {}  # net_name -> (driver_type, inst_name, pin_name)
        for inp in info.inputs:
            net_drivers[inp] = ('input', inp, None)
            net_clean = re.sub(r'[^a-zA-Z0-9_]', '_', inp)
            net_drivers[net_clean] = ('input', inp, None)

        for cell in cells_to_show:
            for pin, net in cell.ports.items():
                if is_ignored_pin(pin):
                    continue
                if is_output_pin(pin):
                    net_drivers[net] = ('cell', cell.instance, pin)
                    net_clean = re.sub(r'[^a-zA-Z0-9_]', '_', net)
                    net_drivers[net_clean] = ('cell', cell.instance, pin)

        # Assign levels
        levels = {}  # inst_name -> level
        for inp in info.inputs:
            levels[f"in_{inp}"] = 0

        cells_to_assign = list(cells_to_show)
        max_iter = 100
        itr = 0
        assigned_any = True

        while cells_to_assign and itr < max_iter and assigned_any:
            assigned_any = False
            next_cells = []
            for cell in cells_to_assign:
                input_levels = []
                for pin, net in cell.ports.items():
                    if is_ignored_pin(pin) or is_output_pin(pin):
                        continue
                    driver = net_drivers.get(net)
                    if not driver:
                        net_clean = re.sub(r'[^a-zA-Z0-9_]', '_', net)
                        driver = net_drivers.get(net_clean)
                        if not driver:
                            base_net = re.sub(r'\[\d+\]', '', net)
                            driver = net_drivers.get(base_net)
                    
                    if driver:
                        drv_type, drv_name, _ = driver
                        if drv_type == 'input':
                            input_levels.append(levels.get(f"in_{drv_name}", 0))
                        elif drv_type == 'cell':
                            if drv_name in levels:
                                input_levels.append(levels[drv_name])
                
                if input_levels:
                    levels[cell.instance] = max(input_levels) + 1
                    assigned_any = True
                else:
                    next_cells.append(cell)

            if not assigned_any and next_cells:
                # Force assign to break cycles or floating inputs
                current_max = max(levels.values()) if levels else 0
                cell = next_cells.pop(0)
                levels[cell.instance] = current_max + 1
                assigned_any = True

            cells_to_assign = next_cells
            itr += 1

        # Catch remaining
        for cell in cells_to_assign:
            levels[cell.instance] = 1

        # Max cell level
        max_cell_lvl = max(levels.values()) if levels else 0
        out_lvl = max_cell_lvl + 2

        # Group nodes by level
        level_groups = {}
        for inp in info.inputs:
            level_groups.setdefault(0, []).append(f"in_{inp}")
        for cell in cells_to_show:
            lvl = levels.get(cell.instance, 1)
            level_groups.setdefault(lvl, []).append(cell.instance)
        for out in info.outputs:
            level_groups.setdefault(out_lvl, []).append(f"out_{out}")

        # Compute Coordinates on a left-to-right grid
        coords = {}  # node -> (x, y)
        x_spacing = 4.0
        y_spacing = 2.0

        for lvl, nodes in sorted(level_groups.items()):
            M = len(nodes)
            x = lvl * x_spacing
            for idx, node in enumerate(nodes):
                # Center vertically around y=0
                y = (idx - (M - 1) / 2.0) * y_spacing
                coords[node] = (x, y)

        fig = go.Figure()

        # Cell sizing constants
        box_w = 0.8
        box_h = 0.6

        # Draw Cells, Pins, and inside pin labels
        pin_coords = {}  # (node, pin) -> (x, y)
        cell_color_map = {
            'dfxtp': ('#1a365d', '#63b3ed'),   # Regs: Dark Blue with blue border
            'xor2':  ('#2c3e50', '#e53e3e'),   # Gates: Dark Slate with red border
            'xnor2': ('#2c3e50', '#e53e3e'),
            'nand2': ('#2d3748', '#ed8936'),   # Gates: Orange border
            'nor2':  ('#2d3748', '#ed8936'),
            'and2':  ('#2c3e50', '#4fd1c5'),   # Gates: Teal border
            'or2':   ('#2c3e50', '#4fd1c5'),
            'inv':   ('#4a1259', '#d6bcfa'),   # Inverters: Dark Purple with light purple border
            'clkbuf':('#1a365d', '#63b3ed'),
            'mux':   ('#1a5235', '#68d391'),   # Muxes: Green border
            'fill':  ('#2d3748', '#718096'),
            'decap': ('#2d3748', '#718096'),
        }

        # Wires (Nets) traces setup
        wire_x = []
        wire_y = []
        clk_wire_x = []
        clk_wire_y = []
        rst_wire_x = []
        rst_wire_y = []

        # Pin Text Labels setup
        pin_lbl_x = []
        pin_lbl_y = []
        pin_lbl_txt = []
        pin_lbl_align = []

        for cell in cells_to_show:
            xc, yc = coords[cell.instance]
            short_type = cell.cell_type.replace('sky130_fd_sc_hd__', '')

            # Determine colors
            bg_color, border_color = '#1a202c', '#cbd5e0'
            for key, val in cell_color_map.items():
                if key in short_type:
                    bg_color, border_color = val
                    break

            # 2. Draw Cell Rectangle (Plotly Polygon)
            rx = [xc - box_w, xc + box_w, xc + box_w, xc - box_w, xc - box_w]
            ry = [yc - box_h, yc - box_h, yc + box_h, yc + box_h, yc - box_h]
            fig.add_trace(go.Scatter(
                x=rx, y=ry,
                fill="toself",
                fillcolor=bg_color,
                line=dict(color=border_color, width=1.5),
                mode='lines',
                hoverinfo='text',
                hovertext=f"Instance: {cell.instance}<br>Type: {cell.cell_type}",
                showlegend=False
            ))

            # Draw Cell Type and Instance Text labels inside the box
            fig.add_trace(go.Scatter(
                x=[xc], y=[yc + 0.15],
                text=[short_type[:12]],
                mode='text',
                textfont=dict(size=9, color='#ffffff', family='Share Tech Mono', weight='bold'),
                showlegend=False,
                hoverinfo='none'
            ))
            fig.add_trace(go.Scatter(
                x=[xc], y=[yc - 0.25],
                text=[cell.instance],
                mode='text',
                textfont=dict(size=7, color='#718096', family='Share Tech Mono'),
                showlegend=False,
                hoverinfo='none'
            ))

            # Separate inputs and outputs
            c_inputs = []
            c_outputs = []
            for pin in cell.ports.keys():
                if is_ignored_pin(pin):
                    continue
                if is_output_pin(pin):
                    c_outputs.append(pin)
                else:
                    c_inputs.append(pin)

            # 3. Space and draw Input Pins (on left edge)
            xl = xc - box_w
            if c_inputs:
                p_in = len(c_inputs)
                for idx, pin in enumerate(c_inputs):
                    yp = yc + (idx - (p_in - 1) / 2.0) * (2 * box_h / (p_in + 1 if p_in > 1 else 2))
                    pin_coords[(cell.instance, pin)] = (xl, yp)
                    
                    # Draw pin marker
                    fig.add_trace(go.Scatter(
                        x=[xl], y=[yp],
                        mode='markers',
                        marker=dict(size=5, color='#00d4ff', symbol='square'),
                        showlegend=False,
                        hoverinfo='text',
                        hovertext=f"Pin: {pin} (Input)<br>Net: {cell.ports[pin]}"
                    ))

                    # Pin Name text (inside box, left-aligned)
                    pin_lbl_x.append(xl + 0.15)
                    pin_lbl_y.append(yp)
                    pin_lbl_txt.append(pin)
                    pin_lbl_align.append('middle right')

            # 4. Space and draw Output Pins (on right edge)
            xr = xc + box_w
            if c_outputs:
                p_out = len(c_outputs)
                for idx, pin in enumerate(c_outputs):
                    yp = yc + (idx - (p_out - 1) / 2.0) * (2 * box_h / (p_out + 1 if p_out > 1 else 2))
                    pin_coords[(cell.instance, pin)] = (xr, yp)
                    
                    # Draw pin marker
                    fig.add_trace(go.Scatter(
                        x=[xr], y=[yp],
                        mode='markers',
                        marker=dict(size=5, color='#00ff9d', symbol='square'),
                        showlegend=False,
                        hoverinfo='text',
                        hovertext=f"Pin: {pin} (Output)<br>Net: {cell.ports[pin]}"
                    ))

                    # Pin Name text (inside box, right-aligned)
                    pin_lbl_x.append(xr - 0.15)
                    pin_lbl_y.append(yp)
                    pin_lbl_txt.append(pin)
                    pin_lbl_align.append('middle left')

        # 5. Draw Primary Input Ports
        for inp in info.inputs:
            x, y = coords[f"in_{inp}"]
            pin_coords[('INPUT', inp)] = (x, y)
            
            # Draw port symbol (invtriangle)
            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode='markers+text',
                marker=dict(size=12, color='#00d4ff', symbol='triangle-right'),
                text=[inp],
                textposition='middle left',
                textfont=dict(size=8, color='#00d4ff', family='Share Tech Mono'),
                showlegend=False,
                hoverinfo='text',
                hovertext=f"Input Port: {inp}"
            ))

        # 6. Draw Primary Output Ports
        for out in info.outputs:
            x, y = coords[f"out_{out}"]
            pin_coords[('OUTPUT', out)] = (x, y)
            
            # Draw port symbol (triangle)
            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode='markers+text',
                marker=dict(size=12, color='#00ff9d', symbol='triangle-right'),
                text=[out],
                textposition='middle right',
                textfont=dict(size=8, color='#00ff9d', family='Share Tech Mono'),
                showlegend=False,
                hoverinfo='text',
                hovertext=f"Output Port: {out}"
            ))

        # Draw Pin text labels inside cells
        fig.add_trace(go.Scatter(
            x=pin_lbl_x, y=pin_lbl_y,
            text=pin_lbl_txt,
            mode='text',
            textposition='middle right',
            textfont=dict(size=6, color='#a0aec0', family='Share Tech Mono'),
            showlegend=False,
            hoverinfo='none'
        ))

        # 7. Orthogonal Routing for Wires (Nets)
        for cell in cells_to_show:
            for pin, net in cell.ports.items():
                if is_ignored_pin(pin) or is_output_pin(pin):
                    continue

                # Find driver node/pin for this net
                driver = net_drivers.get(net)
                if not driver:
                    net_clean = re.sub(r'[^a-zA-Z0-9_]', '_', net)
                    driver = net_drivers.get(net_clean)
                    if not driver:
                        base_net = re.sub(r'\[\d+\]', '', net)
                        driver = net_drivers.get(base_net)

                if driver:
                    drv_type, drv_name, drv_pin = driver
                    
                    # Get driver coordinates
                    if drv_type == 'input':
                        drv_pt = pin_coords.get(('INPUT', drv_name))
                    elif drv_type == 'cell':
                        drv_pt = pin_coords.get((drv_name, drv_pin))
                    else:
                        drv_pt = None

                    # Get sink coordinates (the input pin of the current cell)
                    snk_pt = pin_coords.get((cell.instance, pin))

                    if drv_pt and snk_pt:
                        x1, y1 = drv_pt
                        x2, y2 = snk_pt

                        # Orthogonal routing coordinates
                        x_mid = (x1 + x2) / 2.0
                        wx = [x1, x_mid, x_mid, x2]
                        wy = [y1, y1, y2, y2]

                        # Classify wire color
                        if 'clk' in net.lower():
                            clk_wire_x.extend(wx + [None])
                            clk_wire_y.extend(wy + [None])
                        elif 'reset' in net.lower() or 'rst' in net.lower():
                            rst_wire_x.extend(wx + [None])
                            rst_wire_y.extend(wy + [None])
                        else:
                            wire_x.extend(wx + [None])
                            wire_y.extend(wy + [None])

        # 8. Draw Output Ports connection to their drivers
        for out in info.outputs:
            driver = net_drivers.get(out)
            if not driver:
                # Slices check
                for net_name, drv in net_drivers.items():
                    if re.sub(r'\[\d+\]', '', net_name) == out:
                        driver = drv
                        break

            if driver:
                drv_type, drv_name, drv_pin = driver
                if drv_type == 'input':
                    drv_pt = pin_coords.get(('INPUT', drv_name))
                elif drv_type == 'cell':
                    drv_pt = pin_coords.get((drv_name, drv_pin))
                else:
                    drv_pt = None

                snk_pt = pin_coords.get(('OUTPUT', out))

                if drv_pt and snk_pt:
                    x1, y1 = drv_pt
                    x2, y2 = snk_pt
                    x_mid = (x1 + x2) / 2.0
                    wx = [x1, x_mid, x_mid, x2]
                    wy = [y1, y1, y2, y2]
                    wire_x.extend(wx + [None])
                    wire_y.extend(wy + [None])

        # Add all wire traces to the figure
        # Normal Wires (Slate Gray)
        if wire_x:
            fig.add_trace(go.Scatter(
                x=wire_x, y=wire_y,
                mode='lines',
                line=dict(color='#718096', width=1.0),
                hoverinfo='none',
                name='Nets',
                showlegend=False
            ))

        # Clock Nets (Cyan dashed line)
        if clk_wire_x:
            fig.add_trace(go.Scatter(
                x=clk_wire_x, y=clk_wire_y,
                mode='lines',
                line=dict(color='#00d4ff', width=1.2, dash='dash'),
                hoverinfo='none',
                name='Clock Nets',
                showlegend=True
            ))

        # Reset Nets (Red line)
        if rst_wire_x:
            fig.add_trace(go.Scatter(
                x=rst_wire_x, y=rst_wire_y,
                mode='lines',
                line=dict(color='#e53e3e', width=1.2),
                hoverinfo='none',
                name='Reset Nets',
                showlegend=True
            ))

        # Figure styling layout - clean, black navy CAD board background
        fig.update_layout(
            title=dict(
                text=f"RTL Schematic — {info.module_name} ({len(info.cells)} cells)",
                font=dict(color='#c9d1d9', size=13, family='Share Tech Mono')
            ),
            paper_bgcolor='#080c14',
            plot_bgcolor='#0b0f19',
            showlegend=True,
            legend=dict(
                bgcolor='#080c14',
                bordercolor='#2d3748',
                font=dict(size=8, color='#8b949e')
            ),
            xaxis=dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                range=[-1, out_lvl * x_spacing + 1]
            ),
            yaxis=dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False
            ),
            height=600,
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

        if len(info.cells) > 45:
            st.caption(
                f"Showing 45 levelized cells of {len(info.cells)} total cell instances"
            )

    except ImportError:
        # Pure text fallback — always works
        st.markdown("**Cell List**")
        import pandas as pd
        data = [{
            "Instance": c.instance,
            "Cell Type": c.cell_type.replace(
                'sky130_fd_sc_hd__', ''
            ),
            "Ports": len(c.ports)
        } for c in info.cells[:50]]
        st.dataframe(
            pd.DataFrame(data),
            use_container_width=True
        )


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
