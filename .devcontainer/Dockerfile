FROM python:3.12-slim

# Install system dependencies + native EDA tools
RUN apt-get update && apt-get install -y \
    git curl wget \
    iverilog \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /workspaces/rtl-gen-aii
