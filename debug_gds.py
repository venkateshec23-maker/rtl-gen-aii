#!/usr/bin/env python3
"""Debug GDS generation to see why file is still small."""

from pathlib import Path
import tempfile
from python.gds_generator import MinimalGDSWriter

with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir = Path(tmpdir)
    
    # Create test DEF
    test_def = tmpdir / "test.def"
    test_def.write_text("""
DESIGN adder_8bit;
UNITS DISTANCE MICRONS 1000;

COMPONENTS 10 ;
- cell_1 SKY130_FD_SC_HD__DFF_1 + PLACED ( 500 500 ) N ;
- cell_2 SKY130_FD_SC_HD__AND2_1 + PLACED ( 1000 500 ) N ;
- cell_3 SKY130_FD_SC_HD__OR2_1 + PLACED ( 1500 500 ) N ;
- cell_4 SKY130_FD_SC_HD__XOR2_1 + PLACED ( 2000 500 ) N ;
- cell_5 SKY130_FD_SC_HD__NAND2_1 + PLACED ( 2500 500 ) N ;
- cell_6 SKY130_FD_SC_HD__NOR2_1 + PLACED ( 500 1500 ) N ;
- cell_7 SKY130_FD_SC_HD__MUX2_1 + PLACED ( 1000 1500 ) N ;
- cell_8 SKY130_FD_SC_HD__INV_1 + PLACED ( 1500 1500 ) N ;
- cell_9 SKY130_FD_SC_HD__BUF_1 + PLACED ( 2000 1500 ) N ;
- cell_10 SKY130_FD_SC_HD__NOT_1 + PLACED ( 2500 1500 ) N ;
END COMPONENTS
END DESIGN
""")
    
    output_gds = tmpdir / "test.gds"
    
    # Debug: manually parse DEF
    print("Parsing DEF file manually:")
    content = test_def.read_text()
    lines = content.splitlines()
    
    cells = []
    in_components = False
    for line in lines:
        if line.strip().startswith("COMPONENTS"):
            in_components = True
            print(f"Found COMPONENTS section")
        elif in_components:
            if line.strip().startswith("END COMPONENTS"):
                print(f"End of COMPONENTS section")
                break
            if line.strip().startswith("-"):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        cell_name = parts[1]
                        for i, p in enumerate(parts):
                            if p == "+" and i + 3 < len(parts):
                                x = int(float(parts[i+1]) / 100)
                                y = int(float(parts[i+2]) / 100)
                                cells.append((cell_name, x, y))
                                print(f"  Parsed: {cell_name} @ ({x}, {y})")
                                break
                    except (ValueError, IndexError) as e:
                        print(f"  Error parsing: {line[:50]}... : {e}")
    
    print(f"\nTotal cells parsed: {len(cells)}")
    
    # Now generate GDS with debug
    print("\nGenerating GDS...")
    MinimalGDSWriter.write_gds(str(output_gds), "adder_8bit", str(test_def))
    
    gds_size = output_gds.stat().st_size
    print(f"GDS file size: {gds_size} bytes")
    
    # Read GDS in hex
    with open(output_gds, 'rb') as f:
        data = f.read()
        
    print(f"GDS hex (first 200 bytes):")
    print(data[:200].hex())
    
    # Check expected record pattern
    print(f"\nExpected records:")
    print(f"  HEADER: 0002 0600")
    print(f"  BGNLIB: 0001 (28 bytes total)")
    print(f"  LIBNAME: 0002")
    print(f"  UNITS:  0003 (20 bytes)")
    print(f"  For each cell: BOUNDARY (17) + XY (20) + ENDEL (11)")
    print(f"  BGNSTR:  0005 (28 bytes)")
    print(f"  STRNAME: 0006")
    print(f"  Cells data...")
    print(f"  ENDSTR:  0007")
    print(f"  ENDLIB:  0004")
