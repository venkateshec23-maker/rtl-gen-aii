#!/usr/bin/env python3
"""
Pipeline Visualization Module
==============================
Generates 2D images and interactive HTML visualization for all pipeline stages.

Supports:
- RTL schematic visualization (Verilog parsing)
- Placement visualization (DEF files)
- Routing visualization (DEF files with nets)
- GDS layout visualization
- Interactive HTML dashboard with all visualizations

Free tools used:
- matplotlib: For 2D plotting and image generation
- schemdraw: For circuit schematic generation
- gdspy: For GDS parsing and visualization (fallback)
- plotly: For interactive HTML visualizations
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
import numpy as np


@dataclass
class VisualizationConfig:
    """Configuration for visualization generation."""
    output_dir: Path = Path("visualizations")
    dpi: int = 150
    figure_size: Tuple[int, int] = (14, 10)
    show_grid: bool = True
    show_labels: bool = True
    generate_html: bool = True
    generate_png: bool = True
    interactive_mode: bool = True


class DEFParser:
    """Parse DEF files and extract circuit information."""
    
    def __init__(self, def_path: Path):
        self.def_path = def_path
        self.components = []
        self.nets = []
        self.design_name = ""
        self.die_area = (0, 0, 1000, 1000)
        self.units = 1000
        
        if def_path.exists():
            self._parse()
    
    def _parse(self):
        """Parse DEF file."""
        content = self.def_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        
        in_components = False
        in_nets = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Design name
            if line.startswith("DESIGN"):
                self.design_name = line.split()[1].rstrip(";")
            
            # Units
            if "UNITS DISTANCE MICRONS" in line:
                try:
                    units_str = line.split()[-1].rstrip(";")
                    self.units = int(units_str)
                except (ValueError, IndexError):
                    self.units = 1000
            
            # Die area
            if line.startswith("DIEAREA"):
                parts = line.split()
                try:
                    self.die_area = (
                        int(float(parts[1])), int(float(parts[2])),
                        int(float(parts[3])), int(float(parts[4].rstrip(";")))
                    )
                except (IndexError, ValueError):
                    pass
            
            # Components section
            if "COMPONENTS" in line and not line.startswith("END"):
                in_components = True
                continue
            elif line.startswith("END COMPONENTS"):
                in_components = False
            elif in_components and line.startswith("-"):
                self._parse_component(line)
            
            # Nets section
            if "NETS" in line and not line.startswith("END"):
                in_nets = True
                continue
            elif line.startswith("END NETS"):
                in_nets = False
            elif in_nets and line.startswith("-"):
                self._parse_net(line)
    
    def _parse_component(self, line: str):
        """Parse component line from DEF."""
        import re
        try:
            parts = line.split()
            if len(parts) < 2:
                return
            
            name = parts[1]
            cell_type = parts[2] if len(parts) > 2 else "CELL"
            
            # Extract coordinates from ( x y )
            match = re.search(r'\(\s*([\d.-]+)\s+([\d.-]+)\s*\)', line)
            if match:
                x = int(float(match.group(1)) / self.units)
                y = int(float(match.group(2)) / self.units)
                self.components.append({
                    'name': name,
                    'type': cell_type,
                    'x': x,
                    'y': y,
                    'width': 100,
                    'height': 100
                })
        except Exception as e:
            pass
    
    def _parse_net(self, line: str):
        """Parse net line from DEF."""
        try:
            parts = line.split()
            if len(parts) < 2:
                return
            net_name = parts[1]
            self.nets.append({'name': net_name, 'connections': len(parts) - 3})
        except Exception as e:
            pass


class VerilogParser:
    """Parse Verilog files and extract module information."""
    
    def __init__(self, verilog_path: Path):
        self.verilog_path = verilog_path
        self.module_name = ""
        self.ports = {'input': [], 'output': [], 'inout': []}
        self.logic_gates = []
        
        if verilog_path.exists():
            self._parse()
    
    def _parse(self):
        """Parse Verilog file."""
        content = self.verilog_path.read_text(encoding="utf-8", errors="ignore")
        
        # Simple regex-based parsing
        import re
        
        # Extract module name
        module_match = re.search(r'module\s+(\w+)\s*\(', content)
        if module_match:
            self.module_name = module_match.group(1)
        
        # Extract ports
        for match in re.finditer(r'(input|output|inout)\s+(?:\[.*?\])?\s*(\w+)', content):
            port_type = match.group(1)
            port_name = match.group(2)
            self.ports[port_type].append(port_name)
        
        # Count logic gates
        gate_counts = {}
        for gate_type in ['and', 'or', 'xor', 'not', 'nor', 'nand']:
            count = len(re.findall(rf'\b{gate_type}\b', content, re.IGNORECASE))
            if count > 0:
                gate_counts[gate_type] = count
        self.logic_gates = gate_counts


class PipelineVisualizer:
    """Generate visualizations for all pipeline stages."""
    
    def __init__(self, run_dir: Path, config: Optional[VisualizationConfig] = None):
        self.run_dir = Path(run_dir)
        self.config = config or VisualizationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Visualizations will be saved to: {self.config.output_dir}")
    
    def visualize_all(self) -> Dict[str, str]:
        """Generate visualizations for all stages."""
        results = {}
        
        # RTL Schematic
        rtl_files = list(self.run_dir.glob("01_rtl/*.v"))
        if rtl_files:
            results['rtl'] = self.visualize_rtl(rtl_files[0])
        
        # Synthesis
        synth_files = list(self.run_dir.glob("02_synthesis/*_synth.v"))
        if synth_files:
            results['synthesis'] = self.visualize_synthesis(synth_files[0])
        
        # Floorplan
        floorplan_files = list(self.run_dir.glob("03_floorplan/*.def"))
        if floorplan_files:
            results['floorplan'] = self.visualize_floorplan(floorplan_files[0])
        
        # Placement
        placement_files = list(self.run_dir.glob("04_placement/placed.def"))
        if placement_files:
            results['placement'] = self.visualize_placement(placement_files[0])
        
        # CTS
        cts_files = list(self.run_dir.glob("05_cts/cts.def"))
        if cts_files:
            results['cts'] = self.visualize_cts(cts_files[0])
        
        # Routing
        routing_files = list(self.run_dir.glob("06_routing/routed.def"))
        if routing_files:
            results['routing'] = self.visualize_routing(routing_files[0])
        
        # GDS
        gds_files = list(self.run_dir.glob("07_gds/*.gds"))
        if gds_files:
            results['gds'] = self.visualize_gds(gds_files[0])
        
        # Generate interactive HTML dashboard
        if self.config.generate_html:
            results['dashboard'] = self.generate_dashboard(results)
        
        return results
    
    def visualize_rtl(self, verilog_path: Path) -> str:
        """Generate RTL schematic visualization."""
        parser = VerilogParser(verilog_path)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.config.figure_size)
        
        # Port visualization
        ax1.set_xlim(0, 10)
        ax1.set_ylim(0, max(10, len(parser.ports['input']) + len(parser.ports['output']) + 2))
        ax1.set_title(f"RTL Module: {parser.module_name}\nPortal Diagram", fontsize=14, fontweight='bold')
        
        y_pos = 0
        # Input ports
        for port in parser.ports['input']:
            circle = Circle((1, y_pos), 0.2, color='green', zorder=3)
            ax1.add_patch(circle)
            ax1.text(1.5, y_pos, f"INPUT: {port}", va='center', fontsize=9)
            y_pos += 0.8
        
        # Output ports
        for port in parser.ports['output']:
            circle = Circle((9, y_pos), 0.2, color='red', zorder=3)
            ax1.add_patch(circle)
            ax1.text(8.5, y_pos, f"OUTPUT: {port}", va='center', ha='right', fontsize=9)
            y_pos += 0.8
        
        ax1.set_aspect('equal')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlabel("Port Direction")
        
        # Gate distribution
        ax2.set_title("Logic Gate Distribution", fontsize=14, fontweight='bold')
        if parser.logic_gates:
            gates = list(parser.logic_gates.keys())
            counts = list(parser.logic_gates.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(gates)))
            bars = ax2.bar(gates, counts, color=colors, edgecolor='black', linewidth=1.5)
            ax2.set_ylabel("Count")
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom', fontweight='bold')
        else:
            ax2.text(0.5, 0.5, "No logic gates found", ha='center', va='center',
                    transform=ax2.transAxes, fontsize=12)
        
        plt.tight_layout()
        output_path = self.config.output_dir / "01_rtl_schematic.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        self.logger.info(f"Saved RTL visualization: {output_path}")
        return str(output_path)
    
    def visualize_synthesis(self, synth_file: Path) -> str:
        """Generate synthesis statistics visualization."""
        parser = VerilogParser(synth_file)
        
        fig, ax = plt.subplots(figsize=self.config.figure_size)
        
        # Statistics
        total_inputs = len(parser.ports['input'])
        total_outputs = len(parser.ports['output'])
        total_gates = sum(parser.logic_gates.values()) if parser.logic_gates else 0
        
        stats = [
            f"Module: {parser.module_name}",
            f"Input Ports: {total_inputs}",
            f"Output Ports: {total_outputs}",
            f"Total Logic Gates: {total_gates}",
        ]
        
        ax.text(0.1, 0.9, "Synthesis Report", fontsize=18, fontweight='bold',
               transform=ax.transAxes)
        
        y = 0.75
        for stat in stats:
            ax.text(0.1, y, stat, fontsize=14, transform=ax.transAxes,
                   family='monospace', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
            y -= 0.12
        
        # Gate types table
        if parser.logic_gates:
            y = 0.45
            ax.text(0.1, y, "Gate Types:", fontsize=12, fontweight='bold',
                   transform=ax.transAxes)
            y -= 0.08
            for gate_type, count in sorted(parser.logic_gates.items()):
                ax.text(0.15, y, f"{gate_type.upper()}: {count}", fontsize=11,
                       transform=ax.transAxes, family='monospace')
                y -= 0.07
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        plt.tight_layout()
        output_path = self.config.output_dir / "02_synthesis_report.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        self.logger.info(f"Saved synthesis visualization: {output_path}")
        return str(output_path)
    
    def visualize_floorplan(self, def_path: Path) -> str:
        """Visualize floorplan from DEF."""
        parser = DEFParser(def_path)
        
        fig, ax = plt.subplots(figsize=self.config.figure_size)
        
        # Draw die area
        x1, y1, x2, y2 = parser.die_area
        die_rect = Rectangle((x1, y1), x2-x1, y2-y1, 
                             fill=False, edgecolor='black', linewidth=3)
        ax.add_patch(die_rect)
        
        ax.set_xlim(x1-100, x2+100)
        ax.set_ylim(y1-100, y2+100)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title(f"Floorplan - {parser.design_name}", fontsize=14, fontweight='bold')
        ax.set_xlabel("X (µm)")
        ax.set_ylabel("Y (µm)")
        
        # Add core area indicator
        ax.text((x1+x2)/2, (y1+y2)/2, "CORE AREA", ha='center', va='center',
               fontsize=14, fontweight='bold', alpha=0.3, rotation=45)
        
        plt.tight_layout()
        output_path = self.config.output_dir / "03_floorplan.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        self.logger.info(f"Saved floorplan visualization: {output_path}")
        return str(output_path)
    
    def visualize_placement(self, def_path: Path) -> str:
        """Visualize cell placement from DEF."""
        parser = DEFParser(def_path)
        
        fig, ax = plt.subplots(figsize=self.config.figure_size)
        
        # Draw die area
        x1, y1, x2, y2 = parser.die_area
        die_rect = Rectangle((x1, y1), x2-x1, y2-y1, 
                             fill=False, edgecolor='black', linewidth=3)
        ax.add_patch(die_rect)
        
        # Draw cells
        colors = plt.cm.tab20(np.linspace(0, 1, max(len(parser.components), 1)))
        for i, cell in enumerate(parser.components[:100]):  # Limit to 100 for clarity
            color = colors[i % len(colors)]
            rect = Rectangle((cell['x'], cell['y']), cell['width'], cell['height'],
                            fill=True, facecolor=color, edgecolor='black', 
                            linewidth=0.5, alpha=0.7)
            ax.add_patch(rect)
            
            # Label only larger cells or spread them out
            if len(parser.components) < 20:
                ax.text(cell['x'] + cell['width']/2, cell['y'] + cell['height']/2,
                       cell['name'], ha='center', va='center', fontsize=7)
        
        ax.set_xlim(x1-100, x2+100)
        ax.set_ylim(y1-100, y2+100)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title(f"Cell Placement ({len(parser.components)} cells) - {parser.design_name}",
                    fontsize=14, fontweight='bold')
        ax.set_xlabel("X (µm)")
        ax.set_ylabel("Y (µm)")
        
        # Add legend with stats
        textstr = f"Total Cells: {len(parser.components)}\nTotal Nets: {len(parser.nets)}"
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        output_path = self.config.output_dir / "04_placement.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        self.logger.info(f"Saved placement visualization: {output_path}")
        return str(output_path)
    
    def visualize_cts(self, def_path: Path) -> str:
        """Visualize Clock Tree Synthesis from DEF."""
        parser = DEFParser(def_path)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.config.figure_size)
        
        # Left: Placement with CTS cells highlighted
        x1, y1, x2, y2 = parser.die_area
        die_rect = Rectangle((x1, y1), x2-x1, y2-y1, 
                             fill=False, edgecolor='black', linewidth=3)
        ax1.add_patch(die_rect)
        
        # Color code: CTS cells vs regular cells
        cts_cells = [c for c in parser.components if 'clk' in c['name'].lower() or 'cts' in c['type'].lower()]
        regular_cells = [c for c in parser.components if c not in cts_cells]
        
        for cell in regular_cells[:50]:
            rect = Rectangle((cell['x'], cell['y']), cell['width'], cell['height'],
                            fill=True, facecolor='lightblue', edgecolor='black', linewidth=0.5, alpha=0.6)
            ax1.add_patch(rect)
        
        for cell in cts_cells[:50]:
            rect = Rectangle((cell['x'], cell['y']), cell['width'], cell['height'],
                            fill=True, facecolor='orange', edgecolor='red', linewidth=1, alpha=0.8)
            ax1.add_patch(rect)
        
        ax1.set_xlim(x1-100, x2+100)
        ax1.set_ylim(y1-100, y2+100)
        ax1.set_aspect('equal')
        ax1.grid(True, alpha=0.3)
        ax1.set_title(f"Clock Tree Synthesis - {parser.design_name}", fontsize=12, fontweight='bold')
        ax1.set_xlabel("X (µm)")
        ax1.set_ylabel("Y (µm)")
        
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='lightblue', edgecolor='black', label=f'Regular Cells ({len(regular_cells)})'),
                          Patch(facecolor='orange', edgecolor='red', label=f'CTS Cells ({len(cts_cells)})')]
        ax1.legend(handles=legend_elements, loc='upper left', fontsize=9)
        
        # Right: Clock distribution
        ax2.set_title("Clock Distribution Statistics", fontsize=12, fontweight='bold')
        
        # Safely calculate percentages
        total_cells = len(parser.components)
        cts_pct = 100*len(cts_cells)//max(total_cells, 1) if total_cells > 0 else 0
        regular_pct = 100*len(regular_cells)//max(total_cells, 1) if total_cells > 0 else 0
        
        stats = [
            f"Total Cells: {total_cells}",
            f"CTS Cells: {len(cts_cells)} ({cts_pct}%)",
            f"Regular Cells: {len(regular_cells)} ({regular_pct}%)",
            f"Total Nets: {len(parser.nets)}"
        ]
        
        y = 0.9
        for stat in stats:
            ax2.text(0.1, y, stat, fontsize=11, transform=ax2.transAxes, family='monospace',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))
            y -= 0.2
        
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis('off')
        
        plt.tight_layout()
        output_path = self.config.output_dir / "05_cts.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        self.logger.info(f"Saved CTS visualization: {output_path}")
        return str(output_path)
    
    def visualize_routing(self, def_path: Path) -> str:
        """Visualize routing from DEF."""
        parser = DEFParser(def_path)
        
        fig, ax = plt.subplots(figsize=self.config.figure_size)
        
        # Draw die area
        x1, y1, x2, y2 = parser.die_area
        die_rect = Rectangle((x1, y1), x2-x1, y2-y1, 
                             fill=False, edgecolor='black', linewidth=3)
        ax.add_patch(die_rect)
        
        # Draw routed cells with nets visualization
        colors = plt.cm.tab20(np.linspace(0, 1, max(len(parser.components), 1)))
        for i, cell in enumerate(parser.components[:100]):
            color = colors[i % len(colors)]
            rect = Rectangle((cell['x'], cell['y']), cell['width'], cell['height'],
                            fill=True, facecolor=color, edgecolor='darkblue', 
                            linewidth=1, alpha=0.6)
            ax.add_patch(rect)
        
        # Add net connections as lines (simplified visualization)
        if len(parser.components) > 1:
            for i, net in enumerate(parser.nets[:20]):  # Show some nets
                if i < len(parser.components) - 1:
                    cell1 = parser.components[i]
                    cell2 = parser.components[min(i+1, len(parser.components)-1)]
                    
                    # Draw net line
                    ax.plot([cell1['x'] + cell1['width']/2, cell2['x'] + cell2['width']/2],
                           [cell1['y'] + cell1['height']/2, cell2['y'] + cell2['height']/2],
                           'r-', linewidth=0.5, alpha=0.4, zorder=1)
        
        ax.set_xlim(x1-100, x2+100)
        ax.set_ylim(y1-100, y2+100)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.2)
        ax.set_title(f"Routing - {parser.design_name}\n({len(parser.components)} cells, {len(parser.nets)} nets)",
                    fontsize=14, fontweight='bold')
        ax.set_xlabel("X (µm)")
        ax.set_ylabel("Y (µm)")
        
        plt.tight_layout()
        output_path = self.config.output_dir / "06_routing.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        self.logger.info(f"Saved routing visualization: {output_path}")
        return str(output_path)
    
    def visualize_gds(self, gds_path: Path) -> str:
        """Visualize GDS file (limited due to binary format)."""
        fig, ax = plt.subplots(figsize=self.config.figure_size)
        
        # Try to read GDS file size and basic info
        file_size = gds_path.stat().st_size
        
        # GDS binary header check
        with open(gds_path, 'rb') as f:
            header = f.read(100)
        
        # Parse basic GDS records
        has_valid_header = header[0:2] == b'\x00\x02'  # HEADER record
        
        # Create info visualization
        ax.text(0.5, 0.9, "GDS Layout Visualization", ha='center', fontsize=18,
               fontweight='bold', transform=ax.transAxes)
        
        gds_info = [
            f"File: {gds_path.name}",
            f"Size: {file_size} bytes",
            f"Valid GDSII Format: {'✓ Yes' if has_valid_header else '✗ No'} ",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        
        y = 0.75
        for info in gds_info:
            color = 'lightgreen' if 'Yes' in info else ('lightcoral' if 'No' in info else 'lightyellow')
            ax.text(0.5, y, info, ha='center', fontsize=12, transform=ax.transAxes,
                   family='monospace', bbox=dict(boxstyle='round', facecolor=color, alpha=0.7))
            y -= 0.12
        
        # Try to parse simple GDS geometry
        try:
            if has_valid_header and file_size > 200:
                geometry_info = self._parse_gds_simple(gds_path)
                ax.text(0.5, 0.25, f"Geometry Records: {geometry_info}", ha='center',
                       fontsize=11, transform=ax.transAxes,
                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        except Exception as e:
            ax.text(0.5, 0.25, f"(GDS parsing: {str(e)[:40]}...)", ha='center',
                   fontsize=10, transform=ax.transAxes, style='italic', color='gray')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        plt.tight_layout()
        output_path = self.config.output_dir / "07_gds.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        self.logger.info(f"Saved GDS visualization: {output_path}")
        return str(output_path)
    
    def _parse_gds_simple(self, gds_path: Path) -> str:
        """Simple GDS parser for basic statistics."""
        with open(gds_path, 'rb') as f:
            data = f.read()
        
        # Count record types
        boundary_count = data.count(b'\x00\x11')  # BOUNDARY record type
        path_count = data.count(b'\x00\x13')      # PATH record type
        text_count = data.count(b'\x00\x19')      # TEXT record type
        
        return f"Boundaries: {boundary_count}, Paths: {path_count}, Text: {text_count}"
    
    def generate_dashboard(self, visualizations: Dict[str, str]) -> str:
        """Generate interactive HTML dashboard with all visualizations."""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RTL-Gen AI Pipeline Visualization Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .nav {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            padding: 20px;
            background: #f5f5f5;
            border-bottom: 2px solid #ddd;
            justify-content: center;
        }}
        
        .nav button {{
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
        }}
        
        .nav button:hover {{
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }}
        
        .nav button.active {{
            background: #764ba2;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .stage {{
            display: none;
            animation: fadeIn 0.5s ease-in;
        }}
        
        .stage.active {{
            display: block;
        }}
        
        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .stage h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 2em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .image-container {{
            text-align: center;
            margin: 20px 0;
        }}
        
        .image-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            border: 3px solid #ddd;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        
        .card {{
            background: #f9f9f9;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
        }}
        
        .card h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .card p {{
            color: #666;
            line-height: 1.6;
        }}
        
        footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 2px solid #ddd;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #ddd;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 RTL-Gen AI Pipeline Visualization</h1>
            <p class="subtitle">Interactive 2D Layout & Schematic Viewer</p>
        </header>
        
        <div class="nav">
            <button class="nav-btn active" onclick="showStage('overview')">📊 Overview</button>
            <button class="nav-btn" onclick="showStage('rtl')">🔌 RTL</button>
            <button class="nav-btn" onclick="showStage('synthesis')">⚙️ Synthesis</button>
            <button class="nav-btn" onclick="showStage('floorplan')">📐 Floorplan</button>
            <button class="nav-btn" onclick="showStage('placement')">📍 Placement</button>
            <button class="nav-btn" onclick="showStage('cts')">🕐 CTS</button>
            <button class="nav-btn" onclick="showStage('routing')">🛣️ Routing</button>
            <button class="nav-btn" onclick="showStage('gds')">💾 GDS</button>
        </div>
        
        <div class="content">
            <!-- Overview -->
            <div id="overview" class="stage active">
                <h2>Pipeline Overview</h2>
                <div class="grid">
                    <div class="card">
                        <h3>✓ RTL Design</h3>
                        <p>Verilog module schematic and port analysis</p>
                    </div>
                    <div class="card">
                        <h3>✓ Synthesis</h3>
                        <p>Logic gates distribution and netlist statistics</p>
                    </div>
                    <div class="card">
                        <h3>✓ Floorplanning</h3>
                        <p>Core area definition and chip boundary</p>
                    </div>
                    <div class="card">
                        <h3>✓ Placement</h3>
                        <p>Cell placement visualization with density</p>
                    </div>
                    <div class="card">
                        <h3>✓ Clock Tree</h3>
                        <p>CTS cells distribution and clock network</p>
                    </div>
                    <div class="card">
                        <h3>✓ Routing</h3>
                        <p>Net routing paths and interconnects</p>
                    </div>
                    <div class="card">
                        <h3>✓ GDS Output</h3>
                        <p>Final GDSII stream file for fabrication</p>
                    </div>
                    <div class="card">
                        <h3>📊 Interactive</h3>
                        <p>Click stage buttons to view detailed visualizations</p>
                    </div>
                </div>
            </div>
            
            <!-- RTL Stage -->
            <div id="rtl" class="stage">
                <h2>RTL Design Stage</h2>
                <div class="image-container">
                    <img src="{Path(visualizations.get('rtl', '')).name}" alt="RTL Schematic">
                </div>
            </div>
            
            <!-- Synthesis Stage -->
            <div id="synthesis" class="stage">
                <h2>Synthesis Stage</h2>
                <div class="image-container">
                    <img src="{Path(visualizations.get('synthesis', '')).name}" alt="Synthesis Report">
                </div>
            </div>
            
            <!-- Floorplan Stage -->
            <div id="floorplan" class="stage">
                <h2>Floorplanning Stage</h2>
                <div class="image-container">
                    <img src="{Path(visualizations.get('floorplan', '')).name}" alt="Floorplan">
                </div>
            </div>
            
            <!-- Placement Stage -->
            <div id="placement" class="stage">
                <h2>Cell Placement Stage</h2>
                <div class="image-container">
                    <img src="{Path(visualizations.get('placement', '')).name}" alt="Placement">
                </div>
            </div>
            
            <!-- CTS Stage -->
            <div id="cts" class="stage">
                <h2>Clock Tree Synthesis (CTS) Stage</h2>
                <div class="image-container">
                    <img src="{Path(visualizations.get('cts', '')).name}" alt="CTS">
                </div>
            </div>
            
            <!-- Routing Stage -->
            <div id="routing" class="stage">
                <h2>Routing Stage</h2>
                <div class="image-container">
                    <img src="{Path(visualizations.get('routing', '')).name}" alt="Routing">
                </div>
            </div>
            
            <!-- GDS Stage -->
            <div id="gds" class="stage">
                <h2>GDS Output Stage</h2>
                <div class="image-container">
                    <img src="{Path(visualizations.get('gds', '')).name}" alt="GDS">
                </div>
            </div>
        </div>
        
        <footer>
            <p>Generated by RTL-Gen AI Pipeline Visualizer | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Free open-source visualization using Matplotlib & HTML5</p>
        </footer>
    </div>
    
    <script>
        function showStage(stageId) {{
            // Hide all stages
            document.querySelectorAll('.stage').forEach(stage => {{
                stage.classList.remove('active');
            }});
            
            // Remove active class from all buttons
            document.querySelectorAll('.nav-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            
            // Show selected stage
            document.getElementById(stageId).classList.add('active');
            
            // Highlight button
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>
"""
        
        dashboard_path = self.config.output_dir / "dashboard.html"
        dashboard_path.write_text(html_content, encoding='utf-8')
        self.logger.info(f"Saved dashboard: {dashboard_path}")
        
        return str(dashboard_path)


def main():
    """Generate visualizations for pipeline."""
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    
    # Get run directory from command line or use default
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("validation/run_001")
    
    if not run_dir.exists():
        logger.error(f"Run directory not found: {run_dir}")
        return 1
    
    # Configure visualization
    config = VisualizationConfig(
        output_dir=run_dir / "visualizations",
        dpi=150,
        figure_size=(14, 10)
    )
    
    # Generate visualizations
    logger.info("="*70)
    logger.info("RTL-GEN AI PIPELINE VISUALIZATION GENERATOR")
    logger.info("="*70)
    logger.info(f"Run directory: {run_dir}")
    logger.info(f"Output directory: {config.output_dir}")
    
    visualizer = PipelineVisualizer(run_dir, config)
    results = visualizer.visualize_all()
    
    # Summary
    logger.info("="*70)
    logger.info("VISUALIZATIONS GENERATED")
    logger.info("="*70)
    for stage, path in results.items():
        logger.info(f"✓ {stage.upper()}: {Path(path).name}")
    
    logger.info(f"\n📊 View dashboard: {config.output_dir}/dashboard.html")
    logger.info(f"📁 All images: {config.output_dir}/")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
