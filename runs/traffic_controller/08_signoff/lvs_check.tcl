# ────────────────────────────────────────────────────────────────
# LVS via Netgen  –  RTL-Gen AI
# Top module  : traffic_controller
# ────────────────────────────────────────────────────────────────

# Run Netgen LVS comparison
# layout   = extracted SPICE from GDS
# schematic= original synthesised netlist

# First extract SPICE from the GDS using Magic
# Then compare with Netgen

# Step 1: Extract SPICE from layout (Magic)
magic -noconsole -dnull << 'MAGIC_EOF'
tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
gds read /work/traffic_controller.gds
load traffic_controller
extract all
ext2spice -format ngspice -cthresh 0 -rthresh 0
MAGIC_EOF

# Step 2: Run Netgen LVS
netgen -batch lvs \
    "/work/traffic_controller.spice traffic_controller" \
    "/work/traffic_controller_synth.v traffic_controller" \
    "/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" \
    /work/lvs.rpt \
    -json

puts "LVS complete"