"""
RTL-Gen AI - Complete Production Version
Phases 1-3: LLM + Waveforms + Synthesis
"""

import streamlit as st
import sys
from pathlib import Path
import tempfile
import base64

# Add python directory to path
sys.path.append(str(Path(__file__).parent))

# Phase 1: LLM
from python.llm_client import LLMClient

# Phase 2: Waveforms
from python.waveform_generator import WaveformGenerator
from python.testbench_generator import TestbenchGenerator

# Phase 3: Synthesis
from python.synthesis_engine import SynthesisEngine
from python.synthesis_visualizer import SynthesisVisualizer

# Page config
st.set_page_config(
    page_title="RTL-Gen AI - Complete",
    page_icon="🔷",
    layout="wide"
)

# Initialize session state
if 'generated_code' not in st.session_state:
    st.session_state.generated_code = None
if 'testbench_code' not in st.session_state:
    st.session_state.testbench_code = None
if 'waveform_result' not in st.session_state:
    st.session_state.waveform_result = None
if 'synthesis_result' not in st.session_state:
    st.session_state.synthesis_result = None
if 'synthesis_report' not in st.session_state:
    st.session_state.synthesis_report = None

# Sidebar
with st.sidebar:
    st.title("🔧 RTL-Gen AI")
    st.markdown("### Production Ready v1.0")
    
    st.divider()
    
    # Phase 1: LLM Configuration
    st.subheader("🤖 Phase 1: LLM Provider")
    
    provider = st.selectbox(
        "Select Provider",
        ["mock", "grok", "anthropic", "deepseek"],
        help="Mock = Free (no API), Grok = Fast & Free, Anthropic = Claude, DeepSeek = Free tier"
    )
    
    api_key = None
    if provider != "mock":
        api_key = st.text_input(
            f"Enter {provider.title()} API Key",
            type="password",
            help=f"Get your key from {provider}.com"
        )
    
    if provider == "anthropic":
        model = st.selectbox(
            "Claude Model",
            ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-sonnet-20241022"]
        )
    elif provider == "grok":
        model = st.selectbox(
            "Grok Model",
            ["mixtral-8x7b-32768", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
            help="Mixtral is fastest, Llama 70B is most accurate"
        )
    else:
        model = "deepseek-chat" if provider == "deepseek" else None
    
    st.divider()
    
    # Phase 2: Waveform Settings
    st.subheader("📊 Phase 2: Waveforms")
    generate_waveforms = st.checkbox("Auto-generate waveforms", value=True)
    
    st.divider()
    
    # Phase 3: Synthesis Settings
    st.subheader("🔧 Phase 3: Synthesis")
    enable_synthesis = st.checkbox("Enable synthesis", value=True)
    
    tech_library = st.selectbox(
        "Target Technology",
        ["asic", "fpga"],
        help="ASIC = Standard cells, FPGA = LUTs/FFs"
    )
    
    st.divider()
    
    # Quick Info
    st.markdown("""
    ### ✅ System Ready
    - Phase 1: LLM Providers
    - Phase 2: Waveforms
    - Phase 3: Synthesis
    
    [Documentation](docs/)
    """)

# Main content
st.title("🔷 RTL-Gen AI - Complete")
st.markdown("### Generate → Simulate → Synthesize")

# Input section
col1, col2 = st.columns([3, 1])
with col1:
    prompt = st.text_area(
        "Describe your digital design:",
        height=100,
        placeholder="Example: Create an 8-bit adder with carry in and carry out",
        help="Be specific about bit widths and features"
    )
with col2:
    st.markdown("### Examples")
    if st.button("8-bit Adder"):
        prompt = "Create an 8-bit adder with carry in and carry out"
    if st.button("16-bit Counter"):
        prompt = "Create a 16-bit counter with reset and enable"
    if st.button("4-bit ALU"):
        prompt = "Create a 4-bit ALU with add, sub, and, or operations"

# Generate button
col1, col2 = st.columns([1, 5])
with col1:
    generate_clicked = st.button("🚀 Generate", type="primary", use_container_width=True)

if generate_clicked and prompt:
    with st.spinner("Generating RTL code..."):
        try:
            # Phase 1: LLM Generation
            if provider == "mock" or not api_key:
                client = LLMClient(use_mock=True)
                st.info("Using Mock LLM (free, no API key)")
            else:
                client = LLMClient(
                    provider=provider,
                    api_key=api_key,
                    model=model
                )
            
            response = client.generate(prompt)
            code_blocks = client.extract_code(response)
            
            if code_blocks:
                st.session_state.generated_code = code_blocks[0]
                st.session_state.testbench_code = code_blocks[1] if len(code_blocks) > 1 else None
                
                # Phase 2: Auto-generate testbench if not present
                if not st.session_state.testbench_code:
                    tb_gen = TestbenchGenerator()
                    st.session_state.testbench_code = tb_gen.generate(st.session_state.generated_code)
                
                st.success("✅ RTL code generated successfully!")
            else:
                st.error("No code blocks found in response")
                st.code(response['content'], language='text')
        
        except Exception as e:
            st.error(f"Generation failed: {str(e)}")

# Display results with all 4 tabs
if st.session_state.generated_code:
    tab1, tab2, tab3, tab4 = st.tabs([
        "📄 RTL Code (Phase 1)",
        "🧪 Testbench (Phase 2)", 
        "📊 Waveforms (Phase 2)",
        "🔧 Synthesis (Phase 3)"
    ])
    
    # Tab 1: RTL Code
    with tab1:
        st.markdown("### Generated RTL Module")
        st.code(st.session_state.generated_code, language="verilog")
        
        st.download_button(
            label="📥 Download RTL",
            data=st.session_state.generated_code,
            file_name="rtl_module.v",
            mime="text/plain"
        )
    
    # Tab 2: Testbench
    with tab2:
        if st.session_state.testbench_code:
            st.markdown("### Generated Testbench")
            st.code(st.session_state.testbench_code, language="verilog")
            
            st.download_button(
                label="📥 Download Testbench",
                data=st.session_state.testbench_code,
                file_name="testbench.v",
                mime="text/plain"
            )
        else:
            st.info("No testbench generated")
    
    # Tab 3: Waveforms
    with tab3:
        st.markdown("### Waveform Generation")
        
        if generate_waveforms and st.session_state.testbench_code:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🎬 Generate VCD Waveform", use_container_width=True):
                    with st.spinner("Generating waveform..."):
                        wf_gen = WaveformGenerator(output_dir='outputs/waveforms')
                        result = wf_gen.generate_from_testbench(
                            st.session_state.testbench_code,
                            'design_tb'
                        )
                        st.session_state.waveform_result = result
            
            with col2:
                if st.session_state.waveform_result and st.session_state.waveform_result.get('success'):
                    with open(st.session_state.waveform_result['vcd_file'], 'rb') as f:
                        st.download_button(
                            label="📥 Download VCD",
                            data=f,
                            file_name=Path(st.session_state.waveform_result['vcd_file']).name,
                            mime="text/plain",
                            use_container_width=True
                        )
            
            # Display waveform results
            if st.session_state.waveform_result:
                result = st.session_state.waveform_result
                
                if result['success']:
                    st.success("✅ Waveform generated!")
                    
                    # Import and use the new render function
                    from python.waveform_generator import render_waveform_in_streamlit
                    
                    # Render inline waveform with matplotlib
                    render_waveform_in_streamlit(result)
                    
                    # Optional: Show raw VCD preview
                    with st.expander("📄 Raw VCD Preview"):
                        with open(result['vcd_file'], 'r') as f:
                            st.code(f.read()[:2000], language="text")
                    
                else:
                    st.error(f"Waveform failed: {result.get('error')}")
        else:
            st.info("Generate RTL code first to enable waveforms")
    
    # Tab 4: Synthesis
    with tab4:
        st.markdown("### RTL Synthesis")
        
        if enable_synthesis:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔧 Run Synthesis", use_container_width=True):
                    with st.spinner("Running synthesis..."):
                        synth_engine = SynthesisEngine(
                            output_dir='outputs/synthesis',
                            tech_library=tech_library
                        )
                        st.session_state.synthesis_result = synth_engine.synthesize(
                            st.session_state.generated_code
                        )
                        
                        if st.session_state.synthesis_result.get('success'):
                            viz = SynthesisVisualizer()
                            st.session_state.synthesis_report = viz.generate_full_report(
                                st.session_state.synthesis_result
                            )
            
            with col2:
                if st.session_state.synthesis_report:
                    st.download_button(
                        label="📥 Download HTML Report",
                        data=st.session_state.synthesis_report,
                        file_name="synthesis_report.html",
                        mime="text/html",
                        use_container_width=True
                    )
            
            # Display synthesis results
            if st.session_state.synthesis_result:
                result = st.session_state.synthesis_result
                
                if result['success']:
                    st.success("✅ Synthesis completed!")
                    
                    # Metrics
                    stats = result.get('stats', {})
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if 'area' in stats:
                            unit = 'µm²' if tech_library == 'asic' else 'LUTs'
                            st.metric("Area", f"{stats['area']:.1f} {unit}")
                    
                    with col2:
                        if 'power' in stats:
                            unit = 'µW/MHz' if tech_library == 'asic' else 'mW'
                            st.metric("Power", f"{stats['power']:.3f} {unit}")
                    
                    with col3:
                        if 'frequency' in stats:
                            st.metric("Max Freq", f"{stats['frequency']:.1f} MHz")
                    
                    with col4:
                        if 'total_cells' in stats:
                            st.metric("Total Cells", stats['total_cells'])
                    
                    # Cell distribution
                    if 'cells' in stats and stats['cells']:
                        with st.expander("📊 Cell Distribution"):
                            cells = stats['cells']
                            for cell, count in cells.items():
                                st.text(f"{cell}: {count}")
                    
                    # Netlist preview
                    if result.get('netlist'):
                        with st.expander("🔍 Netlist Preview"):
                            st.code(result['netlist'][:1000] + "...", language="verilog")
                            
                            st.download_button(
                                label="📥 Download Netlist",
                                data=result['netlist'],
                                file_name=f"{result['top_module']}_netlist.v",
                                mime="text/plain"
                            )
                    
                    # Simulator info
                    st.info(f"⚡ Simulator: {result.get('simulator', 'unknown').upper()}")
                    
                else:
                    st.error(f"Synthesis failed: {result.get('error')}")
        else:
            st.info("Enable synthesis in sidebar to generate gate-level netlists")

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center'>
        <p>🚀 RTL-Gen AI v1.0 | All 3 Phases Complete | Production Ready ✅</p>
        <p style='font-size: 0.8em; color: gray;'>
            Phase 1: LLM • Phase 2: Waveforms • Phase 3: Synthesis
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
