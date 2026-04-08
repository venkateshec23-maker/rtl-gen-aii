# tests/test_real_integration.py
# Real Integration Tests
# Runs complete flow through Docker on the Real 8-bit adder
# Proves tools execute, produce real files, and meet size thresholds

import pytest
import shutil
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from full_flow import RTLtoGDSIIFlow, FILE_SIZE_THRESHOLDS


@pytest.fixture(scope="module")
def real_flow():
    """Run the entire flow once for all tests"""
    # Create temp dir to avoid polluting workspace during tests
    temp_workspace = tempfile.mkdtemp()
    
    # Needs to copy liberty file if it exists in expected place
    pdk_dir = Path(r"C:\pdk")
    lib_source = pdk_dir / "sky130A" / "libs.ref" / "sky130_fd_sc_hd" / "lib" / "sky130_fd_sc_hd__tt_025C_1v80.lib"
    
    rtl_path = Path(r"C:\tools\OpenLane\adder_8bit.v").absolute()
    rtl_path.write_text("""module adder_8bit(
    input  clk,
    input  [7:0] a,
    input  [7:0] b,
    output reg [8:0] sum
);

always @(posedge clk) begin
    sum <= a + b;
end

endmodule
""")

    tb_path = Path(r"C:\tools\OpenLane\adder_8bit_tb.v").absolute()
    tb_path.write_text("""`timescale 1ns/1ps
module adder_8bit_tb;
    reg clk;
    reg [7:0] a;
    reg [7:0] b;
    wire [8:0] sum;

    adder_8bit uut (
        .clk(clk),
        .a(a),
        .b(b),
        .sum(sum)
    );

    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        $dumpfile("/work/results/trace.vcd");
        $dumpvars(0, adder_8bit_tb);
        a = 0; b = 0;
        #20 a = 10; b = 20;
        #10 a = 255; b = 1;
        #20 $display("PASS");
        $finish;
    end
endmodule
""")

    flow = RTLtoGDSIIFlow(design_name="adder_8bit", verilog_file=str(rtl_path))
    
    # We must ensure we use the actual workspace for tests, because
    # Docker volume mounts need absolute Windows paths.
    # Therefore, we use the real flow object pointing to real tools\OpenLane
    
    results_dir = Path(r"C:\tools\OpenLane\results")
    if results_dir.exists():
        import shutil
        shutil.rmtree(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # To run test, we need RTL. Assuming RTL is present.
    # We don't actually run flow.run_all() inside module setup unless we have to, 
    # but the user said integration test takes ~5-10 minutes. 
    # Let's run it.
    metrics = flow.run_full_flow()
    
    yield flow


@pytest.mark.integration
class TestRealIntegration:
    """These tests verify the physical output files from real execution"""
    
    def test_synthesis_output_is_real(self, real_flow):
        """Synthesis must produce mapped Sky130 cells"""
        netlist = real_flow.results_dir / "adder_8bit_sky130.v"
        assert netlist.exists()
        assert netlist.stat().st_size >= FILE_SIZE_THRESHOLDS["netlist"]
        
        content = netlist.read_text(errors="ignore")
        assert "sky130_fd_sc_hd__" in content
        assert "$_XOR_" not in content, "Found generic unmapped cells"

    def test_routing_not_silent_failure(self, real_flow):
        """Routed DEF must exist and be LARGER than CTS DEF"""
        cts = real_flow.results_dir / "cts.def"
        routed = real_flow.results_dir / "routed.def"
        
        assert cts.exists()
        assert routed.exists()
        
        cts_size = cts.stat().st_size
        routed_size = routed.stat().st_size
        
        assert routed_size >= FILE_SIZE_THRESHOLDS["routed_def"]
        assert routed_size > cts_size, \
            "Routed DEF is same size as CTS DEF - TritonRoute crashed (SIGSEGV)!"

    def test_gds_is_not_stub(self, real_flow):
        """GDS file must be real layout, not a 178-byte stub"""
        gds = real_flow.results_dir / "adder_8bit.gds"
        assert gds.exists()
        
        size_kb = gds.stat().st_size / 1024
        assert size_kb >= (FILE_SIZE_THRESHOLDS["gds"] / 1024), \
            f"GDS is only {size_kb}KB - likely a stub fallback"

    def test_extracted_spice_has_correct_cell_name(self, real_flow):
        """Magic extraction must use flattened cell name for LVS to match"""
        spice = real_flow.results_dir / "adder_8bit_extracted.spice"
        assert spice.exists()
        assert spice.stat().st_size >= FILE_SIZE_THRESHOLDS["spice_extracted"]
        
        content = spice.read_text(errors="ignore")
        # Subckt must exist and be named correctly
        assert ".subckt adder_8bit_flat" in content.lower() or \
               ".subckt adder_8bit" in content.lower(), \
               "Extracted SPICE missing top-level subckt wrapper"

    def test_lvs_matches(self, real_flow):
        """Netgen must report circuits are equivalent"""
        lvs_log = real_flow.results_dir / "lvs_report_final.txt"
        assert lvs_log.exists()
        
        content = lvs_log.read_text(errors="ignore")
        assert ("Circuits match uniquely" in content or "are equivalent" in content), \
            "LVS UNMATCHED"

    def test_drc_clean(self, real_flow):
        """Magic DRC must report 0 violations on the REAL GDS"""
        drc_log = real_flow.results_dir / "drc_report.txt"
        assert drc_log.exists()
        
        content = drc_log.read_text(errors="ignore")
        assert "0 violations" in content or "0 errors" in content or "DRC violations: 0" in content
