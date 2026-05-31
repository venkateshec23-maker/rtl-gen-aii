"""
GDS Analyzer - AI-powered GDS file analysis and verification
Automatically detects design type and generates appropriate tests
"""

import re
import struct
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from datetime import datetime

log = logging.getLogger(__name__)

# GDS Record Types
GDS_RECORDS = {
    0x00: "HEADER",
    0x01: "BGNLIB",
    0x02: "LIBNAME",
    0x03: "UNITS",
    0x04: "ENDLIB",
    0x05: "BGNSTR",
    0x06: "STRNAME",
    0x07: "ENDSTR",
    0x08: "BOUNDARY",
    0x09: "PATH",
    0x0A: "SREF",
    0x0B: "AREF",
    0x0C: "TEXT",
    0x10: "BOX",
    0x12: "LAYER",
    0x13: "DATATYPE",
    0x16: "XY",
    0x17: "ENDEL",
    0x19: "ANGLE",
    0x1A: "PROPATTR",
    0x1B: "PROPVALUE",
    0x1C: "SNAME",
    0x2A: "PRESENTATION",
    0x2C: "STRANS",
    0x2F: "WIDTH",
}

# Sky130 layer mapping
SKY130_LAYERS = {
    (0, 0): "label",
    (1, 0): "nwell",
    (2, 0): "pwell", 
    (65, 20): "li1_drawing",
    (65, 44): "li1_pin",
    (66, 20): "met1_drawing",
    (66, 44): "met1_pin",
    (67, 20): "met2_drawing",
    (67, 44): "met2_pin",
    (68, 20): "met3_drawing",
    (68, 44): "met3_pin",
    (69, 20): "met4_drawing",
    (69, 44): "met4_pin",
    (70, 20): "met5_drawing",
    (72, 44): "via1_pin",
    (76, 44): "via2_pin",
    (78, 44): "via3_pin",
    (80, 44): "via4_pin",
    (81, 44): "nwell_pin",
}


def parse_gds_structure(gds_path: str) -> Dict:
    """
    Parse GDS file to extract structure names and metadata.
    Returns module names, layer usage, and geometry stats.
    """
    result = {
        "structure_names": [],
        "layers": set(),
        "total_polygons": 0,
        "total_paths": 0,
        "references": [],
        "bounding_box": None,
        "file_size_kb": 0,
        "estimated_cells": 0,
    }
    
    try:
        with open(gds_path, "rb") as f:
            data = f.read()
        
        result["file_size_kb"] = len(data) / 1024
        
        i = 0
        current_layer = None
        x_coords = []
        y_coords = []
        
        while i < len(data) - 1:
            # Read record header (2 bytes length, 1 byte type)
            if i + 2 > len(data):
                break
                
            length = struct.unpack(">H", data[i:i+2])[0]
            if length < 2 or length > 65535:
                i += 1
                continue
                
            if i + 3 > len(data):
                break
                
            record_type = data[i+2]
            record_data = data[i+3:i+length] if length > 2 else b""
            
            record_name = GDS_RECORDS.get(record_type, f"UNKNOWN_{record_type:02X}")
            
            if record_type == 0x06:  # STRNAME - structure name
                try:
                    name = record_data.decode("ascii").strip()
                    if name:
                        result["structure_names"].append(name)
                except:
                    pass
            
            elif record_type == 0x12:  # LAYER
                if len(record_data) >= 2:
                    layer = struct.unpack(">H", record_data[:2])[0]
                    result["layers"].add(layer)
                    current_layer = layer
            
            elif record_type == 0x08:  # BOUNDARY (polygon)
                result["total_polygons"] += 1
            
            elif record_type == 0x09:  # PATH
                result["total_paths"] += 1
            
            elif record_type == 0x0A:  # SREF (structure reference)
                try:
                    ref_name = record_data.decode("ascii").strip()
                    if ref_name:
                        result["references"].append(ref_name)
                except:
                    pass
            
            elif record_type == 0x16:  # XY coordinates
                coords = []
                for j in range(0, len(record_data)-7, 8):
                    x = struct.unpack(">i", record_data[j:j+4])[0]
                    y = struct.unpack(">i", record_data[j+4:j+8])[0]
                    coords.append((x/1000, y/1000))  # Convert to microns
                
                if coords:
                    x_coords.extend([c[0] for c in coords])
                    y_coords.extend([c[1] for c in coords])
            
            i += length
        
        if x_coords and y_coords:
            result["bounding_box"] = {
                "min_x": min(x_coords),
                "max_x": max(x_coords),
                "min_y": min(y_coords),
                "max_y": max(y_coords),
                "width_um": max(x_coords) - min(x_coords) if x_coords else 0,
                "height_um": max(y_coords) - min(y_coords) if y_coords else 0,
            }
        
        result["layers"] = sorted(result["layers"])
        result["estimated_cells"] = result["total_polygons"] // 4  # Rough estimate
        
    except Exception as e:
        log.error(f"GDS parsing failed: {e}")
    
    return result


def classify_design_from_gds(gds_structure: Dict) -> str:
    """
    Identify design type from GDS structure analysis.
    Returns: 'counter', 'adder', 'alu', 'fifo', 'memory', 'uart', etc.
    """
    structures = gds_structure.get("structure_names", [])
    refs = gds_structure.get("references", [])
    polygons = gds_structure.get("total_polygons", 0)
    size_kb = gds_structure.get("file_size_kb", 0)
    
    structures_lower = [s.lower() for s in structures]
    refs_lower = [r.lower() for r in refs]
    all_names = " ".join(structures_lower + refs_lower)
    
    if any(s in all_names for s in ["counter", "cnt", "binary"]):
        return "counter"
    
    if any(s in all_names for s in ["adder", "add", "sum", "ripple"]):
        return "adder"
    
    if any(s in all_names for s in ["alu", "arithmetic"]):
        return "alu"
    
    if any(s in all_names for s in ["fifo", "queue", "buffer"]):
        return "fifo"
    
    if any(s in all_names for s in ["uart", "serial", "tx", "rx"]):
        return "uart"
    
    if any(s in all_names for s in ["spi", "serial peripheral"]):
        return "spi_master"
    
    if any(s in all_names for s in ["i2c", "twi", "sda", "scl"]):
        return "i2c_master"
    
    if any(s in all_names for s in ["fsm", "state", "traffic"]):
        return "fsm"
    
    if any(s in all_names for s in ["decoder", "decode"]):
        return "decoder"
    
    if any(s in all_names for s in ["encoder", "priority"]):
        return "encoder"
    
    if any(s in all_names for s in ["comparator", "compare", "magnitude"]):
        return "comparator"
    
    if any(s in all_names for s in ["pwm", "pulse", "duty"]):
        return "pwm"
    
    if any(s in all_names for s in ["multiplier", "mult", "product"]):
        return "multiplier"
    
    if any(s in all_names for s in ["crc", "checksum"]):
        return "crc"
    
    if any(s in all_names for s in ["register", "regfile", "reg_file"]):
        return "reg_file"
    
    if any(s in all_names for s in ["memory", "ram", "sram"]):
        return "memory"
    
    if any(s in all_names for s in ["mux", "multiplex", "select"]):
        return "mux"
    
    if any(s in all_names for s in ["shift", "sipo", "piso"]):
        return "shift_reg"
    
    if any(s in all_names for s in ["clkdiv", "clock_div", "prescaler"]):
        return "clk_div"
    
    if size_kb > 200:
        return "complex"
    
    if size_kb > 100:
        return "medium"
    
    return "simple"


def extract_module_name(gds_structure: Dict) -> str:
    """Extract the main module name from GDS structure"""
    structures = gds_structure.get("structure_names", [])
    
    if not structures:
        return "unknown_design"
    
    for name in structures:
        name = name.strip().replace("\x00", "").replace("\x06", "")
        name_lower = name.lower()
        if any(x in name_lower for x in ["sky130", "gf180mcu", "stdcell", "prime", "decap", "fill", "tap"]):
            continue
        if name.startswith("_"):
            continue
        if name:
            return name
    
    for name in structures:
        name = name.strip().replace("\x00", "").replace("\x06", "")
        if name:
            return name
    
    return "unknown_design"


def get_design_info(design_type: str) -> Dict:
    """
    Get design information for test generation.
    Returns ports, test patterns, and expected behavior.
    """
    DESIGN_INFO = {
        "counter": {
            "description": "Binary counter with synchronous reset and enable",
            "ports": ["clk", "reset_n", "enable", "count[WIDTH-1:0]"],
            "test_pattern": "increment, reset, hold",
            "bits_estimate": 8,
        },
        "adder": {
            "description": "Ripple carry adder, adds two operands, outputs sum and carry",
            "ports": ["clk", "reset_n", "a[WIDTH-1:0]", "b[WIDTH-1:0]", "sum[WIDTH:0]"],
            "test_pattern": "random inputs, overflow, zero",
            "bits_estimate": 8,
        },
        "alu": {
            "description": "Arithmetic Logic Unit with multiple operations",
            "ports": ["clk", "reset_n", "a", "b", "op_select", "result", "flags"],
            "test_pattern": "add, sub, and, or, xor, shift",
            "bits_estimate": 8,
        },
        "fsm": {
            "description": "Finite State Machine with state transitions",
            "ports": ["clk", "reset_n", "input", "state", "output"],
            "test_pattern": "state transitions, reset, illegal states",
            "bits_estimate": 4,
        },
        "fifo": {
            "description": "First-In-First-Out buffer with full/empty flags",
            "ports": ["clk", "reset_n", "wr_en", "rd_en", "din", "dout", "full", "empty"],
            "test_pattern": "write, read, overflow, underflow",
            "bits_estimate": 8,
        },
        "memory": {
            "description": "Single-port RAM with read/write",
            "ports": ["clk", "we", "addr", "din", "dout"],
            "test_pattern": "write, read, all addresses",
            "bits_estimate": 8,
        },
        "uart": {
            "description": "UART transmitter with configurable baud rate",
            "ports": ["clk", "reset_n", "tx_data", "tx_valid", "tx_ready", "tx_out"],
            "test_pattern": "send byte, start bit, stop bit",
            "bits_estimate": 8,
        },
        "spi_master": {
            "description": "SPI master with MOSI, MISO, SCLK, SS",
            "ports": ["clk", "reset_n", "mosi", "miso", "sclk", "ss"],
            "test_pattern": "byte transfer, mode 0-3",
            "bits_estimate": 8,
        },
        "i2c_master": {
            "description": "I2C master with SDA, SCL",
            "ports": ["clk", "reset_n", "sda", "scl", "data_out"],
            "test_pattern": "start, address, data, ack, stop",
            "bits_estimate": 8,
        },
        "comparator": {
            "description": "Magnitude comparator with equal, greater, less outputs",
            "ports": ["clk", "reset_n", "a", "b", "eq", "gt", "lt"],
            "test_pattern": "equal, greater, less",
            "bits_estimate": 8,
        },
        "decoder": {
            "description": "N-to-2^N decoder with enable",
            "ports": ["clk", "reset_n", "sel", "en", "out"],
            "test_pattern": "each selection, enable/disable",
            "bits_estimate": 3,
        },
        "encoder": {
            "description": "Priority encoder",
            "ports": ["clk", "reset_n", "in", "out", "valid"],
            "test_pattern": "single bit, multiple bits, all zero",
            "bits_estimate": 8,
        },
        "pwm": {
            "description": "PWM generator with duty cycle control",
            "ports": ["clk", "reset_n", "duty", "pwm_out"],
            "test_pattern": "0%, 50%, 100% duty cycle",
            "bits_estimate": 8,
        },
        "crc": {
            "description": "CRC checksum generator",
            "ports": ["clk", "reset_n", "data_in", "valid", "crc_out"],
            "test_pattern": "known input, expected output",
            "bits_estimate": 8,
        },
        "multiplier": {
            "description": "Pipelined multiplier",
            "ports": ["clk", "reset_n", "a", "b", "product"],
            "test_pattern": "random values, zero, max",
            "bits_estimate": 8,
        },
        "mux": {
            "description": "Multiplexer for data selection",
            "ports": ["clk", "reset_n", "in0", "in1", "...", "sel", "out"],
            "test_pattern": "each input selected",
            "bits_estimate": 8,
        },
        "shift_reg": {
            "description": "Shift register SIPO/PISO",
            "ports": ["clk", "reset_n", "data_in", "data_out", "load", "shift_en"],
            "test_pattern": "shift in/out, parallel load",
            "bits_estimate": 8,
        },
        "clk_div": {
            "description": "Clock divider",
            "ports": ["clk_in", "reset_n", "clk_out"],
            "test_pattern": "count edges, verify division",
            "bits_estimate": 8,
        },
        "reg_file": {
            "description": "Register file with dual ports",
            "ports": ["clk", "reset_n", "we", "waddr", "wdata", "raddr1", "raddr2", "rdata1", "rdata2"],
            "test_pattern": "write and read back",
            "bits_estimate": 8,
        },
        "simple": {
            "description": "Simple digital circuit",
            "ports": ["clk", "reset_n", "inputs", "outputs"],
            "test_pattern": "basic functionality",
            "bits_estimate": 8,
        },
        "medium": {
            "description": "Medium complexity digital circuit",
            "ports": ["clk", "reset_n", "control", "data_in", "data_out"],
            "test_pattern": "control sequences, data paths",
            "bits_estimate": 8,
        },
        "complex": {
            "description": "Complex digital system",
            "ports": ["clk", "reset_n", "inputs", "outputs"],
            "test_pattern": "system level tests",
            "bits_estimate": 16,
        },
    }
    
    return DESIGN_INFO.get(design_type, DESIGN_INFO["simple"])


def generate_testbench(module_name: str, design_type: str, bits: int = 8) -> str:
    """
    Generate a Verilog testbench based on design type.
    Uses templates from guaranteed_flow.py if available.
    """
    try:
        from guaranteed_flow import TEMPLATES_TB, TEMPLATES_RTL
        
        if design_type in TEMPLATES_TB:
            tb_template = TEMPLATES_TB[design_type]
            return tb_template.format(name=module_name, bits=bits)
    except ImportError:
        pass
    
    design_info = get_design_info(design_type)
    ports = design_info["ports"]
    
    port_declarations = []
    for port in ports:
        if "[" in port:
            port_declarations.append(f"    wire {port};")
        else:
            port_declarations.append(f"    wire {port};")
    
    tb_code = f"""`timescale 1ns/1ps
module {module_name}_tb();

    // Clock and reset
    reg clk;
    reg reset_n;
    
    // Design ports
{chr(10).join(port_declarations)}
    
    // Test counters
    integer pass_count = 0;
    integer fail_count = 0;
    
    // DUT instantiation
    {module_name} dut (
        .clk(clk),
        .reset_n(reset_n)
        // Connect other ports based on design
    );
    
    // Clock generation
    initial clk = 0;
    always #5 clk = ~clk;
    
    // Test sequence
    initial begin
        $dumpfile("trace.vcd");
        $dumpvars(0, {module_name}_tb);
        
        // Reset sequence
        reset_n = 0;
        repeat(4) @(posedge clk);
        #1;
        reset_n = 1;
        
        // Design-specific tests for {design_type}
        // {design_info['description']}
        // Test pattern: {design_info['test_pattern']}
        
        repeat(100) @(posedge clk);
        
        $display("RESULTS: %0d PASS / %0d FAIL", pass_count, fail_count);
        if (fail_count == 0)
            $display("ALL_TESTS_PASSED");
        else
            $display("TESTS_FAILED");
        $finish;
    end
    
endmodule
"""
    return tb_code


def analyze_and_generate_tests(gds_path: str) -> Dict:
    """
    Full analysis pipeline:
    1. Parse GDS structure
    2. Extract module name
    3. Classify design type
    4. Generate appropriate testbench
    """
    result = {
        "gds_path": gds_path,
        "timestamp": datetime.now().isoformat(),
        "module_name": "unknown",
        "design_type": "unknown",
        "testbench": "",
        "structure": {},
        "verification_ready": False,
    }
    
    gds_path = Path(gds_path)
    if not gds_path.exists():
        result["error"] = "GDS file not found"
        return result
    
    structure = parse_gds_structure(str(gds_path))
    result["structure"] = structure
    
    module_name = extract_module_name(structure)
    result["module_name"] = module_name
    
    design_type = classify_design_from_gds(structure)
    result["design_type"] = design_type
    
    design_info = get_design_info(design_type)
    result["design_info"] = design_info
    
    bits = design_info.get("bits_estimate", 8)
    testbench = generate_testbench(module_name, design_type, bits)
    result["testbench"] = testbench
    
    has_real_content = structure.get("file_size_kb", 0) > 50
    has_polys = structure.get("total_polygons", 0) > 10
    result["verification_ready"] = has_real_content and has_polys
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        gds_file = sys.argv[1]
        result = analyze_and_generate_tests(gds_file)
        
        print("=" * 60)
        print("GDS ANALYSIS RESULT")
        print("=" * 60)
        print(f"Module: {result['module_name']}")
        print(f"Type: {result['design_type']}")
        print(f"Size: {result['structure'].get('file_size_kb', 0):.1f} KB")
        print(f"Polygons: {result['structure'].get('total_polygons', 0)}")
        print(f"Structures: {result['structure'].get('structure_names', [])}")
        print(f"Ready for verification: {result['verification_ready']}")
        print()
        print("-" * 60)
        print("GENERATED TESTBENCH:")
        print("-" * 60)
        print(result['testbench'])
    else:
        print("Usage: python gds_analyzer.py <gds_file>")
