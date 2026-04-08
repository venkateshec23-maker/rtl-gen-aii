#!/usr/bin/env python3
"""
quick_validation_test.py  –  Quick Test of Pipeline Validation Framework
==========================================================================

This script demonstrates how to use the validation framework to check a
design before running it through the full RTL → GDSII flow.
"""

from pathlib import Path
from python.validate_pipeline import PipelineValidator, ValidationConfig


def main():
    """Quick validation test."""
    
    # Example 1: Validate with standard config
    print("=" * 70)
    print("EXAMPLE 1: Standard Validation")
    print("=" * 70)
    
    rtl_file = Path("adder_8bit.v")
    if rtl_file.exists():
        validator = PipelineValidator()
        report = validator.validate_full_pipeline(
            rtl_path=str(rtl_file),
            top_module="adder_8bit",
            output_dir="./validation_results",
        )
        
        # Print summary
        print(report.summary())
        print()
        
        # Check results programmatically
        print("Programmatic Result Check:")
        print(f"  All passed: {report.all_passed}")
        print(f"  Any critical: {report.any_critical}")
        print(f"  Total duration: {report.total_duration_sec:.2f}s")
        print()
    else:
        print(f"✗ RTL file not found: {rtl_file}")
        print()
    
    # Example 2: Custom config (quick mode)
    print("=" * 70)
    print("EXAMPLE 2: Quick Validation (No Docker/PDK Checks)")
    print("=" * 70)
    
    config = ValidationConfig(
        check_docker=False,
        check_pdk=False,
        quick_mode=True,
        generate_html_report=True,
        generate_json_report=True,
    )
    
    validator = PipelineValidator(config)
    report = validator.validate_full_pipeline(
        rtl_path=str(rtl_file),
        top_module="adder_8bit",
        output_dir="./validation_quick",
    )
    
    # Brief output
    status = "✓ PASS" if report.all_passed else "✗ FAIL"
    print(f"{status}: {len(report.stages)} stages validated in {report.total_duration_sec:.2f}s")
    print()
    
    # Example 3: Integration pattern
    print("=" * 70)
    print("EXAMPLE 3: Integration Pattern (for use in full flow)")
    print("=" * 70)
    
    def validate_before_synthesis(rtl_path: str, top_module: str):
        """
        Reusable pattern: validate RTL before sending to full_flow.
        """
        config = ValidationConfig(
            check_docker=True,
            check_pdk=True,
            quick_mode=False,
        )
        
        validator = PipelineValidator(config)
        report = validator.validate_full_pipeline(
            rtl_path=rtl_path,
            top_module=top_module,
        )
        
        # Decision logic
        if report.any_critical:
            raise RuntimeError(
                f"Critical validation failure in {[s for s in report.stages.values() if s.level.value == 'CRITICAL'][0].stage.value}"
            )
        
        if not report.all_passed:
            print(f"⚠ Warnings: {report.failure_summary()}")
        
        return report  # Return for logging/inspection
    
    try:
        report = validate_before_synthesis("adder_8bit.v", "adder_8bit")
        print(f"✓ Validation passed; safe to proceed with full flow")
    except RuntimeError as e:
        print(f"✗ {e}")
    print()
    
    # Example 4: Stage-level inspection
    print("=" * 70)
    print("EXAMPLE 4: Detailed Stage-by-Stage Analysis")
    print("=" * 70)
    
    validator = PipelineValidator()
    report = validator.validate_full_pipeline(
        rtl_path=str(rtl_file),
        top_module="adder_8bit",
    )
    
    print("\nStage-by-Stage Results:")
    for stage_name, result in report.stages.items():
        print(f"  {stage_name.value:30s} [{result.level.value:8s}] {result.message}")
    print()


if __name__ == "__main__":
    main()
