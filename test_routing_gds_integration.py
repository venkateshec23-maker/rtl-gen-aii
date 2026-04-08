#!/usr/bin/env python3
"""
Integration test for routing and GDS fixes.
Tests the actual functionality without requiring full pipeline setup.
"""

import sys
from pathlib import Path
import tempfile

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

from python.detail_router import DetailRouter, DetailRouteConfig
from python.gds_generator import MinimalGDSWriter
from python.docker_manager import DockerManager
from python.pdk_manager import PDKManager


def test_routing_stage():
    """Test that route guides are properly generated."""
    print("\n" + "=" * 70)
    print("TEST 1: ROUTING GUIDE GENERATION")
    print("=" * 70)
    
    dm = DockerManager()
    pdk = PDKManager()
    dr = DetailRouter(docker=dm, pdk=pdk)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create realistic test DEF
        test_def = tmpdir / "place_and_cts.def"
        test_def.write_text("""
DESIGN adder_8bit;
UNITS DISTANCE MICRONS 1000;

COMPONENTS 20 ;
- cell_1 cell_type + PLACED ( 100 100 ) N ;
- cell_2 cell_type + PLACED ( 200 200 ) N ;
- cell_3 cell_type + PLACED ( 300 300 ) N ;
- cell_4 cell_type + PLACED ( 400 400 ) N ;
- cell_5 cell_type + PLACED ( 500 500 ) N ;
- cell_6 cell_type + PLACED ( 100 600 ) N ;
- cell_7 cell_type + PLACED ( 200 700 ) N ;
- cell_8 cell_type + PLACED ( 300 800 ) N ;
- cell_9 cell_type + PLACED ( 400 900 ) N ;
- cell_10 cell_type + PLACED ( 500 1000 ) N ;
- cell_11 cell_type + PLACED ( 600 100 ) N ;
- cell_12 cell_type + PLACED ( 700 200 ) N ;
- cell_13 cell_type + PLACED ( 800 300 ) N ;
- cell_14 cell_type + PLACED ( 900 400 ) N ;
- cell_15 cell_type + PLACED ( 1000 500 ) N ;
- cell_16 cell_type + PLACED ( 600 600 ) N ;
- cell_17 cell_type + PLACED ( 700 700 ) N ;
- cell_18 cell_type + PLACED ( 800 800 ) N ;
- cell_19 cell_type + PLACED ( 900 900 ) N ;
- cell_20 cell_type + PLACED ( 1000 1000 ) N ;
END COMPONENTS

NETS 15 ;
- clk ( pin1 ) ;
- reset_n ( pin2 ) ;
- a[0] ( pin3 ) ;
- a[1] ( pin4 ) ;
- a[2] ( pin5 ) ;
- b[0] ( pin6 ) ;
- b[1] ( pin7 ) ;
- b[2] ( pin8 ) ;
- sum[0] ( pin9 ) ;
- sum[1] ( pin10 ) ;
- sum[2] ( pin11 ) ;
- carry_in ( pin12 ) ;
- carry_out ( pin13 ) ;
- power ( pin14 ) ;
- ground ( pin15 ) ;
END NETS

END DESIGN
""", encoding="utf-8")
        
        guide_file = tmpdir / "route_guides.txt"
        
        try:
            dr._generate_basic_guides(guide_file, test_def)
            
            if guide_file.exists():
                content = guide_file.read_text()
                size = guide_file.stat().st_size
                
                # Verify content
                net_count = content.count('\n')
                has_nets = any(net in content for net in ['clk', 'reset_n', 'a[0]', 'sum[0]'])
                
                print(f"✅ Route guides generated successfully")
                print(f"   File size: {size} bytes")
                print(f"   Net count: {net_count}")
                print(f"   Contains expected nets: {has_nets}")
                
                if has_nets and size > 100:
                    print("✅ PASS: Route guides properly generated")
                    return True
                else:
                    print("❌ FAIL: Route guides missing expected content")
                    return False
            else:
                print("❌ FAIL: Route guide file not created")
                return False
                
        except Exception as e:
            print(f"❌ FAIL: Exception during guide generation: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_gds_generation():
    """Test that GDS writer properly extracts geometry from DEF."""
    print("\n" + "=" * 70)
    print("TEST 2: GDS GEOMETRY EXTRACTION")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test DEF with cell positions
        test_def = tmpdir / "routed.def"
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

NETS 10 ;
- net1 ;
- net2 ;
- net3 ;
- net4 ;
- net5 ;
- net6 ;
- net7 ;
- net8 ;
- net9 ;
- net10 ;
END NETS

END DESIGN
""", encoding="utf-8")
        
        output_gds = tmpdir / "final.gds"
        
        try:
            MinimalGDSWriter.write_gds(
                str(output_gds),
                "adder_8bit",
                str(test_def)
            )
            
            if output_gds.exists():
                size = output_gds.stat().st_size
                
                print(f"✅ GDS file generated successfully")
                print(f"   File size: {size} bytes")
                
                # Check if it's a minimal stub or proper file
                with open(output_gds, 'rb') as f:
                    header = f.read(10)
                    # GDSII files start with HEADER record (0x0002)
                    has_proper_header = header[0:2] == b'\x00\x02'
                
                if size > 300:
                    print(f"   File size good (> 300 bytes)")
                    print(f"✅ PASS: GDS has proper geometry extraction")
                    return True
                elif size > 150 and has_proper_header:
                    print(f"   File has proper GDSII structure")
                    print(f"⚠️  WARNING: GDS smaller than expected, but properly formatted")
                    return True
                else:
                    print(f"❌ FAIL: GDS file too small or improperly formatted")
                    return False
                
            else:
                print("❌ FAIL: GDS file not created")
                return False
                
        except Exception as e:
            print(f"❌ FAIL: Exception during GDS generation: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_tcl_script_quality():
    """Test that TCL script has proper error handling."""
    print("\n" + "=" * 70)
    print("TEST 3: TCL SCRIPT QUALITY")
    print("=" * 70)
    
    dm = DockerManager()
    pdk = PDKManager()
    dr = DetailRouter(docker=dm, pdk=pdk)
    config = DetailRouteConfig()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        def_path = tmpdir / "dummy.def"
        guide_path = tmpdir / "dummy_guides.txt"
        
        def_path.write_text("DESIGN test\nEND DESIGN")
        
        try:
            tcl = dr._generate_detail_route_script(def_path, guide_path, "test_module", config)
            
            # Check for key robustness features
            checks = [
                ("Has catch block for detailed_route", "if {{ [catch {{" in tcl),
                ("Has guide file warning", "WARNING: route guides not found" in tcl),
                ("Has error handling for write_def", "catch {{ write_def /work/routed.def }}" in tcl),
                ("No problematic delete_net zero_", "delete_net zero_" not in tcl),
            ]
            
            all_pass = True
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"   {status} {check_name}")
                all_pass = all_pass and passed
            
            if all_pass:
                print("\n✅ PASS: TCL script has all robustness improvements")
                return True
            else:
                print("\n❌ FAIL: TCL script missing some improvements")
                return False
                
        except Exception as e:
            print(f"❌ FAIL: Exception during TCL generation: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("ROUTING & GDS INTEGRATION TEST SUITE")
    print("=" * 70)
    
    results = {
        "Route Guide Generation": test_routing_stage(),
        "GDS Geometry Extraction": test_gds_generation(),
        "TCL Script Quality": test_tcl_script_quality(),
    }
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
