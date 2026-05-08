#!/bin/bash
set -e

echo "=== RTL-Gen AI Setup ==="

# Install Python dependencies
echo "Installing Python packages..."
pip install -r requirements.txt -q
pip install reportlab fastapi uvicorn pytest pytest-timeout --break-system-packages -q

# Create working directories
mkdir -p openlane_work/designs
mkdir -p openlane_work/runs
mkdir -p openlane_work/results
mkdir -p pdk
mkdir -p reports

# Pull OpenLane Docker image
echo "Pulling OpenLane Docker image..."
docker pull efabless/openlane:latest

# Start PostgreSQL
echo "Starting PostgreSQL..."
docker run -d \
  --name rtlgenai-postgres \
  --restart always \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rtlgenai \
  -p 5432:5432 \
  postgres:15

sleep 5

# Initialize database
docker exec rtlgenai-postgres psql \
  -U postgres -d rtlgenai \
  -c "CREATE TABLE IF NOT EXISTS design_runs (
    run_id TEXT PRIMARY KEY,
    design_name TEXT,
    status TEXT,
    tapeout_ready BOOLEAN,
    elapsed_sec FLOAT,
    gds_size_bytes BIGINT,
    cell_count INTEGER,
    lvs_status TEXT,
    timing_slack_ns FLOAT,
    gds_path TEXT,
    results_dir TEXT,
    steps JSONB,
    all_corners_met BOOLEAN,
    formal_status TEXT,
    signoff_report TEXT,
    created_at TIMESTAMP DEFAULT NOW()
  );" 2>/dev/null || true

# Download Liberty files if PDK not present
if [ ! -f "pdk/sky130_fd_sc_hd__tt_025C_1v80.lib" ]; then
  echo "Downloading Sky130 Liberty files..."
  LIB_BASE="https://raw.githubusercontent.com/google/skywater-pdk-libs-sky130_fd_sc_hd/master/timing"
  wget -q "$LIB_BASE/sky130_fd_sc_hd__tt_025C_1v80.lib" \
       -O pdk/sky130_fd_sc_hd__tt_025C_1v80.lib || true
fi

echo "=== Setup Complete ==="
echo "Run: streamlit run app.py"
echo "API: python api.py"
