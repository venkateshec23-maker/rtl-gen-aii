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

    # Graphviz schematic
    st.markdown("**Schematic (first 50 cells)**")
    try:
        dot = generate_graphviz_dot(info, max_cells=50)
        st.graphviz_chart(dot)
    except Exception as e:
        st.info(
            f"Graphviz not available: {e}. "
            "Install: pip install graphviz"
        )
        # Fallback: show as text
        st.code(
            '\n'.join([
                f"{c.instance}: {c.cell_type.replace('sky130_fd_sc_hd__','')}"
                for c in info.cells[:20]
            ]),
            language="text"
        )

    # Download netlist
    with open(netlist_path, "rb") as f:
        st.download_button(
            " Download Synthesized Netlist",
            f,
            file_name=netlist_path.name,
            mime="text/plain"
        )
