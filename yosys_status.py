#!/usr/bin/env python
"""
Yosys Setup Status and Quick Start Guide
"""

import subprocess
from pathlib import Path

def check_yosys():
    """Check if Yosys is installed"""
    try:
        result = subprocess.run(
            ["yosys", "-V"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return True, result.stdout.strip()
    except:
        return False, None

def main():
    print("\n" + "="*70)
    print("  RTL-GEN AI - SYNTHESIS SETUP STATUS")
    print("="*70 + "\n")
    
    # Check Yosys
    has_yosys, version = check_yosys()
    
    print("[STATUS]\n")
    if has_yosys:
        print(f"  ✓ Yosys INSTALLED")
        print(f"    {version}\n")
        print("  Synthesis will use REAL Yosys for accurate results\n")
    else:
        print("  ✗ Yosys NOT installed")
        print("    Synthesis will use MOCK mode (still very functional!)\n")
    
    print("[SYNTHESIS MODES]\n")
    print("  1. MOCK MODE (current - no dependencies)")
    print("     ✓ Generates gate-level netlists")
    print("     ✓ Estimates area/power/frequency")
    print("     ✓ Creates HTML reports")
    print("     ✓ Generates visualizations")
    print("     ✓ Works on ANY Windows machine")
    print("     → Accuracy: Good for comparison & optimization\n")
    
    print("  2. YOSYS MODE (real synthesis - needs Yosys)")
    print("     ✓ Exact gate-level synthesis")
    print("     ✓ Accurate area/power metrics")
    print("     ✓ Real netlist generation")
    print("     ✓ Full optimization suite")
    print("     → Accuracy: For production designs\n")
    
    print("[QUICK START - USE NOW]\n")
    print("  1. Test mock synthesis:")
    print("     python complete_integration.py\n")
    
    print("  2. Use with Streamlit app:")
    print("     streamlit run app.py")
    print("     → Navigate to 'Synthesis' tab\n")
    
    print("  3. Run unit tests:")
    print("     python -m pytest tests/test_synthesis_engine.py -v\n")
    
    print("[INSTALL YOSYS (OPTIONAL)]\n")
    print("  Option 1: Windows Subsystem for Linux (RECOMMENDED)")
    print("    - Open PowerShell (Admin)")
    print("    - Run: wsl --install")
    print("    - Restart computer")
    print("    - In WSL: sudo apt install yosys\n")
    
    print("  Option 2: Manual Download")
    print("    - Visit: https://github.com/YosysHQ/yosys/releases")
    print("    - Download latest Windows binary")
    print("    - Extract to: C:\\yosys")
    print("    - Add C:\\yosys\\bin to Windows PATH\n")
    
    print("  Option 3: Docker")
    print("    - Install Docker Desktop")
    print("    - docker pull yosys/yosys:latest\n")
    
    print("[VERIFICATION]\n")
    if has_yosys:
        print("  ✓ Real Yosys synthesis ready")
        print("  ✓ Run tests to confirm:")
        print("    python -m pytest tests/test_synthesis_engine.py -v\n")
    else:
        print("  ✓ Mock synthesis ready (no setup needed)")
        print("  ✓ Run now:")
        print("    python complete_integration.py\n")
    
    print("[DOCUMENTATION]\n")
    print("  - User guide: docs/SYNTHESIS_GUIDE.md")
    print("  - Yosys setup: docs/YOSYS_SETUP_GUIDE.md")
    print("  - Streamlit integration: app_synthesis_integration.py\n")
    
    print("="*70)
    print("  RTL-GEN AI SYNTHESIS IS READY TO USE")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
