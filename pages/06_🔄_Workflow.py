"""
Pipeline Workflow - Visual guide to the entire RTL-to-GDSII process
"""

import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Pipeline Workflow",
    page_icon="🔄",
    layout="wide",
)

st.title("🔄 Integrated Pipeline Workflow")
st.markdown("Complete RTL-to-GDSII design flow with UI integration")

# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════

st.subheader("Complete Integration Flow")

with st.container(border=True):
    col1, arrow1, col2, arrow2, col3 = st.columns([1.5, 0.3, 1.5, 0.3, 1.5])
    
    with col1:
        st.markdown("""
        ### ✏️ Create Design
        **Custom Design Studio**
        - Write Verilog code
        - Choose templates
        - Configure pipeline
        - Click Run
        """)
    
    with arrow1:
        st.markdown("""
        <div style='text-align: center; padding-top: 30px; font-size: 24px;'>→</div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        ### 🚀 Execute Pipeline
        **All 9 Stages Automated**
        1. Synthesis (Yosys)
        2. Floorplanning
        3. Placement
        4. Clock Tree
        5. Routing
        6. GDS Gen
        7. DRC Check
        8. LVS Check
        9. Tapeout
        """)
    
    with arrow2:
        st.markdown("""
        <div style='text-align: center; padding-top: 30px; font-size: 24px;'>→</div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        ### 🎯 View Results
        **Results Dashboard**
        - All outputs organized
        - Summary metrics
        - File downloads
        - Sign-off status
        - Ready for fab!
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP-BY-STEP GUIDE
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📖 Step-by-Step Guide")

# Step 1
with st.expander("**STEP 1: Write Custom Verilog** ✏️", expanded=True):
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        ### Navigate to ✏️ Custom Design Studio
        
        1. Click **✏️ Custom Design Studio** in sidebar
        2. Choose a template or start blank
        3. **Edit the Verilog code** in the editor
        4. Enter a **design name** (lowercase, alphanumeric)
        5. Configure DRC/LVS checkbox settings
        
        ### Example: Simple Counter
        ```verilog
        module my_counter (
            input clk,
            input reset,
            output [7:0] count
        );
            reg [7:0] counter;
            always @(posedge clk)
                if (reset)
                    counter <= 0;
                else
                    counter <= counter + 1;
            assign count = counter;
        endmodule
        ```
        """)
    
    with col2:
        st.info("""
        **Tips:**
        - Keep module named same as design name
        - Use realistic clock frequencies
        - Include registered outputs
        - Valid Verilog syntax required
        - All files auto-saved to runs/
        
        **Available Templates:**
        - Blank
        - Simple Counter
        - 8-bit Adder
        - Traffic Light
        - Multiplexer
        """)

# Step 2
with st.expander("**STEP 2: Launch Pipeline Execution** 🚀"):
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        ### Click "🚀 Run Pipeline"
        
        The system will:
        1. **Create timestamped directory** in `runs/`
        2. **Save RTL** to `01_rtl/`
        3. **Execute synthesis** (Yosys)
        4. **Run place & route** (OpenROAD)
        5. **Generate GDS** file
        6. **Run verification** (DRC/LVS)
        7. **Create tape-out package**
        
        **Progress Tracking:**
        - Real-time progress bar
        - Stage execution log
        - Status messages
        - Execution timings
        """)
    
    with col2:
        st.success("""
        ### What Happens Automatically
        
        **Docker Integration:**
        - Auto-starts Docker if needed
        - Runs Yosys in container
        - Executes OpenROAD tools
        - Runs Magic/Netgen checks
        
        **All 9 Stages:**
        - ✅ Synthesis
        - ✅ Floorplan
        - ✅ Placement
        - ✅ CTS
        - ✅ Routing
        - ✅ GDS
        - ✅ DRC
        - ✅ LVS
        - ✅ Tapeout
        
        **Output Location:**
        `runs/design_name_YYYYMMDD_HHMMSS/`
        """)

# Step 3
with st.expander("**STEP 3: View Results in Dashboard** 🎯"):
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        ### Navigate to 🎯 Results Dashboard
        
        1. Click **🎯 Results Dashboard** in sidebar
        2. Select your run from dropdown
        3. View your design's complete results
        """)
    
    with col2:
        st.markdown("""
        ### Available Views:
        
        | Tab | Shows |
        |-----|-------|
        | 📊 Summary | Metrics, timings, status |
        | 📁 Files | All 9 stage outputs with downloads |
        | 📈 Timeline | Execution timing breakdown |
        | ✅ Sign-off | DRC violations, LVS results |
        | 📦 Deliverables | Tape-out package contents |
        | ℹ️ Info | Run metadata and next steps |
        
        ### Download Files
        - Click ⬇️ button to download any file
        - GDS, netlist, reports, all included
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📁 Output Directory Structure")

with st.expander("Click to view directory structure"):
    st.code("""
runs/
├── traffic_controller_20260326_181200/
│   ├── 01_rtl/                    ← Your Verilog source
│   │   └── traffic_controller.v
│   ├── 02_synthesis/              ← Yosys output
│   │   ├── traffic_controller.v   (netlist)
│   │   ├── traffic_controller.sdc (timing constraints)
│   │   └── synthesis.log
│   ├── 03_floorplan/              ← Core area definition
│   │   ├── floorplan.def
│   │   └── floorplan.log
│   ├── 04_placement/              ← Global placement
│   │   ├── placement.def
│   │   └── placement.log
│   ├── 05_cts/                    ← Clock tree synthesis
│   │   ├── cts.def
│   │   └── cts.log
│   ├── 06_routing/                ← Detailed routing
│   │   ├── routing.def
│   │   └── routing.log
│   ├── 07_gds/                    ← Final layout
│   │   └── traffic_controller.gds ✅
│   ├── 08_signoff/                ← Verification results
│   │   ├── drc_report.txt
│   │   ├── lvs_report.txt
│   │   └── *.log
│   ├── 09_tapeout/                ← Delivery package
│   │   ├── traffic_controller.gds
│   │   ├── traffic_controller.v
│   │   ├── traffic_controller.lef
│   │   ├── MANIFEST.txt
│   │   ├── README.md
│   │   └── signoff_results/
│   └── EXECUTION_SUMMARY.json     ← Run metadata
    """, language="bash")

# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION POINTS
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("🔗 Integration Points")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### ✏️ Custom Design
    **Input:**
    - Verilog code (text)
    - Design name
    - Config options
    
    **Output:**
    - Run created in /runs/
    - RTL saved to 01_rtl/
    
    **Next:** Run pipeline
    """)

with col2:
    st.markdown("""
    ### 🚀 Pipeline Execution
    **Inputs:**
    - RTL file path
    - Design name
    - Config settings
    
    **Outputs:**
    - 9 stage directories
    - GDS file
    - Reports
    - Metrics JSON
    
    **Via:** RTLGenAI.run_from_rtl()
    """)

with col3:
    st.markdown("""
    ### 🎯 Results Dashboard
    **Inputs:**
    - Run directory
    - All 9 stages
    - JSON metadata
    
    **Shows:**
    - All outputs
    - Metrics & timing
    - Sign-off results
    - Downloadable files
    
    **Auto-detects:** All runs
    """)

# ═══════════════════════════════════════════════════════════════════════════════
# QUICK TROUBLESHOOTING
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("🔧 Troubleshooting")

trouble_cols = st.columns(2)

with trouble_cols[0]:
    with st.expander("❌ Pipeline failed - where's the error?"):
        st.markdown("""
        **Check these files in order:**
        1. `02_synthesis/*.log` - Synthesis errors
        2. `03_floorplan/*.log` - Floorplan issues
        3. `04_placement/*.log` - Placement failures
        4. `08_signoff/*.txt` - Verification issues
        
        **Common issues:**
        - Syntax errors in Verilog
        - Missing module definitions
        - Incompatible netlist
        """)
    
    with st.expander("⏳ Why is it slow?"):
        st.markdown("""
        **Typical timings:**
        - Synthesis: 2-5s
        - Floorplan: 2-5s
        - Placement: 1-3s
        - CTS: 1-2s
        - Routing: 1-3s
        - GDS: 2-5s
        - **Total: ~10-25s** per design
        
        Slow synthesis usually = complex design
        """)

with trouble_cols[1]:
    with st.expander("❓ Where do I find results?"):
        st.markdown("""
        **Results are in:**
        1. `runs/` directory (disk)
        2. 🎯 Results Dashboard (web UI)
        3. Each stage subdirectory
        4. `09_tapeout/` for deliverables
        
        **All outputs auto-organized**
        by the pipeline
        """)
    
    with st.expander("🚀 How do I iterate?"):
        st.markdown("""
        **Standard workflow:**
        1. Write design in ✏️ Studio
        2. Run pipeline (🚀 button)
        3. Check results (🎯 Dashboard)
        4. Fix issues
        5. Repeat
        
        Each run creates new directory
        with timestamp automatically
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📌 Example: Complete Workflow")

with st.container(border=True):
    st.markdown("""
    ### Example: Design a 4-bit Counter
    
    **1️⃣ Go to ✏️ Custom Design Studio**
    - Select template: "Simple Counter"
    - Modify: Change to 4-bit (8-bit → 4-bit)
    - Design name: `counter_4bit`
    
    **2️⃣ Run Pipeline** 🚀
    - Click "Run Pipeline"
    - Watch progress in real-time
    - Whole flow takes ~15-20 seconds
    
    **3️⃣ View Results** 🎯
    - Go to 🎯 Results Dashboard
    - Select run: `counter_4bit_20260326_181200`
    - Explore each tab:
      - **📊 Summary** → See RTL stats, timing
      - **📁 Files** → Download all outputs
      - **📈 Timeline** → Which stages take time
      - **✅ Sign-off** → DRC/LVS results
      - **📦 Deliverables** → GDS + everything
    
    **4️⃣ Download & Use**
    - Get GDSII file from 📦 Deliverables
    - Use netlist for simulation
    - All ready for fab submission!
    """)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGES OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📑 Complete Page Map")

nav_table = """
| Page | Purpose | Key Action |
|------|---------|-----------|
| 🏠 Home | Overview of platform | Learn about RTL-Gen |
| ✏️ Custom Design | Write & run custom designs | Create your GDS |
| 📜 History | Browse past designs | See what was built |
| 📖 Documentation | Guides & references | Learn platform |
| 🚀 Physical Design | Run pre-configured flows | Quick start designs |
| 🎯 Results Dashboard | View all outputs | Analyze results |
| 🔄 Workflow | Integration guide | You are here! |
"""

st.markdown(nav_table)

st.divider()
st.success("""
✅ **Now ready to design!**

1. Go to ✏️ **Custom Design Studio**
2. Write your Verilog
3. Click 🚀 **Run Pipeline**
4. View results in 🎯 **Results Dashboard**

Everything is integrated. Just write code and run!
""")
