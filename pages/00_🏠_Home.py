"""
🏭 RTL-Gen AI - AI-Powered RTL to GDSII Pipeline
Complete integrated platform for chip design
"""

import streamlit as st
from pathlib import Path
import sys

st.set_page_config(
    page_title="RTL-Gen AI Platform",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 RTL-Gen AI Platform")
st.markdown("**From Prompt or Code to Silicon** — Complete RTL→GDSII Pipeline")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ═══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs(["🚀 Get Started", "📖 How It Works", "🎯 Example"])

with tab1:
    st.subheader("🚀 Start Your Design Journey")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## Two Ways to Create
        
        ### Option 1: Write Custom Verilog ✏️
        1. Go to **✏️ Custom Design Studio** (sidebar)
        2. Write or paste Verilog code
        3. Click **🚀 Run Pipeline**
        4. Watch real-time execution
        5. View results in **🎯 Results Dashboard**
        
        ### Option 2: Use Templates 🎨
        Choose from pre-built designs:
        - ✅ Simple Counter
        - ✅ 8-bit Adder
        - ✅ Traffic Light Controller
        - ✅ Multiplexer (4-to-1)
        
        ### Option 3: AI from Prompt 💡 (LIVE NOW!)
        1. Go to **3️⃣ AI Code Generation** (sidebar)
        2. Describe your circuit (e.g., "8-bit counter with clock and reset")
        3. Click **🚀 Generate Code**
        4. Review generated Verilog
        5. Click **🚀 Run Pipeline** to synthesize
        """)
    
    with col2:
        st.info("""
        ### ⚡ Quick Facts
        
        **Speed:** ~20 seconds per design
        
        **Output:** Complete GDS file
        
        **Stages:** 9 automated stages
        
        **Verification:** DRC + LVS checks
        
        **Download:** All files available
        
        ### 🎯 Your First Step
        
        Click **✏️ Custom Design Studio**
        in the sidebar →
        """)

with tab2:
    st.subheader("📖 How the Pipeline Works")
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("""
        ### 9-Stage Automated Pipeline
        
        1. **RTL Input** — Your Verilog code
        2. **Synthesis** (Yosys) — RTL → Gate-level netlist
        3. **Floorplanning** — Define chip area
        4. **Placement** (OpenROAD) — Position cells
        5. **Clock Tree** (CTS) — Build clock network
        6. **Routing** — Connect all nets
        7. **GDS Generation** — Final layout file
        8. **DRC Check** (Magic) — Design rule verification
        9. **LVS Check** (Netgen) — Layout vs Schematic
        10. **Tape-out** — Professional package
        
        ### Output Structure
        Every run creates an organized directory:
        ```
        runs/design_20260326_181200/
        ├── 01_rtl/          Your code
        ├── 02_synthesis/    Netlist
        ├── 03_floorplan/    Core area
        ├── 04_placement/    Cell positions
        ├── 05_cts/          Clock tree
        ├── 06_routing/      Routed nets
        ├── 07_gds/          Layout file ✅
        ├── 08_signoff/      Verification
        └── 09_tapeout/      Deliverables
        ```
        """)
    
    with col2:
        st.metric("Total Stages", "9+1")
        st.metric("Avg Time", "~20s")
        st.metric("Technology", "Sky130A (130nm)")
        st.metric("Docker", "Automated")

with tab3:
    st.subheader("🎯 Live Example: Traffic Light Controller")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.code("""// Traffic Light Controller
module traffic_controller (
    input clk, reset, enable,
    output reg red, green, yellow
);
    localparam RED = 30M, GREEN = 25M, YELLOW = 5M;
    reg [1:0] state;
    reg [27:0] timer;
    
    always @(posedge clk) begin
        if (reset) state <= RED;
        else case (state)
            RED: if (timer == 0) state <= GREEN;
            GREEN: if (timer == 0) state <= YELLOW;
            YELLOW: if (timer == 0) state <= RED;
        endcase
    end
endmodule""", language="verilog")
    
    with col2:
        st.success("✅ Status: Ready")
        st.info("""
        **Results Available:**
        - GDS file: 212 bytes
        - DRC: 0 violations
        - LVS: Matched
        - Complete tape-out package
        
        **View in Results Dashboard:**
        Run name: `traffic_controller_...`
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# NAVIGATION CARDS
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("🗺️ Platform Pages")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown("### ✏️ Custom Design Studio")
        st.markdown("""
        **What:** Write & run designs
        **How:** Code editor + Run button
        **Output:** Full pipeline execution
        """)

with col2:
    with st.container(border=True):
        st.markdown("### 🎯 Results Dashboard")
        st.markdown("""
        **What:** View all outputs
        **How:** Browse 6 tabs per run
        **Output:** Metrics, files, data
        """)

with col3:
    with st.container(border=True):
        st.markdown("### 🔄 Workflow")
        st.markdown("""
        **What:** Integration guide
        **How:** Visual architecture
        **Output:** Understanding flow
        """)

with col4:
    with st.container(border=True):
        st.markdown("### 📖 Documentation")
        st.markdown("""
        **What:** Detailed guides
        **How:** Step-by-step docs
        **Output:** Learning resources
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📝 Input", "Verilog RTL")
with col2:
    st.metric("⚙️ Stages", "9 automated")
with col3:
    st.metric("📤 Output", "GDS + reports")
with col4:
    st.metric("⏱️ Speed", "~20 seconds")

# ═══════════════════════════════════════════════════════════════════════════════
# AI CODE GENERATION FEATURE
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()

st.subheader("🤖 AI Code Generation (NEW!)")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    **Generate Verilog from Plain English!**
    
    Instead of writing code, just describe what you want:
    - "8-bit counter with clock and reset"
    - "4-to-1 multiplexer"
    - "State machine with 3 states"
    
    The AI generates synthesis-ready Verilog automatically!
    """)

with col2:
    st.info("""
    **How to Use:**
    1. Click **3️⃣ AI Code Generation** (sidebar)
    2. Describe your circuit
    3. Click **Generate Code**
    4. Review & **Run Pipeline**
    """)

# ═══════════════════════════════════════════════════════════════════════════════
# QUICK START
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()

st.success("""
### 🚀 Ready to Design?

Everything is integrated — from code to silicon! ✨
""")

# ═══════════════════════════════════════════════════════════════════════════════
# NAVIGATION GUIDE
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()

st.subheader("🔗 Navigation Guide")

st.info("""
👈 **Use the sidebar to navigate to any page:**

**Main Pages:**
- ✏️ **Custom Design Studio** - Write and run your Verilog code
- 🤖 **AI Code Generation** - Generate Verilog from descriptions
- 🎯 **Results Dashboard** - View outputs and metrics

**Reference Pages:**
- 📖 **Documentation** - Step-by-step guides
- 🔄 **Workflow** - Integration architecture
- 📜 **History** - Design history and saved runs
- 📋 **Physical Design Flow** - Pre-configured design flows
""")


