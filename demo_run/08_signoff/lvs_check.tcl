# ────────────────────────────────────────────────────────────────
# LVS via Netgen  –  RTL-Gen AI
# Top module  : adder_8bit
# ────────────────────────────────────────────────────────────────

# Run Netgen LVS comparison
# layout   = extracted SPICE from GDS
# schematic= original synthesised netlist

# First extract SPICE from the GDS using Magic
# Then compare with Netgen

# Step 1: Extract SPICE from layout (Magic)
magic -noconsole -dnull << 'MAGIC_EOF'
tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
gds read /work/adder_8bit.gds
load adder_8bit
extract all
ext2spice -format ngspice -cthresh 0 -rthresh 0
MAGIC_EOF

# Step 2: Run Netgen LVS
netgen -batch lvs \
    "/work/adder_8bit.spice adder_8bit" \
    "/work/adder_8bit_synth.v adder_8bit" \
    "/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" \
    /work/lvs.rpt \
    -json

puts "LVS complete"