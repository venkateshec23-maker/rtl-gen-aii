
# Floorplanning Configuration - Auto-generated
set design_name adder_8bit
set core_width 36.40094190304107

# Load PDK Data
read_lef /pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
read_lef /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

# Read synthesized netlist and initialize database
read_verilog /work/design_syn.v
link_design adder_8bit

# Floorplan core area
initialize_floorplan -site unithd \
    -die_area "0 0 50.00 50.00" \
    -core_area "10 10 40.00 40.00"

# I/O Pin Placement


# Power Grid Generation
tapcell -distance 14 -tapcell_master sky130_fd_sc_hd__tapvpwrvgnd_1

# Export
write_def /work/floorplan.def

