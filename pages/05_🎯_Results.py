"""
Results Dashboard - View completed design runs
"""

import streamlit as st
from pathlib import Path
import json
from datetime import datetime

st.set_page_config(
    page_title="Results Dashboard",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Design Results Dashboard")
st.markdown("View completed RTL-to-GDSII runs and their deliverables")

# Get runs directory
runs_dir = Path(__file__).parent.parent / "runs"

if not runs_dir.exists():
    st.warning("📂 No design runs found. Create and run a design in **✏️ Custom Design** first.")
    st.stop()

# List available runs
runs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)

if not runs:
    st.warning("📂 No completed runs found. Use **✏️ Custom Design** to create and run designs.")
    st.stop()

# Show quick stats
st.subheader("📊 Run Statistics")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Runs", len(runs))
with col2:
    gds_count = sum(1 for r in runs if (r / "07_gds").exists())
    st.metric("With GDS", gds_count)
with col3:
    tapeout_count = sum(1 for r in runs if (r / "09_tapeout").exists())
    st.metric("Tape-out Ready", tapeout_count)
with col4:
    latest_run = runs[0] if runs else None
    if latest_run:
        time_ago = datetime.now() - datetime.fromtimestamp(latest_run.stat().st_mtime)
        minutes = int(time_ago.total_seconds() / 60)
        st.metric("Latest", f"{minutes}m ago" if minutes > 0 else "Just now")

st.divider()

# Sidebar: Select run
with st.sidebar:
    st.subheader("📂 Available Runs")
    selected_run = st.selectbox(
        "Select run:",
        options=[r.name for r in runs],
        index=0,
        help="Click to view detailed results for this run"
    )

run_dir = runs_dir / selected_run
st.markdown(f"**Run:** `{selected_run}`  |  **Path:** `runs/{selected_run}/`")

# Try to load execution summary
summary_file = run_dir / "EXECUTION_SUMMARY.json"
summary_data = {}
if summary_file.exists():
    try:
        summary_data = json.loads(summary_file.read_text())
    except:
        pass

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Summary",
    "📁 Output Files",
    "📈 Timeline",
    "✅ Sign-off",
    "📦 Deliverables",
    "ℹ️ Info",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Get design stats
        rtl_dir = run_dir / "01_rtl"
        rtl_lines = 0
        if rtl_dir.exists():
            rtl_files = list(rtl_dir.glob("*.v"))
            if rtl_files:
                rtl_lines = len(rtl_files[0].read_text().splitlines())
        st.metric("📝 RTL Lines", f"{rtl_lines:,}")
    
    with col2:
        # Synthesis
        synth_dir = run_dir / "02_synthesis"
        cell_count = "N/A"
        if synth_dir.exists():
            netlist_files = list(synth_dir.glob("*.v"))
            if netlist_files:
                cell_count = f"{len(netlist_files)}"
        st.metric("🔗 Netlists", cell_count)
    
    with col3:
        # GDS
        gds_dir = run_dir / "07_gds"
        gds_size = "N/A"
        if gds_dir.exists():
            gds_files = list(gds_dir.glob("*.gds"))
            if gds_files:
                gds_size = f"{gds_files[0].stat().st_size:,} bytes"
        st.metric("💾 GDS Size", gds_size)
    
    with col4:
        # Total time
        total_time = summary_data.get("total_time", 0)
        st.metric("⏱️ Total Time", f"{total_time:.1f}s" if total_time else "N/A")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Design Metrics")
        
        metrics = {
            "Design": summary_data.get("design_name", "Unknown"),
            "Status": summary_data.get("status", "Unknown"),
            "DRC Violations": summary_data.get("drc_violations", "N/A"),
            "LVS Match": "✅ Yes" if summary_data.get("lvs_matched") else "❌ No",
        }
        
        for key, value in metrics.items():
            st.write(f"**{key}:** {value}")
    
    with col2:
        st.subheader("Stage Timings")
        
        if summary_data.get("stages"):
            stage_times = summary_data["stages"]
            for stage, time in sorted(stage_times.items()):
                bar_width = int(time * 10)
                st.write(f"`{stage:12}` {'█' * bar_width} {time:.2f}s")
        else:
            st.info("Stage timing data not available")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: OUTPUT FILES
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Pipeline Output Files")
    
    stages = [
        ("01_rtl", "🔤 RTL Sources", "Original Verilog code"),
        ("02_synthesis", "🔗 Synthesis", "Yosys gate-level netlists"),
        ("03_floorplan", "📍 Floorplan", "Core area and boundaries"),
        ("04_placement", "📍 Placement", "Cell placement results"),
        ("05_cts", "⏱️ Clock Tree", "Clock distribution files"),
        ("06_routing", "🛣️ Routing", "Routed DEF files"),
        ("07_gds", "💾 GDS", "Final GDSII layout"),
        ("08_signoff", "✅ Sign-off", "DRC and LVS reports"),
        ("09_tapeout", "📦 Tapeout", "Tape-out deliverables"),
    ]
    
    for stage_name, stage_icon, stage_desc in stages:
        stage_dir = run_dir / stage_name
        if stage_dir.exists():
            files = list(stage_dir.glob("*"))
            if files:
                with st.expander(f"{stage_icon} {stage_desc} ({len(files)} files)"):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    for f in sorted(files)[:20]:  # Show first 20
                        if f.is_file():
                            size = f.stat().st_size
                            
                            # Format size
                            if size < 1024:
                                size_str = f"{size}B"
                            elif size < 1024*1024:
                                size_str = f"{size/1024:.1f}KB"
                            else:
                                size_str = f"{size/(1024*1024):.1f}MB"
                            
                            col1.write(f"`{f.name}`")
                            col2.write(size_str)
                            
                            # Add download button for small files
                            if size < 100*1024*1024:
                                with col3:
                                    with open(f, "rb") as file_handle:
                                        st.download_button(
                                            "⬇️",
                                            data=file_handle.read(),
                                            file_name=f.name,
                                            key=f"dl_{f.name}_{stage_name}"
                                        )
                    
                    if len(files) > 20:
                        st.caption(f"... and {len(files)-20} more files")
            else:
                st.info(f"No files in {stage_name}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Pipeline Execution Timeline")
    
    if summary_data.get("stages"):
        stage_times = summary_data["stages"]
        total_time = sum(stage_times.values())
        
        # Create visual timeline
        for stage, time in sorted(stage_times.items()):
            percentage = (time / total_time * 100) if total_time > 0 else 0
            col1, col2, col3, col4 = st.columns([2, 8, 1, 1])
            
            with col1:
                st.write(f"`{stage:12}`")
            
            with col2:
                bar = "█" * int(percentage / 2)
                st.write(f"{bar:<50} {percentage:.1f}%")
            
            with col3:
                st.write(f"{time:.2f}s")
            
            with col4:
                st.write(f"{percentage:.0f}%")
        
        st.divider()
        st.metric("Total Pipeline Time", f"{total_time:.1f}s")
    else:
        st.info("Timeline data not available")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: SIGN-OFF
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("DRC & LVS Verification Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### 🔍 DRC (Design Rule Check)")
        drc_violations = summary_data.get("drc_violations", "N/A")
        
        if isinstance(drc_violations, int):
            if drc_violations == 0:
                st.success(f"✅ No DRC violations found!")
            else:
                st.warning(f"⚠️ {drc_violations} DRC violations detected")
        else:
            st.info(f"Status: {drc_violations}")
        
        # Show DRC details
        signoff_dir = run_dir / "08_signoff"
        if signoff_dir.exists():
            drc_files = list(signoff_dir.glob("*drc*"))
            if drc_files:
                st.write("**DRC Report Files:**")
                for f in drc_files:
                    if f.is_file():
                        st.code(f.name)
    
    with col2:
        st.write("### 🔗 LVS (Layout vs Schematic)")
        lvs_matched = summary_data.get("lvs_matched", False)
        
        if lvs_matched:
            st.success("✅ LVS verification passed!")
        else:
            st.warning("⚠️ LVS verification needs review")
        
        # Show LVS details
        signoff_dir = run_dir / "08_signoff"
        if signoff_dir.exists():
            lvs_files = list(signoff_dir.glob("*lvs*"))
            if lvs_files:
                st.write("**LVS Report Files:**")
                for f in lvs_files:
                    if f.is_file():
                        st.code(f.name)
    
    st.divider()
    
    # Overall sign-off status
    if drc_violations == 0 and lvs_matched:
        st.success("🎉 Design passes all sign-off checks!")
    elif drc_violations == 0 or lvs_matched:
        st.info("⚠️ Design partially passes sign-off checks")
    else:
        st.warning("❌ Design has sign-off issues")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: DELIVERABLES
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Final Tape-out Deliverables")
    
    tapeout_dir = run_dir / "09_tapeout"
    
    if tapeout_dir.exists():
        st.success("✅ Tape-out package ready for fabrication")
        
        # Key files
        files_found = {
            "GDSII": None,
            "Netlist": None,
            "LEF": None,
            "DEF": None,
            "MANIFEST": None,
            "README": None,
        }
        
        for f in tapeout_dir.rglob("*"):
            if f.suffix == ".gds":
                files_found["GDSII"] = f
            elif "netlist" in f.name.lower() or f.suffix == ".v":
                files_found["Netlist"] = f
            elif f.suffix == ".lef":
                files_found["LEF"] = f
            elif f.suffix == ".def":
                files_found["DEF"] = f
            elif "MANIFEST" in f.name:
                files_found["MANIFEST"] = f
            elif "README" in f.name:
                files_found["README"] = f
        
        # Display key deliverables
        col1, col2, col3, col4 = st.columns(4)
        
        deliverable_cols = [col1, col2, col3, col4]
        
        for idx, (name, file_path) in enumerate(files_found.items()):
            if file_path:
                with deliverable_cols[idx % 4]:
                    size = file_path.stat().st_size if file_path.is_file() else 0
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024*1024:
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/(1024*1024):.1f}MB"
                    
                    st.metric(f"📦 {name}", size_str)
        
        st.divider()
        
        # Detailed file listing
        st.write("**All Deliverable Files:**")
        
        all_files = list(tapeout_dir.rglob("*"))
        for f in sorted(all_files):
            if f.is_file():
                rel_path = f.relative_to(tapeout_dir)
                size = f.stat().st_size
                
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024*1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size/(1024*1024):.1f}MB"
                
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"`{rel_path}`")
                col2.write(size_str)
                
                # Download button
                with col3:
                    with open(f, "rb") as file_handle:
                        st.download_button(
                            "⬇️",
                            data=file_handle.read(),
                            file_name=f.name,
                            key=f"dl_deliverable_{f.name}"
                        )
    else:
        st.warning("⚠️ Tape-out package not found")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6: INFO
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("Run Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Execution Details**")
        st.code(f"""
Run Name: {selected_run}
Path: runs/{selected_run}/
Technology: Sky130A (130nm)
""")
    
    with col2:
        if summary_data:
            st.write("**Summary Data**")
            st.json(summary_data)
    
    st.divider()
    
    st.write("**Next Steps**")
    if summary_data.get("is_tapeable") or (summary_data.get("drc_violations") == 0 and summary_data.get("lvs_matched")):
        st.success("""
✅ Design is ready for fabrication!
- Review tape-out package contents
- Prepare for submission to foundry
- Generate final documentation
        """)
    else:
        st.info("""
⚠️ Design requires refinement:
- Review DRC violations in sign-off tab
- Check LVS matching issues
- Return to ✏️ Custom Design to iterate
        """)
