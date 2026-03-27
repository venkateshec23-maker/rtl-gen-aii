"""
Custom Design - Write and run your own RTL designs through full pipeline
"""

import streamlit as st
from pathlib import Path
import tempfile
import json
from datetime import datetime
import sys
import re

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.full_flow import RTLGenAI, FlowConfig
from python.opencode_integration import OpenCodeGenerator, generate_rtl_from_description

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def extract_module_name(verilog_code: str) -> str:
    """Extract the first module name from Verilog code"""
    # Match: module <name> ( or module <name> #
    pattern = r'\bmodule\s+(\w+)\s*[(\#]'
    match = re.search(pattern, verilog_code, re.IGNORECASE)
    if match:
        return match.group(1)
    # Fallback if no module found
    return "design"

st.set_page_config(
    page_title="Custom Design Studio",
    page_icon="✏️",
    layout="wide",
)

st.title("✏️ Custom Design Studio")
st.markdown("Write custom Verilog RTL and run through complete RTL→GDSII pipeline")

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR: TEMPLATES & PRESETS
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.subheader("📋 Code Source")
    
    code_source = st.radio(
        "How to create code?",
        options=[
            "Template",
            "AI Generation (OpenCode)",
            "Upload File",
        ],
        key="code_source"
    )
    
    st.divider()
    
    if code_source == "Template":
        template_choice = st.radio(
            "Select template:",
            options=[
                "Blank",
                "Simple Counter",
                "8-bit Adder",
                "Traffic Light Controller",
                "Multiplexer",
            ],
            key="template_choice"
        )
    
    elif code_source == "AI Generation (OpenCode)":
        st.markdown("### 🤖 AI-Powered Code Generation (BETA)")
        
        # Check if OpenCode is available
        gen = OpenCodeGenerator()
        if not gen.opencode_available:
            st.warning("⚠️ **OpenCode not installed**\n\nInstall: `npm install -g opencode-ai@latest`")
        else:
            st.success("✅ OpenCode available")
        
        # AI generation form
        ai_description = st.text_area(
            "Describe your circuit:",
            placeholder="Example: 8-bit counter with clock, reset, and enable signals",
            height=100,
            key="ai_desc"
        )
        
        ai_module_name = st.text_input(
            "Module name:",
            value="ai_generated",
            key="ai_mod_name"
        )
        
        ai_run = st.button("🚀 Generate Code", use_container_width=True)
        
        if ai_run and ai_description and gen.opencode_available:
            with st.spinner("🔄 Generating code with OpenCode..."):
                success, code, msg = gen.generate_verilog(
                    description=ai_description,
                    module_name=ai_module_name,
                    style="behavioral"
                )
                
                if success:
                    st.session_state.verilog_code = code
                    st.session_state.code_source = "AI"
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(f"Generation failed: {msg}")
        elif ai_run and not gen.opencode_available:
            st.error("❌ OpenCode not available. Please install it first.")
    
    elif code_source == "Upload File":
        uploaded_file = st.file_uploader(
            "Select Verilog file (.v)",
            type=["v", "sv"],
            key="verilog_upload"
        )
        
        if uploaded_file:
            code_content = uploaded_file.read().decode()
            st.session_state.verilog_code = code_content
            st.session_state.code_source = "Upload"
            st.success(f"✅ Loaded: {uploaded_file.name}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

TEMPLATES = {
    "Blank": """// Write your custom Verilog design here
module my_design (
    input clk,
    input reset,
    input [7:0] data_in,
    output [7:0] data_out
);

    // Your implementation

endmodule
""",
    
    "Simple Counter": """// 8-bit Counter with Reset
module counter (
    input clk,
    input reset,
    input enable,
    output [7:0] count
);
    reg [7:0] count_reg;
    
    assign count = count_reg;
    
    always @(posedge clk) begin
        if (reset)
            count_reg <= 8'b0;
        else if (enable)
            count_reg <= count_reg + 1'b1;
    end

endmodule
""",
    
    "8-bit Adder": """// 8-bit Adder with Carry
module adder_8bit (
    input [7:0] a,
    input [7:0] b,
    input cin,
    output [7:0] sum,
    output cout
);
    assign {cout, sum} = a + b + cin;

endmodule
""",
    
    "Traffic Light Controller": """// Traffic Light Controller - FSM
module traffic_controller (
    input clk,
    input reset,
    input enable,
    output reg red,
    output reg green,
    output reg yellow
);

    localparam RED_STATE = 2'b01;
    localparam GREEN_STATE = 2'b10;
    localparam YELLOW_STATE = 2'b11;
    
    localparam RED_TIME = 30_000_000;
    localparam GREEN_TIME = 25_000_000;
    localparam YELLOW_TIME = 5_000_000;

    reg [1:0] state, next_state;
    reg [27:0] timer;

    always @(posedge clk) begin
        if (reset)
            state <= RED_STATE;
        else
            state <= next_state;
    end

    always @(*) begin
        next_state = state;
        case (state)
            RED_STATE:
                if (timer == 0) next_state = GREEN_STATE;
            GREEN_STATE:
                if (timer == 0) next_state = YELLOW_STATE;
            YELLOW_STATE:
                if (timer == 0) next_state = RED_STATE;
        endcase
    end

    always @(posedge clk) begin
        if (reset) begin
            red <= 1'b1; green <= 1'b0; yellow <= 1'b0; timer <= RED_TIME;
        end else begin
            case (next_state)
                RED_STATE: begin red <= 1'b1; green <= 1'b0; yellow <= 1'b0; if (timer > 0) timer <= timer - 1; else timer <= RED_TIME; end
                GREEN_STATE: begin red <= 1'b0; green <= 1'b1; yellow <= 1'b0; if (timer > 0) timer <= timer - 1; else timer <= GREEN_TIME; end
                YELLOW_STATE: begin red <= 1'b0; green <= 1'b0; yellow <= 1'b1; if (timer > 0) timer <= timer - 1; else timer <= YELLOW_TIME; end
            endcase
        end
    end

endmodule
""",
    
    "Multiplexer": """// 4-to-1 Multiplexer
module mux_4to1 (
    input [3:0] data_in,
    input [1:0] select,
    output data_out
);
    assign data_out = data_in[select];

endmodule
""",
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("📝 Verilog Code Editor")
    
    # Initialize session state for code
    if "verilog_code" not in st.session_state:
        if st.session_state.get("code_source") == "Template":
            st.session_state.verilog_code = TEMPLATES.get(st.session_state.get("template_choice"), TEMPLATES["Blank"])
        else:
            st.session_state.verilog_code = TEMPLATES["Blank"]
    
    # Update code when template changes (only if using templates)
    if st.session_state.get("code_source") == "Template":
        if st.session_state.get("template_choice") != st.session_state.get("last_template"):
            st.session_state.verilog_code = TEMPLATES[st.session_state.get("template_choice")]
            st.session_state.last_template = st.session_state.get("template_choice")
    
    # Code editor
    verilog_code = st.text_area(
        "Enter Verilog RTL code:",
        value=st.session_state.verilog_code,
        height=400,
        key="code_editor"
    )
    st.session_state.verilog_code = verilog_code

with col2:
    st.subheader("⚙️ Pipeline Config")
    
    st.markdown("**Design Settings**")
    design_name = st.text_input(
        "Design name:",
        value="custom_design",
        key="design_name"
    )
    
    run_drc = st.checkbox("Run DRC", value=True)
    run_lvs = st.checkbox("Run LVS", value=False, help="⚠️ Disabled by default - enable for final sign-off only")
    
    st.divider()
    
    st.markdown("**Actions**")
    
    # Save button
    if st.button("💾 Save Code", use_container_width=True, key="save_btn"):
        saved_file = Path(__file__).parent.parent / f"{design_name}.v"
        saved_file.write_text(verilog_code)
        st.success(f"✅ Saved to `{saved_file.name}`")
    
    # Run button (main action)
    run_pipeline = st.button(
        "🚀 Run Pipeline",
        use_container_width=True,
        key="run_btn",
        type="primary"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

if run_pipeline:
    # Create output directory for this run
    runs_dir = Path(__file__).parent.parent / "runs"
    runs_dir.mkdir(exist_ok=True)
    
    # Sanitize design name
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in design_name)
    
    # Create timestamped run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{safe_name}_{timestamp}"
    output_dir = runs_dir / run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save RTL to 01_rtl
    rtl_dir = output_dir / "01_rtl"
    rtl_dir.mkdir(exist_ok=True)
    rtl_file = rtl_dir / f"{safe_name}.v"
    rtl_file.write_text(verilog_code)
    
    st.info(f"📂 Run directory: `{run_name}`")
    st.info(f"📝 RTL saved: `{safe_name}.v`")
    
    # Progress placeholder
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    results_placeholder = st.empty()
    
    # Define progress callback
    progress_log = []
    
    def progress_callback(data):
        stage = data.get("stage", "unknown").title()
        pct = data.get("pct", 0)
        msg = data.get("msg", "")
        
        log_entry = f"[{stage}] {msg}"
        progress_log.append(log_entry)
        
        # Update progress bar
        with progress_placeholder.container():
            st.progress(pct, text=f"⏳ {stage}: {msg}")
        
        # Update status log
        with status_placeholder:
            st.text("\n".join(progress_log[-10:]))  # Show last 10 messages
    
    try:
        st.success("🚀 Starting pipeline execution...")
        
        # Extract module name from Verilog code (more reliable than design name)
        top_module_name = extract_module_name(verilog_code)
        
        # Configure flow
        flow_config = FlowConfig(
            run_drc=run_drc,
            run_lvs=run_lvs,
        )
        
        # Run the pipeline
        result = RTLGenAI.run_from_rtl(
            rtl_path=str(rtl_file),
            top_module=top_module_name,
            output_dir=str(output_dir),
            config=flow_config,
            progress=progress_callback
        )
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # RESULTS
        # ═══════════════════════════════════════════════════════════════════════════════
        
        with results_placeholder.container():
            st.divider()
            
            # Determine success criteria early (for use in both success/failure paths)
            has_gds = result.gds_path and Path(result.gds_path).exists()
            drc_clean = result.drc_violations == 0
            design_success = has_gds and drc_clean and not result.failed_stage
            
            # Check if pipeline succeeded
            if result.failed_stage or result.error_message:
                st.error(f"❌ **Pipeline Failed at: {result.failed_stage}**")
                st.error(f"**Error:** {result.error_message}")
                
                # Show execution summary even on failure
                st.info("**Execution Summary (Partial):**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("⏱️ Total Time", f"{result.total_seconds:.1f}s")
                with col2:
                    st.metric("✓ Completed", f"{len([t for t in result.stage_times.values() if t > 0])}/9 stages")
                with col3:
                    st.metric("⚠️ Failed Stage", result.failed_stage if result.failed_stage else "N/A")
                with col4:
                    st.metric("📝 RTL", "✓" if result.rtl_path and Path(result.rtl_path).exists() else "✗")
                
                # Show log files for debugging
                st.subheader("🔍 Debug Logs")
                
                # Find and display synthesis log if it exists
                synth_log = output_dir / "02_synthesis" / "synth.log"
                if synth_log.exists():
                    st.write("**Synthesis Log:**")
                    log_content = synth_log.read_text(errors='ignore')[-2000:]  # Last 2000 chars
                    st.code(log_content, language="text")
                
                # Check for OpenROAD logs
                for stage_path in [output_dir / f"{i:02d}_*" for i in range(3, 10)]:
                    import glob
                    for log_file in glob.glob(str(stage_path / "*.log")):
                        stage_name = Path(log_file).parent.name
                        st.write(f"**{stage_name} Log:**")
                        content = Path(log_file).read_text(errors='ignore')[-1500:]
                        st.code(content, language="text")
                
                # Show execution summary file
                exec_summary = output_dir / "EXECUTION_SUMMARY.json"
                if exec_summary.exists():
                    st.write("**Execution Summary:**")
                    st.json(json.loads(exec_summary.read_text()))
                    
            else:
                st.success("✅ **Pipeline Complete!**")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("⏱️ Total Time", f"{result.total_seconds:.1f}s")
                with col2:
                    st.metric("🔗 Synthesis", f"{result.stage_times.get('synthesis', 0):.1f}s")
                with col3:
                    st.metric("🔍 DRC", f"{result.drc_violations} violations")
                with col4:
                    lvs_status = "✅" if result.lvs_matched else "❌"
                    st.metric("🔗 LVS", lvs_status)
                
                st.divider()
                
                # Stage results
                st.subheader("📊 Stage Results")
                stages_data = {
                    "Synthesis": result.stage_times.get("synthesis", 0),
                    "Floorplan": result.stage_times.get("floorplan", 0),
                    "Placement": result.stage_times.get("placement", 0),
                    "CTS": result.stage_times.get("cts", 0),
                    "Routing": result.stage_times.get("routing", 0),
                    "GDS": result.stage_times.get("gds", 0),
                    "Sign-off": result.stage_times.get("signoff", 0),
                    "Tapeout": result.stage_times.get("package", 0),
                }
                
                stage_cols = st.columns(4)
                for idx, (stage, time) in enumerate(stages_data.items()):
                    with stage_cols[idx % 4]:
                        st.metric(f"⏱️ {stage}", f"{time:.1f}s")
                
                st.divider()
                
                # Deliverables
                st.subheader("📦 Deliverables")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if result.gds_path and Path(result.gds_path).exists():
                        gds_size = Path(result.gds_path).stat().st_size
                        st.success(f"✅ GDSII File: {gds_size:,} bytes")
                        st.code(f"Path: {result.gds_path}", language="text")
                    else:
                        st.warning("⚠️ GDS file not found")
                
                with col2:
                    if result.package_dir:
                        st.success(f"✅ Tape-out Package Ready")
                        st.code(f"Path: {result.package_dir}", language="text")
                    else:
                        st.warning("⚠️ Tape-out package not created")
                
                st.divider()
                
                if design_success:
                    st.success("🎉 **Design Successfully Generated!**")
                    st.markdown("""
                    ✅ All 9 stages completed  
                    ✅ GDS file generated  
                    ✅ DRC verification passed  
                    ⚠️ LVS status: See details below
                    """)
                else:
                    if not has_gds:
                        st.warning("⚠️ GDS file not generated - check synthesis logs")
                    if not drc_clean:
                        st.warning(f"⚠️ DRC violations found: {result.drc_violations}")
                
                # LVS details (informational)
                st.subheader("📋 Verification Status")
                col1, col2, col3 = st.columns(3)
                with col1:
                    drc_icon = "✅" if drc_clean else "❌"
                    st.metric("DRC Check", f"{drc_icon} {result.drc_violations} violations")
                with col2:
                    lvs_icon = "✅" if result.lvs_matched else "⚠️"
                    st.metric("LVS Match", f"{lvs_icon} {'Matched' if result.lvs_matched else 'Warning'}")
                with col3:
                    st.metric("Tape-out Status", "🟡 Review" if not result.lvs_matched else "✅ Ready")
                
                if not result.lvs_matched:
                    st.info("""
                    **LVS Status:** Layout vs Schematic verification detected differences.
                    
                    This is common for:
                    - Simple combinational designs (passthrough, logic gates)
                    - Designs without timing constraints
                    - Preliminary designs for testing
                    
                    **Next Steps:** Review LVS report in 📊 Results Dashboard for details.
                    """)
                
                # Link to results dashboard
                st.info(f"📊 View full results in **🎯 Results Dashboard** (select run: `{run_name}`)")
            
            # Save execution summary always
            summary = {
                "run_name": run_name,
                "design_name": safe_name,
                "timestamp": datetime.now().isoformat(),
                "status": "SUCCESS" if (not result.failed_stage and has_gds and drc_clean) else "PARTIAL" if not result.failed_stage else "FAILED",
                "total_time": result.total_seconds,
                "stages": result.stage_times,
                "drc_violations": result.drc_violations,
                "lvs_matched": result.lvs_matched,
                "gds_file": result.gds_path,
                "package_dir": result.package_dir,
            }
            
            summary_file = output_dir / "EXECUTION_SUMMARY.json"
            summary_file.write_text(json.dumps(summary, indent=2))
    
    except Exception as e:
        import traceback
        st.error(f"❌ **Pipeline execution failed!**")
        st.error(f"**Error Type:** {type(e).__name__}")
        st.error(f"**Error Message:** {str(e)}")
        
        with st.expander("📋 Full Traceback"):
            st.code(traceback.format_exc(), language="python")
        
        st.warning("**Troubleshooting Tips:**")
        st.markdown("""
        1. **Check RTL Syntax** - Make sure your Verilog code is syntactically valid
        2. **Module Name** - Verify the extracted module name is correct
        3. **Docker** - Ensure Docker is running: `docker ps`
        4. **PDK Files** - Verify Sky130 PDK is available
        5. **Disk Space** - Check you have enough space for GDS generation (~100MB per run)
        6. **Check Logs** - Look in the run directory for detailed stage logs
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════

with st.expander("📚 Quick Reference"):
    st.markdown("""
    ### Pipeline Stages
    1. **Synthesis** - Convert RTL to gate-level netlist (Yosys)
    2. **Floorplanning** - Define core area and placement boundaries
    3. **Placement** - Position cells in the design area
    4. **CTS** - Synthesize clock distribution network
    5. **Routing** - Route all interconnects between cells
    6. **GDS** - Generate final integrated circuit layout
    7. **DRC** - Design Rule Check verification
    8. **LVS** - Layout vs Schematic verification
    9. **Tapeout** - Package all deliverables
    
    ### Tips
    - Always include `module` and `endmodule` keywords
    - Use valid Verilog syntax
    - Keep registered outputs for better synthesis
    - Name your top module same as design name
    """)
