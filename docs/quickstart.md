# Quick Start

## Prerequisites

- Python 3.10+
- Docker Desktop (for EDA tools)
- A Groq API key (free tier: 100K tokens/day)

## Installation

```bash
# Clone the repository
git clone https://github.com/venkateshec23-maker/rtl-gen-aii.git
cd rtl-gen-aii

# Install Python dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your keys:
# GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Run the dashboard
streamlit run app.py
```

## First Design

1. Open `http://localhost:8501`
2. Click "Generate / Upload"
3. Enter module name: `my_adder`
4. Enter description: `8-bit synchronous adder with carry output`
5. Click "Generate Verilog"
6. Wait for the pipeline to complete (~1-2 minutes)
7. Click "Sign-Off" to view results

## Conversational Design

1. Click "Conversational Designer"
2. Describe your design: `Design an 8-bit counter with enable`
3. Click "Start Design"
4. Chat to refine: `Make it 16-bit`, `Add a reset flag`, etc.
5. Each change is validated and synthesized

## Example Library

1. Click "Example Library"
2. Browse 30+ proven synthesizable designs
3. Search by keyword: `uart`, `spi`, `fifo`, `alu`
4. Copy any example as a starting point
