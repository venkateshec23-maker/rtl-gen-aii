#!/usr/bin/env python
"""
Automated Yosys Setup Script for Windows
Downloads and configures Yosys for RTL-Gen AI synthesis
"""

import os
import sys
import subprocess
import zipfile
import json
from pathlib import Path
from urllib.request import urlopen, Request
import shutil

class YosysSetup:
    """Automated Yosys installation and configuration"""
    
    def __init__(self):
        self.yosys_dir = Path("C:/yosys")
        self.yosys_bin = self.yosys_dir / "bin" / "yosys.exe"
        # Try to get latest release dynamically
        self.yosys_url = None
        self.backup_urls = [
            # Official Yosys releases
            "https://github.com/YosysHQ/oss-cad-suite-build/releases",
            # Alternative: Try direct GitHub API
        ]
        
    def check_internet(self):
        """Check if internet connection is available"""
        try:
            urlopen("https://api.github.com", timeout=5)
            return True
        except Exception:
            return False
    
    def yosys_installed(self):
        """Check if Yosys is already installed"""
        if self.yosys_bin.exists():
            return True
        
        # Check if yosys is in PATH
        try:
            result = subprocess.run(
                ["yosys", "-V"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def download_yosys(self):
        """Download Yosys binary"""
        print("\n[DOWNLOAD] Fetching Yosys...")
        
        zip_path = self.yosys_dir / "yosys.zip"
        
        # Try to find latest release from GitHub API
        urls = self._get_download_urls()
        
        for url in urls:
            try:
                print(f"  Trying: {url}")
                
                # Custom headers to avoid GitHub API limits
                headers = {"User-Agent": "RTL-Gen-AI/1.0"}
                request = Request(url, headers=headers)
                
                with urlopen(request, timeout=120) as response:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    block_size = 8192
                    
                    with open(zip_path, 'wb') as f:
                        while True:
                            chunk = response.read(block_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size:
                                percent = (downloaded / total_size) * 100
                                print(f"    Downloaded: {percent:.1f}%", end='\r')
                
                print(f"\n  [OK] Downloaded to: {zip_path}")
                return zip_path
                
            except Exception as e:
                print(f"  [FAILED] {e}")
                if zip_path.exists():
                    zip_path.unlink()
                continue
        
        return None
    
    def _get_download_urls(self):
        """Get list of download URLs to try"""
        urls = []
        
        try:
            # Try GitHub API to find latest releases
            import json as json_module
            
            # Yosys releases
            api_url = "https://api.github.com/repos/YosysHQ/yosys/releases/latest"
            headers = {"User-Agent": "RTL-Gen-AI/1.0"}
            request = Request(api_url, headers=headers)
            
            try:
                with urlopen(request, timeout=10) as response:
                    data = json_module.loads(response.read())
                    
                    # Look for Windows binary
                    for asset in data.get("assets", []):
                        name = asset.get("name", "").lower()
                        if ("windows" in name or "win" in name or "x86" in name) and \
                           ("zip" in name or "exe" in name):
                            urls.append(asset["browser_download_url"])
                            print(f"    Found: {asset['name']}")
            except Exception:
                pass
            
            # Add fallback OSS CAD Suite (which includes Yosys)
            urls.extend([
                "https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2024-12-17/oss-cad-suite-2024-12-17.msys2-ucrt64.tar.gz",
                "https://github.com/YosysHQ/oss-cad-suite-build/releases/download/nightly/oss-cad-suite-nightly.msys2-ubuntu-64.tar.xz",
            ])
            
        except Exception as e:
            print(f"    [INFO] Could not fetch from API: {e}")
        
        # Add known working alternatives
        urls.extend([
            "https://github.com/ghdl/ghdl-yosys-plugin/releases/download/ghdl-yosys-0.37/ghdl-yosys-0.37-x86_64-MSYS2.zip",
        ])
        
        return urls
    
    def extract_yosys(self, zip_path):
        """Extract Yosys archive"""
        print("\n[EXTRACT] Extracting Yosys...")
        
        try:
            self.yosys_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the top-level directory in zip
                namelist = zip_ref.namelist()
                common_prefix = os.path.commonpath(namelist) if namelist else ""
                
                print(f"  Extracting {len(namelist)} files...")
                zip_ref.extractall(self.yosys_dir)
            
            # Clean up
            zip_path.unlink()
            
            print(f"  [OK] Extracted to: {self.yosys_dir}")
            return True
            
        except Exception as e:
            print(f"  [ERROR] Extraction failed: {e}")
            return False
    
    def add_to_path_permanent(self):
        """Add Yosys to Windows PATH permanently"""
        print("\n[PATH] Adding Yosys to Windows PATH...")
        
        bin_path = str(self.yosys_bin.parent)
        
        try:
            # Use setx to set user environment variable
            result = subprocess.run(
                ["setx", "PATH", f"{bin_path};%PATH%"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"  [OK] Added to PATH: {bin_path}")
                print("  [INFO] Please restart terminal for changes to take effect")
                return True
            else:
                print(f"  [WARNING] setx failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"  [WARNING] Could not add to PATH automatically: {e}")
            print(f"  [INFO] Manual: Add '{bin_path}' to System Environment Variables")
            return False
    
    def verify_yosys(self):
        """Verify Yosys installation"""
        print("\n[VERIFY] Testing Yosys installation...")
        
        try:
            # First try local installation
            if self.yosys_bin.exists():
                result = subprocess.run(
                    [str(self.yosys_bin), "-V"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                print(f"  [OK] Local Yosys: {result.stdout.strip()}")
                return True
            
            # Then try system PATH
            result = subprocess.run(
                ["yosys", "-V"],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"  [OK] System Yosys: {result.stdout.strip()}")
            return True
            
        except Exception as e:
            print(f"  [ERROR] Yosys not found: {e}")
            return False
    
    def test_synthesis(self):
        """Test synthesis with a simple example"""
        print("\n[TEST] Running synthesis test...")
        
        test_rtl = """
module test_adder(
    input [3:0] a, b,
    input cin,
    output [3:0] sum,
    output cout
);
    assign {cout, sum} = a + b + cin;
endmodule
"""
        
        try:
            # Write test file
            test_file = Path("test_synth.v")
            test_file.write_text(test_rtl)
            
            # Run synthesis
            yosys_script = """
read_verilog test_synth.v
hierarchy -check -top test_adder
proc; opt
stat
"""
            script_file = Path("test_synth.ys")
            script_file.write_text(yosys_script)
            
            # Execute
            if self.yosys_bin.exists():
                cmd = [str(self.yosys_bin), "-s", str(script_file)]
            else:
                cmd = ["yosys", "-s", str(script_file)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Cleanup
            test_file.unlink(missing_ok=True)
            script_file.unlink(missing_ok=True)
            
            if result.returncode == 0:
                print("  [OK] Synthesis test passed!")
                if "Number of cells" in result.stdout:
                    print("  [OK] Real Yosys synthesis working!")
                    return True
            else:
                print(f"  [WARNING] Synthesis test had issues: {result.stderr[:200]}")
                return False
                
        except Exception as e:
            print(f"  [ERROR] Test failed: {e}")
            return False
    
    def run(self):
        """Execute full setup"""
        print("="*60)
        print("RTL-Gen AI - Yosys Setup Script")
        print("="*60)
        
        # Check if already installed
        if self.yosys_installed():
            print("\n[OK] Yosys is already installed!")
            if self.verify_yosys():
                print("\n[SUCCESS] Yosys is ready to use!")
                self.test_synthesis()
                return True
        
        # Check internet
        if not self.check_internet():
            print("\n[ERROR] No internet connection detected")
            print("[INFO] Please download Yosys manually from:")
            print("  https://github.com/YosysHQ/yosys/releases")
            print("  Extract to: C:\\yosys")
            print("  Then add C:\\yosys\\bin to PATH")
            return False
        
        # Create directory
        print("\n[SETUP] Preparing installation...")
        self.yosys_dir.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] Directory ready: {self.yosys_dir}")
        
        # Download
        zip_path = self.download_yosys()
        if not zip_path:
            print("\n[ERROR] Download failed from all sources")
            print("[INFO] See docs/YOSYS_SETUP_GUIDE.md for manual installation")
            return False
        
        # Extract
        if not self.extract_yosys(zip_path):
            print("\n[ERROR] Extraction failed")
            return False
        
        # Add to PATH
        self.add_to_path_permanent()
        
        # Verify
        if self.verify_yosys():
            print("\n[SUCCESS] Yosys installed successfully!")
            self.test_synthesis()
            
            # Final instructions
            print("\n" + "="*60)
            print("NEXT STEPS:")
            print("="*60)
            print("1. Restart your terminal or PowerShell")
            print("2. Run tests with real Yosys synthesis:")
            print("   python complete_integration.py")
            print("\n3. Launch Streamlit app:")
            print("   streamlit run app.py")
            print("="*60)
            return True
        else:
            print("\n[WARNING] Verification failed")
            print("[INFO] Try restarting terminal and run again")
            return False

def main():
    """Main entry point"""
    setup = YosysSetup()
    
    try:
        success = setup.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[CANCELLED] Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
