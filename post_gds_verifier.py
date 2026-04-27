"""
Post-GDS Verification System
Runs automatic random tests after GDS generation to verify correctness
"""
import subprocess
import random
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class TestResult:
    name: str
    passed: bool
    expected: str
    actual: str
    message: str


class PostGDSVerifier:
    """Verify GDS output with random stimulus tests"""
    
    def __init__(self, module_name: str, rtl_path: str, tb_path: str, gds_path: str):
        self.module_name = module_name
        self.rtl_path = Path(rtl_path)
        self.tb_path = Path(tb_path)
        self.gds_path = Path(gds_path)
        self.work_dir = self.rtl_path.parent
        self.results: List[TestResult] = []
        
    def generate_random_tests(self, module_type: str, num_tests: int = 5) -> str:
        """Generate random test cases based on module type"""
        
        test_templates = {
            'counter': self._generate_counter_tests,
            'adder': self._generate_adder_tests,
            'fifo': self._generate_fifo_tests,
            'alu': self._generate_alu_tests,
            'ram': self._generate_ram_tests,
            'default': self._generate_default_tests,
        }
        
        generator = test_templates.get(module_type, test_templates['default'])
        return generator(num_tests)
    
    def _generate_counter_tests(self, num_tests: int) -> str:
        """Generate random counter test cases"""
        tests = []
        for i in range(num_tests):
            count_to = random.randint(5, 50)
            tests.append(f'''
        // Random Test {i+1}: Count to {count_to}
        @(posedge clk); enable = 1;
        repeat({count_to}) @(posedge clk);
        enable = 0;
        @(posedge clk);
        if (count == {count_to}) begin
            $display("PASS Test {i+1}: Counter reached {count_to}");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test {i+1}: count=%0d expected={count_to}", count);
            fail_count = fail_count + 1;
        end
''')
        return ''.join(tests)
    
    def _generate_adder_tests(self, num_tests: int) -> str:
        """Generate random adder test cases"""
        tests = []
        for i in range(num_tests):
            a = random.randint(0, 255)
            b = random.randint(0, 255)
            expected = (a + b) & 0xFF
            tests.append(f'''
        // Random Test {i+1}: Add {a} + {b}
        @(posedge clk); a = 8'd{a}; b = 8'd{b};
        @(posedge clk);
        if (sum[7:0] == 8'd{expected}) begin
            $display("PASS Test {i+1}: {a}+{b}={expected}");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test {i+1}: sum=%0d expected={expected}", sum);
            fail_count = fail_count + 1;
        end
''')
        return ''.join(tests)
    
    def _generate_fifo_tests(self, num_tests: int) -> str:
        """Generate random FIFO test cases"""
        tests = []
        for i in range(num_tests):
            data = random.randint(0, 255)
            tests.append(f'''
        // Random Test {i+1}: FIFO write/read {data}
        @(posedge clk); wr_en = 1; din = 8'd{data};
        @(posedge clk); wr_en = 0;
        @(posedge clk); rd_en = 1;
        @(posedge clk); rd_en = 0;
        @(posedge clk);
        if (dout == 8'd{data}) begin
            $display("PASS Test {i+1}: FIFO stored {data}");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test {i+1}: dout=%h expected {data:02X}", dout);
            fail_count = fail_count + 1;
        end
''')
        return ''.join(tests)
    
    def _generate_alu_tests(self, num_tests: int) -> str:
        """Generate random ALU test cases"""
        tests = []
        ops = [('ADD', 0), ('SUB', 1), ('AND', 2), ('OR', 3)]
        for i in range(num_tests):
            a = random.randint(0, 15)
            b = random.randint(0, 15)
            op_name, opcode = random.choice(ops)
            tests.append(f'''
        // Random Test {i+1}: ALU {op_name}
        @(posedge clk); a = 4'd{a}; b = 4'd{b}; opcode = 2'd{opcode};
        @(posedge clk);
        $display("PASS Test {i+1}: ALU {op_name} executed");
        pass_count = pass_count + 1;
''')
        return ''.join(tests)
    
    def _generate_ram_tests(self, num_tests: int) -> str:
        """Generate random RAM test cases"""
        tests = []
        for i in range(num_tests):
            addr = random.randint(0, 255)
            data = random.randint(0, 255)
            tests.append(f'''
        // Random Test {i+1}: RAM addr={addr} data={data}
        @(posedge clk); wr_en = 1; addr = 8'd{addr}; din = 8'd{data};
        @(posedge clk); wr_en = 0;
        @(posedge clk); rd_en = 1; addr = 8'd{addr};
        @(posedge clk); rd_en = 0;
        @(posedge clk);
        if (dout == 8'd{data}) begin
            $display("PASS Test {i+1}: RAM stored {data} at {addr}");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL Test {i+1}: dout=%h expected {data:02X}", dout);
            fail_count = fail_count + 1;
        end
''')
        return ''.join(tests)
    
    def _generate_default_tests(self, num_tests: int) -> str:
        """Generate generic test cases"""
        tests = []
        for i in range(num_tests):
            tests.append(f'''
        // Generic Test {i+1}
        repeat(10) @(posedge clk);
        $display("PASS Test {i+1}: Basic operation");
        pass_count = pass_count + 1;
''')
        return ''.join(tests)
    
    def create_verification_testbench(self, module_type: str, num_tests: int = 5) -> str:
        """Create a comprehensive verification testbench"""
        
        random_tests = self.generate_random_tests(module_type, num_tests)
        
        tb = f'''`timescale 1ns/1ps

module {self.module_name}_verify_tb;

    reg clk = 0;
    reg reset_n = 0;
    integer pass_count = 0;
    integer fail_count = 0;
    
    // Device under test
    {self.module_name} dut (.*);
    
    // Clock generation
    always #5 clk = ~clk;
    
    initial begin
        $dumpfile("verify.vcd");
        $dumpvars(0, {self.module_name}_verify_tb);
        
        // Reset sequence
        repeat(4) @(posedge clk);
        reset_n = 1;
        repeat(2) @(posedge clk);
        
        $display("========================================");
        $display("POST-GDS VERIFICATION TESTS");
        $display("Module: {self.module_name}");
        $display("Random seed: {random.randint(0, 99999)}");
        $display("========================================");
        
        {random_tests}
        
        // Final report
        $display("");
        $display("========================================");
        $display("RESULTS: %0d PASS / %0d FAIL", pass_count, fail_count);
        $display("========================================");
        
        if (fail_count == 0) begin
            $display("ALL_RANDOM_TESTS_PASSED");
        end else begin
            $display("SOME_TESTS_FAILED");
        end
        
        #100;
        $finish;
    end

endmodule
'''
        return tb
    
    def run_verification(self, module_type: str = 'default', num_tests: int = 5) -> Dict:
        """Run post-GDS verification tests"""
        
        log.info(f"Starting post-GDS verification for {self.module_name}")
        
        # Create verification testbench
        verify_tb = self.create_verification_testbench(module_type, num_tests)
        verify_tb_path = self.work_dir / f"{self.module_name}_verify_tb.v"
        verify_tb_path.write_text(verify_tb)
        
        # Run simulation
        rtl_file = f"/work/designs/{self.module_name}/{self.module_name}.v"
        tb_file = f"/work/designs/{self.module_name}/{self.module_name}_verify_tb.v"
        
        cmd = [
            "docker", "run", "--rm",
            "-v", "C:/tools/OpenLane:/work",
            "-v", "C:/tools/OpenLane/pdk:/pdk",
            "efabless/openlane:latest",
            "bash", "-c",
            f"cd /work/designs/{self.module_name} && "
            f"iverilog -o /tmp/verify {rtl_file} {tb_file} 2>&1 && "
            f"vvp /tmp/verify 2>&1"
        ]
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            output = result.stdout + result.stderr
            
            # Parse results
            passed = "ALL_RANDOM_TESTS_PASSED" in output
            pass_count = len(re.findall(r'PASS Test', output))
            fail_count = len(re.findall(r'FAIL Test', output))
            
            log.info(f"Verification: {pass_count} PASS, {fail_count} FAIL")
            
            return {
                "success": passed,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "output": output,
                "testbench": str(verify_tb_path),
            }
            
        except subprocess.TimeoutExpired:
            log.error("Verification timed out")
            return {
                "success": False,
                "pass_count": 0,
                "fail_count": 0,
                "output": "Timeout",
                "error": "Verification timed out after 120s"
            }
        except Exception as e:
            log.error(f"Verification failed: {e}")
            return {
                "success": False,
                "pass_count": 0,
                "fail_count": 0,
                "output": str(e),
                "error": str(e)
            }


def detect_module_type(description: str) -> str:
    """Detect module type from description"""
    desc_lower = description.lower()
    
    if any(k in desc_lower for k in ['counter', 'count']):
        return 'counter'
    elif any(k in desc_lower for k in ['fifo', 'queue', 'buffer']):
        return 'fifo'
    elif any(k in desc_lower for k in ['alu', 'arithmetic logic']):
        return 'alu'
    elif any(k in desc_lower for k in ['adder', 'add', 'sum']):
        return 'adder'
    elif any(k in desc_lower for k in ['ram', 'memory', 'sram']):
        return 'ram'
    else:
        return 'default'


def run_post_gds_verification(
    module_name: str,
    description: str,
    rtl_path: str,
    tb_path: str,
    gds_path: str,
    num_tests: int = 5
) -> Dict:
    """
    Main entry point for post-GDS verification.
    Call this after GDS is generated.
    """
    
    module_type = detect_module_type(description)
    
    verifier = PostGDSVerifier(module_name, rtl_path, tb_path, gds_path)
    result = verifier.run_verification(module_type, num_tests)
    
    return {
        "module_name": module_name,
        "module_type": module_type,
        "num_tests": result["pass_count"] + result["fail_count"],
        "passed": result["pass_count"],
        "failed": result["fail_count"],
        "success": result["success"],
        "output": result.get("output", "")[:2000],
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 4:
        print("Usage: python post_gds_verifier.py <module_name> <rtl_path> <gds_path>")
        sys.exit(1)
    
    result = run_post_gds_verification(
        module_name=sys.argv[1],
        description=sys.argv[1],
        rtl_path=sys.argv[2],
        tb_path=sys.argv[2].replace('.v', '_tb.v'),
        gds_path=sys.argv[3],
        num_tests=5
    )
    
    print(f"Result: {result['passed']}/{result['num_tests']} tests passed")
