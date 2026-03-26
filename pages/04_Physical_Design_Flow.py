"""
Physical Design Flow - RTL→GDS Pipeline in Streamlit
Integrates full 9-stage pipeline: Synthesis → Floorplan → Placement → CTS → Routing → GDS → Sign-off → Tapeout
"""

import streamlit as st
import sys
from pathlib import Path
import tempfile
import time
import json
from datetime import datetime

# Add python directory to path
sys.path.append(str(Path(__file__).parent.parent))

from python.full_flow import RTLGenAI, FlowConfig
from python.docker_manager import DockerManager
from python.pdk_manager import PDKManager

# Page config
st.set_page_config(
    page_title="Physical Design Flow - RTL-to-GDSII",
    page_icon="🏭",
    layout="wide"
)

# Title and description
st.title("🏭 RTL-to-GDSII Physical Design Pipeline")
st.markdown("""
**Complete 9-stage flow:** RTL → Synthesis → Floorplan → Placement → CTS → Routing → GDS → Sign-off → Tapeout

This pipeline takes synthesized Verilog and produces a fabrication-ready GDS file with DRC/LVS verification.
""")

# Session state initialization
if 'pipeline_running' not in st.session_state:
    st.session_state.pipeline_running = False
if 'pipeline_result' not in st.session_state:
    st.session_state.pipeline_result = None
if 'pipeline_logs' not in st.session_state:
    st.session_state.pipeline_logs = []
if 'docker_status' not in st.session_state:
    st.session_state.docker_status = None

# Sidebar configuration
with st.sidebar:
    st.subheader("⚙️ Pipeline Configuration")
    
    # Design input
    design_source = st.radio(
        "Design Input Source",
        ["Use previous synthesis result", "Upload Verilog file", "Use template"]
    )
    
    design_code = None
    if design_source == "Upload Verilog file":
        uploaded_file = st.file_uploader("Upload Verilog (.v)", type=["v", "sv"])
        if uploaded_file:
            design_code = uploaded_file.read().decode("utf-8")
    elif design_source == "Use template":
        design_code = """// Simple 8-bit Adder
module adder_8bit(
    input  [7:0] a,
    input  [7:0] b,
    input        cin,
    output [7:0] sum,
    output       cout
);
    assign {cout, sum} = a + b + cin;
endmodule"""
    
    # Flow options
    st.subheader("Flow Options")
    
    run_synthesis = st.checkbox("Run Synthesis", value=True, help="Yosys: RTL→Gate-level")
    run_floorplan = st.checkbox("Run Floorplanning", value=True, help="Define design area")
    run_placement = st.checkbox("Run Placement", value=True, help="OpenROAD: Place cells")
    run_cts = st.checkbox("Run Clock Tree Synthesis", value=True, help="Balanced clock distribution")
    run_routing = st.checkbox("Run Routing", value=True, help="Global + Detailed routing")
    run_gds = st.checkbox("Generate GDS", value=True, help="Final layout export")
    run_signoff = st.checkbox("Run DRC/LVS", value=True, help="Design verification")
    run_tapeout = st.checkbox("Create Tapeout Package", value=True, help="Final deliverables")
    
    st.divider()
    
    # Design parameters
    st.subheader("Design Parameters")
    top_module = st.text_input("Top Module Name", value="adder_8bit", help="Main chip name")
    chip_area_um2 = st.number_input("Target Chip Area (µm²)", value=100000, min_value=10000, step=10000)
    power_budget_mw = st.number_input("Power Budget (mW)", value=10.0, min_value=0.1)
    
    st.divider()
    
    # Docker status check
    st.subheader("🐳 Docker Status")
    if st.button("Check Docker Health"):
        with st.spinner("Checking Docker..."):
            docker = DockerManager()
            docker_status = docker.verify_installation()
            st.session_state.docker_status = docker_status
            
            if docker_status.running:
                st.success(f"✅ Docker running ({docker_status.version.strip()})")
            else:
                st.warning("⚠️ Docker not running - will attempt auto-start")
                st.info(docker_status.error or "Docker daemon not responding")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Pipeline Execution")
    
    # Start pipeline button
    if st.button("▶️ Start Full Pipeline", use_container_width=True, type="primary"):
        if not top_module:
            st.error("Enter a top module name")
        else:
            st.session_state.pipeline_running = True
            st.session_state.pipeline_logs = []
            
            # Create temporary working directory
            with tempfile.TemporaryDirectory() as tmpdir:
                work_dir = Path(tmpdir)
                output_dir = work_dir / "output"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Prepare design file
                if design_code and design_source in ["Upload Verilog file", "Use template"]:
                    rtl_file = work_dir / f"{top_module}.v"
                    rtl_file.write_text(design_code)
                else:
                    st.error("Please provide Verilog code (upload file or use template)")
                    st.stop()
                
                # Configure flow
                flow_config = FlowConfig(
                    run_drc=run_signoff,
                    run_lvs=run_signoff,
                )
                
                # Create progress containers
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                logs_container = st.empty()
                
                # Run pipeline with callback
                def progress_callback(data):
                    stage = data.get("stage", "unknown").title()
                    pct = data.get("pct", 0)
                    msg = data.get("msg", "")
                    progress_bar.progress(min(pct, 0.99))
                    status_text.write(f"**Current Stage:** {stage} - {msg}")
                    st.session_state.pipeline_logs.append(f"[{stage}] {msg}")
                    with logs_container.container():
                        for log in st.session_state.pipeline_logs[-10:]:  # Show last 10
                            st.text(log)
                
                try:
                    # Run the pipeline with RTLGenAI
                    result = RTLGenAI.run_from_rtl(
                        rtl_path=str(rtl_file),
                        top_module=top_module,
                        output_dir=str(output_dir),
                        config=flow_config,
                        progress=progress_callback
                    )
                    
                    # Update progress bar
                    progress_bar.progress(1.0)
                    st.session_state.pipeline_result = result
                    
                    # Display results
                    col_summary, col_details = st.columns([1, 1])
                    
                    with col_summary:
                        st.subheader("✅ Pipeline Complete")
                        metrics = {
                            "Status": "✅ SUCCESS" if result.is_tapeable else "⚠️ WARNINGS",
                            "Total Time": f"{result.total_seconds:.1f}s",
                            "RTL Module": result.top_module,
                            "GDS File": result.gds_path or "Not generated",
                        }
                        for k, v in metrics.items():
                            st.metric(k, v)
                    
                    with col_details:
                        st.subheader("🔍 Verification Results")
                        metrics_verify = {
                            "DRC Violations": result.drc_violations if result.drc_violations >= 0 else "Skipped",
                            "LVS Status": "✅ MATCHED" if result.lvs_matched else "❌ MISMATCH",
                            "Tape-out Ready": "✅ Yes" if result.is_tapeable else "❌ No",
                            "Package Dir": result.package_dir or "Not created",
                        }
                        for k, v in metrics_verify.items():
                            st.metric(k, v)
                    
                    # Stage timings
                    st.subheader("⏱️ Stage Timings")
                    if result.stage_times:
                        stage_df_data = {
                            "Stage": list(result.stage_times.keys()),
                            "Time (s)": list(result.stage_times.values())
                        }
                        import pandas as pd
                        st.bar_chart(pd.DataFrame(stage_df_data).set_index("Stage"))
                    
                    # Download results
                    st.subheader("📥 Download Results")
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        if result.gds_path and Path(result.gds_path).exists():
                            with open(result.gds_path, "rb") as f:
                                st.download_button(
                                    "📥 Download GDS",
                                    f.read(),
                                    file_name=f"{top_module}.gds"
                                )
                    with col_dl2:
                        if result.package_dir and Path(result.package_dir).exists():
                            # Create summary JSON
                            summary = {
                                "design": top_module,
                                "timestamp": datetime.now().isoformat(),
                                "status": "SUCCESS" if result.is_tapeable else "WARNING",
                                "gds_file": result.gds_path,
                                "drc_violations": result.drc_violations,
                                "lvs_matched": result.lvs_matched,
                                "stage_timings": result.stage_times
                            }
                            st.download_button(
                                "📥 Download Summary",
                                json.dumps(summary, indent=2),
                                file_name=f"{top_module}_summary.json"
                            )
                    
                except Exception as e:
                    st.error(f"Pipeline failed: {str(e)}")
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
                finally:
                    st.session_state.pipeline_running = False

with col2:
    st.subheader("📋 Pipeline Stages")
    
    stages = [
        ("1. Synthesis", "RTL→Netlist (Yosys)"),
        ("2. Floorplan", "Define area & pins"),
        ("3. Placement", "Cell placement"),
        ("4. CTS", "Clock tree"),
        ("5. Routing", "Signal routing"),
        ("6. GDS", "Export layout"),
        ("7. Sign-off", "DRC/LVS checks"),
        ("8. Tapeout", "Final package"),
    ]
    
    for stage_name, stage_desc in stages:
        st.markdown(f"**{stage_name}** - {stage_desc}")

# Footer
st.divider()
st.markdown("""
### 📖 Documentation
- **Initial Setup:** Make sure Docker is installed and running
- **Design Input:** Provide a Verilog RTL file or use template
- **Output:** Complete GDS file + verification reports
- **Requirements:** 
  - Docker Desktop (efabless/openlane image)
  - Sky130A PDK (auto-mounted by system)
  - ~30-60 seconds for typical designs
""")

if st.session_state.pipeline_logs:
    with st.expander("📜 Full Pipeline Logs"):
        for log in st.session_state.pipeline_logs:
            st.text(log)
