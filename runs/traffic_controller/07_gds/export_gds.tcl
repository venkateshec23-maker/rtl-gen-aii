
        # ────────────────────────────────────────────────────────────────
        # GDS Export via Magic  –  RTL-Gen AI
        # Top module  : traffic_controller
        # Flatten     : True
        # Version     : GDSII stream v2
        # ────────────────────────────────────────────────────────────────

        # ── 1. Load Sky130A technology rules ──────────────────────────
        tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
        tech revert

        # ── 2. Read PDK cell GDS libraries ───────────────────────────
        # These contain the transistor-level polygon geometry for each
        # standard cell (AND gates, flip-flops, buffers, etc.)
        gds readonly true
        gds flatglob {}
        gds read /pdk/sky130A/libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds

        # Also read I/O cell library if available
        if {[file exists /pdk/sky130A/libs.ref/sky130_fd_io/gds/sky130_fd_io.gds]} {
            gds read /pdk/sky130A/libs.ref/sky130_fd_io/gds/sky130_fd_io.gds
        }
        gds readonly false

        # ── 3. Read LEF abstracts for pin locations ───────────────────
        tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
        lef read /pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
        lef read /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef

        # ── 4. Read the placed-and-routed DEF ─────────────────────────
        def read /work/floorplan.def
        load traffic_controller

# Flatten hierarchy for self-contained GDS
flatten -nolabels traffic_controller
load traffic_controller


# Note: seal ring added by fab during tape-out prep
# Sky130 uses a standard seal ring defined in the PDK

        # ── 5. Write GDSII stream ─────────────────────────────────────
        gds write /work/traffic_controller.gds

        puts "\n✅  GDS written: /work/traffic_controller.gds\n"
        quit
