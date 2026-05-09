"""
app_cloud.py
============
Cloud deployment version of RTL-Gen AI.
Shows UI and historical data.
Pipeline runs link to the API server.
"""

import streamlit as st
import os

st.set_page_config(
    page_title="RTL-Gen AI",
    page_icon="square",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set cloud mode
os.environ["CLOUD_MODE"] = "true"

# Show demo banner
st.markdown("""
<div style="
    background: rgba(255,215,0,0.1);
    border: 1px solid #ffd700;
    border-left: 4px solid #ffd700;
    border-radius: 4px;
    padding: 12px 16px;
    margin-bottom: 16px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.85rem;
    color: #ffd700">
    CLOUD MODE - UI and history only.
    For full pipeline with GDS generation,
    run locally with Docker Desktop installed.
    See: github.com/venkateshec23-maker/rtl-gen-aii
</div>
""", unsafe_allow_html=True)

# Import and run main app
try:
    from app import page_design_history, page_api_test
    
    st.sidebar.title("RTL-Gen AI")
    st.sidebar.info("Cloud deployment - limited functionality")
    
    page = st.sidebar.radio(
        "Navigate",
        ["Design History", "API Test", "About"],
        index=0
    )
    
    if page == "Design History":
        st.header("Design Run History")
        try:
            page_design_history()
        except Exception as e:
            st.warning(f"Database not available in cloud mode: {e}")
            st.info("Run locally with PostgreSQL for full history")
    
    elif page == "API Test":
        st.header("API Test")
        page_api_test()
    
    else:
        st.header("About RTL-Gen AI")
        st.markdown("""
        **Natural language to manufacturable silicon in 30 seconds.**
        
        This cloud deployment shows the UI and design history.
        For full GDS generation, run locally with:
        - Docker Desktop
        - OpenLane EDA tools  
        - Sky130 or GF180MCU PDK
        
        [GitHub Repository](https://github.com/venkateshec23-maker/rtl-gen-aii)
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading app: {e}")
    st.info("Please ensure all dependencies are installed")
