# RTL-Gen AI — Yosys Synthesis Script
# Simple, robust synthesis for Yosys 0.38+

read_verilog /work/rtl.v
hierarchy -check -top adder_8bit
proc
synth -flatten
opt
write_verilog -noattr -noexpr /work/adder_8bit_synth.v
stat
