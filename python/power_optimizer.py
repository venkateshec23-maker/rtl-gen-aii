"""
Power Optimizer

Suggests power optimization strategies for RTL designs.

Usage:
    from python.power_optimizer import PowerOptimizer

    optimizer = PowerOptimizer()
    suggestions = optimizer.analyze_and_suggest(rtl_code, power_results)
"""

from typing import Dict, List


class PowerOptimizer:
    """Power optimization analysis and suggestions."""

    def __init__(self):
        """Initialize power optimizer."""
        self.optimization_techniques = {
            'clock_gating': {
                'name': 'Clock Gating',
                'description': 'Disable clock to idle registers',
                'typical_savings': '20-40%',
                'complexity': 'Medium',
            },
            'power_gating': {
                'name': 'Power Gating',
                'description': 'Shut down power to unused blocks',
                'typical_savings': '50-70%',
                'complexity': 'High',
            },
            'voltage_scaling': {
                'name': 'Dynamic Voltage Scaling',
                'description': 'Reduce voltage for lower performance modes',
                'typical_savings': '30-50%',
                'complexity': 'High',
            },
            'operand_isolation': {
                'name': 'Operand Isolation',
                'description': 'Prevent unnecessary transitions in logic',
                'typical_savings': '10-20%',
                'complexity': 'Low',
            },
            'register_balancing': {
                'name': 'Register Balancing',
                'description': 'Reduce register count by pipelining',
                'typical_savings': '15-25%',
                'complexity': 'Medium',
            },
            'logic_restructuring': {
                'name': 'Logic Restructuring',
                'description': 'Optimize logic for lower power',
                'typical_savings': '10-30%',
                'complexity': 'Medium',
            },
        }

    def analyze_and_suggest(
        self,
        rtl_code: str,
        power_results: Dict,
        target_power_mw: float = None,
    ) -> Dict:
        """
        Analyze design and suggest optimizations.

        Args:
            rtl_code: RTL code
            power_results: Power analysis results
            target_power_mw: Target power budget

        Returns:
            dict: Optimization suggestions
        """
        print(f"\n{'=' * 70}")
        print("POWER OPTIMIZATION ANALYSIS")
        print(f"{'=' * 70}")

        current_power = power_results['total_power']['total_power_mw']
        print(f"\nCurrent power: {current_power:.4f} mW")

        if target_power_mw:
            required = current_power - target_power_mw
            required_pct = (required / current_power * 100) if current_power else 0.0
            print(f"Target power: {target_power_mw:.4f} mW")
            print(
                f"Required reduction: {required:.4f} mW ({required_pct:.1f}%)"
            )

        opportunities = self._identify_opportunities(rtl_code, power_results)
        suggestions = self._generate_suggestions(
            opportunities,
            power_results,
            target_power_mw,
        )

        self._print_suggestions(suggestions, current_power)

        return {
            'current_power_mw': current_power,
            'target_power_mw': target_power_mw,
            'opportunities': opportunities,
            'suggestions': suggestions,
        }

    def _identify_opportunities(
        self,
        rtl_code: str,
        power_results: Dict,
    ) -> List[Dict]:
        """Identify optimization opportunities."""
        opportunities = []

        breakdown = power_results['breakdown']
        design_info = power_results['design_info']

        if breakdown.get('clock_percent', 0) > 30:
            if design_info.get('registers', 0) > 10 and 'enable' in rtl_code.lower():
                opportunities.append({
                    'technique': 'clock_gating',
                    'reason': (
                        f"High clock power ({breakdown['clock_percent']:.1f}%) "
                        "with enable signal present"
                    ),
                    'applicable': True,
                    'priority': 'High',
                })

        if breakdown.get('leakage_percent', 0) > 25:
            opportunities.append({
                'technique': 'power_gating',
                'reason': f"High leakage power ({breakdown['leakage_percent']:.1f}%)",
                'applicable': True,
                'priority': 'Medium',
            })

        if design_info.get('adders', 0) > 0 or design_info.get('multipliers', 0) > 0:
            opportunities.append({
                'technique': 'operand_isolation',
                'reason': 'Arithmetic units present that could benefit from isolation',
                'applicable': True,
                'priority': 'Low',
            })

        if design_info.get('registers', 0) > 50:
            opportunities.append({
                'technique': 'register_balancing',
                'reason': f"Large register count ({design_info['registers']})",
                'applicable': True,
                'priority': 'Medium',
            })

        if breakdown.get('logic_percent', 0) > 30:
            opportunities.append({
                'technique': 'logic_restructuring',
                'reason': (
                    f"High combinational logic power ({breakdown['logic_percent']:.1f}%)"
                ),
                'applicable': True,
                'priority': 'Low',
            })

        return opportunities

    def _generate_suggestions(
        self,
        opportunities: List[Dict],
        power_results: Dict,
        target_power_mw: float,
    ) -> List[Dict]:
        """Generate detailed optimization suggestions."""
        suggestions = []
        current_power = power_results['total_power']['total_power_mw']

        for opp in opportunities:
            technique = self.optimization_techniques[opp['technique']]

            savings_range = technique['typical_savings'].split('-')
            min_savings_pct = float(savings_range[0].replace('%', ''))
            max_savings_pct = float(savings_range[1].replace('%', ''))
            avg_savings_pct = (min_savings_pct + max_savings_pct) / 2

            estimated_savings_mw = current_power * avg_savings_pct / 100
            new_power_mw = current_power - estimated_savings_mw

            suggestion = {
                'technique': technique['name'],
                'description': technique['description'],
                'reason': opp['reason'],
                'priority': opp['priority'],
                'complexity': technique['complexity'],
                'estimated_savings_pct': avg_savings_pct,
                'estimated_savings_mw': estimated_savings_mw,
                'estimated_new_power_mw': new_power_mw,
                'implementation_steps': self._get_implementation_steps(
                    opp['technique']
                ),
            }

            if target_power_mw is not None:
                suggestion['meets_target'] = new_power_mw <= target_power_mw

            suggestions.append(suggestion)

        priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
        suggestions.sort(
            key=lambda x: (priority_order.get(x['priority'], 99), -x['estimated_savings_mw'])
        )

        return suggestions

    def _get_implementation_steps(self, technique: str) -> List[str]:
        """Get implementation steps for a technique."""
        steps = {
            'clock_gating': [
                '1. Identify registers that can be clock-gated',
                '2. Create enable logic for clock gating',
                '3. Insert integrated clock-gating cells',
                '4. Verify functionality with clock gating',
                '5. Measure actual power savings',
            ],
            'power_gating': [
                '1. Identify blocks that can be powered down',
                '2. Design power switch network',
                '3. Add isolation cells at domain boundaries',
                '4. Implement retention registers if needed',
                '5. Create power management controller',
                '6. Verify power-up/down sequences',
            ],
            'voltage_scaling': [
                '1. Identify critical and non-critical paths',
                '2. Create voltage domains',
                '3. Add level shifters at domain crossings',
                '4. Implement voltage controller',
                '5. Verify timing at different voltages',
            ],
            'operand_isolation': [
                '1. Identify arithmetic units to isolate',
                '2. Add AND gates on inputs when disabled',
                '3. Connect AND gates to enable signal',
                '4. Verify functionality',
            ],
            'register_balancing': [
                '1. Analyze register usage',
                '2. Identify opportunities for register sharing',
                '3. Restructure datapath for efficiency',
                '4. Verify timing and functionality',
            ],
            'logic_restructuring': [
                '1. Analyze critical paths',
                '2. Identify high-activity nets',
                '3. Restructure logic to reduce switching',
                '4. Balance logic levels',
                '5. Verify functionality and timing',
            ],
        }
        return steps.get(technique, ['Implementation steps not specified'])

    def _print_suggestions(self, suggestions: List[Dict], current_power: float):
        """Print optimization suggestions."""
        print(f"\n{'=' * 70}")
        print("OPTIMIZATION SUGGESTIONS")
        print(f"{'=' * 70}")

        cumulative_savings = 0.0

        for i, sug in enumerate(suggestions, 1):
            print(f"\n{i}. {sug['technique']} [{sug['priority']} Priority]")
            print(f"   {sug['description']}")
            print(f"   Reason: {sug['reason']}")
            print(f"   Complexity: {sug['complexity']}")
            print(
                f"   Estimated savings: {sug['estimated_savings_pct']:.1f}% "
                f"({sug['estimated_savings_mw']:.4f} mW)"
            )
            print(f"   New power: {sug['estimated_new_power_mw']:.4f} mW")

            if 'meets_target' in sug:
                status = 'YES' if sug['meets_target'] else 'NO'
                print(f"   Meets target: {status}")

            cumulative_savings += sug['estimated_savings_mw']

        cumulative_power = current_power - cumulative_savings
        savings_pct = (cumulative_savings / current_power * 100) if current_power else 0.0

        print(f"\n{'=' * 70}")
        print("COMBINED IMPACT (if all applied)")
        print(f"{'=' * 70}")
        print(f"  Total savings: {cumulative_savings:.4f} mW ({savings_pct:.1f}%)")
        print(f"  Final power: {cumulative_power:.4f} mW")

    def generate_optimization_code(
        self,
        rtl_code: str,
        technique: str,
    ) -> str:
        """
        Generate optimized RTL code for a specific technique.

        Args:
            rtl_code: Original RTL code
            technique: Optimization technique

        Returns:
            str: Optimized RTL code
        """
        if technique == 'clock_gating':
            return self._apply_clock_gating(rtl_code)
        if technique == 'operand_isolation':
            return self._apply_operand_isolation(rtl_code)
        return rtl_code + "\n// Other optimizations require manual implementation\n"

    def _apply_clock_gating(self, rtl_code: str) -> str:
        """Apply clock gating optimization."""
        optimized = "// Clock-gated version\n\n"

        optimized += """// Clock gating cell
module clock_gate(
    input clk,
    input enable,
    output gated_clk
);
    reg enable_latched;

    always @(clk or enable) begin
        if (!clk)
            enable_latched <= enable;
    end

    assign gated_clk = clk & enable_latched;
endmodule

"""

        optimized += "// Original design with clock gating\n"
        optimized += rtl_code.replace(
            'always @(posedge clk',
            '// Use gated_clk instead\nalways @(posedge gated_clk',
        )

        return optimized

    def _apply_operand_isolation(self, rtl_code: str) -> str:
        """Apply operand isolation."""
        optimized = "// Operand-isolated version\n\n"
        optimized += "// Add AND gates on arithmetic operands when not enabled\n"
        optimized += rtl_code
        optimized += """
// Operand isolation
wire [WIDTH-1:0] isolated_a = enable ? a : '0;
wire [WIDTH-1:0] isolated_b = enable ? b : '0;
// Use isolated_a and isolated_b in arithmetic operations
"""
        return optimized


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == '__main__':
    print('Power Optimizer Self-Test\n')

    optimizer = PowerOptimizer()

    power_results = {
        'total_power': {'total_power_mw': 45.0},
        'breakdown': {
            'clock_percent': 35.0,
            'logic_percent': 30.0,
            'register_percent': 20.0,
            'leakage_percent': 15.0,
        },
        'design_info': {
            'registers': 64,
            'combinational_gates': 200,
            'adders': 4,
            'multipliers': 2,
        },
    }

    rtl_code = """
module processor_core(
    input clk,
    input rst,
    input enable,
    input [31:0] data_in,
    output reg [31:0] data_out
);
    reg [31:0] registers [0:31];

    always @(posedge clk) begin
        if (enable) begin
            data_out <= registers[0] + data_in;
        end
    end
endmodule
"""

    suggestions = optimizer.analyze_and_suggest(
        rtl_code,
        power_results,
        target_power_mw=30.0,
    )

    if suggestions['suggestions']:
        print('\nGenerating optimized code for: Clock Gating')
        optimized_code = optimizer.generate_optimization_code(rtl_code, 'clock_gating')
        print('\nOptimized code preview:')
        print(optimized_code[:500] + '...')

    print('\nSelf-test complete')
