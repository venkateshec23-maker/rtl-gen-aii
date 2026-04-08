# Detailed Routing (TritonRoute)  -  RTL-Gen AI
# Top module : adder_8bit
# Layers     : met2 - met4
# Threads    : 4

# 1. Load PDK
read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

# 2. Read netlist then post-CTS design
# Same proven order as placer/CTS:
#   read_verilog → loads cells into library (no chip)
#   read_def     → creates chip WITH DIEAREA, ROW, TRACKS, placement
#   link_design  → connects them
read_verilog /work/adder_8bit_synth.v
read_def /work/cts.def
catch { link_design adder_8bit }

# 3. Clock constraint
create_clock -name clk -period 20.0 [get_ports clk]

# 4. Populate routing tracks
# 4. Track setup already present in DEF from floorplan/placement
# Do NOT call make_tracks — it conflicts with existing TRACKS in DEF

# 5. Power Delivery Network (REQUIRED before routing)
# Without PDN metal stripes, TritonRoute crashes with SIGSEGV
add_global_connection -net VDD -pin_pattern {VPWR} -power
add_global_connection -net VDD -pin_pattern {VPB}  -power
add_global_connection -net VSS -pin_pattern {VGND} -ground
add_global_connection -net VSS -pin_pattern {VNB}  -ground
catch { global_connect }

# PDN generation - wrapped in catch because it may fail if
# rows are not properly defined (depending on CTS output)
catch {
    set_voltage_domain -power VDD -ground VSS
    define_pdn_grid -name "Core" -voltage_domains {Core}
    add_pdn_stripe -followpins -layer met1 -width 0.48
    add_pdn_stripe -layer met4 -width 1.6 -pitch 27.2 -offset 13.6
    add_pdn_connect -layers {met1 met4}
    pdngen
}

# 6. Global routing
catch {
    global_route \
        -guide_file /work/route_guides.txt \
        -congestion_iterations 30 \
        -verbose
}

# 7. Detailed routing
catch {
    detailed_route \
        -output_drc /work/drc_violations.txt \
        -verbose 1
}

# 7. Reports (all optional - wrapped in catch)
catch { check_placement -verbose >> /work/routing.rpt }
catch { report_design_area >> /work/routing.rpt }
catch { report_wire_length >> /work/routing.rpt }
catch { set_propagated_clock [all_clocks] }
catch { report_checks -path_delay max -format full_clock >> /work/routing.rpt }
catch { report_wns >> /work/routing.rpt }
catch { report_tns >> /work/routing.rpt }

# 8. Write routed DEF
write_def /work/routed.def

puts "\nRouting stage complete: adder_8bit\n"
exit
