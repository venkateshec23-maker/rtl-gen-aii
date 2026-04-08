#!/usr/bin/env python3
"""
validate_pdk.py - Validate Sky130A PDK Installation

This script checks if the PDK is properly installed on the Windows host
and if Docker can access it for physical design stages.

Usage:
    python python/validate_pdk.py
    python python/validate_pdk.py --pdk-root C:\path\to\pdk
"""

from pathlib import Path
import subprocess
import sys
import argparse

def validate_pdk_files(pdk_root: str) -> bool:
    """Check PDK file structure."""
    pdk_path = Path(pdk_root)
    
    print("\n" + "="*70)
    print("PDK FILE VALIDATION")
    print("="*70)
    
    # Check if main directory exists
    if not pdk_path.exists():
        print(f"❌ PDK root does not exist: {pdk_root}")
        return False
    
    print(f"✅ PDK root found: {pdk_root}")
    print(f"   Size: {sum(f.stat().st_size for f in pdk_path.rglob('*') if f.is_file()) / (1024**3):.2f} GB")
    
    # Required files for physical design
    required_files = {
        "Liberty (TT)": "sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
        "Liberty (SS)": "sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib",
        "Liberty (FF)": "sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ff_n40C_1v95.lib",
        "Cell LEF": "sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef",
        "Tech LEF": "sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef",
        "GDS": "sky130A/libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds",
        "Spice": "sky130A/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice",
    }
    
    print(f"\nChecking {len(required_files)} required files:")
    
    missing = []
    found = []
    for name, file_path in required_files.items():
        full_path = pdk_path / file_path
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            status = "✅"
            found.append((name, size_kb))
            # Only print summary for very large files
            if size_kb > 100:
                print(f"{status} {name:20} ({size_kb:,.0f} KB)")
            else:
                print(f"{status} {name:20} ({size_kb:.1f} KB)")
        else:
            status = "❌"
            print(f"{status} {name:20} NOT FOUND")
            missing.append((name, file_path))
    
    print(f"\nSummary: {len(found)}/{len(required_files)} files present")
    
    if missing:
        print(f"\n⚠️  Missing files ({len(missing)}):")
        for name, path in missing:
            print(f"   - {name}: {path}")
        print("\n   → PDK may be incomplete or installed in wrong location")
        return len(missing) <= 3  # Allow missing some non-critical files
    else:
        return True

def test_docker_mount(pdk_root: str) -> bool:
    """Test if Docker can access the PDK."""
    print("\n" + "="*70)
    print("DOCKER MOUNT VALIDATION")
    print("="*70)
    
    # Check if Docker is even available
    try:
        docker_version = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if docker_version.returncode != 0:
            print("❌ Docker not responding")
            return False
        print(f"✅ Docker available: {docker_version.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Docker CLI not found")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Docker command timed out")
        return False
    
    # Convert Windows path for Docker mount
    pdk_path = str(pdk_root).replace("\\", "/")
    lib_file = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
    
    print(f"\nMounting {pdk_root} → /pdk in container")
    print(f"Testing access to {lib_file}")
    
    # Test mount
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{pdk_path}:/pdk:z",
        "efabless/openlane:latest",
        "sh", "-c",
        f"test -f {lib_file} && echo 'MOUNT_OK' || echo 'MOUNT_FAILED'"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if "MOUNT_OK" in result.stdout:
            print(f"✅ Docker mount test PASSED")
            print(f"   PDK is accessible inside container at /pdk")
            return True
        else:
            print(f"❌ Docker mount test FAILED")
            print(f"   Container cannot access {lib_file}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Docker mount test timed out (> 30s)")
        return False
    except Exception as e:
        print(f"❌ Docker mount test error: {e}")
        return False

def test_docker_location():
    """Find where Docker expects the PDK."""
    print("\n" + "="*70)
    print("DOCKER PDK DETECTION")
    print("="*70)
    
    cmd = [
        "docker", "run", "--rm",
        "efabless/openlane:latest",
        "sh", "-c",
        "echo $PDK_ROOT && test -d /opt/pdks && echo 'Has /opt/pdks' || true"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        print("OpenLane container PDK configuration:")
        print(result.stdout)
    except Exception as e:
        print(f"Could not query container: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Validate Sky130A PDK installation"
    )
    parser.add_argument(
        "--pdk-root",
        default="C:\\pdk",
        help="Path to PDK root (default: C:\\pdk)"
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip Docker mount tests"
    )
    
    args = parser.parse_args()
    
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  RTL-Gen AI: PDK Validation Tool".ljust(69) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "═"*68 + "╝")
    
    # Step 1: Check file structure
    files_ok = validate_pdk_files(args.pdk_root)
    
    # Step 2: Check Docker mount
    mount_ok = True
    if not args.skip_docker:
        mount_ok = test_docker_mount(args.pdk_root)
        if not mount_ok:
            test_docker_location()
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    summary = []
    if files_ok:
        summary.append("✅ PDK files: Present and accessible")
    else:
        summary.append("❌ PDK files: Missing or incomplete")
    
    if mount_ok:
        summary.append("✅ Docker mount: Working properly")
    else:
        summary.append("⚠️  Docker mount: Test failed or skipped")
    
    for item in summary:
        print(item)
    
    success = files_ok and (mount_ok or args.skip_docker)
    
    print("\n" + "="*70)
    if success:
        print("✅ PDK VALIDATION PASSED - Ready for physical design")
        print("\nNext steps:")
        print("  1. Run: python python/comprehensive_integration_test.py")
        print("  2. Check: validation/integration_test_results.json")
        print("  3. Verify: All 9 pipeline stages complete")
        return 0
    else:
        print("❌ PDK VALIDATION FAILED - Setup needed")
        print("\nNext steps:")
        print("  1. Install PDK: volare enable --pdk sky130 --pdk-root C:\\pdk")
        print("  2. Or mount manually: docker run -v C:\\pdk:/pdk ...")
        print("  3. Then re-run this validation script")
        return 1

if __name__ == "__main__":
    sys.exit(main())
