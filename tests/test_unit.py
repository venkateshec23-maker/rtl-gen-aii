# tests/test_unit.py
# Unit tests — run with: pytest -m unit
# Fast, no Docker, no EDA tools
# Tests logic, parsing, and file validation rules

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the classes we are testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from full_flow import RealMetricsParser, DockerManager, FILE_SIZE_THRESHOLDS


# ============================================================
# RealMetricsParser UNIT TESTS
# ============================================================

@pytest.mark.unit
class TestRealMetricsParser:
    """Test the parser logic without running real tools"""

    def setup_method(self):
        """Create temporary directory for test files"""
        self.tmpdir = tempfile.mkdtemp()
        self.parser = RealMetricsParser(self.tmpdir)

    def _write_file(self, filename: str, content: str) -> Path:
        """Helper to write test files"""
        path = Path(self.tmpdir) / filename
        path.write_text(content)
        return path

    def test_parse_synthesis_returns_error_when_missing(self):
        """Parser must return error dict when netlist missing"""
        result = self.parser.parse_synthesis()
        assert result["status"] == "MISSING"
        assert "action" in result
        assert "error" in result

    def test_parse_synthesis_detects_stub(self):
        """Parser must detect file that is too small"""
        path = self._write_file("adder_8bit_sky130.v", "small")
        result = self.parser.parse_synthesis()
        assert result["status"] == "STUB"
        assert "size_bytes" in result

    def test_parse_synthesis_detects_generic_cells(self):
        """Parser must flag generic cells as synthesis failure"""
        content = (
            "module adder_8bit();\n"
            "  $_XOR_ inst1 (.A(a), .B(b), .Y(y));\n"
            "  $_SDFF_PN0_ inst2 (.D(d), .Q(q));\n"
            "endmodule\n"
        ) * 20  # Make it large enough to pass size check

        self._write_file("adder_8bit_sky130.v", content)
        result = self.parser.parse_synthesis()
        assert result["status"] == "SYNTHESIS_INCOMPLETE"
        assert "action" in result

    def test_parse_synthesis_accepts_real_sky130(self):
        """Parser must accept real Sky130 mapped netlist"""
        content = (
            "module adder_8bit(clk, a, b, sum);\n"
            "  sky130_fd_sc_hd__xor2_1 inst1(.A(a[0]),.B(b[0]),.X(s0));\n"
            "  sky130_fd_sc_hd__dfrtp_1 ff1(.D(s0),.CLK(clk),.Q(sum[0]));\n"
            "endmodule\n"
        ) * 30  # Large enough

        self._write_file("adder_8bit_sky130.v", content)
        result = self.parser.parse_synthesis()
        assert result["status"] == "REAL_SKY130"
        assert result["total_cells"] > 0
        assert result["data_type"] == "REAL_TOOL_OUTPUT"

    def test_parse_routing_detects_silent_failure(self):
        """
        Parser must detect when routed.def == cts.def.
        This is the most dangerous silent failure in the pipeline.
        """
        # Write identical files — simulates the silent failure
        content = "VERSION 5.8;\nCOMPONENTS 42;\nEND DESIGN\n" * 100

        Path(self.tmpdir, "routed.def").write_text(content)
        Path(self.tmpdir, "cts.def").write_text(content)

        result = self.parser.parse_routing()
        assert result["status"] == "ROUTING_FAILED_SILENTLY"
        assert "SIGSEGV" in result["action"] or "PDN" in result["action"]

    def test_parse_routing_accepts_real_routing(self):
        """Parser must accept routing where routed.def > cts.def"""
        cts_content = "CTS DEF\n" * 100
        routed_content = "ROUTED DEF with wire data\n" * 300

        Path(self.tmpdir, "cts.def").write_text(cts_content)
        Path(self.tmpdir, "routed.def").write_text(routed_content)

        result = self.parser.parse_routing()
        assert result["status"] == "REAL_ROUTING"
        assert result["size_difference"] > 0

    def test_parse_gds_detects_empty_stub(self):
        """Parser must detect GDS stub"""
        stub = Path(self.tmpdir) / "adder_8bit.gds"
        stub.write_bytes(b'\x00' * 178)  # 178 bytes = the famous stub size

        result = self.parser.parse_gds()
        assert result["status"] == "EMPTY_STUB"
        assert "action" in result

    def test_parse_gds_accepts_real_gds(self):
        """Parser must accept GDS above threshold"""
        real_gds = Path(self.tmpdir) / "adder_8bit.gds"
        real_gds.write_bytes(b'\x00' * 100_000)  # 100KB

        result = self.parser.parse_gds()
        assert result["status"] == "REAL_GDS"
        assert result["size_kb"] > 50

    def test_parse_signoff_invalidates_drc_on_stub(self):
        """
        DRC passing on a stub GDS must be marked INVALID.
        This catches the false positive from April 1 audit.
        """
        # Write a stub GDS
        stub = Path(self.tmpdir) / "adder_8bit.gds"
        stub.write_bytes(b'\x00' * 178)

        # Write a DRC report showing 0 violations
        drc_report = Path(self.tmpdir) / "drc_report.txt"
        drc_report.write_text("DRC violations: 0\n")

        result = self.parser.parse_signoff()
        # DRC passing on stub must be INVALID not PASS
        assert result["drc"]["status"] == "INVALID", \
            "DRC should be INVALID when GDS is a stub — " \
            "0 violations on empty GDS is meaningless"

    def test_parse_lvs_detects_matched(self):
        """Parser must detect LVS MATCHED"""
        lvs_report = Path(self.tmpdir) / "lvs_report_final.txt"
        lvs_report.write_text(
            "Device classes adder_8bit_flat and adder_8bit are equivalent.\n"
        )

        result = self.parser.parse_signoff()
        assert result["lvs"]["status"] == "MATCHED"

    def test_parse_timing_handles_wns_zero(self):
        """
        WNS = 0.00 means no negative slack — timing is PASS.
        This was misread as "timing not analyzed" in early sessions.
        """
        sta_report = Path(self.tmpdir) / "sta_final.txt"
        sta_report.write_text(
            "slack (MET)   6.14\n"
            "wns 0.00\n"
            "tns 0.00\n"
        )

        result = self.parser.parse_timing()
        assert result["status"] == "PASS", \
            "WNS=0.00 must be PASS — it means no negative slack exists"

    def test_parse_timing_detects_violation(self):
        """Parser must detect negative slack as FAIL"""
        sta_report = Path(self.tmpdir) / "sta_final.txt"
        sta_report.write_text(
            "slack (VIOLATED)  -1.23\n"
            "wns -1.23\n"
            "tns -5.67\n"
        )

        result = self.parser.parse_timing()
        assert result["status"] == "FAIL"

    def test_get_all_metrics_never_returns_hardcoded(self):
        """
        get_all_metrics must never return hardcoded values.
        All values must come from files or be honest error dicts.
        """
        result = self.parser.get_all_metrics()

        # Flatten all string values
        all_strings = str(result)

        # These specific values were hardcoded in the old fake system
        forbidden = [
            "2450",     # hardcoded area
            "110 gates", # hardcoded gate count
            "45 ps",    # hardcoded CTS skew
            "1213",     # hardcoded wirelength
        ]
        for f in forbidden:
            assert f not in all_strings, \
                f"Hardcoded value '{f}' found in metrics output — " \
                f"remove all hardcoded values from RealMetricsParser"

    def test_get_all_metrics_has_disclaimer(self):
        """All metrics output must carry real data disclaimer"""
        result = self.parser.get_all_metrics()
        assert "disclaimer" in result
        assert "synthetic" not in result["disclaimer"].lower() or \
               "real" in result["disclaimer"].lower()


# ============================================================
# DockerManager UNIT TESTS (Strict Mocks)
# ============================================================

@pytest.mark.unit
class TestDockerManager:
    """
    Test DockerManager logic with strict mocks.
    Mocks enforce that Windows paths never leak into container commands.
    """

    def setup_method(self):
        self.manager = DockerManager(
            host_work = r"C:\tools\OpenLane",
            host_pdk  = r"C:\pdk"
        )

    def test_no_windows_paths_in_container_command(self):
        """
        CRITICAL: Windows backslash paths must never appear in
        the command string passed to Docker container.
        """
        cmd = self.manager._build_docker_cmd("yosys --version")
        container_cmd = " ".join(cmd)

        # The container command (last arg) must not have backslashes
        assert "\\" not in cmd[-1], \
            "Windows path leaked into Docker container command"

    def test_volume_mounts_use_windows_paths(self):
        """Volume mounts must use Windows paths on host side"""
        cmd = self.manager._build_docker_cmd("test")
        cmd_str = " ".join(cmd)

        # Volume mounts (-v) must reference Windows host paths
        assert r"C:\tools\OpenLane" in cmd_str, \
            "Docker volume mount missing Windows host path"

    def test_run_command_returns_tuple(self):
        """run_command must always return (rc, stdout, stderr)"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test output",
                stderr=""
            )
            rc, out, err = self.manager.run_command("echo test")

        assert isinstance(rc, int)
        assert isinstance(out, str)
        assert isinstance(err, str)

    def test_run_command_handles_timeout(self):
        """run_command must handle timeout gracefully — never raises"""
        import subprocess
        with patch("subprocess.run",
                   side_effect=subprocess.TimeoutExpired("cmd", 60)):
            rc, out, err = self.manager.run_command("slow_command", timeout=60)

        assert rc == -1
        assert "TIMEOUT" in err

    def test_run_command_handles_exception(self):
        """run_command must handle all exceptions — never raises"""
        with patch("subprocess.run", side_effect=Exception("test error")):
            rc, out, err = self.manager.run_command("bad_command")

        assert rc == -1
        assert "test error" in err


# ============================================================
# PREVENTION RULE ENFORCEMENT TESTS
# ============================================================

@pytest.mark.unit
class TestPreventionRules:
    """
    These tests enforce the prevention policy in code.
    They fail if forbidden patterns appear in the codebase.
    """

    PROJECT_ROOT = Path(__file__).parent.parent

    def _scan_for_pattern(self, pattern: str, file_glob: str) -> list:
        """Find files containing forbidden pattern"""
        found = []
        for f in self.PROJECT_ROOT.rglob(file_glob):
            f_str = str(f)
            if ".git" in f_str or "__pycache__" in f_str or ".venv" in f_str:
                continue
            try:
                content = f.read_text(errors="ignore")
                if pattern in content:
                    # Find line numbers
                    for i, line in enumerate(content.split('\n'), 1):
                        if pattern in line:
                            found.append(f"{f}:{i}: {line.strip()}")
            except Exception:
                pass
        return found

    def test_no_hardcoded_gate_count(self):
        """110 gates must not appear as hardcoded value in Python files"""
        found = self._scan_for_pattern("110 gates", "*.py")
        real_found = [
            f for f in found
            if "test_" not in f.lower()
        ]
        assert len(real_found) == 0, \
            f"Hardcoded gate count '110 gates' found:\n" + \
            "\n".join(real_found)

    def test_no_hardcoded_area(self):
        """2450 μm² must not appear as hardcoded value"""
        found = self._scan_for_pattern("2450", "*.py")
        # Filter out legitimate occurrences (comments, test data)
        real_found = [
            f for f in found
            if "hardcoded" not in f.lower() and
               "test" not in f.lower() and
               "forbidden" not in f.lower()
        ]
        assert len(real_found) == 0, \
            f"Hardcoded area '2450' found in non-test code:\n" + \
            "\n".join(real_found)

    def test_no_return_fake_status(self):
        """
        No function may return hardcoded status='PASS' for EDA steps.
        Must always come from file parsing.
        """
        found = self._scan_for_pattern(
            '"status": "PASS"', "*.py"
        )
        # Allow in test files and comments
        real_found = [
            f for f in found
            if "test_" not in str(Path(f).name) and
               "#" not in f.split(":")[-1][:5]
        ]
        assert len(real_found) == 0, \
            f"Hardcoded status='PASS' found in non-test code:\n" + \
            "\n".join(real_found)

    def test_file_thresholds_cover_all_outputs(self):
        """
        FILE_SIZE_THRESHOLDS must cover every key output file.
        Missing thresholds = no validation = potential stub acceptance.
        """
        required_keys = {
            "liberty", "vcd", "netlist",
            "placed_def", "cts_def", "routed_def",
            "gds", "spice_extracted"
        }
        for key in required_keys:
            assert key in FILE_SIZE_THRESHOLDS, \
                f"FILE_SIZE_THRESHOLDS missing key: '{key}' — " \
                f"add minimum size threshold to prevent stub acceptance"

    def test_all_thresholds_are_nonzero(self):
        """Every threshold must be greater than zero"""
        for key, value in FILE_SIZE_THRESHOLDS.items():
            assert value > 0, \
                f"Threshold for '{key}' is {value} — " \
                f"zero threshold accepts any file including empty stubs"
