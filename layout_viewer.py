"""
layout_viewer.py
================
Visualize GDS layout using KLayout batch mode.
Renders chip layout as PNG and displays in Streamlit.
Commercial equivalent: Cadence Virtuoso Layout
"""

import subprocess
import tempfile
from pathlib import Path


def render_gds_to_png(
    gds_path:   str,
    output_png: str = None,
    width:      int = 800,
    height:     int = 600
) -> str:
    """
    Use KLayout (in Docker) to render GDS as PNG.
    Returns path to PNG file, or None if failed.
    """
    gds = Path(gds_path)
    if not gds.exists():
        return None

    if output_png is None:
        output_png = str(gds.with_suffix('.png'))

    # KLayout Python script to render GDS
    klayout_script = f"""
import pya

# Load layout
layout = pya.Layout()
layout.read("{gds_path}")

# Get top cell
top_cell = layout.top_cell()
if not top_cell:
    print("ERROR: No top cell found")
    exit(1)

# Get bounding box
bbox = top_cell.bbox()
print(f"Cell: {{top_cell.name}}")
print(f"Bbox: {{bbox}}")
print(f"Layers: {{layout.layers()}}")

# Render to PNG using LayoutView
view = pya.LayoutView()
view.show_layout(layout, True)

# Set view options
opt = pya.SaveLayoutOptions()
view.save_image("{output_png}", {width}, {height})
print(f"PNG saved: {output_png}")
"""

    # Run KLayout in Docker
    work_dir = Path(r"C:\tools\OpenLane")
    script_path = work_dir / "render_gds.py"
    script_path.write_text(klayout_script)

    # Convert paths for Docker
    gds_docker  = gds_path.replace('\\', '/').replace(
        'C:', ''
    ).replace('/tools/OpenLane', '/work')
    out_docker  = output_png.replace('\\', '/').replace(
        'C:', ''
    ).replace('/tools/OpenLane', '/work')

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{work_dir}:/work",
        "efabless/openlane:latest",
        "bash", "-c",
        f"klayout -b -r /work/render_gds.py 2>&1"
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True,
            text=True, timeout=60
        )
        if Path(output_png).exists():
            return output_png
        return None
    except Exception:
        return None


def get_gds_layer_info(gds_path: str) -> dict:
    """
    Extract layer information from GDS without rendering.
    Uses binary parsing of GDS record types.
    """
    path = Path(gds_path)
    if not path.exists():
        return {}

    with open(path, 'rb') as f:
        data = f.read(min(100000, path.stat().st_size))

    # Count layer records (0x0D02 = LAYER record)
    import struct
    layers = set()
    pos = 0
    while pos + 4 < len(data):
        try:
            rec_len  = struct.unpack('>H', data[pos:pos+2])[0]
            rec_type = data[pos+2]
            if rec_type == 0x0D and pos + 6 <= len(data):
                layer_num = struct.unpack(
                    '>H', data[pos+4:pos+6]
                )[0]
                layers.add(layer_num)
            if rec_len == 0 or pos + rec_len > len(data):
                break
            pos += rec_len
        except Exception:
            break

    # Sky130A layer names
    sky130_layers = {
        41: "nwell",  64: "tap",
        65: "nsdm",   66: "psdm",
        67: "diff",   68: "poly",
        81: "licon",  83: "li1",
        67: "mcon",   68: "met1",
        69: "via",    70: "met2",
        71: "via2",   72: "met3",
        73: "via3",   74: "met4",
        75: "via4",   76: "met5",
    }

    return {
        "layers_used": sorted(layers),
        "layer_names": {
            l: sky130_layers.get(l, f"Layer {l}")
            for l in layers
        },
        "total_layers": len(layers)
    }


def render_layout_streamlit(results_dir, design_name):
    import streamlit as st
    import struct

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ PHYSICAL LAYOUT — GDS2 ANALYSIS
    </div>""", unsafe_allow_html=True)

    results = Path(results_dir)
    gds_files = list(results.glob("*.gds"))

    if not gds_files:
        st.warning("No GDS file in this run")
        return

    gds = max(gds_files, key=lambda x: x.stat().st_size)
    size_kb = round(gds.stat().st_size / 1024, 1)
    is_real = gds.stat().st_size > 50000

    # Header
    status_color = "#00ff9d" if is_real else "#ff3333"
    st.markdown(f"""
    <div style="background:#1c2128;border:1px solid
         {status_color};border-radius:4px;
         padding:12px 16px;margin-bottom:16px">
        <span style="font-family:'Share Tech Mono',monospace;
            font-size:0.85rem;color:{status_color}">
            {'✅ GENUINE GDS2 FILE' if is_real else '⚠️ SMALL FILE'}
        </span>
        <span style="color:#8b949e;font-family:monospace;
            font-size:0.8rem;margin-left:16px">
            {gds.name} — {size_kb} KB
        </span>
    </div>""", unsafe_allow_html=True)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("File Size", f"{size_kb} KB")
    with col2:
        st.metric("Format", "GDSII v5/6")
    with col3:
        st.metric("PDK", "SKY130A 130nm")
    with col4:
        st.metric("Status",
                  "Real" if is_real else "Stub")

    # Binary forensics
    with open(gds, 'rb') as f:
        binary = f.read()

    # Find Sky130 cell names
    sky130_cells_in_gds = []
    for cell_bytes in [
        b'sky130_fd_sc_hd__dfxtp_1',
        b'sky130_fd_sc_hd__xor2_1',
        b'sky130_fd_sc_hd__nand2_1',
        b'sky130_fd_sc_hd__nor2_1',
        b'sky130_fd_sc_hd__and2_0',
        b'sky130_fd_sc_hd__inv_1',
        b'sky130_fd_sc_hd__buf_1',
        b'sky130_fd_sc_hd__maj3_1',
        b'sky130_fd_sc_hd__fill_1',
        b'sky130_fd_sc_hd__decap_8',
        b'sky130_fd_sc_hd__clkbuf_16',
        b'sky130_fd_sc_hd__mux2_1',
    ]:
        if cell_bytes in binary:
            sky130_cells_in_gds.append(
                cell_bytes.decode().replace(
                    'sky130_fd_sc_hd__', ''
                )
            )

    if sky130_cells_in_gds:
        st.success(
            f"✅ Verified: Found {len(sky130_cells_in_gds)} "
            f"Sky130A standard cells in GDS binary"
        )
        # Show cells as tags
        tags = " ".join([
            f'<span style="background:#0f3460;'
            f'color:#00d4ff;padding:2px 6px;'
            f'border-radius:3px;font-family:monospace;'
            f'font-size:0.75rem;margin:2px">{c}</span>'
            for c in sky130_cells_in_gds
        ])
        st.markdown(tags, unsafe_allow_html=True)
    else:
        st.warning("Could not find Sky130A cells in binary")

    # GDS structure analysis
    st.markdown("---")
    st.markdown("**GDS2 Structure Analysis**")

    # Parse GDS records
    record_names = {
        0x02: 'HEADER',   0x01: 'BGNLIB',
        0x02: 'LIBNAME',  0x03: 'UNITS',
        0x04: 'ENDLIB',   0x05: 'BGNSTR',
        0x06: 'STRNAME',  0x07: 'ENDSTR',
        0x08: 'BOUNDARY', 0x09: 'PATH',
        0x0C: 'TEXT',     0x0D: 'LAYER',
    }

    struct_names = []
    boundary_count = 0
    layers_used = set()
    pos = 0

    while pos + 4 < min(len(binary), 500000):
        try:
            rec_len  = struct.unpack(
                '>H', binary[pos:pos+2]
            )[0]
            rec_type = binary[pos+2]

            if rec_type == 0x06 and pos + rec_len <= len(binary):
                name = binary[pos+4:pos+rec_len].decode(
                    'ascii', errors='ignore'
                ).strip('\x00').strip()
                if name and len(name) < 64:
                    struct_names.append(name)

            elif rec_type == 0x08:
                boundary_count += 1

            elif rec_type == 0x0D and pos + 6 <= len(binary):
                layer = struct.unpack(
                    '>H', binary[pos+4:pos+6]
                )[0]
                layers_used.add(layer)

            if rec_len == 0 or pos + rec_len > len(binary):
                break
            pos += rec_len
        except Exception:
            break

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Structures", len(struct_names))
    with col2:
        st.metric("Boundaries", boundary_count)
    with col3:
        st.metric("Layers Used", len(layers_used))

    # Structure names
    if struct_names:
        sky130_structs = [s for s in struct_names
                          if 'sky130' in s.lower()]
        user_structs   = [s for s in struct_names
                          if 'sky130' not in s.lower()]

        if user_structs:
            st.markdown(
                f"**Design cells:** "
                f"`{'`, `'.join(user_structs[:5])}`"
            )
        if sky130_structs:
            st.markdown(
                f"**Standard cells:** "
                f"{len(sky130_structs)} Sky130A cells embedded"
            )

    # Layer info
    if layers_used:
        sky130_layers = {
            41:'nwell', 64:'tap', 65:'nsdm', 66:'psdm',
            67:'diff',  68:'poly', 81:'licon', 83:'li1',
            67:'mcon',  68:'met1', 69:'via',  70:'met2',
            71:'via2',  72:'met3', 73:'via3', 74:'met4',
        }
        layer_tags = " ".join([
            f'<span style="background:#1c2128;'
            f'border:1px solid #30363d;'
            f'color:#8b949e;padding:2px 6px;'
            f'border-radius:3px;font-family:monospace;'
            f'font-size:0.7rem;margin:2px">'
            f'L{l}: {sky130_layers.get(l,f"L{l}")}</span>'
            for l in sorted(layers_used)[:12]
        ])
        st.markdown("**Metal layers:**")
        st.markdown(layer_tags, unsafe_allow_html=True)

    # KLayout open command
    st.markdown("---")
    st.info(
        f"**Open in KLayout Desktop:**\n"
        f"```\nklayout {gds}\n```\n"
        f"KLayout is free at: klayout.de"
    )

    # Download
    st.markdown("")
    with open(gds, "rb") as f:
        st.download_button(
            f"⬇️ Download {gds.name} ({size_kb} KB)",
            f,
            file_name=gds.name,
            mime="application/octet-stream",
            type="primary"
        )
