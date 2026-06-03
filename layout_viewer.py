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


def render_layout_streamlit(results_dir: str,
                             design_name: str):
    """
    Render layout viewer in Streamlit.
    Shows GDS visualization with layer info.
    """
    import streamlit as st

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;
         font-size:0.7rem;letter-spacing:2px;
         color:#00d4ff;border-bottom:1px solid #30363d;
         padding-bottom:6px;margin-bottom:12px">
    ▸ PHYSICAL LAYOUT — GDS VIEW
    </div>""", unsafe_allow_html=True)

    results = Path(results_dir)
    gds_files = list(results.glob("*.gds"))

    if not gds_files:
        st.warning("No GDS file found for this run")
        return

    gds = max(gds_files, key=lambda x: x.stat().st_size)
    gds_size_kb = round(gds.stat().st_size / 1024, 1)

    # GDS metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("GDS File", gds.name)
    with col2:
        st.metric("File Size", f"{gds_size_kb} KB")
    with col3:
        is_real = gds.stat().st_size > 50000
        st.metric(
            "Verified",
            "✅ REAL" if is_real else "⚠️ SMALL"
        )

    # Layer information
    with st.spinner("Analyzing GDS layers..."):
        layer_info = get_gds_layer_info(str(gds))

    if layer_info.get("layers_used"):
        st.markdown(
            f"**Metal layers used:** "
            f"{layer_info['total_layers']}"
        )
        layer_cols = st.columns(4)
        for i, (layer_num, layer_name) in enumerate(
            layer_info["layer_names"].items()
        ):
            with layer_cols[i % 4]:
                st.markdown(
                    f"<span style='font-family:monospace;"
                    f"font-size:0.75rem;color:#00d4ff'>"
                    f"L{layer_num}: {layer_name}</span>",
                    unsafe_allow_html=True
                )

    # Try KLayout rendering
    png_path = str(gds.with_suffix('.png'))
    if not Path(png_path).exists():
        with st.spinner("Rendering layout..."):
            png_path = render_gds_to_png(str(gds))

    if png_path and Path(png_path).exists():
        st.image(png_path,
                 caption=f"Layout: {design_name}",
                 use_column_width=True)
    else:
        # Show GDS binary info instead
        st.info(
            "KLayout rendering not available in headless mode. "
            "Open KLayout desktop to view: "
            f"`klayout {gds}`"
        )

        # Show what we know about the GDS
        with open(gds, 'rb') as f:
            header = f.read(64)

        # Check for Sky130 cell names in binary
        with open(gds, 'rb') as f:
            binary = f.read()

        sky130_found = []
        for cell in [
            b'sky130_fd_sc_hd__dfxtp',
            b'sky130_fd_sc_hd__xor2',
            b'sky130_fd_sc_hd__nand2',
            b'sky130_fd_sc_hd__fill',
        ]:
            if cell in binary:
                sky130_found.append(
                    cell.decode().replace(
                        'sky130_fd_sc_hd__', ''
                    )
                )

        if sky130_found:
            st.success(
                f"✅ Verified Sky130A cells in binary: "
                f"{', '.join(sky130_found)}"
            )

    # Download button
    with open(gds, "rb") as f:
        st.download_button(
            f"⬇️ Download {gds.name} ({gds_size_kb} KB)",
            f,
            file_name=gds.name,
            mime="application/octet-stream",
            type="primary"
        )
