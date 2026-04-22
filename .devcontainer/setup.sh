#!/bin/bash
# setup.sh — Runs once when Codespace is created

echo "============================================"
echo "  RTL-Gen AI - Codespace Setup"
echo "============================================"

# Install Python dependencies
pip install -r requirements.txt

# Pull OpenLane Docker image (background)
echo "Pulling EDA Docker image (background)..."
docker pull efabless/openlane:latest &

# Verify iverilog is available
if command -v iverilog &> /dev/null; then
    echo "[OK] iverilog available: $(iverilog -V 2>&1 | head -1)"
else
    echo "[WARNING] iverilog not found - installing..."
    apt-get update && apt-get install -y iverilog 2>/dev/null || true
fi

# Create directory structure
mkdir -p openroad/designs/adder_8bit
mkdir -p openroad/designs/counter_4bit
mkdir -p openroad/runs
mkdir -p pdk

# Copy designs
cp -r designs/ openroad/ 2>/dev/null || true

# Download Liberty file (essential for synthesis)
PDK_LIB="pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib"
mkdir -p "$PDK_LIB"
LIB_URL="https://raw.githubusercontent.com/google/skywater-pdk/main/libraries/sky130_fd_sc_hd/latest/timing/sky130_fd_sc_hd__tt_025C_1v80.lib"
wget -q "$LIB_URL" -O "$PDK_LIB/sky130_fd_sc_hd__tt_025C_1v80.lib"

LIB_SIZE=$(wc -c < "$PDK_LIB/sky130_fd_sc_hd__tt_025C_1v80.lib")
if [ "$LIB_SIZE" -gt 1000000 ]; then
    echo "[OK] Liberty file: $LIB_SIZE bytes"
else
    echo "[WARNING] Liberty file download may have failed"
fi

# Create .env from secrets if not exists
if [ ! -f .env ]; then
    cat > .env << 'EOF'
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-your_key_here}
GROQ_API_KEY=${GROQ_API_KEY:-your_key_here}
GEMINI_API_KEY=${GEMINI_API_KEY:-your_key_here}
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rtlgenai
EOF
    echo "[OK] .env created from template"
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo "  Run: streamlit run app.py"
echo "============================================"
