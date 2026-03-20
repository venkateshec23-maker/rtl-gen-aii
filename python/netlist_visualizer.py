"""
Netlist Diagram Generator
Creates visual diagrams of gate-level netlists
"""

import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    logger.warning("NetworkX not installed - netlist graph visualization will be limited")

class NetlistVisualizer:
    """Generate visual diagrams from Verilog netlists"""
    
    def __init__(self):
        self.graph = None
        if HAS_NETWORKX:
            self.graph = nx.DiGraph()
        self.gates = {}
        self.signals = {}
        
    def parse_netlist(self, netlist_code: str) -> Optional[Any]:
        """Parse netlist and create graph"""
        if not netlist_code:
            logger.warning("Empty netlist provided")
            return None
        
        if HAS_NETWORKX:
            self.graph = nx.DiGraph()
        
        self.gates = {}
        self.signals = {}
        
        # Find all gates/instances
        gate_pattern = r'(\w+)\s+(\w+)\s*\((.*?)\);'
        gates = re.findall(gate_pattern, netlist_code, re.DOTALL)
        
        for gate_type, gate_name, connections in gates:
            self.gates[gate_name] = {'type': gate_type, 'connections': {}}
            
            if HAS_NETWORKX:
                self.graph.add_node(gate_name, type=gate_type, node_type='gate')
            
            # Parse port connections
            conn_pattern = r'\.(\w+)\s*\(\s*([^)]+)\s*\)'
            conns = re.findall(conn_pattern, connections)
            
            for port, signal in conns:
                signal = signal.strip()
                self.gates[gate_name]['connections'][port] = signal
                
                if signal and signal not in ['clk', 'rst', '1', '0']:
                    self.signals[signal] = self.signals.get(signal, []) + [gate_name]
                    
                    if HAS_NETWORKX:
                        if signal not in self.graph:
                            self.graph.add_node(signal, node_type='signal')
                        
                        if port in ['a', 'b', 'c', 'd', 'in', 'input']:
                            self.graph.add_edge(signal, gate_name, port=port)
                        elif port in ['y', 'out', 'output', 'q']:
                            self.graph.add_edge(gate_name, signal, port=port)
        
        logger.info(f"Parsed netlist: {len(self.gates)} gates, {len(self.signals)} signals")
        return self.graph
    
    def draw_schematic(self, figsize=(16, 12), output_file: str = None) -> Optional[plt.Figure]:
        """Draw gate-level schematic"""
        if not self.gates:
            logger.warning("No gates to draw")
            return None
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Assign levels
        levels = self._assign_levels()
        pos = self._position_nodes(levels)
        
        # Draw wires first (background)
        self._draw_wires(ax, pos)
        
        # Draw gates
        for gate_name, gate_info in self.gates.items():
            if gate_name in pos:
                x, y = pos[gate_name]
                gate_type = gate_info['type']
                self._draw_gate(ax, x, y, gate_name, gate_type)
        
        # Draw signals
        for signal_name in self.signals.keys():
            if signal_name in pos:
                x, y = pos[signal_name]
                self._draw_signal(ax, x, y, signal_name)
        
        ax.set_title("Gate-Level Netlist Diagram", fontsize=14, fontweight='bold')
        ax.axis('off')
        ax.set_aspect('equal')
        
        if pos:
            xs = [p[0] for p in pos.values()]
            ys = [p[1] for p in pos.values()]
            ax.set_xlim(min(xs) - 1, max(xs) + 1)
            ax.set_ylim(min(ys) - 1, max(ys) + 1)
        
        plt.tight_layout()
        
        if output_file:
            try:
                fig.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
                logger.info(f"Saved schematic to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save schematic: {e}")
        
        return fig
    
    def draw_hierarchy(self, figsize=(16, 12), layout='hierarchical') -> Optional[plt.Figure]:
        """Draw netlist as hierarchical diagram"""
        if not HAS_NETWORKX or self.graph is None:
            logger.warning("NetworkX not available or graph not initialized")
            return self.draw_schematic(figsize=figsize)
        
        if len(self.graph) == 0:
            logger.warning("Empty graph, cannot draw hierarchy")
            return None
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Create layout
        if layout == 'hierarchical':
            pos = self._hierarchical_layout()
        elif layout == 'spring':
            pos = nx.spring_layout(self.graph, k=2, iterations=50)
        else:
            pos = nx.circular_layout(self.graph)
        
        # Get node types
        gate_nodes = [n for n, d in self.graph.nodes(data=True) 
                     if d.get('node_type') == 'gate']
        signal_nodes = [n for n, d in self.graph.nodes(data=True) 
                       if d.get('node_type') == 'signal']
        
        # Draw edges
        for u, v, data in self.graph.edges(data=True):
            if u in pos and v in pos:
                x1, y1 = pos[u]
                x2, y2 = pos[v]
                ax.plot([x1, x2], [y1, y2], 'k-', linewidth=1, alpha=0.6)
        
        # Draw gate nodes
        gate_pos = {n: pos[n] for n in gate_nodes if n in pos}
        if gate_pos:
            xs = [p[0] for p in gate_pos.values()]
            ys = [p[1] for p in gate_pos.values()]
            ax.scatter(xs, ys, s=500, c='lightblue', marker='s', 
                      edgecolors='black', linewidths=1.5, zorder=3)
        
        # Draw signal nodes
        signal_pos = {n: pos[n] for n in signal_nodes if n in pos}
        if signal_pos:
            xs = [p[0] for p in signal_pos.values()]
            ys = [p[1] for p in signal_pos.values()]
            ax.scatter(xs, ys, s=300, c='lightgreen', marker='o', 
                      edgecolors='black', linewidths=1.5, zorder=3)
        
        # Draw labels
        labels = {}
        for n in gate_nodes:
            gate_type = self.graph.nodes[n].get('type', '')
            labels[n] = f"{n}\n({gate_type})"
        
        for n in signal_nodes:
            labels[n] = n
        
        pos_filtered = {n: p for n, p in pos.items() if n in labels}
        for node, (x, y) in pos_filtered.items():
            ax.text(x, y, labels[node], ha='center', va='center', fontsize=7, fontweight='bold')
        
        ax.set_title("Netlist Hierarchy (Hierarchical Layout)", fontsize=14, fontweight='bold')
        ax.axis('off')
        
        plt.tight_layout()
        return fig
    
    def _hierarchical_layout(self) -> Dict[str, Tuple[float, float]]:
        """Create hierarchical layout"""
        if not HAS_NETWORKX or self.graph is None:
            return {}
        
        levels = {}
        inputs = [n for n in self.graph.nodes() 
                 if self.graph.in_degree(n) == 0 and n not in ['clk', 'rst']]
        
        queue = [(n, 0) for n in inputs]
        visited = set(inputs)
        
        while queue:
            node, level = queue.pop(0)
            levels[node] = level
            
            for succ in self.graph.successors(node):
                if succ not in visited:
                    visited.add(succ)
                    queue.append((succ, level + 1))
        
        pos = {}
        max_level = max(levels.values()) if levels else 0
        
        for node, level in levels.items():
            nodes_at_level = [n for n, l in levels.items() if l == level]
            idx = nodes_at_level.index(node)
            pos[node] = (level, idx - len(nodes_at_level) / 2)
        
        return pos
    
    def _assign_levels(self) -> Dict[str, int]:
        """Assign levels to nodes for hierarchical layout"""
        levels = {}
        
        # Find primary inputs
        inputs = []
        for signal in self.signals:
            if signal not in self.gates:
                inputs.append(signal)
        
        # BFS from inputs
        queue = [(n, 0) for n in inputs]
        visited = set(inputs)
        
        while queue:
            node, level = queue.pop(0)
            levels[node] = level
            
            # Find gates
            if node in self.signals:
                for gate in self.signals[node]:
                    if gate not in visited:
                        visited.add(gate)
                        queue.append((gate, level + 1))
                        
                        # Find outputs of this gate
                        if gate in self.gates:
                            for port, signal in self.gates[gate]['connections'].items():
                                if signal and signal not in visited:
                                    visited.add(signal)
                                    queue.append((signal, level + 2))
        
        return levels
    
    def _position_nodes(self, levels: Dict[str, int]) -> Dict[str, Tuple[float, float]]:
        """Position nodes for drawing"""
        pos = {}
        
        level_nodes = {}
        for node, level in levels.items():
            if level not in level_nodes:
                level_nodes[level] = []
            level_nodes[level].append(node)
        
        for level, nodes in level_nodes.items():
            y_spacing = 3.0 / (len(nodes) + 1) if nodes else 1
            for i, node in enumerate(nodes):
                y = -1.5 + (i + 1) * y_spacing
                pos[node] = (level * 2, y)
        
        return pos
    
    def _draw_wires(self, ax, pos):
        """Draw wires between gates"""
        for gate_name, gate_info in self.gates.items():
            if gate_name not in pos:
                continue
            
            x1, y1 = pos[gate_name]
            
            for port, signal in gate_info['connections'].items():
                if signal in pos:
                    x2, y2 = pos[signal]
                    
                    # Draw connection line
                    color = '#0066ff' if port in ['a', 'b', 'c', 'd', 'in'] else '#ff0000'
                    ax.plot([x1, x2], [y1, y2], color=color, linewidth=1.5, alpha=0.7)
    
    def _draw_gate(self, ax, x, y, name, gate_type, width=0.6, height=0.4):
        """Draw gate rectangle"""
        rect = patches.Rectangle((x - width/2, y - height/2), width, height, 
                                 fill=True, facecolor='lightblue', 
                                 edgecolor='black', linewidth=1.5)
        ax.add_patch(rect)
        
        # Add label
        ax.text(x, y, f"{name}\n{gate_type}", ha='center', va='center', 
               fontsize=7, fontweight='bold')
    
    def _draw_signal(self, ax, x, y, name, radius=0.2):
        """Draw signal circle"""
        circle = patches.Circle((x, y), radius, fill=True, 
                               facecolor='lightgreen', edgecolor='black', linewidth=1)
        ax.add_patch(circle)
        
        ax.text(x, y + 0.35, name, ha='center', va='bottom', 
               fontsize=8, fontweight='bold')
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get netlist statistics"""
        stats = {
            'total_gates': len(self.gates),
            'gate_types': {},
            'total_signals': len(self.signals),
            'total_connections': sum(len(g['connections']) for g in self.gates.values())
        }
        
        for gate_name, gate_info in self.gates.items():
            gate_type = gate_info['type']
            stats['gate_types'][gate_type] = stats['gate_types'].get(gate_type, 0) + 1
        
        return stats
