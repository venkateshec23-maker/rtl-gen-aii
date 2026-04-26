#!/bin/bash
set -e

echo "=========================================="
echo "RTL-Gen AI - Codespaces Setup"
echo "=========================================="

# Create directories
mkdir -p $OPENLANE_WORK/designs
mkdir -p $OPENLANE_WORK/runs
mkdir -p $PDK_ROOT

# Download minimal Sky130A PDK (partial - just what we need for synthesis)
echo ""
echo "Downloading Sky130A PDK (this may take a few minutes)..."
if [ ! -f "$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib" ]; then
    wget -q --show-progress \
        "https://github.com/RTimothyEdwards/open_pdks/releases/download/v1.0.401/sky130A.tar.xz" \
        -O /tmp/sky130A.tar.xz 2>/dev/null || echo "PDK download skipped - will use Docker volume"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the app:"
echo "  streamlit run app.py"
echo ""
echo "Open the forwarded port 8501 to view the UI."
echo ""
