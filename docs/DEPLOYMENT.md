# Deployment Guide

This guide describes how to deploy the RTL-Gen AI Web Application (Streamlit) or how to distribute the tool to your team.

## Local Production Deployment

To run the application locally on a stable server environment instead of the development server, you can configure Streamlit:

1. Create a `~/.streamlit/config.toml` file:
   ```toml
   [server]
   port = 8501
   address = "0.0.0.0"
   headless = true
   
   [browser]
   gatherUsageStats = false
   ```

2. Run the application:
   ```bash
   streamlit run app.py
   ```

## Cloud Deployment (Streamlit Community Cloud)

Streamlit Community Cloud is the easiest way to share RTL-Gen AI:

1. Push your repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in.
3. Click **New app** and select your GitHub repository, branch, and `app.py` as the main file path.
4. In **Advanced Settings**, add your environment variables securely:
   ```
   ANTHROPIC_API_KEY=your_key_here
   DEBUG_MODE=False
   ```
5. Click **Deploy**. Note that Streamlit Cloud doesn't come with `iverilog` installed. You'll need to mock verification or use a custom Docker container if verification is strictly required in the cloud UI.

## Docker Deployment (Coming Soon)

A fully containerized Docker workflow will be introduced in future updates, enabling local compilation of `iverilog` alongside the Streamlit web server.

## Releasing a Package

To build source distributions and wheels to publish on PyPI (or an internal company index):

```bash
pip install build twine
python -m build
twine upload dist/*
```
