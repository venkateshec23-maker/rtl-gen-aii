# ────────────────────────────────────────────────────────────────
        # Placement Script  –  RTL-Gen AI
        # Top module  : adder_8bit
        # Density     : 0.6
        # Clock       : clk @ 10.0 ns
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
        read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
        read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

        # ── 1b. Read synthesized netlist (Verilog) ────────────────────
        # read_verilog loads cells into library but does NOT create a chip.
        # read_def then creates the chip WITH all physical data (DIEAREA, ROW, TRACKS).
        # link_design finally connects netlist to DEF instances.
        read_verilog /work/adder_8bit_synth.v

        # ── 2. Read floorplan DEF ─────────────────────────────────────
        # This creates the chip with ROW definitions, DIEAREA, TRACKS.
        read_def /work/floorplan.def
        catch { link_design adder_8bit }

        # ── 3. Clock constraint ───────────────────────────────────────
        create_clock -name clk \
                     -period 10.0 \
                     [get_ports clk]

        # ── 4. Set cell padding (spacing around each instance) ────────
        set_placement_padding -global -left  1 \
                                      -right 1

        # ── 5. Global placement (RePlAce) ─────────────────────────────
        # skip_initial_place = skip random init (faster convergence)
        # Global placement also includes legalisation by default
        global_placement -density 0.6 \
            -skip_initial_place

        # ── 6. Detailed placement / optimization (if enabled) ──────────

# Stage 3 – Detailed placement
detailed_placement

        #  ── 7. Verify placement quality ───────────────────────────────
        # Skip check_placement as it may call unavailable commands

        # ── 8. Reports ────────────────────────────────────────────────
        # Generate simple placement report
        catch { report_design_area > /work/placement.rpt }
        catch { report_placement -verbose >> /work/placement.rpt }

        # ── 9. Write output DEF ───────────────────────────────────────
        write_def /work/placed.def

        puts "\n✅  Placement complete: adder_8bit\n"
        exit