"""
Power Analyzer

Estimates power consumption of RTL designs.

Usage:
    from python.power_analyzer import PowerAnalyzer

    analyzer = PowerAnalyzer()
    result = analyzer.analyze_power(rtl_code, module_name, frequency_mhz)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class PowerAnalyzer:
    """Power consumption analysis."""

    def __init__(self):
        """Initialize power analyzer."""
        # Technology parameters (simplified for 45nm)
        self.tech_params = {
            'technology_nm': 45,
            'supply_voltage_v': 1.1,
            'vt_voltage_v': 0.4,
            'gate_capacitance_pf': 0.5,
            'wire_capacitance_pf_mm': 0.2,
            'leakage_current_na_gate': 1.0,
        }

        # Activity factors (typical values)
        self.activity_factors = {
            'clock': 1.0,
            'data': 0.25,
            'control': 0.15,
        }

        # Component power models
        self.component_power = {
            'and_gate': {'dynamic_pj': 0.1, 'leakage_nw': 1.0},
            'or_gate': {'dynamic_pj': 0.1, 'leakage_nw': 1.0},
            'xor_gate': {'dynamic_pj': 0.15, 'leakage_nw': 1.2},
            'not_gate': {'dynamic_pj': 0.05, 'leakage_nw': 0.5},
            'mux': {'dynamic_pj': 0.2, 'leakage_nw': 2.0},
            'flipflop': {'dynamic_pj': 0.5, 'leakage_nw': 3.0},
            'adder_bit': {'dynamic_pj': 1.0, 'leakage_nw': 5.0},
            'multiplier_bit': {'dynamic_pj': 2.0, 'leakage_nw': 10.0},
        }

    def analyze_power(
        self,
        rtl_code: str,
        module_name: str,
        frequency_mhz: float = 100.0,
        activity_factor: float = 0.25,
    ) -> Dict:
        """
        Analyze power consumption.

        Args:
            rtl_code: RTL code
            module_name: Module name
            frequency_mhz: Operating frequency in MHz
            activity_factor: Switching activity factor (0-1)

        Returns:
            dict: Power analysis results
        """
        print(f"\n{'=' * 70}")
        print(f"POWER ANALYSIS: {module_name}")
        print(f"{'=' * 70}")

        # Analyze design structure
        design_info = self._analyze_design_structure(rtl_code)

        # Estimate dynamic power
        dynamic_power = self._estimate_dynamic_power(
            design_info,
            frequency_mhz,
            activity_factor,
        )

        # Estimate leakage power
        leakage_power = self._estimate_leakage_power(design_info)

        # Calculate total power
        total_power = {
            'dynamic_power_mw': dynamic_power['total_mw'],
            'leakage_power_mw': leakage_power['total_mw'],
            'total_power_mw': dynamic_power['total_mw'] + leakage_power['total_mw'],
            'frequency_mhz': frequency_mhz,
            'activity_factor': activity_factor,
        }

        results = {
            'module_name': module_name,
            'design_info': design_info,
            'dynamic_power': dynamic_power,
            'leakage_power': leakage_power,
            'total_power': total_power,
            'breakdown': self._create_power_breakdown(dynamic_power, leakage_power),
        }

        # Print summary
        self._print_power_summary(results)

        return results

    def _analyze_design_structure(self, rtl_code: str) -> Dict:
        """Analyze design structure for power estimation."""
        info = {
            'registers': 0,
            'combinational_gates': 0,
            'muxes': 0,
            'adders': 0,
            'multipliers': 0,
            'clock_signals': 0,
            'bit_width': 8,
            'is_sequential': False,
        }

        # Count registers
        info['registers'] = len(re.findall(r'\breg\s+', rtl_code))

        # Check if sequential
        info['is_sequential'] = 'always @(posedge' in rtl_code

        # Count clock signals
        info['clock_signals'] = rtl_code.count('clk')

        # Estimate combinational gates from operators (rough)
        info['combinational_gates'] = (
            rtl_code.count('&')
            + rtl_code.count('|')
            + rtl_code.count('^')
            + rtl_code.count('~')
        )

        # Count muxes (? : operator and case statements)
        info['muxes'] = rtl_code.count('?') + rtl_code.count('case')

        # Count adders/subtractors
        info['adders'] = rtl_code.count('+') + rtl_code.count('-')

        # Count multipliers
        info['multipliers'] = rtl_code.count('*')

        # Estimate bit width
        width_matches = re.findall(r'\[(\d+):0\]', rtl_code)
        if width_matches:
            info['bit_width'] = max(int(w) for w in width_matches) + 1

        return info

    def _estimate_dynamic_power(
        self,
        design_info: Dict,
        frequency_mhz: float,
        activity_factor: float,
    ) -> Dict:
        """Estimate dynamic power consumption."""
        power = {
            'clock_power_mw': 0.0,
            'logic_power_mw': 0.0,
            'register_power_mw': 0.0,
            'total_mw': 0.0,
        }

        # Clock power (typically highest activity)
        if design_info['is_sequential']:
            clock_activity = self.activity_factors['clock']
            clock_capacitance = (
                design_info['registers'] * self.tech_params['gate_capacitance_pf']
            )

            # P = alpha * C * V^2 * f
            power['clock_power_mw'] = (
                clock_activity
                * clock_capacitance
                * 1e-12
                * self.tech_params['supply_voltage_v'] ** 2
                * frequency_mhz
                * 1e6
                * 1000
            )

        # Register power
        register_energy = self.component_power['flipflop']['dynamic_pj']
        power['register_power_mw'] = (
            design_info['registers']
            * register_energy
            * 1e-12
            * frequency_mhz
            * 1e6
            * activity_factor
            * 1000
        )

        # Logic power
        gate_energy = self.component_power['and_gate']['dynamic_pj']
        logic_power = (
            design_info['combinational_gates']
            * gate_energy
            * 1e-12
            * frequency_mhz
            * 1e6
            * activity_factor
            * 1000
        )

        mux_energy = self.component_power['mux']['dynamic_pj']
        logic_power += (
            design_info['muxes']
            * mux_energy
            * 1e-12
            * frequency_mhz
            * 1e6
            * activity_factor
            * 1000
        )

        adder_energy = self.component_power['adder_bit']['dynamic_pj']
        logic_power += (
            design_info['adders']
            * design_info['bit_width']
            * adder_energy
            * 1e-12
            * frequency_mhz
            * 1e6
            * activity_factor
            * 1000
        )

        mult_energy = self.component_power['multiplier_bit']['dynamic_pj']
        logic_power += (
            design_info['multipliers']
            * design_info['bit_width']
            * mult_energy
            * 1e-12
            * frequency_mhz
            * 1e6
            * activity_factor
            * 1000
        )

        power['logic_power_mw'] = logic_power

        power['total_mw'] = (
            power['clock_power_mw']
            + power['logic_power_mw']
            + power['register_power_mw']
        )

        return power

    def _estimate_leakage_power(self, design_info: Dict) -> Dict:
        """Estimate leakage (static) power consumption."""
        power = {
            'register_leakage_mw': 0.0,
            'logic_leakage_mw': 0.0,
            'total_mw': 0.0,
        }

        register_leakage = self.component_power['flipflop']['leakage_nw']
        power['register_leakage_mw'] = (
            design_info['registers'] * register_leakage * 1e-9 * 1000
        )

        gate_leakage = self.component_power['and_gate']['leakage_nw']
        logic_leakage = (
            design_info['combinational_gates'] * gate_leakage * 1e-9 * 1000
        )

        mux_leakage = self.component_power['mux']['leakage_nw']
        logic_leakage += design_info['muxes'] * mux_leakage * 1e-9 * 1000

        adder_leakage = self.component_power['adder_bit']['leakage_nw']
        logic_leakage += (
            design_info['adders']
            * design_info['bit_width']
            * adder_leakage
            * 1e-9
            * 1000
        )

        power['logic_leakage_mw'] = logic_leakage
        power['total_mw'] = power['register_leakage_mw'] + power['logic_leakage_mw']

        return power

    def _create_power_breakdown(
        self,
        dynamic_power: Dict,
        leakage_power: Dict,
    ) -> Dict:
        """Create power breakdown by component."""
        total_power = dynamic_power['total_mw'] + leakage_power['total_mw']
        breakdown = {}

        if total_power > 0:
            breakdown['clock_percent'] = dynamic_power['clock_power_mw'] / total_power * 100
            breakdown['logic_percent'] = dynamic_power['logic_power_mw'] / total_power * 100
            breakdown['register_percent'] = (
                dynamic_power['register_power_mw'] / total_power * 100
            )
            breakdown['leakage_percent'] = leakage_power['total_mw'] / total_power * 100
            breakdown['dynamic_percent'] = dynamic_power['total_mw'] / total_power * 100
            breakdown['static_percent'] = leakage_power['total_mw'] / total_power * 100

        return breakdown

    def _print_power_summary(self, results: Dict):
        """Print power summary."""
        total = results['total_power']
        breakdown = results['breakdown']

        print("\nOperating Conditions:")
        print(f"  Frequency: {total['frequency_mhz']:.2f} MHz")
        print(f"  Activity factor: {total['activity_factor']:.2f}")
        print(f"  Technology: {self.tech_params['technology_nm']}nm")
        print(f"  Supply voltage: {self.tech_params['supply_voltage_v']:.2f}V")

        print("\nPower Consumption:")
        print(
            f"  Dynamic power: {total['dynamic_power_mw']:.4f} mW "
            f"({breakdown.get('dynamic_percent', 0):.1f}%)"
        )
        print(f"    - Clock: {results['dynamic_power']['clock_power_mw']:.4f} mW")
        print(f"    - Logic: {results['dynamic_power']['logic_power_mw']:.4f} mW")
        print(f"    - Registers: {results['dynamic_power']['register_power_mw']:.4f} mW")
        print(
            f"  Leakage power: {total['leakage_power_mw']:.4f} mW "
            f"({breakdown.get('static_percent', 0):.1f}%)"
        )
        print(f"\n  TOTAL POWER: {total['total_power_mw']:.4f} mW")

        if results['design_info']['bit_width'] > 0:
            power_per_bit = total['total_power_mw'] / results['design_info']['bit_width']
            print(f"\n  Power per bit: {power_per_bit:.4f} mW/bit")

    def compare_power_scenarios(
        self,
        rtl_code: str,
        module_name: str,
        scenarios: List[Dict],
    ) -> Dict:
        """
        Compare power across different scenarios.

        Args:
            rtl_code: RTL code
            module_name: Module name
            scenarios: List of scenarios (freq, activity)

        Returns:
            dict: Comparison results
        """
        print(f"\n{'=' * 70}")
        print(f"POWER SCENARIO ANALYSIS: {module_name}")
        print(f"{'=' * 70}")

        results = []

        for i, scenario in enumerate(scenarios, 1):
            freq = scenario.get('frequency_mhz', 100.0)
            activity = scenario.get('activity_factor', 0.25)
            name = scenario.get('name', f'Scenario {i}')

            print(f"\n[{i}/{len(scenarios)}] {name}:")
            print(f"  Frequency: {freq} MHz, Activity: {activity}")

            power_result = self.analyze_power(rtl_code, module_name, freq, activity)

            results.append({
                'name': name,
                'scenario': scenario,
                'power': power_result,
            })

        print(f"\n{'=' * 70}")
        print("SCENARIO COMPARISON")
        print(f"{'=' * 70}")
        print(f"\n{'Scenario':<20} {'Freq (MHz)':<12} {'Activity':<10} {'Power (mW)':<12}")
        print('-' * 70)

        for result in results:
            print(
                f"{result['name']:<20} "
                f"{result['scenario']['frequency_mhz']:<12.1f} "
                f"{result['scenario']['activity_factor']:<10.2f} "
                f"{result['power']['total_power']['total_power_mw']:<12.4f}"
            )

        return {
            'scenarios': results,
            'best_power': min(
                results,
                key=lambda x: x['power']['total_power']['total_power_mw'],
            ),
            'worst_power': max(
                results,
                key=lambda x: x['power']['total_power']['total_power_mw'],
            ),
        }

    def generate_power_report(
        self,
        results: Dict,
        output_file: Optional[str] = None,
    ) -> str:
        """Generate power analysis report."""
        if output_file is None:
            output_file = (
                f"power_report_{results['module_name']}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )

        total = results['total_power']
        breakdown = results['breakdown']

        report = f"""# Power Analysis Report

**Module:** {results['module_name']}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Operating Conditions

- **Frequency:** {total['frequency_mhz']:.2f} MHz
- **Activity Factor:** {total['activity_factor']:.2f}
- **Technology:** {self.tech_params['technology_nm']}nm
- **Supply Voltage:** {self.tech_params['supply_voltage_v']:.2f}V

---

## Power Summary

| Component | Power (mW) | Percentage |
|-----------|------------|------------|
| Dynamic Power | {total['dynamic_power_mw']:.4f} | {breakdown.get('dynamic_percent', 0):.1f}% |
| - Clock | {results['dynamic_power']['clock_power_mw']:.4f} | {breakdown.get('clock_percent', 0):.1f}% |
| - Logic | {results['dynamic_power']['logic_power_mw']:.4f} | {breakdown.get('logic_percent', 0):.1f}% |
| - Registers | {results['dynamic_power']['register_power_mw']:.4f} | {breakdown.get('register_percent', 0):.1f}% |
| Leakage Power | {total['leakage_power_mw']:.4f} | {breakdown.get('static_percent', 0):.1f}% |
| **TOTAL** | **{total['total_power_mw']:.4f}** | **100%** |

---

## Design Statistics

- **Registers:** {results['design_info']['registers']}
- **Combinational Gates:** {results['design_info']['combinational_gates']}
- **Muxes:** {results['design_info']['muxes']}
- **Adders:** {results['design_info']['adders']}
- **Multipliers:** {results['design_info']['multipliers']}
- **Bit Width:** {results['design_info']['bit_width']}

---

## Power Efficiency

- **Power per bit:** {total['total_power_mw'] / results['design_info']['bit_width']:.4f} mW/bit
- **Energy per operation:** {total['total_power_mw'] / total['frequency_mhz']:.4f} pJ

---

## Recommendations

"""

        if breakdown.get('clock_percent', 0) > 40:
            report += (
                f"- Clock power is dominant (>{breakdown['clock_percent']:.1f}%). "
                "Consider clock gating.\n"
            )

        if breakdown.get('leakage_percent', 0) > 30:
            report += (
                f"- High leakage power (>{breakdown['leakage_percent']:.1f}%). "
                "Consider power gating or lower-leakage cells.\n"
            )

        if total['total_power_mw'] > 100:
            report += (
                f"- Total power is high (>{total['total_power_mw']:.1f} mW). "
                "Review design for optimization opportunities.\n"
            )

        if total['total_power_mw'] < 10:
            report += "- Low power design achieved (<10 mW).\n"

        report += (
            "\n---\n\n"
            "Note: These are estimated values. Actual power depends on "
            "technology library and layout.\n"
        )

        Path(output_file).write_text(report)
        print(f"\nPower report saved: {output_file}")

        return output_file


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Power Analyzer Self-Test\n")

    analyzer = PowerAnalyzer()

    rtl_code = """
module counter_16bit(
    input clk,
    input rst,
    input enable,
    output reg [15:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 16'b0;
        else if (enable)
            count <= count + 1;
    end
endmodule
"""

    result = analyzer.analyze_power(rtl_code, 'counter_16bit', 100.0, 0.25)
    report_file = analyzer.generate_power_report(result)

    scenarios = [
        {'name': 'Low Power', 'frequency_mhz': 10, 'activity_factor': 0.1},
        {'name': 'Normal', 'frequency_mhz': 100, 'activity_factor': 0.25},
        {'name': 'High Performance', 'frequency_mhz': 500, 'activity_factor': 0.5},
    ]

    analyzer.compare_power_scenarios(rtl_code, 'counter_16bit', scenarios)

    print("\nSelf-test complete")
