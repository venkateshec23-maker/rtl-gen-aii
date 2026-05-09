# RTL-Gen AI Deployment Guide

## Local Deployment (Full Pipeline)

Requirements:
- Windows 10/11 or Linux
- Docker Desktop running
- Python 3.12+
- 4GB RAM minimum

```bash
git clone https://github.com/venkateshec23-maker/rtl-gen-aii
cd rtl-gen-aii
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# Start everything
powershell -File start_all.ps1
```

Access:
- UI:  http://localhost:8501
- API: http://localhost:8502
- Docs: http://localhost:8502/docs

## Cloud Deployment (UI Only)

[![Deploy to Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

1. Fork this repository
2. Go to share.streamlit.io
3. Connect your GitHub account
4. Deploy from your fork
5. Add API keys in secrets

Note: Cloud deployment shows UI and history.
Full pipeline requires local Docker setup.

## API Only (Headless)

```bash
python api.py
# API available at http://localhost:8502
```

Test:
```bash
curl -X POST http://localhost:8502/api/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "8-bit adder"}'
```

## GitHub Codespaces (Zero Install)

Click: Code -> Codespaces -> Create codespace
Wait 5 minutes for automatic setup.
Run: streamlit run app.py

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| ANTHROPIC_API_KEY | Recommended | Claude API |
| GOOGLE_API_KEY | Recommended | Gemini API |
| GROQ_API_KEY | Optional | Groq API |
| DATABASE_URL | Optional | PostgreSQL URL |
| OPENLANE_WORK | Optional | Default: C:\tools\OpenLane |
| PDK_ROOT | Optional | Default: C:\pdk |
