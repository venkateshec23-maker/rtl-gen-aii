# ────────────────────────────────────────────────────────────────
        # Detailed Routing (TritonRoute)  –  RTL-Gen AI
        # Top module  : adder_8bit
        # Layers      : met2 – met4
        # Threads     : 2
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
        read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
        read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

        # ── 2. Read netlist and post-CTS DEF ─────────────────────────
        catch { read_verilog /work/adder_8bit_synth.v }
        catch { link_design adder_8bit }
        read_def /work/cts.def

        # ── 3. Clock constraint ───────────────────────────────────────
        create_clock -name clk \
                     -period 25.0 \
                     [get_ports clk]
        # ── 4. Load global route guides ───────────────────────────
        # Route guides constrain routing to recommended paths
        if {[file exists /work/route_guides.txt]} {
            read_guides /work/route_guides.txt
        }

        # ── 5. Remove power/ground routing nets (only route signal nets) ─
        # Power/ground routing is handled separately as special nets
        delete_net zero_

        # ── 6. Run TritonRoute detailed routing ───────────────────────
        # -output_drc       : write DRC violations to file
        # -output_maze      : write maze routing debug log
        # -verbose          : output level (1 = standard)
        detailed_route \
            -output_drc  /work/drc_violations.txt \
            -output_maze /work/maze.log \
            -verbose 1

# ── 7. DRC check report ─────────────────────────────────────
check_placement -verbose
set_check_types -max_slew
report_check_types >> /work/routing.rpt


# ── 8. Post-route static timing analysis ───────────────────
set_propagated_clock [all_clocks]
report_checks -path_delay max -format full_clock >> /work/routing.rpt
report_wns >> /work/routing.rpt
report_tns >> /work/routing.rpt

        # ── 7. Wire length and via statistics ─────────────────────────
        report_design_area          >> /work/routing.rpt
        report_wire_length          >> /work/routing.rpt

        # ── 7. Write fully-routed DEF ────────────────────────────────
        write_def /work/routed.def

        puts "\n✅  Detailed routing complete: adder_8bit\n"
        exit