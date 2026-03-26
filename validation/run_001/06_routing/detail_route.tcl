# ────────────────────────────────────────────────────────────────
        # Detailed Routing (TritonRoute)  –  RTL-Gen AI
        # Top module  : adder_8bit
        # Layers      : met2 – met4
        # Threads     : 4
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_lef     /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_liberty /pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
        read_liberty /pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

        # ── 2. Read post-CTS DEF ─────────────────────────────────────
        read_def /work/" ;

DESIGN adder_8bit ;

UNITS DISTANCE MICRONS 1000 ;

DIEAREA ( 0 0 ) ( 30000 30000 ) ;

REGIONS
  REGION core
    ( 10000 10000 ) ( 31809 31809 )
    RECTANGULAR ;
END REGIONS

COMPONENTS 0 ;

PINS 4
  - clk
    + NET clk
    + LAYER metal1 ( 0 0 ) ( 100 100 )
    + PLACED ( 10000 10000 ) N ;
  - a
    + NET a
    + LAYER metal1 ( 0 0 ) ( 100 100 )
    + PLACED ( 10100 10100 ) N ;
  - b
    + NET b
    + LAYER metal1 ( 0 0 ) ( 100 100 )
    + PLACED ( 10200 10200 ) N ;
  - sum
    + NET sum
    + LAYER metal1 ( 0 0 ) ( 100 100 )
    + PLACED ( 10300 10300 ) N ;
END PINS

NETS 0 ;

END DESIGN

        link_design adder_8bit

        # ── 3. Clock constraint ───────────────────────────────────────
        create_clock -name clk \
                     -period 10.0 \
                     [get_ports clk]

        # ── 4. Load global route guides ───────────────────────────────
        # Route guides tell TritonRoute which layers/tiles to use per net
        read_guides /work/route_guides.txt

        # ── 5. Set routing layer bounds ───────────────────────────────
        set_routing_layers -signal {met2 met4}

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

        # ── 9. Wire length and via statistics ─────────────────────────
        report_design_area          >> /work/routing.rpt
        report_wire_length          >> /work/routing.rpt

        # ── 10. Write fully-routed DEF ────────────────────────────────
        write_def /work/routed.def

        puts "\n✅  Detailed routing complete: adder_8bit\n"
        exit