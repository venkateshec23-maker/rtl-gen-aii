# ────────────────────────────────────────────────────────────────
        # Placement Script  –  RTL-Gen AI
        # Top module  : counter_4bit
        # Density     : 0.6
        # Clock       : clk @ 10.0 ns
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
        read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
        read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

        # ── 2. Read floorplan DEF ─────────────────────────────────────
        read_def /work/floorplan.def
        link_design counter_4bit

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

        puts "\n✅  Placement complete: counter_4bit\n"
        exit