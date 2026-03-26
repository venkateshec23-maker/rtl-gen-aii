# Fill Cell Insertion  –  RTL-Gen AI
        read_lef     /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_lef     /pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
        read_liberty /pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
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

        # Insert fill cells in all empty row spaces
        # Largest cells first (reduces total cell count)
        filler_placement {sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}

        # Verify placement is still legal
        check_placement

        write_def /work/fill.def
        puts "Fill cells inserted"
        exit