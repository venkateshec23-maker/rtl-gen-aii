"""
netlist_viewer.py
=================
Parse synthesized Verilog netlist and generate
schematic visualization using Streamlit + Graphviz.
Shows: cells, connections, inputs, outputs.
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


def generate_graphviz_dot(info: NetlistInfo,
                           max_cells: int = 50) -> str:
    """
    Generate Graphviz DOT language for netlist schematic.
    Limits display to max_cells for readability.
    """
    if not info:
        return 'digraph { label="No netlist found" }'

    lines = [
        'digraph netlist {',
        '  rankdir=LR;',
        '  node [fontname="Share Tech Mono" fontsize=10];',
        '  edge [fontsize=8];',
        '',
        '  // Style',
        '  graph [bgcolor="#0d1117" fontcolor="#c9d1d9"];',
        '  node [style=filled color="#30363d" fontcolor="#c9d1d9"];',
        '',
    ]

    # Input ports (left side)
    lines.append('  subgraph cluster_inputs {')
    lines.append('    label="INPUTS"; style=filled;')
    lines.append('    fillcolor="#0f3460"; color="#00d4ff";')
    lines.append('    fontcolor="#00d4ff";')
    for inp in info.inputs[:8]:
        safe = inp.replace('[','_').replace(']','_').replace(':','_')
        lines.append(
            f'    in_{safe} [label="{inp}" '
            f'shape=invtriangle fillcolor="#00d4ff" '
            f'fontcolor="#000000"];'
        )
    lines.append('  }')
    lines.append('')

    # Output ports (right side)
    lines.append('  subgraph cluster_outputs {')
    lines.append('    label="OUTPUTS"; style=filled;')
    lines.append('    fillcolor="#0f3460"; color="#00ff9d";')
    lines.append('    fontcolor="#00ff9d";')
    for out in info.outputs[:8]:
        safe = out.replace('[','_').replace(']','_').replace(':','_')
        lines.append(
            f'    out_{safe} [label="{out}" '
            f'shape=triangle fillcolor="#00ff9d" '
            f'fontcolor="#000000"];'
        )
    lines.append('  }')
    lines.append('')

    # Cell instances (limit for display)
    cell_colors = {
        'dfxtp': '#4a90d9',   # flip-flop: blue
        'xor2':  '#e74c3c',   # XOR: red
        'xnor2': '#c0392b',   # XNOR: dark red
        'nand2': '#f39c12',   # NAND: orange
        'nor2':  '#d35400',   # NOR: dark orange
        'and2':  '#27ae60',   # AND: green
        'or2':   '#2ecc71',   # OR: light green
        'inv':   '#9b59b6',   # inverter: purple
        'mux2':  '#1abc9c',   # MUX: teal
        'maj3':  '#e67e22',   # MAJ: amber
        'clkbuf':'#3498db',   # clock buf: blue
        'fill':  '#7f8c8d',   # filler: gray
        'decap': '#95a5a6',   # decap: light gray
    }

    displayed_cells = info.cells[:max_cells]
    for cell in displayed_cells:
        short = cell.cell_type.replace('sky130_fd_sc_hd__', '')
        # Get base cell type for coloring
        color = '#586e75'  # default
        for key, c in cell_colors.items():
            if key in short:
                color = c
                break

        label = short[:20]  # truncate long names
        safe_inst = cell.instance.replace('[','_').replace(']','_')
        lines.append(
            f'  {safe_inst} [label="{label}\\n{cell.instance}" '
            f'shape=box fillcolor="{color}" '
            f'fontcolor="white"];'
        )

    lines.append('')

    # Add edges for first few connections
    connected = set()
    edge_count = 0
    for cell in displayed_cells[:30]:
        safe_inst = cell.instance.replace('[','_').replace(']','_')
        for port, net in cell.ports.items():
            if port in ('VPWR','VGND','VPB','VNB','CLK'):
                continue
            # Check if net connects to input
            net_clean = net.replace('[','').replace(']','').replace('\\','')
            for inp in info.inputs:
                if inp in net and edge_count < 50:
                    safe_inp = inp.replace('[','_').replace(']','_').replace(':','_')
                    edge_key = f"in_{safe_inp}_{safe_inst}"
                    if edge_key not in connected:
                        lines.append(
                            f'  in_{safe_inp} -> {safe_inst} '
                            f'[color="#00d4ff" penwidth=0.5];'
                        )
                        connected.add(edge_key)
                        edge_count += 1
            # Check if net connects to output
            for out in info.outputs:
                if out in net and edge_count < 80:
                    safe_out = out.replace('[','_').replace(']','_').replace(':','_')
                    edge_key = f"{safe_inst}_out_{safe_out}"
                    if edge_key not in connected:
                        lines.append(
                            f'  {safe_inst} -> out_{safe_out} '
                            f'[color="#00ff9d" penwidth=0.5];'
                        )
                        connected.add(edge_key)
                        edge_count += 1

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
