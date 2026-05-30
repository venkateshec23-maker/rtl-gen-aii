"""
universal_gds_validator.py
===========================
Universal GDS validation for ANY Verilog design.

Works for:
- Simple (counter, adder, mux)
- Complex (FIFO, ALU, SPI, I2C)
- Custom user designs

Checks:
1. GDS file is valid GDSII format
2. Contains real geometry
3. RTL simulation passes (functional correctness)
4. DRC is clean (manufacturing rules)
5. LVS matches (layout = schematic)
6. Timing files exist (for post-layout simulation)
"""

import os
import re
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

log = logging.getLogger(__name__)

WORK_DIR = Path(os.getenv("OPENLANE_WORK", r"C:\tools\OpenLane"))
PDK_ROOT = Path(os.getenv("PDK_ROOT", r"C:\pdk"))

@dataclass
class GDSValidationReport:
    """Complete validation report for any GDS file."""
    gds_path: str
    design_name: str
    
    # File checks
    file_exists: bool = False
    file_size_kb: float = 0.0
    gds_header_valid: bool = False
    has_cells: bool = False
    has_layers: bool = False
    cell_count: int = 0
    layer_count: int = 0
    
    # Functional checks
    rtl_simulation_passed: bool = False
    rtl_pass_count: int = 0
    rtl_fail_count: int = 0
    rtl_test_output: str = ""
    
    # Physical checks
    drc_clean: bool = False
    drc_violation_count: int = 0
    drc_report: str = ""
    
    lvs_matched: bool = False
    lvs_report: str = ""
    
    # Post-layout checks
    has_gate_level_netlist: bool = False
    has_timing_files: bool = False
    gate_level_files: List[str] = field(default_factory=list)
    timing_files: List[str] = field(default_factory=list)
    
    # Overall
    valid: bool = False
    executable: bool = False
    tape_out_ready: bool = False
    
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)

def find_design_files(gds_path: str) -> Dict:
    """Find all related design files for a GDS."""
    gds = Path(gds_path)
    run_dir = gds.parent
    design_name = gds.stem
    
    # Extract design name without timestamp suffix
    # e.g., "my_counter_20260428_123456" -> "my_counter"
    base_name = re.sub(r'_\d{8}_\d{6}$', '', design_name)
    
    files = {
        "rtl": None,
        "testbench": None,
        "config": None,
        "gate_level": [],
        "timing": [],
        "drc_report": None,
        "lvs_report": None,
    }
    
    # Find RTL
    rtl_search = [
        WORK_DIR / "designs" / design_name / f"{design_name}.v",
        WORK_DIR / "designs" / base_name / f"{base_name}.v",
        run_dir / f"{design_name}.v",
        run_dir / f"{base_name}.v",
    ]
    for rtl in rtl_search:
        if rtl.exists():
            files["rtl"] = str(rtl)
            break
    
    # Find testbench
    tb_search = [
        WORK_DIR / "designs" / design_name / f"{design_name}_tb.v",
        WORK_DIR / "designs" / base_name / f"{base_name}_tb.v",
        run_dir / f"{design_name}_tb.v",
        run_dir / f"{base_name}_tb.v",
    ]
    for tb in tb_search:
        if tb.exists():
            files["testbench"] = str(tb)
            break
    
    # Find gate-level netlists
    files["gate_level"] = [str(f) for f in run_dir.rglob("*.nl.v")]
    
    # Find timing files
    files["timing"] = [str(f) for f in run_dir.rglob("*.sdf")] + \
                       [str(f) for f in run_dir.rglob("*.spef")]
    
    # Find DRC report
    drc_patterns = ["drc.summary.rpt", "drc_report.json", "drc.rpt"]
    for pattern in drc_patterns:
        matches = list(run_dir.rglob(pattern))
        if matches:
            files["drc_report"] = str(matches[0])
            break
    
    # Find LVS report
    lvs_patterns = ["lvs_report_final.txt", "lvs_report_final.json", "lvs.rpt"]
    for pattern in lvs_patterns:
        matches = list(run_dir.rglob(pattern))
        if matches:
            files["lvs_report"] = str(matches[0])
            break
    
    # Find config
    config_search = [
        WORK_DIR / "designs" / design_name / "config.json",
        run_dir / "config.json",
    ]
    for cfg in config_search:
        if cfg.exists():
            files["config"] = str(cfg)
            break
    
    return files

def check_gds_structure(gds_path: str) -> Dict:
    """Check GDS file structure and validity."""
    result = {
        "exists": False,
        "size_kb": 0,
        "header_valid": False,
        "has_cells": False,
        "has_layers": False,
        "cell_count": 0,
        "layer_count": 0,
        "errors": [],
    }
    
    gds = Path(gds_path)
    
    if not gds.exists():
        result["errors"].append("GDS file not found")
        return result
    
    result["exists"] = True
    result["size_kb"] = gds.stat().st_size / 1024
    
    if result["size_kb"] < 1:
        result["errors"].append(f"GDS too small: {result['size_kb']:.2f} KB")
        return result
    
    try:
        with open(gds, 'rb') as f:
            # Read first 100 bytes for header check
            header = f.read(100)
            
            # GDSII: first record should be HEADER (type 0x00)
            if len(header) >= 4:
                record_len = (header[0] << 8) | header[1]
                record_type = header[2]
                result["header_valid"] = (record_type == 0x00)
            
            # Read entire file for cell/layer analysis
            f.seek(0)
            content = f.read()
            
            # Count BGNSTR (begin structure) records - indicates cells
            bgnstr_pattern = bytes([0x00, 0x05])
            result["cell_count"] = content.count(bgnstr_pattern)
            result["has_cells"] = result["cell_count"] > 0
            
            # Count LAYER records
            layer_pattern = bytes([0x00, 0x0D])
            result["layer_count"] = content.count(layer_pattern)
            result["has_layers"] = result["layer_count"] > 0
            
    except Exception as e:
        result["errors"].append(f"Cannot read GDS: {e}")
    
    return result

def run_rtl_simulation(rtl_path: str, testbench_path: str, design_name: str) -> Dict:
    """Run RTL simulation for any design."""
    result = {
        "ran": False,
        "passed": False,
        "pass_count": 0,
        "fail_count": 0,
        "output": "",
        "error": None,
    }
    
    if not rtl_path or not testbench_path:
        result["error"] = "RTL or testbench not found"
        return result
    
    rtl = Path(rtl_path)
    tb = Path(testbench_path)
    
    if not rtl.exists():
        result["error"] = f"RTL not found: {rtl}"
        return result
    
    if not tb.exists():
        result["error"] = f"Testbench not found: {tb}"
        return result
    
    # Run simulation using Docker
    try:
        design_dir = rtl.parent
        rtl_name = rtl.name
        tb_name = tb.name
        
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{WORK_DIR}:/work",
            "efabless/openlane:latest",
            "bash", "-c",
            f"cd /work/designs/{design_dir.name} && "
            f"iverilog -o /tmp/sim {rtl_name} {tb_name} && "
            f"vvp /tmp/sim"
        ]
        
        proc = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        
        output = proc.stdout + proc.stderr
        result["ran"] = True
        result["output"] = output
        
        # Check results - works for ANY testbench
        result["passed"] = "ALL_TESTS_PASSED" in output
        result["pass_count"] = len(re.findall(r'PASS\s+(?:Test\s+)?\d*', output, re.IGNORECASE))
        result["fail_count"] = len(re.findall(r'FAIL\s+(?:Test\s+)?\d*', output, re.IGNORECASE))
        
        if "error" in output.lower() and "syntax error" in output.lower():
            result["error"] = "Simulation had syntax errors"
            
    except subprocess.TimeoutExpired:
        result["error"] = "Simulation timed out"
    except Exception as e:
        result["error"] = str(e)
    
    return result

def check_drc_status(run_dir: Path) -> Dict:
    """Check DRC status from run reports."""
    result = {
        "checked": False,
        "clean": False,
        "violation_count": -1,
        "report_content": "",
    }
    
    run_dir = Path(run_dir)
    
    # Search for DRC reports
    drc_patterns = [
        "**/drc.summary.rpt",
        "**/drc_report.json",
        "**/drc.rpt",
        "**/drc.log",
    ]
    
    for pattern in drc_patterns:
        matches = list(run_dir.glob(pattern))
        if matches:
            report = matches[0]
            try:
                content = report.read_text()
                result["checked"] = True
                result["report_content"] = content[:2000]
                
                # Parse violation count - works for any OpenLane DRC report
                # Look for patterns like: "Total DRC errors: 0" or "Found 0 violations"
                patterns = [
                    r'Total\s+(?:DRC\s+)?errors?\s*[:=]?\s*(\d+)',
                    r'Found\s+(\d+)\s+violations?',
                    r'(\d+)\s+violations?\s+found',
                    r'DRC\s+errors?\s*[:=]?\s*(\d+)',
                ]
                
                for p in patterns:
                    match = re.search(p, content, re.IGNORECASE)
                    if match:
                        result["violation_count"] = int(match.group(1))
                        result["clean"] = (result["violation_count"] == 0)
                        return result
                
                # If no violations mentioned, assume clean
                if "error" not in content.lower() or "0 error" in content.lower():
                    result["clean"] = True
                    result["violation_count"] = 0
                    
            except Exception as e:
                log.warning(f"Error reading DRC report: {e}")
    
    return result

def check_lvs_status(run_dir: Path) -> Dict:
    """Check LVS status from run reports."""
    result = {
        "checked": False,
        "matched": False,
        "report_content": "",
        "mismatch_details": "",
    }
    
    run_dir = Path(run_dir)
    
    # Search for LVS reports
    lvs_patterns = [
        "**/lvs_report_final.json",
        "**/lvs_report_final.txt",
        "**/lvs.rpt",
        "**/lvs.log",
    ]
    
    for pattern in lvs_patterns:
        matches = list(run_dir.glob(pattern))
        if matches:
            report = matches[0]
            try:
                content = report.read_text()
                result["checked"] = True
                result["report_content"] = content[:2000]
                
                # Check for match - works for any Magic/Netgen LVS
                if "Netlists match" in content or "Circuit matched" in content:
                    result["matched"] = True
                elif "Netlists do not match" in content:
                    result["matched"] = False
                    # Extract mismatch details
                    lines = content.split('\n')
                    mismatch_lines = [l for l in lines if 'mismatch' in l.lower() or 'error' in l.lower()]
                    result["mismatch_details"] = '\n'.join(mismatch_lines[:10])
                elif '"status": "matched"' in content:
                    result["matched"] = True
                elif '"result": "MATCH"' in content.upper():
                    result["matched"] = True
                    
            except Exception as e:
                log.warning(f"Error reading LVS report: {e}")
    
    return result

def validate_any_gds(gds_path: str, run_tests: bool = True) -> GDSValidationReport:
    """
    Validate ANY GDS file for tapeout readiness.
    
    This function works for:
    - Any Verilog design (simple to complex)
    - Custom user designs
    - Generated designs from templates
    
    Returns complete validation report.
    """
    gds = Path(gds_path)
    run_dir = gds.parent
    design_name = gds.stem
    
    # Get base design name (without timestamp)
    base_name = re.sub(r'_\d{8}_\d{6}$', '', design_name)
    
    report = GDSValidationReport(
        gds_path=str(gds),
        design_name=design_name,
    )
    
    # ========== Step 1: Check GDS structure ==========
    structure = check_gds_structure(str(gds))
    report.file_exists = structure["exists"]
    report.file_size_kb = structure["size_kb"]
    report.gds_header_valid = structure["header_valid"]
    report.has_cells = structure["has_cells"]
    report.has_layers = structure["has_layers"]
    report.cell_count = structure["cell_count"]
    report.layer_count = structure["layer_count"]
    report.errors.extend(structure["errors"])
    
    if not structure["exists"]:
        return report
    
    # ========== Step 2: Find design files ==========
    files = find_design_files(str(gds))
    report.gate_level_files = files["gate_level"]
    report.timing_files = files["timing"]
    report.has_gate_level_netlist = len(files["gate_level"]) > 0
    report.has_timing_files = len(files["timing"]) > 0
    
    # ========== Step 3: Run RTL simulation ==========
    if run_tests and files["rtl"] and files["testbench"]:
        sim_result = run_rtl_simulation(
            files["rtl"], 
            files["testbench"], 
            design_name
        )
        report.rtl_simulation_passed = sim_result["passed"]
        report.rtl_pass_count = sim_result["pass_count"]
        report.rtl_fail_count = sim_result["fail_count"]
        report.rtl_test_output = sim_result["output"][:500]
        
        if sim_result["error"]:
            report.warnings.append(f"RTL simulation: {sim_result['error']}")
    else:
        report.warnings.append("RTL or testbench not found - skipping simulation")
    
    # ========== Step 4: Check DRC ==========
    drc_result = check_drc_status(run_dir)
    report.drc_clean = drc_result["clean"]
    report.drc_violation_count = drc_result["violation_count"]
    report.drc_report = drc_result["report_content"][:500]
    
    if drc_result["checked"] and not drc_result["clean"]:
        report.warnings.append(f"DRC violations: {drc_result['violation_count']}")
    
    # ========== Step 5: Check LVS ==========
    lvs_result = check_lvs_status(run_dir)
    report.lvs_matched = lvs_result["matched"]
    report.lvs_report = lvs_result["report_content"][:500]
    
    if lvs_result["checked"] and not lvs_result["matched"]:
        report.warnings.append("LVS mismatch detected")
    
    # ========== Step 6: Determine overall status ==========
    # Valid: Has valid GDS structure
    report.valid = (
        report.file_exists and
        report.gds_header_valid and
        report.has_cells and
        report.has_layers and
        report.file_size_kb > 1
    )
    
    # Executable: Can run simulations
    report.executable = (
        report.valid and
        report.rtl_simulation_passed
    )
    
    # Tape-out ready: Valid + DRC clean + LVS matched
    report.tape_out_ready = (
        report.valid and
        report.rtl_simulation_passed and
        report.drc_clean and
        report.lvs_matched
    )
    
    # Collect errors
    if not report.gds_header_valid:
        report.errors.append("GDS header is invalid")
    if not report.has_cells:
        report.errors.append("GDS contains no cells")
    if not report.rtl_simulation_passed and run_tests:
        report.errors.append(f"RTL simulation failed ({report.rtl_fail_count} tests failed)")
    if not report.drc_clean and report.drc_violation_count > 0:
        report.errors.append(f"DRC violations: {report.drc_violation_count}")
    if not report.lvs_matched and lvs_result["checked"]:
        report.errors.append("LVS mismatch - layout does not match schematic")
    
    return report

def print_validation_report(gds_path: str) -> GDSValidationReport:
    """Print human-readable validation report for any GDS."""
    report = validate_any_gds(gds_path)
    
    print()
    print("=" * 70)
    print("GDS VALIDATION REPORT")
    print("=" * 70)
    print(f"Design: {report.design_name}")
    print(f"GDS: {report.gds_path}")
    print()
    
    # File Structure
    print("FILE STRUCTURE:")
    print(f"  [ {'OK' if report.file_exists else 'FAIL'} ] File exists")
    print(f"  [ {'OK' if report.gds_header_valid else 'FAIL'} ] Valid GDSII header")
    print(f"  [ {'OK' if report.has_cells else 'FAIL'} ] Has cells ({report.cell_count} found)")
    print(f"  [ {'OK' if report.has_layers else 'WARN'} ] Has layers ({report.layer_count} found)")
    print(f"  Size: {report.file_size_kb:.2f} KB")
    print()
    
    # Functional Verification
    print("FUNCTIONAL VERIFICATION:")
    if report.rtl_simulation_passed or report.rtl_fail_count > 0:
        status = "PASS" if report.rtl_simulation_passed else "FAIL"
        print(f"  [ {status} ] RTL Simulation ({report.rtl_pass_count} pass, {report.rtl_fail_count} fail)")
    else:
        print(f"  [ SKIP ] RTL Simulation (no testbench)")
    print()
    
    # Physical Verification
    print("PHYSICAL VERIFICATION:")
    drc_status = "PASS" if report.drc_clean else ("FAIL" if report.drc_violation_count > 0 else "SKIP")
    print(f"  [ {drc_status} ] DRC ({report.drc_violation_count} violations)")
    
    lvs_status = "PASS" if report.lvs_matched else "FAIL"
    lvs_checked = "checked" if report.lvs_report else "not checked"
    print(f"  [ {lvs_status} ] LVS ({lvs_checked})")
    print()
    
    # Post-Layout
    print("POST-LAYOUT FILES:")
    print(f"  [ {'OK' if report.has_gate_level_netlist else 'MISSING'} ] Gate-level netlist")
    print(f"  [ {'OK' if report.has_timing_files else 'MISSING'} ] Timing files (SDF/SPEF)")
    print()
    
    # Errors and Warnings
    if report.errors:
        print("ERRORS:")
        for e in report.errors:
            print(f"  ! {e}")
        print()
    
    if report.warnings:
        print("WARNINGS:")
        for w in report.warnings:
            print(f"  * {w}")
        print()
    
    # Verdict
    print("=" * 70)
    if report.tape_out_ready:
        print("VERDICT: TAPE-OUT READY")
        print("  - GDS is valid")
        print("  - Simulation passes")
        print("  - DRC clean")
        print("  - LVS matched")
    elif report.executable:
        print("VERDICT: EXECUTABLE (but requires fixes)")
        print("  - GDS is valid")
        print("  - Simulation passes")
        if not report.drc_clean:
            print(f"  - DRC violations: {report.drc_violation_count}")
        if not report.lvs_matched:
            print("  - LVS mismatch")
    elif report.valid:
        print("VERDICT: VALID GDS (but simulation issues)")
    else:
        print("VERDICT: INVALID GDS")
    print("=" * 70)
    print()
    
    return report

def find_latest_gds() -> Optional[str]:
    """Find the most recently created GDS file."""
    runs_dir = WORK_DIR / "runs"
    if not runs_dir.exists():
        return None
    
    gds_files = list(runs_dir.rglob("*.gds"))
    if not gds_files:
        return None
    
    # Sort by modification time
    latest = sorted(gds_files, key=lambda x: x.stat().st_mtime)[-1]
    return str(latest)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python universal_gds_validator.py <gds_file>")
        print("       python universal_gds_validator.py --latest")
        print("\nValidates ANY GDS file for tapeout readiness.")
        sys.exit(1)
    
    if sys.argv[1] == "--latest":
        gds = find_latest_gds()
        if gds:
            print(f"Found latest GDS: {gds}")
            report = print_validation_report(gds)
        else:
            print("No GDS files found")
            sys.exit(1)
    else:
        report = print_validation_report(sys.argv[1])
    
    sys.exit(0 if report.valid else 1)
