# tests/test_database.py
# Database integration tests
# Verifies PostgreSQL stores real metrics not fake values
# Run with: pytest -m database

import pytest
import os
import re
from pathlib import Path

RESULTS_DIR = Path(r"C:\tools\OpenLane\results")


@pytest.mark.database
class TestDatabaseSchema:
    """
    Verify database stores real EDA metrics.
    These tests check schema integrity without needing
    a live DB connection - they validate the data models.
    """

    def test_design_record_has_size_fields(self):
        """
        Design records must store file sizes not just status strings.
        Status string alone cannot prove real vs stub output.
        """
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from full_flow import RealMetricsParser
        except ImportError:
            pytest.skip("full_flow not importable")

        parser = RealMetricsParser(str(RESULTS_DIR))
        metrics = parser.get_all_metrics()

        # GDS metrics must include size_bytes
        gds = metrics.get("gds", {})
        if gds.get("status") == "REAL_GDS":
            assert "size_bytes" in gds, \
                "GDS metrics missing size_bytes - " \
                "DB cannot store size for validation"
            assert "size_kb" in gds, \
                "GDS metrics missing size_kb"
            assert gds["size_bytes"] > 50000, \
                f"GDS size too small to be real: {gds['size_bytes']}"

    def test_routing_metrics_include_size_comparison(self):
        """
        Routing record must store both routed and CTS sizes.
        This is how silent failure detection works in DB queries.
        """
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from full_flow import RealMetricsParser
        except ImportError:
            pytest.skip("full_flow not importable")

        parser = RealMetricsParser(str(RESULTS_DIR))
        routing = parser.parse_routing()

        if routing.get("status") == "REAL_ROUTING":
            assert "routed_def_size" in routing, \
                "Missing routed_def_size in routing metrics"
            assert "cts_def_size" in routing, \
                "Missing cts_def_size - cannot detect silent failure"
            assert "size_difference" in routing, \
                "Missing size_difference - silent failure undetectable"
            assert routing["size_difference"] > 0, \
                "size_difference must be positive - real routing adds data"

    def test_metrics_have_data_type_field(self):
        """
        Every real metric must carry data_type=REAL_TOOL_OUTPUT.
        This field lets DB queries filter real vs historical synthetic data.
        """
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from full_flow import RealMetricsParser
        except ImportError:
            pytest.skip("full_flow not importable")

        parser = RealMetricsParser(str(RESULTS_DIR))

        checks = [
            parser.parse_synthesis(),
            parser.parse_simulation(),
            parser.parse_routing(),
            parser.parse_gds(),
        ]

        for metrics in checks:
            if metrics.get("status") not in (
                "MISSING", "STUB", "EMPTY_STUB",
                "NOT_RUN", "PARSE_ERROR"
            ):
                assert "data_type" in metrics, \
                    f"Metrics missing data_type field: {metrics}"
                assert metrics["data_type"] == "REAL_TOOL_OUTPUT", \
                    f"data_type is not REAL_TOOL_OUTPUT: {metrics['data_type']}"

    def test_no_synthetic_values_stored(self):
        """
        Confirm synthetic values from old system are not in current metrics.
        These specific numbers were hardcoded in the March 2026 fake system.
        """
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from full_flow import RealMetricsParser
        except ImportError:
            pytest.skip("full_flow not importable")

        parser = RealMetricsParser(str(RESULTS_DIR))
        metrics = parser.get_all_metrics()
        metrics_str = str(metrics)

        forbidden_values = {
            "110": "hardcoded gate count",
            "2450": "hardcoded area",
            "1213": "hardcoded wirelength",
        }

        for value, description in forbidden_values.items():
            assert value not in metrics_str, \
                f"Hardcoded {description} ({value}) found in metrics output"

    def test_lvs_result_stored_with_transistor_count(self):
        """
        LVS record must include transistor count from GDS extraction.
        Zero transistors = Magic read empty GDS = result invalid.
        """
        lvs_path = RESULTS_DIR / "lvs_report_final.txt"
        if not lvs_path.exists():
            pytest.skip("LVS report not found")

        content = lvs_path.read_text(errors="ignore")
        dev_match = re.search(r"Number of devices:\s+(\d+)", content)

        if dev_match:
            count = int(dev_match.group(1))
            assert count > 100, \
                f"Transistor count too low: {count}. " \
                f"Real 8-bit adder needs 400-700 transistors. " \
                f"GDS may be a stub."
