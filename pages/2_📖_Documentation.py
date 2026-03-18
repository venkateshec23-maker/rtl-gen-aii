"""
Documentation Page
User guide and examples.
"""

import streamlit as st

st.set_page_config(page_title="Documentation", page_icon="📖", layout="wide")

st.title("📖 Documentation")

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Quick Start", "Examples", "Best Practices", "API Reference"])

with tab1:
    st.header("🚀 Quick Start")
    
    st.markdown("""
    ### Getting Started
    
    1. **Describe your design** in natural language
    2. **Click Generate** to create RTL code
    3. **Review** the generated Verilog
    4. **Verify** through simulation
    5. **Download** your design files
    
    ### Tips for Good Descriptions
    
    ✅ **Good:**
    - "Create an 8-bit adder with carry-in and carry-out"
    - "Design a 4-bit counter with synchronous reset and enable"
    - "Build a 4-to-1 multiplexer with 8-bit inputs"
    
    ❌ **Too vague:**
    - "Make an adder"
    - "Counter circuit"
    - "Mux"
    
    ### What to Specify
    
    - **Bit width:** "8-bit", "16-bit", etc.
    - **Functionality:** What operations/features
    - **Control signals:** reset, enable, load, etc.
    - **Type:** Combinational or sequential
    """)

with tab2:
    st.header("📝 Examples")
    
    examples = {
        "Basic Combinational": [
            {"name": "Full Adder", "desc": "1-bit full adder with carry"},
            {"name": "4-bit Adder", "desc": "4-bit ripple carry adder"},
            {"name": "8-bit ALU", "desc": "8-bit ALU with ADD, SUB, AND, OR, XOR"},
            {"name": "4-to-1 Mux", "desc": "4-to-1 multiplexer with 8-bit inputs"},
        ],
        "Sequential Circuits": [
            {"name": "D Flip-Flop", "desc": "D flip-flop with async reset"},
            {"name": "8-bit Register", "desc": "8-bit register with enable and reset"},
            {"name": "4-bit Counter", "desc": "4-bit up counter with reset"},
            {"name": "Shift Register", "desc": "8-bit shift register"},
        ],
        "Complex Designs": [
            {"name": "FIFO", "desc": "8-entry 8-bit FIFO with full/empty flags"},
            {"name": "UART TX", "desc": "UART transmitter, 9600 baud, 8N1"},
            {"name": "PWM Generator", "desc": "8-bit PWM generator"},
        ]
    }
    
    for category, items in examples.items():
        st.subheader(category)
        for item in items:
            with st.expander(item["name"]):
                st.code(item["desc"])
                if st.button("Try This", key=f"try_{item['name']}"):
                    st.session_state['example_desc'] = item["desc"]
                    st.info("Example loaded! Go to main page.")

with tab3:
    st.header("💡 Best Practices")
    
    st.markdown("""
    ### Design Description
    
    1. **Be Specific:** Include bit widths, operation types, control signals
    2. **One Module:** Describe one module per generation
    3. **Clear Naming:** Use standard names (clk, reset, enable)
    
    ### Verification
    
    1. **Always Verify:** Enable verification to catch errors
    2. **Check Waveforms:** Review VCD files for timing issues
    3. **Read Warnings:** Address warnings before using code
    
    ### Code Quality
    
    1. **Review Generated Code:** Always review before using
    2. **Test Thoroughly:** The testbench is auto-generated, add more tests
    3. **Synthesis Check:** Test synthesis if targeting FPGA/ASIC
    
    ### Performance
    
    1. **Use Mock LLM:** For testing without API costs
    2. **Cache Results:** System caches similar requests
    3. **Batch Generation:** Generate multiple variants
    """)

with tab4:
    st.header("🔌 API Reference")
    
    st.markdown("""
    ### Command Line Interface
    
    ```bash
    # Generate design
    python -m python.cli generate "8-bit adder" --output ./designs
    
    # With verification
    python -m python.cli generate "4-bit counter" --verify --simulate
    
    # Batch mode
    python -m python.cli batch designs.txt --output ./batch
    ```
    
    ### Python API
    
    ```python
    from python.rtl_generator import RTLGenerator
    
    # Initialize
    generator = RTLGenerator(use_mock=False)
    
    # Generate
    result = generator.generate("8-bit adder with carry")
    
    # Access code
    print(result['rtl_code'])
    print(result['testbench_code'])
    
    # Verify
    if result['verification_passed']:
        print("✓ Design verified!")
    ```
    """)
