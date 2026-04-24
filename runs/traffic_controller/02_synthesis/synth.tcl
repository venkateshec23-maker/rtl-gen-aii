# RTL-Gen AI — Yosys Synthesis Script
# Sky130 HD cell mapping for Yosys 0.38+

read_verilog /work/rtl.v
hierarchy -check -top traffic_controller
proc; flatten; opt

# Generic synthesis (logic optimization, techmap combinational)
synth -top traffic_controller -noabc

# Map sequential cells (DFFs) to Sky130 library first
dfflibmap -liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib

# Map combinational cells to Sky130 gates
abc -liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib

opt_clean
write_verilog -noattr -noexpr /work/traffic_controller_synth.v
stat
