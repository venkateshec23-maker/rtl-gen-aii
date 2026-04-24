# ────────────────────────────────────────────────────────────────
# LVS via Netgen  –  RTL-Gen AI
# Top module  : my_design
# ────────────────────────────────────────────────────────────────

# Run Netgen LVS comparison
# layout   = extracted SPICE from GDS
# schematic= original synthesised netlist

# First extract SPICE from the GDS using Magic
# Then compare with Netgen

# Step 1: Extract SPICE from layout (Magic)
magic -noconsole -dnull << 'MAGIC_EOF'
tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
gds read /work/my_design.gds
load my_design
extract all
ext2spice -format ngspice -cthresh 0 -rthresh 0
MAGIC_EOF

# Step 2: Run Netgen LVS
netgen -batch lvs \
    "/work/my_design.spice my_design" \
    "/work/my_design_synth.v my_design" \
    "/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" \
    /work/lvs.rpt \
    -json

puts "LVS complete"