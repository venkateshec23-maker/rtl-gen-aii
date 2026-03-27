"""
Streamlit Page: AI Code Generation with OpenCode

Natural language to Verilog RTL generation using OpenCode AI.
"""

import streamlit as st
import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from opencode_integration import (
    OpenCodeGenerator, 
    generate_rtl_from_description,
    extract_module_name_from_text
)

st.set_page_config(
    page_title="AI Code Generation",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Code Generation with OpenCode")

# Initialize session state
if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""
if "opencode_available" not in st.session_state:
    gen = OpenCodeGenerator()
    st.session_state.opencode_available = gen.opencode_available

# Status indicator
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### Generate Verilog RTL from Natural Language")
with col2:
    status_color = "🟢" if st.session_state.opencode_available else "🔴"
    st.markdown(f"{status_color} **OpenCode**: {'Available' if st.session_state.opencode_available else 'Not Installed'}")

st.divider()

if not st.session_state.opencode_available:
    st.warning("""
    ### OpenCode is not installed
    
    Install OpenCode to enable AI code generation:
    ```bash
    npm install -g opencode-ai@latest
    ```
    
    Or download from: https://opencode.ai/download
    """)
    st.info("Once installed, refresh this page to use AI generation features.")
else:
    # Main interface
    st.success("✅ OpenCode is ready! Describe your circuit and let AI generate the Verilog code.")
    
    st.subheader("Describe Your Circuit")
    
    # Example templates
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 Suggested Design Types"):
            st.markdown("""
            - **Counter**: n-bit counter with clock, reset, enable
            - **Shift Register**: Parallel-in/Serial-out (PISO) shift register
            - **Multiplexer**: 4-to-1 or 8-to-1 MUX with select lines
            - **Decoder**: Binary to one-hot decoder with enable
            - **Comparator**: Magnitude comparator (LT, EQ, GT)
            - **Adder**: Ripple carry or carry lookahead adder
            - **State Machine**: FSM with specific states and transitions
            - **Memory Interface**: Simple RAM controller
            """)
    
    with col2:
        if st.button("💡 Example Descriptions"):
            st.markdown("""
            *"Create an 8-bit binary counter with active-high reset"*
            
            *"Design a 16-bit shift register with parallel load"*
            
            *"Implement a 4-to-1 multiplexer for 8-bit data"*
            
            *"Build a 4-bit magnitude comparator"*
            """)
    
    st.divider()
    
    # Input section
    description = st.text_area(
        "Circuit Description",
        placeholder="Example: Create a 4-bit binary counter with:\n- Clock input (clk)\n- Active-high reset (rst)\n- Enable signal (en)\n- 4-bit output (count)",
        height=120
    )
    
    # Configuration options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        module_name = st.text_input(
            "Module Name",
            value=extract_module_name_from_text(description) if description else "my_design",
            placeholder="Generated module name"
        )
    
    with col2:
        data_width = st.slider("Data Width (bits)", min_value=1, max_value=32, value=8)
    
    with col3:
        style = st.selectbox(
            "Implementation Style",
            ["behavioral", "dataflow", "structural"]
        )
    
    st.divider()
    
    # Generate button
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🚀 Generate Verilog", key="gen_button"):
            if not description.strip():
                st.error("❌ Please describe your circuit first")
            else:
                with st.spinner("🔄 Generating Verilog code..."):
                    gen = OpenCodeGenerator()
                    success, code, message = gen.generate_verilog(
                        description=description,
                        module_name=module_name,
                        width=data_width,
                        style=style
                    )
                    
                    if success:
                        st.session_state.generated_code = code
                        st.success(message)
                    else:
                        st.error(f"❌ {message}")
    
    with col2:
        if st.button("🧹 Clear", key="clear_button"):
            st.session_state.generated_code = ""
            st.rerun()
    
    # Display generated code
    if st.session_state.generated_code:
        st.subheader("Generated Verilog Code")
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col2:
            if st.button("📋 Copy to Clipboard"):
                st.info("Code copied! (Use Ctrl+C from the code block)")
        
        with col3:
            if st.button("💾 Save as File"):
                st.session_state.save_pending = True
        
        st.code(st.session_state.generated_code, language="verilog")
        
        # Code analysis section
        st.divider()
        st.subheader("Analysis & Optimization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Analyze Code", key="analyze_btn"):
                with st.spinner("Analyzing..."):
                    gen = OpenCodeGenerator()
                    success, analysis = gen.analyze_verilog(st.session_state.generated_code)
                    if success:
                        st.info(analysis)
                    else:
                        st.error(f"Analysis failed: {analysis}")
        
        with col2:
            if st.button("⚡ Optimize for Speed/Area", key="optimize_btn"):
                with st.spinner("Optimizing..."):
                    gen = OpenCodeGenerator()
                    success, optimized, msg = gen.optimize_design(st.session_state.generated_code)
                    if success:
                        st.session_state.generated_code = optimized
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(f"Optimization failed: {msg}")
        
        # Integration options
        st.divider()
        st.subheader("Next Steps")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ Run Through Pipeline", key="pipeline_btn"):
                st.info("Navigate to **Custom Design** page to run this code through the full RTL→GDSII pipeline")
        
        with col2:
            if st.button("📄 Insert into Custom Design", key="insert_btn"):
                st.session_state.custom_verilog = st.session_state.generated_code
                st.session_state.custom_module_name = module_name
                st.success("✅ Code saved to Custom Design page!")


# Sidebar: Quick reference
with st.sidebar:
    st.markdown("### 💡 Quick Tips")
    st.markdown("""
    **Best Practices for Descriptions:**
    
    1. **Be Specific**
       - Specify bit widths
       - Mention clock/reset behavior
    
    2. **Include Details**
       - What signals needed
       - Synchronous or combinational
       - Expected functionality
    
    3. **Use Examples**
       - "8-bit counter that increments on clock"
       - "2-to-1 multiplexer with 32-bit inputs"
    
    **Code Quality Tips:**
    
    - Generated code is synthesis-ready
    - Review for your specific PDK
    - Test on simple designs first
    - Use Analyze to get suggestions
    """)
    
    st.divider()
    
    st.markdown("### 📚 Resources")
    st.markdown("""
    - [OpenCode Docs](https://opencode.ai/docs)
    - [Verilog Guide](https://www.verilog.com)
    - [RTL Best Practices](https://www.digitaldesign.org)
    """)
