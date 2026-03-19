"""
Timing Analyzer

Performs static timing analysis on synthesized designs.

Usage:
    from python.timing_analyzer import TimingAnalyzer

    analyzer = TimingAnalyzer()
    result = analyzer.analyze_timing(rtl_code, module_name)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TimingAnalyzer:
    """Static timing analysis."""

    def __init__(self):
        """Initialize timing analyzer."""
        self.default_constraints = {
            'clock_period_ns': 10.0,
            'input_delay_ns': 1.0,
            'output_delay_ns': 1.0,
            'clock_uncertainty_ns': 0.5,
        }

    def analyze_timing(
        self,
        rtl_code: str,
        module_name: str,
        clock_period_ns: float = 10.0
    ) -> Dict:
        """
        Analyze timing of design.

        Args:
            rtl_code: RTL code
            module_name: Module name
            clock_period_ns: Clock period in nanoseconds

        Returns:
            dict: Timing analysis results
        """
        print(f"\n{'='*70}")
        print(f"TIMING ANALYSIS: {module_name}")
        print(f"{'='*70}")

        # Extract timing information from RTL
        timing_info = self._analyze_rtl_timing(rtl_code)

        # Calculate critical path (simplified)
        critical_path = self._estimate_critical_path(timing_info, rtl_code)

        # Determine if timing is met
        slack_ns = clock_period_ns - critical_path['delay_ns']
        timing_met = slack_ns >= 0

        results = {
            'clock_period_ns': clock_period_ns,
            'clock_frequency_mhz': 1000.0 / clock_period_ns,
            'critical_path_delay_ns': critical_path['delay_ns'],
            'slack_ns': slack_ns,
            'timing_met': timing_met,
            'critical_path': critical_path,
            'timing_info': timing_info,
        }

        # Print summary
        self._print_timing_summary(results)

        return results

    def _analyze_rtl_timing(self, rtl_code: str) -> Dict:
        """Analyze RTL for timing characteristics."""
        info = {
            'has_sequential_logic': False,
            'has_combinational_logic': False,
            'logic_levels': 1,
            'register_count': 0,
        }

        # Check for sequential logic
        if 'always @(posedge' in rtl_code or 'always_ff' in rtl_code:
            info['has_sequential_logic'] = True
            info['register_count'] = len(re.findall(r'reg\s+', rtl_code))

        # Check for combinational logic
        if 'always @(*)' in rtl_code or 'always_comb' in rtl_code or 'assign' in rtl_code:
            info['has_combinational_logic'] = True

        # Estimate logic levels
        nesting_depth = 0
        max_nesting = 0

        for char in rtl_code:
            if char == '(':
                nesting_depth += 1
                max_nesting = max(max_nesting, nesting_depth)
            elif char == ')':
                nesting_depth -= 1

        info['logic_levels'] = max(1, max_nesting // 2)

        return info

    def _estimate_critical_path(self, timing_info: Dict, rtl_code: str) -> Dict:
        """
        Estimate critical path delay.

        This is a simplified estimation.
        """
        # Base delays
        delays = {
            'and_gate': 0.1,
            'or_gate': 0.1,
            'xor_gate': 0.15,
            'mux': 0.2,
            'adder_per_bit': 0.5,
            'multiplier_per_bit': 1.0,
            'register_clk_to_q': 0.5,
            'register_setup': 0.3,
        }

        critical_path = {
            'delay_ns': 0.0,
            'components': [],
        }

        # If sequential, add register delays
        if timing_info['has_sequential_logic']:
            critical_path['delay_ns'] += delays['register_clk_to_q']
            critical_path['components'].append({
                'type': 'register_clk_to_q',
                'delay_ns': delays['register_clk_to_q']
            })

        # Add combinational logic delay
        if timing_info['has_combinational_logic']:
            logic_delay = timing_info['logic_levels'] * delays['and_gate']

            # Add extra delay for complex operations
            if 'adder' in rtl_code.lower() or '+' in rtl_code:
                bit_width = self._estimate_bit_width(rtl_code)
                logic_delay += bit_width * delays['adder_per_bit']
                critical_path['components'].append({
                    'type': 'adder',
                    'bit_width': bit_width,
                    'delay_ns': bit_width * delays['adder_per_bit']
                })

            if 'multiplier' in rtl_code.lower() or '*' in rtl_code:
                bit_width = self._estimate_bit_width(rtl_code)
                logic_delay += bit_width * delays['multiplier_per_bit']
                critical_path['components'].append({
                    'type': 'multiplier',
                    'bit_width': bit_width,
                    'delay_ns': bit_width * delays['multiplier_per_bit']
                })

            critical_path['delay_ns'] += logic_delay
            critical_path['components'].append({
                'type': 'combinational_logic',
                'levels': timing_info['logic_levels'],
                'delay_ns': logic_delay
            })

        # If sequential, add setup time
        if timing_info['has_sequential_logic']:
            critical_path['delay_ns'] += delays['register_setup']
            critical_path['components'].append({
                'type': 'register_setup',
                'delay_ns': delays['register_setup']
            })

        return critical_path

    def _estimate_bit_width(self, rtl_code: str) -> int:
        """Estimate bit width from RTL code."""
        matches = re.findall(r'\[(\d+):0\]', rtl_code)

        if matches:
            return max(int(m) for m in matches) + 1

        return 8

    def _print_timing_summary(self, results: Dict):
        """Print timing summary."""
        print(f"\nTiming Constraints:")
        print(f"  Clock period: {results['clock_period_ns']:.2f} ns")
        print(f"  Clock frequency: {results['clock_frequency_mhz']:.2f} MHz")

        print(f"\nTiming Results:")
        print(f"  Critical path delay: {results['critical_path_delay_ns']:.2f} ns")
        print(f"  Slack: {results['slack_ns']:.2f} ns")

        if results['timing_met']:
            print(f"  Status: [PASS] TIMING MET")
        else:
            print(f"  Status: [FAIL] TIMING VIOLATION")

        print(f"\nCritical Path Components:")
        for component in results['critical_path']['components']:
            comp_type = component['type']
            delay = component['delay_ns']
            print(f"  - {comp_type}: {delay:.2f} ns")

    def calculate_max_frequency(self, critical_path_delay_ns: float) -> Dict:
        """
        Calculate maximum operating frequency.

        Args:
            critical_path_delay_ns: Critical path delay

        Returns:
            dict: Frequency information
        """
        if critical_path_delay_ns <= 0:
            return {
                'max_frequency_mhz': float('inf'),
                'min_period_ns': 0,
            }

        max_freq_mhz = 1000.0 / critical_path_delay_ns

        return {
            'max_frequency_mhz': max_freq_mhz,
            'min_period_ns': critical_path_delay_ns,
        }

    def check_timing_constraints(
        self,
        timing_results: Dict,
        constraints: Optional[Dict] = None
    ) -> Dict:
        """
        Check if timing constraints are met.

        Args:
            timing_results: Timing analysis results
            constraints: Timing constraints

        Returns:
            dict: Constraint check results
        """
        if constraints is None:
            constraints = self.default_constraints

        checks = {
            'all_met': True,
            'violations': [],
        }

        # Check clock constraint
        if timing_results['critical_path_delay_ns'] > constraints['clock_period_ns']:
            checks['all_met'] = False
            checks['violations'].append({
                'type': 'setup_violation',
                'constraint': constraints['clock_period_ns'],
                'actual': timing_results['critical_path_delay_ns'],
                'slack': timing_results['slack_ns'],
            })

        return checks


if __name__ == "__main__":
    print("Timing Analyzer Self-Test\n")

    analyzer = TimingAnalyzer()

    # Test with sample RTL
    rtl_code = """
module counter_8bit(
    input clk,
    input rst,
    input enable,
    output reg [7:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 8'b0;
        else if (enable)
            count <= count + 1;
    end
endmodule
"""

    # Analyze at 100 MHz
    result = analyzer.analyze_timing(rtl_code, 'counter_8bit', clock_period_ns=10.0)

    if result['timing_met']:
        print("\n[PASS] Timing constraints met")
    else:
        print("\n[FAIL] Timing violation")

    # Calculate max frequency
    max_freq = analyzer.calculate_max_frequency(result['critical_path_delay_ns'])
    print(f"\nMaximum frequency: {max_freq['max_frequency_mhz']:.2f} MHz")

    print("\n[PASS] Self-test complete")
