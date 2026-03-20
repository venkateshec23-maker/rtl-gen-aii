"""Tests for synthesis engine"""

import pytest
import tempfile
import shutil
from pathlib import Path
from python.synthesis_engine import SynthesisEngine

@pytest.fixture
def sample_rtl():
    return """
module adder_8bit(
    input [7:0] a,
    input [7:0] b,
    input cin,
    output [7:0] sum,
    output cout
);
    assign {cout, sum} = a + b + cin;
endmodule
"""

def test_init():
    """Test engine initialization"""
    synth = SynthesisEngine()
    assert synth.output_dir.exists()

def test_detect_top_module(sample_rtl):
    """Test top module detection"""
    synth = SynthesisEngine()
    top = synth._detect_top_module(sample_rtl)
    assert top == "adder_8bit"

def test_analyze_complexity(sample_rtl):
    """Test complexity analysis"""
    synth = SynthesisEngine()
    complexity = synth._analyze_complexity(sample_rtl)
    assert 'module_count' in complexity
    assert 'input_count' in complexity
    assert complexity['input_count'] == 3  # a, b, cin

def test_mock_synthesis(sample_rtl):
    """Test mock synthesis"""
    test_dir = Path('test_outputs_synth')
    try:
        synth = SynthesisEngine(output_dir=str(test_dir / 'synthesis'))
        result = synth.synthesize(sample_rtl)
        
        assert result['success'] is True
        assert result['top_module'] == "adder_8bit"
        assert result.get('netlist') is not None
        assert result.get('stats') is not None
        assert result['simulator'] == 'mock'
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)

def test_estimate_cells(sample_rtl):
    """Test cell estimation"""
    synth = SynthesisEngine()
    complexity = synth._analyze_complexity(sample_rtl)
    cells = synth._estimate_cells(complexity)
    
    assert isinstance(cells, dict)
    assert len(cells) > 0

def test_generate_mock_netlist(sample_rtl):
    """Test mock netlist generation"""
    synth = SynthesisEngine()
    netlist = synth._generate_mock_netlist(sample_rtl, "adder_8bit")
    
    assert "module adder_8bit_netlist" in netlist
    assert "endmodule" in netlist

def test_compare_synthesis():
    """Test design comparison"""
    synth = SynthesisEngine()
    
    designs = [
        """module simple(input a, output z);
           assign z = a;
        endmodule""",
        """module complex(input [3:0] a, input [3:0] b, output [3:0] sum);
           assign sum = a + b;
        endmodule"""
    ]
    
    comparison = synth.compare_synthesis(designs, ["Simple", "Complex"])
    
    assert 'designs' in comparison
    assert 'area' in comparison
    assert 'power' in comparison
    assert 'frequency' in comparison

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
