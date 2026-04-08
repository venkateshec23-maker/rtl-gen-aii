#!/bin/bash
# start.sh — Launch RTL-Gen AI with OpenCode.ai
# Works in GitHub Codespaces, cloud, or local deployment

echo "🚀 Starting RTL-Gen AI..."
echo "=================================="

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "Starting Docker daemon..."
    if command -v sudo &> /dev/null; then
        sudo service docker start || true
    else
        service docker start || true
    fi
fi

# Pull EDA Docker image if not present
if ! docker image inspect efabless/openlane:latest > /dev/null 2>&1; then
    echo "Pulling OpenLane Docker image (2.5GB, one-time)..."
    docker pull efabless/openlane:latest
fi

# Check if OpenCode.ai is running (optional but recommended)
if ! curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
    echo ""
    echo "⚠️  OpenCode.ai is not running locally at http://localhost:8000"
    echo "   To use AI Verilog generation, run in another terminal:"
    echo "   $ opencode serve --port 8000"
    echo ""
    echo "   Or use Groq provider (free tier available)"
    echo ""
fi

# Start Streamlit
echo "Launching RTL-Gen AI Dashboard..."
echo "Open browser at: http://localhost:8501"
echo ""

streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --logger.level=info
