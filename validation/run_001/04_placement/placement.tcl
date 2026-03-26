# ────────────────────────────────────────────────────────────────
        # Placement Script  –  RTL-Gen AI
        # Top module  : adder_8bit
        # Density     : 0.6
        # Clock       : clk @ 10.0 ns
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_lef     /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_liberty /pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
        read_liberty /pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

        # ── 2. Read floorplan DEF ─────────────────────────────────────
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

        # ── 4. Set cell padding (spacing around each instance) ────────
        set_placement_padding -global -left  1 \
                                      -right 1

        # ── 5. Global placement (RePlAce) ─────────────────────────────
        # skip_initial_place = skip random init (faster convergence)
        global_placement -timing_driven \
            -density 0.6 \
            -skip_initial_place

        # ── 6. Legalisation (OpenDP) ──────────────────────────────────
        # Resolves all cell overlaps; snaps to placement rows
        legalize_placement

# Stage 3 – Detailed placement
detailed_placement

        # ── 7. Verify zero overlaps ───────────────────────────────────
        check_placement -verbose

        # ── 8. Reports ────────────────────────────────────────────────
        # Timing report after placement
        set_propagated_clock [all_clocks]
        report_checks -path_delay max -format full_clock > /work/placement.rpt
        report_wns >> /work/placement.rpt
        report_tns >> /work/placement.rpt

        # Density / HPWL report
        report_design_area >> /work/placement.rpt

        # ── 9. Write output DEF ───────────────────────────────────────
        write_def /work/placed.def

        puts "\n✅  Placement complete: adder_8bit\n"
        exit