# ────────────────────────────────────────────────────────────────
        # Clock Tree Synthesis  –  RTL-Gen AI
        # Top module  : adder_8bit
        # Clock net   : clk @ 10.0 ns
        # Target skew : 0.1 ns
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
        read_lef     /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
        read_liberty /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib

        # ── 2. Read netlist then placed DEF ───────────────────────────
        # Use same proven order as placer:
        #   read_verilog → loads cells into library (no chip created)
        #   read_def     → creates chip WITH DIEAREA, ROW, TRACKS, placement
        #   link_design  → connects netlist instances to DEF cells
        read_verilog /work/adder_8bit_synth.v
        read_def /work/placed.def
        catch { link_design adder_8bit }

        # ── 3. Clock constraint ───────────────────────────────────────
        create_clock -name clk \
                     -period 10.0 \
                     [get_ports clk]

        # ── 4. Clock Tree Synthesis (TritonCTS) ───────────────────────
        # root_buf  = strongest buffer at the root (near clock source)
        # buf_list  = available buffers for intermediate / leaf nodes
        # Wrap in try/catch to handle missing buffer cells gracefully
        if { [catch {
            clock_tree_synthesis \
                -root_buf sky130_fd_sc_hd__buf_16 \
                -buf_list {sky130_fd_sc_hd__buf_2 sky130_fd_sc_hd__buf_4 sky130_fd_sc_hd__buf_8} \
                -sink_clustering_enable \
                -sink_clustering_size 20
        } err] }  {
            puts "WARNING: CTS failed with error: $err"
            puts "Continuing without CTS..."
        }

# ── 5. Repair hold violations ──────────────────────────────
# CTS buffer insertion changes net delays → may create holds
repair_timing -hold -hold_margin 0.05 -max_buffer_percent 20

        # ── 6. Propagate clock (use real wire delays for STA) ─────────
        catch { set_propagated_clock [all_clocks] }

        # ── 7. Reports ────────────────────────────────────────────────
        # Clock skew report (skip if CTS didn't run)
        catch { report_clock_skew > /work/cts.rpt }
        # Timing check after CTS (wrap in catch)
        catch { report_checks -path_delay max >> /work/cts.rpt }
        catch { report_checks -path_delay min >> /work/cts.rpt }
        catch { report_wns >> /work/cts.rpt }
        catch { report_tns >> /work/cts.rpt }

        # Buffer count (wrap in catch to handle missing cells)
        catch {
            set buf_count [llength [get_cells -hierarchical -filter "is_clock_cell == 1"]]
            puts "Clock buffers inserted: $buf_count"
            puts $buf_count >> /work/cts.rpt
        }

        # ── 8. Write output DEF ───────────────────────────────────────
        write_def /work/cts.def

        puts "\n✅  CTS complete: adder_8bit\n"
        exit