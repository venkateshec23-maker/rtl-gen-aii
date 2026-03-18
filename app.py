"""
RTL-Gen AI Web Application
Main Streamlit interface for RTL code generation.

Run with: streamlit run app.py
"""

import streamlit as st
from pathlib import Path

# Page config
st.set_page_config(
    page_title="RTL-Gen AI",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-size: 1.2rem;
        padding: 0.75rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">🔧 RTL-Gen AI</div>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Generate Professional Verilog Code from Natural Language</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # LLM Settings
    st.subheader("LLM Configuration")
    use_mock = st.checkbox("Use Mock LLM (Free)", value=True, help="Use mock LLM for testing without API costs")
    
    if not use_mock:
        api_key = st.text_input("Anthropic API Key", type="password", help="Your Anthropic API key")
        model = st.selectbox("Model", ["claude-sonnet-4-20250514", "claude-opus-4-20250514"])
    
    # Verification Settings
    st.subheader("Verification")
    enable_verification = st.checkbox("Enable Verification", value=True, help="Compile and simulate generated code")
    enable_waveforms = st.checkbox("Generate Waveforms", value=True, help="Create VCD waveform files")
    
    # Advanced Settings
    with st.expander("🔬 Advanced"):
        temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1, help="LLM creativity (lower = more consistent)")
        max_tokens = st.slider("Max Tokens", 1000, 8000, 4000, 500, help="Maximum response length")
        auto_generate_tb = st.checkbox("Auto-generate Testbench", value=True, help="Generate testbench if LLM doesn't provide one")

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Describe Your Design")
    
    # Input methods
    input_method = st.radio("Input Method", ["Text Description", "Load Example", "Upload Specification"])
    
    if input_method == "Text Description":
        description = st.text_area(
            "Design Description",
            placeholder="Example: Create an 8-bit ALU with ADD, SUB, AND, OR, XOR operations...",
            height=200,
            help="Describe your digital circuit in natural language"
        )
    
    elif input_method == "Load Example":
        example = st.selectbox(
            "Select Example",
            ["4-bit Adder", "8-bit Counter", "4-bit ALU", "8-bit Register", "4-to-1 Multiplexer"]
        )
        
        examples = {
            "4-bit Adder": "Create a 4-bit adder with carry-in and carry-out",
            "8-bit Counter": "Design an 8-bit counter with synchronous reset, enable, and load",
            "4-bit ALU": "Build a 4-bit ALU with operations: ADD, SUB, AND, OR, XOR",
            "8-bit Register": "Implement an 8-bit register with clock, reset, and enable",
            "4-to-1 Multiplexer": "Create a 4-to-1 multiplexer with 8-bit data inputs"
        }
        
        description = st.text_area("Design Description", value=examples[example], height=200)
    
    else:  # Upload
        uploaded_file = st.file_uploader("Upload Specification (.txt, .md)", type=['txt', 'md'])
        if uploaded_file:
            description = uploaded_file.read().decode('utf-8')
            st.text_area("Design Description", value=description, height=200)
        else:
            description = ""
    
    # Generate button
    generate_button = st.button("🚀 Generate RTL Code", type="primary", use_container_width=True)

with col2:
    st.subheader("📊 Generation Status")
    status_placeholder = st.empty()
    progress_placeholder = st.empty()

# Results area (below)
if generate_button and description:
    # Import here to avoid slow startup
    from python.input_processor import InputProcessor
    from python.prompt_builder import PromptBuilder
    from python.llm_client import LLMClient
    from python.extraction_pipeline import ExtractionPipeline
    from python.verification_engine import VerificationEngine
    
    # Initialize components
    processor = InputProcessor(debug=False)
    builder = PromptBuilder(debug=False)
    client = LLMClient(use_mock=use_mock)
    extractor = ExtractionPipeline(debug=False)
    
    # Progress tracking
    progress_bar = progress_placeholder.progress(0)
    status_text = status_placeholder.empty()
    
    try:
        # Step 1: Parse (20%)
        status_text.info("🔍 Parsing description...")
        progress_bar.progress(20)
        parsed = processor.parse_description(description)
        
        if not parsed['valid']:
            st.error(f"❌ Invalid description: {parsed['errors']}")
            st.stop()
        
        # Step 2: Build prompt (40%)
        status_text.info("📝 Building prompt...")
        progress_bar.progress(40)
        prompt = builder.build_prompt(parsed)
        
        # Step 3: Generate (60%)
        status_text.info("🤖 Generating RTL code...")
        progress_bar.progress(60)
        response = client.generate(prompt)
        
        # Step 4: Extract (80%)
        status_text.info("✂️ Extracting and formatting code...")
        progress_bar.progress(80)
        extraction = extractor.process(response['content'] if isinstance(response, dict) and 'content' in response else str(response), description=description)
        
        if not extraction['success']:
            st.error(f"❌ Extraction failed: {extraction['errors']}")
            st.stop()
        
        # Step 5: Verify (100%)
        if enable_verification:
            status_text.info("✔️ Verifying design...")
            progress_bar.progress(90)
            
            verifier = VerificationEngine(debug=False)
            verification = verifier.verify(
                extraction['rtl_code'],
                extraction['testbench_code'],
                module_name=extraction['module_name']
            )
        else:
            verification = None
        
        progress_bar.progress(100)
        status_text.success("✅ Generation complete!")
        
        # Display results
        st.markdown("---")
        st.header("📦 Generated Design")
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📄 RTL Code", "🧪 Testbench", "✔️ Verification", "📊 Details"])
        
        with tab1:
            st.subheader(f"Module: {extraction['module_name']}")
            st.code(extraction['rtl_code'], language='verilog')
            st.download_button(
                "⬇️ Download RTL",
                extraction['rtl_code'],
                file_name=f"{extraction['module_name']}.v",
                mime="text/plain"
            )
        
        with tab2:
            st.subheader(f"Testbench: {extraction['testbench_name']}")
            st.code(extraction['testbench_code'], language='verilog')
            st.download_button(
                "⬇️ Download Testbench",
                extraction['testbench_code'],
                file_name=f"{extraction['testbench_name']}.v",
                mime="text/plain"
            )
        
        with tab3:
            if verification:
                if verification['passed']:
                    st.success("✅ Verification PASSED")
                else:
                    st.error("❌ Verification FAILED")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Compilation", "✓ Pass" if verification['compilation_passed'] else "✗ Fail")
                with c2:
                    st.metric("Simulation", "✓ Pass" if verification['simulation_passed'] else "✗ Fail")
                with c3:
                    st.metric("Tests", f"{verification['tests_passed']}/{verification['total_tests']}")
                
                if verification['errors']:
                    with st.expander("❌ Errors", expanded=True):
                        for error in verification['errors']:
                            st.error(error)
                
                if getattr(extraction, 'warnings', []):
                    with st.expander("⚠️ Warnings"):
                        for warning in extraction['warnings']:
                            st.warning(warning)
                
                if verification['simulation_output']:
                    with st.expander("📋 Simulation Output"):
                        st.code(verification['simulation_output'])
                
                if verification.get('waveform_file'):
                    st.info(f"📊 Waveform: {verification['waveform_file']}")
            else:
                st.info("Verification disabled")
        
        with tab4:
            st.json({
                'module_name': extraction['module_name'],
                'component_type': parsed.get('component_type', 'unknown'),
                'bit_width': parsed.get('bit_width', 'unknown'),
                'rtl_length': len(extraction['rtl_code']),
                'tb_length': len(extraction['testbench_code']),
                'has_warnings': len(extraction.get('warnings', [])) > 0,
                'verified': verification['passed'] if verification else None,
            })
    
    except Exception as e:
        status_text.error(f"❌ Error: {e}")
        st.exception(e)

elif generate_button:
    st.warning("⚠️ Please enter a design description")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>RTL-Gen AI v1.0 | Built with ❤️ using Anthropic Claude (or Deepseek)</p>
</div>
""", unsafe_allow_html=True)
