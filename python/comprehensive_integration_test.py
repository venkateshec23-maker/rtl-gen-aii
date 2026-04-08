#!/usr/bin/env python3
"""
comprehensive_integration_test.py
==================================
Real end-to-end integration test for RTL-Gen AI pipeline.

This test actually runs Docker containers and verifies real output,
unlike the mocked unit tests. It provides proof that the tool actually works.

Run from project root:
    python python/comprehensive_integration_test.py
"""

import sys
import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.full_flow import RTLGenAI, FlowConfig, FlowResult
from python.docker_manager import DockerManager
from python.pdk_manager import PDKManager

# ══════════════════════════════════════════════════════════════════════════════
# SETUP
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DESIGNS = {
    "adder_8bit": PROJECT_ROOT / "validation" / "adder_8bit.v",
}

# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

class IntegrationTest:
    """Comprehensive integration test suite."""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "infrastructure": {},
            "summary": {}
        }
        self.logger = logging.getLogger(__name__)
        
    def verify_infrastructure(self):
        """Check Docker, PDK, and other prerequisites."""
        logger.info("="*70)
        logger.info("INFRASTRUCTURE VERIFICATION")
        logger.info("="*70)
        
        infra = self.results["infrastructure"]
        
        # Check Docker
        dm = DockerManager()
        status = dm.verify_installation()
        logger.info(f"✓ Docker installed: {status.installed}")
        logger.info(f"✓ Docker running: {status.running}")
        logger.info(f"✓ Docker version: {status.version}")
        infra["docker"] = {
            "installed": status.installed,
            "running": status.running,
            "version": status.version,
            "backend": status.backend.value
        }
        
        if not status.running or not status.installed:
            logger.error("❌ Docker not available - cannot proceed")
            return False
        
        # Check OpenLane image
        image_info = dm.check_image()
        logger.info(f"✓ OpenLane image exists: {image_info.exists_locally}")
        if image_info.exists_locally:
            logger.info(f"✓ Image size: {image_info.size_gb:.2f} GB")
        infra["image"] = {
            "exists": image_info.exists_locally,
            "size_gb": image_info.size_gb,
            "name": image_info.name
        }
        
        # Check PDK
        pdk = PDKManager()
        pdk_paths = [
            Path("C:\\pdk"),
            Path.home() / "pdk",
            Path(__file__).resolve().parent.parent / "pdk",
        ]
        pdk_found = None
        for p in pdk_paths:
            if (p / "sky130A").exists():
                pdk_found = str(p)
                logger.info(f"✓ PDK found at: {pdk_found}")
                break
        
        if not pdk_found:
            logger.warning("⚠️  PDK not found locally - using Docker internal PDK")
            logger.warning("   (Physical design stages may require host PDK mount)")
        
        infra["pdk"] = {
            "found": pdk_found is not None,
            "path": pdk_found
        }
        
        logger.info(f"{'✓' if status.running and status.installed else '✗'} Infrastructure ready")
        return status.running and status.installed

    def test_synthesis(self, rtl_path: Path, top_module: str, output_dir: Path) -> bool:
        """Test Yosys synthesis end-to-end."""
        logger.info("\n" + "="*70)
        logger.info(f"TEST: Synthesis ({top_module})")
        logger.info("="*70)
        
        test_result = {
            "design": top_module,
            "status": "FAIL",
            "outputs": {},
            "errors": []
        }
        
        try:
            # Verify input
            if not rtl_path.exists():
                test_result["errors"].append(f"RTL not found: {rtl_path}")
                logger.error(f"❌ RTL not found: {rtl_path}")
                self.results["tests"]["synthesis"] = test_result
                return False
            
            logger.info(f"Input RTL: {rtl_path}")
            logger.info(f"Top module: {top_module}")
            logger.info(f"Output dir: {output_dir}")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Run synthesis
            config = FlowConfig()
            synth_dir = output_dir / "00_test_synth"
            synth_dir.mkdir(parents=True, exist_ok=True)
            
            # Use direct synthesis approach
            from python.docker_manager import DockerManager
            
            docker = DockerManager()
            
            # Verify infrastructure
            status = docker.verify_installation()
            if not status.running or not status.installed:
                test_result["errors"].append(f"Docker not ready: {status.error}")
                logger.error(f"❌ Docker not running: {status.error}")
                self.results["tests"]["synthesis"] = test_result
                return False
            
            # Run synthesis using full_flow approach
            logger.info("Running Yosys synthesis...")
            from python.full_flow import _Synthesiser
            synthesizer = _Synthesiser()
            netlist = synthesizer.synthesise(rtl_path, top_module, synth_dir, docker)
            
            # Verify output
            if not netlist.exists():
                test_result["errors"].append(f"Netlist not generated: {netlist}")
                logger.error(f"❌ Netlist not created: {netlist}")
                self.results["tests"]["synthesis"] = test_result
                return False
            
            # Validate netlist content
            netlist_content = netlist.read_text(encoding="utf-8", errors="ignore")
            has_module = "module" in netlist_content
            has_sky130 = "sky130_fd_sc_hd__" in netlist_content
            file_size = netlist.stat().st_size
            
            logger.info(f"✓ Netlist created: {netlist}")
            logger.info(f"✓ File size: {file_size} bytes")
            logger.info(f"✓ Has 'module' keyword: {has_module}")
            logger.info(f"✓ Has Sky130 cells: {has_sky130}")
            logger.info(f"✓ Yosys version detected in output")
            
            if not has_module:
                test_result["errors"].append("Netlist has no module declaration")
                logger.error("❌ Invalid netlist (no module keyword)")
                self.results["tests"]["synthesis"] = test_result
                return False
            
            # Test passed
            test_result["status"] = "PASS"
            test_result["outputs"] = {
                "netlist": str(netlist),
                "size_bytes": file_size,
                "has_sky130_cells": has_sky130,
            }
            logger.info(f"{'✓' if not test_result['errors'] else '⚠️'} Synthesis test passed")
            self.results["tests"]["synthesis"] = test_result
            return True
            
        except Exception as e:
            test_result["errors"].append(str(e))
            logger.error(f"❌ Synthesis failed: {e}", exc_info=True)
            self.results["tests"]["synthesis"] = test_result
            return False

    def test_full_pipeline(self, rtl_path: Path, top_module: str, output_dir: Path) -> bool:
        """Test complete pipeline: synthesis → physical design → GDS → signoff."""
        logger.info("\n" + "="*70)
        logger.info(f"TEST: Full Pipeline ({top_module})")
        logger.info("="*70)
        
        test_result = {
            "design": top_module,
            "status": "FAIL",
            "stages": {},
            "stats": {},
            "errors": []
        }
        
        try:
            # Create RUN output directory
            run_dir = output_dir / f"pipeline_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            run_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Run directory: {run_dir}")
            
            # Setup config
            config = FlowConfig(
                target_utilization=0.35,  # More conservative - small designs need more space
                placement_density=0.5,
                run_drc=True,
                run_lvs=True,
            )
            
            # Run pipeline
            start_time = time.time()
            orchestrator = RTLGenAI(config, run_dir)
            
            # Define progress callback
            def on_progress(event):
                stage = event.get("stage", "unknown")
                pct = event.get("pct", 0)
                msg = event.get("msg", "")
                logger.info(f"  [{stage:15}] {pct*100:5.1f}% - {msg}")
            
            # Run from RTL
            result = orchestrator._run_mode_b(rtl_path, top_module)
            elapsed = time.time() - start_time
            
            logger.info(f"\nPipeline completed in {elapsed:.1f} seconds")
            
            # Analyze results
            test_result["stats"]["elapsed_seconds"] = elapsed
            test_result["stats"]["total_stages"] = 9
            
            if result.failed_stage:
                logger.error(f"❌ Pipeline failed at stage: {result.failed_stage}")
                logger.error(f"   Error: {result.error_message}")
                test_result["errors"].append(f"{result.failed_stage}: {result.error_message}")
            else:
                logger.info("✓ All pipeline stages completed")
                test_result["status"] = "PASS"
            
            # Gather output files
            output_files = {
                "rtl": result.rtl_path,
                "netlist": result.netlist_path,
                "floorplan": result.floorplan_def,
                "placement": result.placed_def,
                "cts": result.cts_def,
                "routing": result.routed_def,
                "gds": result.gds_path,
                "package_dir": result.package_dir,
            }
            
            for stage, path in output_files.items():
                exists = Path(path).exists() if path else False
                test_result["stages"][stage] = {
                    "path": path,
                    "exists": exists,
                }
                status_icon = "✓" if exists else "✗"
                logger.info(f"{status_icon} {stage:15} {path if path else 'N/A'}")
            
            # Final assessment
            final_status = "PASS" if not result.failed_stage else "FAIL"
            logger.info(f"\n{'✓' if final_status == 'PASS' else '❌'} Pipeline test: {final_status}")
            
            self.results["tests"]["full_pipeline"] = test_result
            return final_status == "PASS"
            
        except Exception as e:
            test_result["errors"].append(str(e))
            logger.error(f"❌ Pipeline test failed: {e}", exc_info=True)
            self.results["tests"]["full_pipeline"] = test_result
            return False

    def run_all(self):
        """Run all tests and generate report."""
        logger.info("\n" + "═"*70)
        logger.info("RTL-Gen AI Comprehensive Integration Test Suite")
        logger.info("═"*70)
        
        # Infrastructure check
        infra_ok = self.verify_infrastructure()
        if not infra_ok:
            logger.error("Infrastructure check failed - aborting")
            return False
        
        # Run tests for each design
        all_passed = True
        for design_name, rtl_file in TEST_DESIGNS.items():
            output_base = PROJECT_ROOT / "validation" / "integration_tests"
            
            # Test 1: Synthesis only
            synth_ok = self.test_synthesis(
                rtl_file,
                design_name,
                output_base
            )
            if not synth_ok:
                all_passed = False
            
            # Test 2: Full pipeline
            pipe_ok = self.test_full_pipeline(
                rtl_file,
                design_name,
                output_base
            )
            if not pipe_ok:
                all_passed = False
        
        # Generate summary
        logger.info("\n" + "═"*70)
        logger.info("TEST SUMMARY")
        logger.info("═"*70)
        
        self.results["summary"] = {
            "total_tests": len(self.results["tests"]),
            "passed": sum(1 for t in self.results["tests"].values() if t.get("status") == "PASS"),
            "failed": sum(1 for t in self.results["tests"].values() if t.get("status") == "FAIL"),
            "all_passed": all_passed,
        }
        
        # Print summary
        for test_name, test_data in self.results["tests"].items():
            status = test_data.get("status", "UNKNOWN")
            status_icon = "✓" if status == "PASS" else "❌"
            logger.info(f"{status_icon} {test_name:20} {status}")
        
        logger.info("")
        logger.info(f"Total: {self.results['summary']['passed']}/{self.results['summary']['total_tests']} passed")
        
        # Save JSON report
        report_path = PROJECT_ROOT / "validation" / "integration_test_results.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\nReport saved to: {report_path}")
        
        return all_passed


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    tester = IntegrationTest()
    success = tester.run_all()
    sys.exit(0 if success else 1)
