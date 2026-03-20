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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📄 RTL Code (Phase 1)",
        "🧪 Testbench (Phase 2)", 
        "📊 Waveforms (Phase 2)",
        "🎨 Pro Waveforms",
        "🔧 Synthesis (Phase 3)",
        "🔌 Netlist Diagram"
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
            
            # Extract module name from RTL code
            import re
            module_name = "design"
            if st.session_state.generated_code:
                match = re.search(r'module\s+(\w+)', st.session_state.generated_code)
                if match:
                    module_name = match.group(1)
            
            with col1:
                if st.button("🎬 Generate VCD Waveform", use_container_width=True):
                    with st.spinner("Generating waveform..."):
                        wf_gen = WaveformGenerator(output_dir='outputs/waveforms')
                        result = wf_gen.generate_from_testbench(
                            st.session_state.testbench_code,
                            module_name
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
        
        if enable_synthesis and st.session_state.generated_code:
            # Extract module name
            import re
            module_name = "design"
            match = re.search(r'module\s+(\w+)', st.session_state.generated_code)
            if match:
                module_name = match.group(1)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔧 Run Synthesis", use_container_width=True):
                    with st.spinner("Running synthesis..."):
                        synth_engine = SynthesisEngine(
                            output_dir='outputs/synthesis',
                            tech_library=tech_library
                        )
                        st.session_state.synthesis_result = synth_engine.synthesize(
                            st.session_state.generated_code,
                            top_module=module_name
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
    
    # Tab 5: Professional Waveforms
    with tab5:
        st.markdown("### 🎨 Professional Timing Diagrams")
        
        if st.session_state.waveform_result and st.session_state.waveform_result.get('success'):
            try:
                # Extract module name
                import re
                module_name = "design"
                if st.session_state.generated_code:
                    match = re.search(r'module\s+(\w+)', st.session_state.generated_code)
                    if match:
                        module_name = match.group(1)
                
                from python.waveform_professional import ProfessionalWaveformPlot
                
                result = st.session_state.waveform_result
                viz_data = result.get('visualization', {})
                signals = viz_data.get('signals', [])
                time_points = viz_data.get('time_points', [])
                values = viz_data.get('values', {})
                if signals and time_points:
                    # Create professional plot
                    prof_plot = ProfessionalWaveformPlot(width=14, height=max(8, len(signals) * 1.5))
                    
                    # Filter signals to 8 for clarity
                    filtered_signals = {s: values.get(s, []) for s in signals[:8] if s in values}
                    
                    if filtered_signals:
                        fig = prof_plot.create_waveform_plot(
                            signals=filtered_signals,
                            time_points=time_points,
                            title=f"Professional Timing Diagram - {module_name}"
                        )
                        
                        if fig:
                            st.pyplot(fig)
                            
                            # Export option
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if st.button("💾 Save as PNG", key="save_waveform_png"):
                                    output_dir = Path('outputs/waveforms')
                                    output_dir.mkdir(parents=True, exist_ok=True)
                                    filename = str(output_dir / f"{module_name}_timing_diagram.png")
                                    prof_plot.export_to_image(fig, filename, dpi=300)
                                    st.success(f"✅ Saved to {filename}")
                            
                            with col2:
                                if st.button("📊 Export Bus Signals", key="export_bus"):
                                    # Try to extract bus signals
                                    bus_sigs = [s for s in signals if any(x in s.lower() for x in ['bus', 'data', 'addr'])]
                                    if bus_sigs:
                                        fig_bus = prof_plot.create_bus_waveform(
                                            signals=filtered_signals,
                                            time_points=time_points,
                                            bus_signals=bus_sigs,
                                            title="Bus Signals"
                                        )
                                        if fig_bus:
                                            st.pyplot(fig_bus)
                                            st.info(f"Bus signals: {', '.join(bus_sigs)}")
                            
                            with col3:
                                st.metric("Signals", len(signals))
                        else:
                            st.warning("Could not generate professional waveform plot")
                    else:
                        st.warning("No signal data available for professional plotting")
                else:
                    st.warning("Incomplete waveform data - generate waveform first")
                    
            except ImportError as e:
                st.error(f"professional waveform module not available: {e}")
            except Exception as e:
                st.error(f"Error generating professional waveform: {e}")
        else:
            st.info("📊 Generate a waveform in the Waveforms tab first")
    
    # Tab 6: Netlist Diagram
    with tab6:
        st.markdown("### 🔌 Gate-Level Netlist Visualization")
        
        if st.session_state.synthesis_result and st.session_state.synthesis_result.get('netlist'):
            try:
                # Extract module name
                import re
                module_name = st.session_state.synthesis_result.get('top_module', 'design')
                if not module_name or module_name == 'design':
                    if st.session_state.generated_code:
                        match = re.search(r'module\s+(\w+)', st.session_state.generated_code)
                        if match:
                            module_name = match.group(1)
                
                from python.netlist_visualizer import NetlistVisualizer
                
                result = st.session_state.synthesis_result
                netlist = result.get('netlist', '')
                
                if netlist:
                    # Create visualizer
                    viz = NetlistVisualizer()
                    viz.parse_netlist(netlist)
                    
                    # Get statistics
                    stats = viz.get_statistics()
                    
                    # Display statistics
                    st.markdown("#### 📊 Netlist Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Gates", stats['total_gates'])
                    with col2:
                        st.metric("Gate Types", len(stats['gate_types']))
                    with col3:
                        st.metric("Signals", stats['total_signals'])
                    with col4:
                        st.metric("Connections", stats['total_connections'])
                    
                    # Gate type breakdown
                    if stats['gate_types']:
                        st.markdown("#### Gate Type Breakdown")
                        cols = st.columns(min(3, len(stats['gate_types'])))
                        for idx, (gate_type, count) in enumerate(stats['gate_types'].items()):
                            cols[idx % 3].metric(gate_type, count)
                    
                    # Drawing options
                    st.markdown("#### 📐 Visualization Options")
                    draw_layout = st.selectbox(
                        "Layout Algorithm",
                        ["hierarchical", "spring", "circular"],
                        help="Choose visualization layout"
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("🎨 Draw Netlist Diagram", use_container_width=True):
                            with st.spinner("Generating netlist diagram..."):
                                try:
                                    fig = viz.draw_hierarchy(figsize=(14, 10), layout=draw_layout)
                                    if fig:
                                        st.pyplot(fig)
                                        st.success("✅ Netlist diagram generated!")
                                    else:
                                        st.warning("Could not generate diagram")
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    with col2:
                        if st.button("⚙️ Draw Schematic", use_container_width=True):
                            with st.spinner("Generating schematic..."):
                                try:
                                    fig = viz.draw_schematic(figsize=(16, 12))
                                    if fig:
                                        st.pyplot(fig)
                                        st.success("✅ Schematic generated!")
                                    else:
                                        st.warning("Could not generate schematic")
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    # Export options
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("💾 Export Diagram as PNG", key="export_netlist_diagram"):
                            output_dir = Path('outputs/diagrams')
                            output_dir.mkdir(parents=True, exist_ok=True)
                            try:
                                fig = viz.draw_hierarchy(figsize=(16, 12), layout=draw_layout)
                                if fig:
                                    filename = str(output_dir / f"{module_name}_netlist_diagram.png")
                                    fig.savefig(filename, dpi=300, bbox_inches='tight')
                                    st.success(f"✅ Saved to {filename}")
                            except Exception as e:
                                st.error(f"Export failed: {e}")
                    
                    with col2:
                        if st.button("📥 Download Netlist", key="download_netlist"):
                            st.download_button(
                                label="📥 Netlist.v",
                                data=netlist,
                                file_name=f"{module_name}_netlist.v",
                                mime="text/plain",
                                use_container_width=True
                            )
                    
                    # Show netlist preview
                    with st.expander("📄 Netlist Code Preview"):
                        st.code(netlist[:2000] + ("...\n\n[Truncated]" if len(netlist) > 2000 else ""), language="verilog")
                        
                else:
                    st.warning("No netlist available")
                    
            except ImportError as e:
                st.error(f"Netlist visualizer module not available: {e}")
            except Exception as e:
                st.error(f"Error visualizing netlist: {e}")
        else:
            st.info("🔧 Run synthesis first to generate and visualize netlist diagram")

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
