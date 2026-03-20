"""Tests for waveform generator"""

import pytest
import tempfile
import shutil
from pathlib import Path
from python.waveform_generator import WaveformGenerator

@pytest.fixture
def sample_testbench():
    return """
`timescale 1ns/1ps
module testbench;
    reg clk;
    reg rst;
    wire [7:0] out;
    
    initial begin
        clk = 0;
        rst = 1;
        #10 rst = 0;
        #100 $finish;
    end
    
    always #5 clk = ~clk;
endmodule
"""

def test_init():
    gen = WaveformGenerator()
    assert gen.output_dir.exists()

def test_extract_signals(sample_testbench):
    gen = WaveformGenerator()
    signals = gen._extract_signals(sample_testbench)
    assert 'clk' in signals
    assert 'rst' in signals
    assert 'out' in signals

def test_extract_timescale(sample_testbench):
    gen = WaveformGenerator()
    unit, precision = gen._extract_timescale(sample_testbench)
    assert unit == '1ns'
    assert precision == '1ps'

def test_estimate_duration(sample_testbench):
    gen = WaveformGenerator()
    duration = gen._estimate_duration(sample_testbench)
    assert duration == 100

def test_generate_mock_vcd(sample_testbench):
    gen = WaveformGenerator(output_dir='test_outputs')
    vcd_file = gen._generate_mock_vcd(sample_testbench, 'test_tb', ['clk', 'rst'])
    assert vcd_file.exists()
    assert vcd_file.suffix == '.vcd'
    
    # Cleanup
    if Path('test_outputs').exists():
        shutil.rmtree('test_outputs')

def test_full_generation(sample_testbench):
    gen = WaveformGenerator(output_dir='test_outputs')
    result = gen.generate_from_testbench(sample_testbench, 'test_tb')
    
    assert result['success'] is True
    assert result['vcd_file'] is not None
    assert 'signals' in result
    
    # Cleanup
    if Path('test_outputs').exists():
        shutil.rmtree('test_outputs')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
