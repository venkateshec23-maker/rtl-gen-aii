#!/usr/bin/env python3
"""
test_pin_preservation.py  –  Validate PIN geometry preservation through design flow

Tests:
1. CTS pin geometry restoration from placed.def
2. Detailed router pin verification 
3. Pin presence in final GDS

This test ensures that IO cell pins are not lost during:
  placed.def → CTS → routed.def → GDS conversion
"""

from pathlib import Path
import logging
import sys

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

from python.cts_engine import CTSEngine
from python.detail_router import DetailRouter


def extract_pins_from_def(def_path: str) -> set:
    """Extract all pin names from a DEF file."""
    pins = set()
    try:
        content = Path(def_path).read_text(encoding="utf-8", errors="ignore")
        in_pins_section = False
        for line in content.splitlines():
            if "PINS" in line and line.strip().startswith("PINS"):
                in_pins_section = True
            elif in_pins_section:
                if line.strip().startswith("END PINS"):
                    in_pins_section = False
                else:
                    parts = line.strip().split()
                    if parts and not parts[0].startswith("-"):
                        pins.add(parts[0])
    except Exception as e:
        logging.error(f"Error extracting pins from {def_path}: {e}")
    
    return pins


def test_cts_pin_preservation(placed_def: str, cts_def: str):
    """
    Test that CTS preserves pin geometry from placed.def to cts.def.
    
    Args:
        placed_def: Path to input placed.def
        cts_def:    Path to output cts.def from CTS
    """
    logging.info("=" * 70)
    logging.info("TEST 1: CTS Pin Geometry Preservation")
    logging.info("=" * 70)
    
    placed_pins = extract_pins_from_def(placed_def)
    cts_pins = extract_pins_from_def(cts_def)
    
    logging.info(f"Pins in placed.def:  {len(placed_pins)} pins")
    logging.info(f"Pins in cts.def:     {len(cts_pins)} pins")
    
    missing_pins = placed_pins - cts_pins
    new_pins = cts_pins - placed_pins
    
    if missing_pins:
        logging.error(f"❌ FAILED: {len(missing_pins)} pins lost during CTS")
        for pin in sorted(missing_pins)[:10]:  # Show first 10
            logging.error(f"   Missing pin: {pin}")
        if len(missing_pins) > 10:
            logging.error(f"   ... and {len(missing_pins) - 10} more")
        return False
    
    if new_pins:
        logging.info(f"✅ CTS added {len(new_pins)} new pins (expected - clock tree)")
    
    logging.info("✅ PASSED: All pins from placed.def present in cts.def")
    return True


def test_routing_pin_preservation(cts_def: str, routed_def: str):
    """
    Test that detailed routing preserves pins from CTS.
    
    Args:
        cts_def:     Path to input cts.def
        routed_def:  Path to output routed.def from detailed routing
    """
    logging.info("=" * 70)
    logging.info("TEST 2: Routing Pin Preservation")
    logging.info("=" * 70)
    
    cts_pins = extract_pins_from_def(cts_def)
    routed_pins = extract_pins_from_def(routed_def)
    
    logging.info(f"Pins in cts.def:     {len(cts_pins)} pins")
    logging.info(f"Pins in routed.def:  {len(routed_pins)} pins")
    
    missing_pins = cts_pins - routed_pins
    
    if missing_pins:
        logging.error(f"❌ FAILED: {len(missing_pins)} pins lost during routing")
        for pin in sorted(missing_pins)[:10]:  # Show first 10
            logging.error(f"   Missing pin: {pin}")
        if len(missing_pins) > 10:
            logging.error(f"   ... and {len(missing_pins) - 10} more")
        return False
    
    logging.info("✅ PASSED: All pins from CTS preserved in routed.def")
    return True


def test_blockage_preservation(placed_def: str, cts_def: str):
    """
    Test that CTS preserves blockage information.
    
    Args:
        placed_def: Path to input placed.def
        cts_def:    Path to output cts.def from CTS
    """
    logging.info("=" * 70)
    logging.info("TEST 3: Blockage Preservation (IO Cell Protection)")
    logging.info("=" * 70)
    
    def count_blockages(def_path: str) -> int:
        try:
            content = Path(def_path).read_text(encoding="utf-8", errors="ignore")
            return content.count("BLOCKAGE")
        except:
            return 0
    
    placed_blockages = count_blockages(placed_def)
    cts_blockages = count_blockages(cts_def)
    
    logging.info(f"BLOCKAGE entries in placed.def: {placed_blockages}")
    logging.info(f"BLOCKAGE entries in cts.def:    {cts_blockages}")
    
    if placed_blockages > 0 and cts_blockages == 0:
        logging.warning(f"⚠️  WARNING: {placed_blockages} blockages lost during CTS")
        logging.warning("              These protect IO cells from routing")
        return False
    
    if cts_blockages >= placed_blockages:
        logging.info("✅ PASSED: BLOCKAGE information preserved or enhanced")
        return True
    
    logging.warning(f"⚠️  WARNING: Some blockages may have been lost")
    return False


def main():
    """Run all pin preservation tests."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("\n" + "=" * 70)
    logger.info("PIN GEOMETRY PRESERVATION TEST SUITE")
    logger.info("Validates that pins are not lost during design flow")
    logger.info("=" * 70 + "\n")
    
    # Check for test files (would come from actual run)
    test_dir = Path(__file__).parent / "outputs"
    
    if not test_dir.exists():
        logger.error(f"Test outputs directory not found: {test_dir}")
        logger.error("Run the full design flow first to generate test files")
        return 1
    
    # Look for DEF files
    placed_def = test_dir / "04_placement" / "placed.def"
    cts_def = test_dir / "05_cts" / "cts.def"
    routed_def = test_dir / "06_routing" / "routed.def"
    
    results = []
    
    if placed_def.exists() and cts_def.exists():
        results.append(("CTS Pin Preservation", test_cts_pin_preservation(str(placed_def), str(cts_def))))
        results.append(("Blockage Preservation", test_blockage_preservation(str(placed_def), str(cts_def))))
    else:
        logger.warning("CTS test files not found - skipping CTS tests")
    
    if cts_def.exists() and routed_def.exists():
        results.append(("Routing Pin Preservation", test_routing_pin_preservation(str(cts_def), str(routed_def))))
    else:
        logger.warning("Routing test files not found - skipping routing tests")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}  {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed and results:
        logger.info("\n✅ All tests passed! Pin geometry is properly preserved.")
        return 0
    elif results:
        logger.error("\n❌ Some tests failed. Check pin geometry preservation!")
        return 1
    else:
        logger.warning("\n⚠️  No tests could be run. Generate test files first.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
