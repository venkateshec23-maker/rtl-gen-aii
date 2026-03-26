# ────────────────────────────────────────────────────────────────
        # Clock Tree Synthesis  –  RTL-Gen AI
        # Top module  : adder_8bit
        # Clock net   : clk @ 10.0 ns
        # Target skew : 0.1 ns
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_lef     /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_liberty /pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
        read_liberty /pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

        # ── 2. Read placed DEF ────────────────────────────────────────
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

        # ── 4. Clock Tree Synthesis (TritonCTS) ───────────────────────
        # root_buf  = strongest buffer at the root (near clock source)
        # buf_list  = available buffers for intermediate / leaf nodes
        clock_tree_synthesis \
            -root_buf sky130_fd_sc_hd__clkbuf_16 \
            -buf_list {sky130_fd_sc_hd__clkbuf_2,sky130_fd_sc_hd__clkbuf_4,sky130_fd_sc_hd__clkbuf_8} \
            -sink_clustering_enable \
            -sink_clustering_size 20

# ── 5. Repair hold violations ──────────────────────────────
# CTS buffer insertion changes net delays → may create holds
repair_timing -hold -hold_margin 0.05 -max_buffer_percent 20

        # ── 6. Propagate clock (use real wire delays for STA) ─────────
        set_propagated_clock [all_clocks]

        # ── 7. Reports ────────────────────────────────────────────────
        # Clock skew report
        report_clock_skew                   > /work/cts.rpt
        # Timing check after CTS
        report_checks -path_delay max      >> /work/cts.rpt
        report_checks -path_delay min      >> /work/cts.rpt
        report_wns                         >> /work/cts.rpt
        report_tns                         >> /work/cts.rpt

        # Buffer count
        set buf_count [llength [get_cells -hierarchical -filter "is_clock_cell == 1"]]
        puts "Clock buffers inserted: $buf_count"
        puts $buf_count >> /work/cts.rpt

        # ── 8. Write output DEF ───────────────────────────────────────
        write_def /work/cts.def

        puts "\n✅  CTS complete: adder_8bit\n"
        exit