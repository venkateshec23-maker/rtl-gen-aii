
        # ────────────────────────────────────────────────────────────────
        # GDS Export via Magic  –  RTL-Gen AI
        # Top module  : adder_8bit
        # Flatten     : True
        # Version     : GDSII stream v2
        # ────────────────────────────────────────────────────────────────

        # ── 1. Load Sky130A technology rules ──────────────────────────
        tech load /pdk/libs.tech/magic/sky130A.tech
        tech revert

        # ── 2. Read PDK cell GDS libraries ───────────────────────────
        # These contain the transistor-level polygon geometry for each
        # standard cell (AND gates, flip-flops, buffers, etc.)
        gds readonly true
        gds flatglob {}
        gds read /pdk/libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds

        # Also read I/O cell library if available
        if {[file exists /pdk/libs.ref/sky130_fd_io/gds/sky130_fd_io.gds]} {
            gds read /pdk/libs.ref/sky130_fd_io/gds/sky130_fd_io.gds
        }
        gds readonly false

        # ── 3. Read LEF abstracts for pin locations ───────────────────
        lef read /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        lef read /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef

        # ── 4. Read the placed-and-routed DEF ─────────────────────────
        def read /work/" ;

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

        load adder_8bit

# Flatten hierarchy for self-contained GDS
flatten -nolabels adder_8bit
load adder_8bit


# Note: seal ring added by fab during tape-out prep
# Sky130 uses a standard seal ring defined in the PDK

        # ── 5. Write GDSII stream ─────────────────────────────────────
        gds write /work/adder_8bit.gds

        puts "\n✅  GDS written: /work/adder_8bit.gds\n"
        quit
