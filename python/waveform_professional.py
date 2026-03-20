"""
Professional Waveform Visualization
Generates high-quality timing diagrams like industry tools
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ProfessionalWaveformPlot:
    """Generate professional-quality waveform diagrams"""
    
    def __init__(self, width=14, height=8):
        self.width = width
        self.height = height
        self.style_config = {
            'signal_height': 0.8,
            'signal_spacing': 1.2,
            'time_major_step': 50,
            'time_minor_step': 10,
            'colors': {
                'clk': '#1f77b4',
                'data': '#2ca02c',
                'control': '#d62728',
                'state': '#ff7f0e',
                'bus': '#9467bd'
            }
        }
    
    def create_waveform_plot(self, signals: Dict[str, List], time_points: List[int], 
                              title: str = "Timing Diagram") -> plt.Figure:
        """
        Create professional waveform plot
        
        Args:
            signals: dict of signal_name -> list of values
            time_points: list of time points
            title: plot title
        """
        num_signals = len(signals)
        if num_signals == 0:
            logger.warning("No signals to plot")
            return None
        
        fig, axes = plt.subplots(num_signals, 1, figsize=(self.width, self.height))
        
        if num_signals == 1:
            axes = [axes]
        
        fig.suptitle(title, fontsize=14, fontweight='bold')
        
        for idx, (signal_name, values) in enumerate(signals.items()):
            ax = axes[idx]
            
            # Convert time points to ns
            time_ns = [t for t in time_points]
            
            # Create step plot with digital style
            self._plot_digital_waveform(ax, time_ns, values, signal_name)
            
            # Format y-axis
            ax.set_ylim(-0.5, 1.5)
            ax.set_yticks([0, 1])
            ax.set_yticklabels(['0', '1'])
            ax.set_ylabel(signal_name, rotation=0, labelpad=50, ha='right', 
                         fontsize=10, fontweight='bold')
            
            # Grid and styling
            ax.grid(True, axis='x', alpha=0.3, linestyle='--')
            ax.set_xlim(time_ns[0], time_ns[-1])
            
            # Set x-axis ticks
            if len(time_ns) > 1:
                time_range = time_ns[-1] - time_ns[0]
                major_step = max(10, time_range // 10)
                major_ticks = np.arange(time_ns[0], time_ns[-1] + major_step, major_step)
                minor_ticks = np.arange(time_ns[0], time_ns[-1] + major_step//2, major_step//2)
                ax.set_xticks(major_ticks)
                ax.set_xticks(minor_ticks, minor=True)
            
            ax.set_xlabel('Time (ns)' if idx == num_signals - 1 else '', fontsize=10)
            
            # Color based on signal type
            color = self._get_signal_color(signal_name)
            ax.spines['left'].set_color(color)
            ax.tick_params(axis='y', colors=color)
        
        plt.tight_layout()
        return fig
    
    def _plot_digital_waveform(self, ax, time_points, values, signal_name):
        """Plot digital waveform with transitions"""
        try:
            # Convert to numeric
            t = np.array([float(x) for x in time_points])
            v = np.array([float(x) if isinstance(x, (int, float)) else 0 for x in values])
            
            # Create step points
            t_step = []
            v_step = []
            
            for i in range(len(t)):
                t_step.append(t[i])
                v_step.append(v[i])
                if i < len(t) - 1:
                    t_step.append(t[i+1])
                    v_step.append(v[i])
            
            # Plot with color
            color = self._get_signal_color(signal_name)
            ax.step(t_step, v_step, where='post', linewidth=2.5, 
                    color=color, label=signal_name)
            
            # Add markers at transitions
            for i in range(1, len(v)):
                if v[i] != v[i-1]:
                    ax.plot(t[i], v[i], 'o', markersize=6, 
                           color=color, markeredgecolor='black', markeredgewidth=0.5)
        except Exception as e:
            logger.error(f"Error plotting waveform for {signal_name}: {e}")
    
    def _get_signal_color(self, signal_name):
        """Get color based on signal type"""
        signal_lower = signal_name.lower()
        if 'clk' in signal_lower:
            return self.style_config['colors']['clk']
        elif 'data' in signal_lower or 'in' in signal_lower or 'out' in signal_lower:
            return self.style_config['colors']['data']
        elif 'state' in signal_lower or 'cnt' in signal_lower:
            return self.style_config['colors']['state']
        elif 'rst' in signal_lower or 'reset' in signal_lower or 'enable' in signal_lower:
            return self.style_config['colors']['control']
        else:
            return self.style_config['colors']['bus']
    
    def create_bus_waveform(self, signals: Dict[str, List], time_points: List[int],
                             bus_signals: List[str], title: str = "Bus Waveform") -> plt.Figure:
        """Create waveform plot for bus signals (multi-bit)"""
        if not bus_signals:
            logger.warning("No bus signals specified")
            return None
        
        fig, ax = plt.subplots(figsize=(self.width, self.height * 0.6))
        
        # Calculate bus values
        bus_values = []
        for i in range(len(time_points)):
            value = 0
            for bit_idx, bus_sig in enumerate(bus_signals):
                if bus_sig in signals and i < len(signals[bus_sig]):
                    try:
                        val = int(signals[bus_sig][i])
                        value |= (val << bit_idx)
                    except:
                        pass
            bus_values.append(value)
        
        # Plot as analog waveform
        time_ns = [t for t in time_points]
        ax.plot(time_ns, bus_values, linewidth=2.5, color='#9467bd', marker='o', markersize=4)
        ax.fill_between(time_ns, bus_values, alpha=0.2, color='#9467bd')
        
        ax.set_xlabel('Time (ns)', fontsize=10)
        ax.set_ylabel('Value (Hex)', fontsize=10)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add hex labels
        for i, (t, v) in enumerate(zip(time_ns, bus_values)):
            if i % max(1, len(time_ns) // 10) == 0:  # Show every ~10th point
                ax.annotate(f'{v:X}', (t, v), xytext=(5, 5), 
                           textcoords='offset points', fontsize=8)
        
        plt.tight_layout()
        return fig
    
    def export_to_image(self, fig, filename: str, dpi=150):
        """Export figure to image file"""
        if fig is None:
            logger.error("Cannot export None figure")
            return None
        
        try:
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(filename, dpi=dpi, bbox_inches='tight', facecolor='white')
            logger.info(f"Exported waveform to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to export waveform: {e}")
            return None
