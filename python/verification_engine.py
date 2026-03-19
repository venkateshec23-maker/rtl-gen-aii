"""
Verification Engine for RTL-Gen AI
Complete verification pipeline: compile → simulate → analyze.

This is the main orchestration class that ties together:
- CompilationManager (compile Verilog)
- SimulationRunner (run simulation)
- ResultsParser (analyze results)

Usage:
    engine = VerificationEngine()
    result = engine.verify(rtl_code, testbench_code)
    
    if result['passed']:
        print("[PASS] Verification passed!")
    else:
        print("[FAIL] Verification failed")
        for error in result['errors']:
            print(f"  - {error}")
"""

from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from python.compilation_manager import CompilationManager
from python.simulation_runner import SimulationRunner
from python.results_parser import ResultsParser
from python.config import DEBUG_MODE

# Import synthesis and timing modules if available
try:
    from python.synthesis_engine import SynthesisEngine
    SYNTHESIS_AVAILABLE = True
except ImportError:
    SYNTHESIS_AVAILABLE = False

try:
    from python.timing_analyzer import TimingAnalyzer
    TIMING_AVAILABLE = True
except ImportError:
    TIMING_AVAILABLE = False


class VerificationEngine:
    """
    Complete verification engine.
    
    Workflow:
    1. Compile RTL and testbench
    2. Run simulation
    3. Parse results
    4. Return comprehensive verification report
    
    Usage:
        engine = VerificationEngine()
        result = engine.verify(rtl_code, testbench_code)
    """
    
    def __init__(self, debug: bool = None):
        """
        Initialize verification engine.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug if debug is not None else DEBUG_MODE
        
        # Initialize components
        self.compiler = CompilationManager(debug=self.debug)
        self.simulator = SimulationRunner(debug=self.debug)
        self.parser = ResultsParser(debug=self.debug)
        
        # Initialize synthesis and timing engines if available
        if SYNTHESIS_AVAILABLE:
            self.synthesis_engine = SynthesisEngine()
        else:
            self.synthesis_engine = None
        
        if TIMING_AVAILABLE:
            self.timing_analyzer = TimingAnalyzer()
        else:
            self.timing_analyzer = None
        
        # Statistics
        self.stats = {
            'total_verifications': 0,
            'passed': 0,
            'failed': 0,
            'compilation_errors': 0,
            'simulation_errors': 0,
        }
        
        if self.debug:
            print("VerificationEngine initialized")
    
    def verify(self, rtl_code: str, testbench_code: str = None,
               module_name: str = None) -> Dict:
        """
        Verify Verilog code.
        
        Args:
            rtl_code: RTL module code
            testbench_code: Testbench code (required for full verification)
            module_name: Module name (for naming outputs)
            
        Returns:
            dict: {
                'passed': bool (overall pass/fail),
                'compilation_passed': bool,
                'simulation_passed': bool,
                'tests_passed': int,
                'tests_failed': int,
                'total_tests': int,
                'errors': list (all errors),
                'warnings': list (all warnings),
                'compilation_output': str,
                'simulation_output': str,
                'waveform_file': Path (if generated),
                'runtime_seconds': float,
                'timestamp': str,
            }
        """
        self.stats['total_verifications'] += 1
        
        if self.debug:
            print("\n" + "=" * 70)
            print("STARTING VERIFICATION")
            print("=" * 70)
        
        timestamp = datetime.now().isoformat()
        all_errors = []
        all_warnings = []
        
        # ====================================================================
        # PHASE 1: COMPILATION
        # ====================================================================
        
        if self.debug:
            print("\n[PHASE 1] Compilation")
            print("-" * 70)
        
        compile_result = self.compiler.compile(
            rtl_code,
            testbench_code,
            output_name=module_name or "design"
        )
        
        compilation_passed = compile_result['success']
        
        if not compilation_passed:
            self.stats['compilation_errors'] += 1
            all_errors.extend(compile_result['errors'])
            all_warnings.extend(compile_result['warnings'])
            
            if self.debug:
                print("[FAIL] Compilation FAILED")
                for error in compile_result['errors']:
                    print(f"  ERROR: {error}")
            
            # Can't simulate if compilation failed
            return {
                'passed': False,
                'compilation_passed': False,
                'simulation_passed': False,
                'tests_passed': 0,
                'tests_failed': 0,
                'total_tests': 0,
                'errors': all_errors,
                'warnings': all_warnings,
                'compilation_output': compile_result['output'],
                'simulation_output': "",
                'waveform_file': None,
                'runtime_seconds': 0.0,
                'timestamp': timestamp,
            }
        
        if self.debug:
            print("[PASS] Compilation PASSED")
            if compile_result['warnings']:
                for warning in compile_result['warnings']:
                    print(f"  WARNING: {warning}")
        
        all_warnings.extend(compile_result['warnings'])
        
        # ====================================================================
        # PHASE 2: SIMULATION
        # ====================================================================
        
        if self.debug:
            print("\n[PHASE 2] Simulation")
            print("-" * 70)
        
        # Only simulate if we have a testbench
        if not testbench_code:
            if self.debug:
                print("[WARN] No testbench provided - skipping simulation")
            
            return {
                'passed': True,  # Compilation passed, no sim to fail
                'compilation_passed': True,
                'simulation_passed': None,  # N/A
                'tests_passed': 0,
                'tests_failed': 0,
                'total_tests': 0,
                'errors': all_errors,
                'warnings': all_warnings + ["No testbench provided"],
                'compilation_output': compile_result['output'],
                'simulation_output': "",
                'waveform_file': None,
                'runtime_seconds': 0.0,
                'timestamp': timestamp,
            }
        
        sim_result = self.simulator.run(
            compile_result['executable'],
            waveform_name=module_name
        )
        
        simulation_passed = sim_result['success']
        
        if not simulation_passed:
            self.stats['simulation_errors'] += 1
            all_errors.extend(sim_result['errors'])
            
            if self.debug:
                print("[FAIL] Simulation FAILED")
                for error in sim_result['errors']:
                    print(f"  ERROR: {error}")
        else:
            if self.debug:
                print("[PASS] Simulation completed")
        
        # ====================================================================
        # PHASE 3: RESULTS ANALYSIS
        # ====================================================================
        
        if self.debug:
            print("\n[PHASE 3] Results Analysis")
            print("-" * 70)
        
        parse_result = self.parser.parse(sim_result['output'])
        
        # Overall pass/fail
        passed = (
            compilation_passed and 
            simulation_passed and 
            parse_result['passed']
        )
        
        if passed:
            self.stats['passed'] += 1
        else:
            self.stats['failed'] += 1
        
        # Combine errors from parsing
        all_errors.extend(parse_result['errors'])
        
        if self.debug:
            if parse_result['passed']:
                print(f"[PASS] Tests PASSED ({parse_result['tests_passed']} tests)")
            else:
                print(f"[FAIL] Tests FAILED")
                print(f"  Passed: {parse_result['tests_passed']}")
                print(f"  Failed: {parse_result['tests_failed']}")
        
        # ====================================================================
        # FINAL RESULT
        # ====================================================================
        
        if self.debug:
            print("\n" + "=" * 70)
            print(f"VERIFICATION {'[PASS]' if passed else '[FAIL]'}")
            print("=" * 70)
        
        return {
            'passed': passed,
            'compilation_passed': compilation_passed,
            'simulation_passed': simulation_passed,
            'tests_passed': parse_result['tests_passed'],
            'tests_failed': parse_result['tests_failed'],
            'total_tests': parse_result['total_tests'],
            'errors': all_errors,
            'warnings': all_warnings,
            'compilation_output': compile_result['output'],
            'simulation_output': sim_result['output'],
            'waveform_file': sim_result['waveform_file'],
            'runtime_seconds': sim_result['runtime_seconds'],
            'timestamp': timestamp,
        }
    
    def verify_from_files(self, rtl_file: Path, tb_file: Path = None) -> Dict:
        """
        Verify from existing files.
        
        Args:
            rtl_file: Path to RTL file
            tb_file: Path to testbench file
            
        Returns:
            dict: Verification result
        """
        rtl_code = rtl_file.read_text(encoding='utf-8')
        tb_code = tb_file.read_text(encoding='utf-8') if tb_file else None
        
        module_name = rtl_file.stem
        
        return self.verify(rtl_code, tb_code, module_name)
    
    def verify_with_synthesis(
        self,
        rtl_code: str,
        testbench_code: str,
        module_name: str,
        synthesize: bool = True,
        analyze_timing: bool = True,
        clock_period_ns: float = 10.0
    ) -> Dict:
        """
        Verify with synthesis and timing analysis.
        
        Args:
            rtl_code: RTL code
            testbench_code: Testbench code
            module_name: Module name
            synthesize: Whether to synthesize
            analyze_timing: Whether to analyze timing
            clock_period_ns: Target clock period
            
        Returns:
            dict: Complete verification results
        """
        print(f"\n{'='*70}")
        print(f"COMPLETE VERIFICATION: {module_name}")
        print(f"{'='*70}")
        
        results = {
            'module_name': module_name,
            'passed': False,
        }
        
        # Step 1: Syntax verification
        print("\n[1/4] Syntax Verification...")
        syntax_result = self.verify_syntax(rtl_code, module_name)
        results['syntax'] = syntax_result
        
        if not syntax_result['passed']:
            results['message'] = 'Syntax verification failed'
            return results
        
        print("  ✓ Syntax check passed")
        
        # Step 2: Simulation
        print("\n[2/4] Functional Simulation...")
        sim_result = self.verify(rtl_code, testbench_code, module_name)
        results['simulation'] = sim_result
        
        if not sim_result['passed']:
            results['message'] = 'Simulation failed'
            return results
        
        print("  ✓ Simulation passed")
        
        # Step 3: Synthesis
        if synthesize and self.synthesis_engine:
            print("\n[3/4] Logic Synthesis...")
            synth_result = self.synthesis_engine.synthesize(rtl_code, module_name)
            results['synthesis'] = synth_result
            
            if synth_result['success']:
                print("  ✓ Synthesis successful")
                
                # Area estimation
                area = self.synthesis_engine.estimate_area(synth_result['gate_count'])
                results['area'] = area
                print(f"  Gate count: {synth_result['gate_count']}")
                print(f"  Area: {area['area_um2']:.2f} µm²")
                
                # Power estimation
                power = self.synthesis_engine.estimate_power(
                    synth_result['gate_count'],
                    frequency_mhz=1000.0 / clock_period_ns
                )
                results['power'] = power
                print(f"  Power: {power['total_power_mw']:.4f} mW")
            else:
                print(f"  ⚠ Synthesis failed: {synth_result.get('message', 'Unknown')}")
        else:
            print("\n[3/4] Logic Synthesis... SKIPPED")
        
        # Step 4: Timing Analysis
        if analyze_timing and self.timing_analyzer:
            print("\n[4/4] Timing Analysis...")
            timing_result = self.timing_analyzer.analyze_timing(
                rtl_code,
                module_name,
                clock_period_ns=clock_period_ns
            )
            results['timing'] = timing_result
            
            if timing_result['timing_met']:
                print("  ✓ Timing constraints met")
            else:
                print(f"  ⚠ Timing violation: {timing_result['slack_ns']:.2f} ns")
        else:
            print("\n[4/4] Timing Analysis... SKIPPED")
        
        # Overall pass/fail
        results['passed'] = (
            results['syntax']['passed'] and
            results['simulation']['passed'] and
            (not synthesize or results.get('synthesis', {}).get('success', False)) and
            (not analyze_timing or results.get('timing', {}).get('timing_met', False))
        )
        
        print(f"\n{'='*70}")
        if results['passed']:
            print("✓ ALL VERIFICATION PASSED")
        else:
            print("✗ VERIFICATION FAILED")
        print(f"{'='*70}")
        
        return results
    
    def verify_syntax(self, rtl_code: str, module_name: str) -> Dict:
        """
        Verify syntax only (no simulation).
        
        Args:
            rtl_code: RTL code
            module_name: Module name
            
        Returns:
            dict: Syntax verification result
        """
        compile_result = self.compiler.compile(
            rtl_code,
            testbench_code=None,
            output_name=module_name
        )
        
        return {
            'passed': compile_result['success'],
            'errors': compile_result['errors'],
            'warnings': compile_result['warnings'],
            'output': compile_result['output'],
        }
    
    def get_stats(self) -> Dict:
        """Get verification statistics."""
        return self.stats.copy()
    
    def print_stats(self):
        """Print formatted statistics."""
        print("=" * 70)
        print("VERIFICATION ENGINE STATISTICS")
        print("=" * 70)
        
        total = self.stats['total_verifications']
        passed = self.stats['passed']
        failed = self.stats['failed']
        
        print(f"\nTotal verifications: {total}")
        if total > 0:
            pass_rate = (passed / total) * 100
            print(f"Passed: {passed} ({pass_rate:.1f}%)")
            print(f"Failed: {failed} ({100 - pass_rate:.1f}%)")
            print(f"Compilation errors: {self.stats['compilation_errors']}")
            print(f"Simulation errors: {self.stats['simulation_errors']}")
        
        print("=" * 70)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_verify(rtl_code: str, testbench_code: str = None) -> bool:
    """
    Quick verification function.
    
    Args:
        rtl_code: RTL module code
        testbench_code: Testbench code
        
    Returns:
        bool: True if verification passed
    """
    engine = VerificationEngine(debug=False)
    result = engine.verify(rtl_code, testbench_code)
    return result['passed']


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Verification Engine Self-Test\n")
    print("=" * 70)
    
    engine = VerificationEngine(debug=True)
    
    # Test 1: Complete verification (should pass)
    print("\n" + "=" * 70)
    print("TEST 1: Valid design (should PASS)")
    print("=" * 70)
    
    rtl_code = """
module adder_4bit(
    input [3:0] a, b,
    input cin,
    output [3:0] sum,
    output cout
);
    assign {cout, sum} = a + b + cin;
endmodule
"""
    
    tb_code = """
module adder_4bit_tb;
    reg [3:0] a, b;
    reg cin;
    wire [3:0] sum;
    wire cout;
    
    adder_4bit dut(.*);
    
    initial begin
        $dumpfile("waveform.vcd");
        $dumpvars(0, adder_4bit_tb);
        
        $display("Testing 4-bit adder");
        
        // Test 1: 5 + 3 = 8
        a = 4'd5; b = 4'd3; cin = 0;
        #10;
        if (sum == 4'd8 && cout == 0)
            $display("Test 1: PASS");
        else
            $display("Test 1: FAIL");
        
        // Test 2: 15 + 1 = 0 with carry
        a = 4'd15; b = 4'd1; cin = 0;
        #10;
        if (sum == 4'd0 && cout == 1)
            $display("Test 2: PASS");
        else
            $display("Test 2: FAIL");
        
        $display("All tests passed!");
        $finish;
    end
endmodule
"""
    
    result1 = engine.verify(rtl_code, tb_code, module_name="adder_4bit")
    
    print("\n" + "-" * 70)
    print("RESULT:")
    print(f"  Overall: {'[PASS]' if result1['passed'] else '[FAIL]'}")
    print(f"  Compilation: {'[PASS]' if result1['compilation_passed'] else '[FAIL]'}")
    print(f"  Simulation: {'[PASS]' if result1['simulation_passed'] else '[FAIL]'}")
    print(f"  Tests: {result1['tests_passed']}/{result1['total_tests']} passed")
    if result1['waveform_file']:
        print(f"  Waveform: {result1['waveform_file']}")
    
    # Test 2: Syntax error (should fail compilation)
    print("\n" + "=" * 70)
    print("TEST 2: Syntax error (should FAIL compilation)")
    print("=" * 70)
    
    bad_rtl = """
module broken(
    input a, b
    output c  // Missing comma!
);
    assign c = a & b;
endmodule
"""
    
    result2 = engine.verify(bad_rtl)
    
    print("\n" + "-" * 70)
    print("RESULT:")
    print(f"  Overall: {'[PASS]' if result2['passed'] else '[FAIL]'}")
    print(f"  Errors: {len(result2['errors'])}")
    for error in result2['errors'][:3]:  # Show first 3
        print(f"    - {error}")
    
    # Show statistics
    print("\n")
    engine.print_stats()
    
    print("\n" + "=" * 70)
    print("Self-test complete!")
    print("=" * 70)
