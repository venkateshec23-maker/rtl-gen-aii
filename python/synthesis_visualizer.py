"""
Synthesis Visualizer for RTL-Gen AI
Creates visual representations of synthesis results
"""

import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

class SynthesisVisualizer:
    """Create visualizations from synthesis results"""
    
    def __init__(self, output_dir='outputs/synthesis/plots'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_cell_pie_chart(self, synthesis_result: Dict[str, Any], 
                             title: str = "Cell Distribution") -> Optional[str]:
        """Create pie chart of cell types"""
        stats = synthesis_result.get('stats', {})
        cells = stats.get('cells', {})
        
        if not cells:
            return None
        
        # Prepare data
        labels = list(cells.keys())
        sizes = list(cells.values())
        
        # Create plot
        plt.figure(figsize=(10, 8))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
        plt.title(title)
        
        # Save
        output_file = self.output_dir / f"cell_pie_{synthesis_result.get('top_module', 'design')}.png"
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        plt.close()
        
        return str(output_file)
    
    def create_area_bar_chart(self, comparison_result: Dict[str, Any]) -> Optional[str]:
        """Create bar chart comparing area across designs"""
        designs = comparison_result.get('designs', [])
        area = comparison_result.get('area', {})
        
        if not designs or not area:
            return None
        
        # Prepare data
        x = list(range(len(designs)))
        values = [area.get(d, 0) for d in designs]
        
        # Create plot
        plt.figure(figsize=(12, 6))
        bars = plt.bar(x, values, color='skyblue', edgecolor='navy')
        
        # Customize
        plt.xlabel('Design')
        plt.ylabel(f'Area ({comparison_result.get("area_unit", "units")})')
        plt.title('Area Comparison')
        plt.xticks(x, designs, rotation=45, ha='right')
        
        # Add value labels
        for bar, val in zip(bars, values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{val:.1f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Save
        output_file = self.output_dir / "area_comparison.png"
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        plt.close()
        
        return str(output_file)
    
    def create_power_frequency_scatter(self, comparison_result: Dict[str, Any]) -> Optional[str]:
        """Create scatter plot of power vs frequency"""
        designs = comparison_result.get('designs', [])
        power = comparison_result.get('power', {})
        frequency = comparison_result.get('frequency', {})
        
        if not designs or not power or not frequency:
            return None
        
        # Prepare data
        x = [frequency.get(d, 0) for d in designs]
        y = [power.get(d, 0) for d in designs]
        
        # Create plot
        plt.figure(figsize=(10, 8))
        plt.scatter(x, y, s=100, c='red', alpha=0.6, edgecolors='darkred')
        
        # Add labels
        for i, design in enumerate(designs):
            plt.annotate(design, (x[i], y[i]), 
                        xytext=(5, 5), textcoords='offset points')
        
        plt.xlabel('Frequency (MHz)')
        plt.ylabel(f'Power ({comparison_result.get("power_unit", "units")})')
        plt.title('Power vs Frequency Trade-off')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save
        output_file = self.output_dir / "power_vs_frequency.png"
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        plt.close()
        
        return str(output_file)
    
    def create_resource_table_html(self, synthesis_result: Dict[str, Any]) -> str:
        """Create HTML table of synthesis results"""
        stats = synthesis_result.get('stats', {})
        cells = stats.get('cells', {})
        
        html = """
        <style>
            .synth-table {
                border-collapse: collapse;
                width: 100%;
                font-family: monospace;
            }
            .synth-table th, .synth-table td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            .synth-table th {
                background-color: #4CAF50;
                color: white;
            }
            .synth-table tr:nth-child(even) {
                background-color: #f2f2f2;
            }
            .metric-value {
                font-weight: bold;
                color: #2196F3;
            }
        </style>
        """
        
        html += "<h3>Synthesis Results</h3>"
        html += f"<p>Top Module: <b>{synthesis_result.get('top_module', 'unknown')}</b></p>"
        html += f"<p>Technology: <b>{synthesis_result.get('tech_library', 'unknown')}</b></p>"
        html += f"<p>Simulator: <b>{synthesis_result.get('simulator', 'unknown')}</b></p>"
        
        # Main metrics
        html += "<h4>Key Metrics</h4>"
        html += "<table class='synth-table'>"
        html += "<tr><th>Metric</th><th>Value</th></tr>"
        
        metrics = ['area', 'power', 'frequency', 'total_cells']
        for metric in metrics:
            if metric in stats:
                value = stats[metric]
                if metric == 'frequency':
                    html += f"<tr><td>{metric.title()}</td><td class='metric-value'>{value:.1f} MHz</td></tr>"
                elif metric == 'area':
                    unit = 'µm²' if 'asic' in synthesis_result.get('tech_library', '') else 'LUTs'
                    html += f"<tr><td>{metric.title()}</td><td class='metric-value'>{value:.1f} {unit}</td></tr>"
                elif metric == 'power':
                    unit = 'µW/MHz' if 'asic' in synthesis_result.get('tech_library', '') else 'mW'
                    html += f"<tr><td>{metric.title()}</td><td class='metric-value'>{value:.3f} {unit}</td></tr>"
                else:
                    html += f"<tr><td>{metric.title()}</td><td class='metric-value'>{value}</td></tr>"
        
        html += "</table>"
        
        # Cell counts
        if cells:
            html += "<h4>Cell Distribution</h4>"
            html += "<table class='synth-table'>"
            html += "<tr><th>Cell Type</th><th>Count</th></tr>"
            
            for cell, count in cells.items():
                html += f"<tr><td>{cell}</td><td class='metric-value'>{count}</td></tr>"
            
            html += "</table>"
        
        return html
    
    def generate_full_report(self, synthesis_result: Dict[str, Any]) -> str:
        """Generate complete HTML report"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Synthesis Report - RTL-Gen AI</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #4CAF50; }
                .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .success { color: green; }
                .warning { color: orange; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <h1>RTL-Gen AI Synthesis Report</h1>
            <p>Generated: """ + synthesis_result.get('synthesis_time', 'unknown') + """</p>
        """
        
        if synthesis_result.get('success'):
            html += '<p class="success">✅ Synthesis completed successfully</p>'
        else:
            html += f'<p class="error">❌ Synthesis failed: {synthesis_result.get("error", "unknown")}</p>'
        
        # Add resource table
        html += '<div class="section">'
        html += self.create_resource_table_html(synthesis_result)
        html += '</div>'
        
        # Add netlist preview
        netlist = synthesis_result.get('netlist', '')
        if netlist:
            html += '<div class="section">'
            html += '<h3>Netlist Preview</h3>'
            html += '<pre style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto;">'
            # Show first 20 lines
            preview = '\n'.join(netlist.split('\n')[:20])
            html += preview
            if len(netlist.split('\n')) > 20:
                html += '\n... (truncated)'
            html += '</pre>'
            html += '</div>'
        
        html += """
        </body>
        </html>
        """
        
        return html

# Standalone test
if __name__ == "__main__":
    viz = SynthesisVisualizer()
    
    # Mock result for testing
    result = {
        'success': True,
        'top_module': 'test_design',
        'tech_library': 'asic',
        'simulator': 'mock',
        'synthesis_time': '2026-03-19T12:00:00',
        'stats': {
            'area': 1250.5,
            'power': 2.3,
            'frequency': 150.0,
            'total_cells': 450,
            'cells': {
                'AND': 120,
                'OR': 80,
                'NAND': 60,
                'NOR': 40,
                'DFF': 150
            }
        }
    }
    
    html = viz.generate_full_report(result)
    print(html[:500] + "...")
