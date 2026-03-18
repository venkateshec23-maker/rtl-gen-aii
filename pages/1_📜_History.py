"""
Design History Page
View and manage previously generated designs.
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Design History", page_icon="📜", layout="wide")

st.title("📜 Design History")

# Load history from cache
history_file = Path("cache/history.json")

if history_file.exists():
    with open(history_file, encoding='utf-8') as f:
        history = json.load(f)
    
    if history:
        st.write(f"Total designs: {len(history)}")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_type = st.selectbox("Type", ["All", "Combinational", "Sequential", "FSM"])
        with col2:
            filter_status = st.selectbox("Status", ["All", "Passed", "Failed"])
        with col3:
            sort_by = st.selectbox("Sort by", ["Newest", "Oldest", "Name"])
        
        # Display history
        for design in history:
            with st.expander(f"{design['module_name']} - {design['timestamp']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Description:** {design['description']}")
                    st.write(f"**Type:** {design.get('type', 'Unknown')}")
                    st.write(f"**Status:** {'✅ Passed' if design.get('passed') else '❌ Failed'}")
                
                with col2:
                    if st.button("Load", key=f"load_{design['id']}"):
                        st.session_state['loaded_design'] = design
                        st.success("Design loaded! Go to main page.")
                    
                    if st.button("Delete", key=f"del_{design['id']}"):
                        # Remove from history
                        history.remove(design)
                        with open(history_file, 'w', encoding='utf-8') as f:
                            json.dump(history, f, indent=2)
                        st.rerun()
    else:
        st.info("No design history yet. Generate your first design!")
else:
    st.info("No design history yet. Generate your first design!")
