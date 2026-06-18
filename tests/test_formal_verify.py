import pytest
from pathlib import Path
from formal_verify import (
    Property,
    PropertyResult,
    FormalReport,
    UNIVERSAL_PROPERTIES,
    SEQUENTIAL_PROPERTIES,
    _build_formal_tcl,
    _parse_formal_output,
    run_formal_verification,
)


class TestProperties:
    def test_universal_properties_defined(self):
        assert len(UNIVERSAL_PROPERTIES) >= 3

    def test_sequential_properties_defined(self):
        assert len(SEQUENTIAL_PROPERTIES) >= 1

    def test_property_fields(self):
        for p in UNIVERSAL_PROPERTIES + SEQUENTIAL_PROPERTIES:
            assert p.name
            assert p.description
            assert p.yosys_cmd
            assert p.kind in ("safety", "liveness", "equivalence")


class TestTCLBuilder:
    def test_basic_tcl(self):
        tcl = _build_formal_tcl("/work/test.v", "my_design", UNIVERSAL_PROPERTIES)
        assert "read_verilog /work/test.v" in tcl
        assert "hierarchy -top my_design" in tcl
        assert "RTL_FORMAL_START" in tcl
        assert "RTL_FORMAL_END" in tcl

    def test_property_markers(self):
        tcl = _build_formal_tcl("/work/test.v", "top", UNIVERSAL_PROPERTIES)
        for prop in UNIVERSAL_PROPERTIES:
            assert f"RTL_PROP_START:{prop.name}" in tcl
            assert "RTL_PROP_RESULT:" in tcl

    def test_empty_properties(self):
        tcl = _build_formal_tcl("/work/test.v", "top", [])
        assert "read_verilog /work/test.v" in tcl
        assert "RTL_FORMAL_START" in tcl


class TestParser:
    def test_all_pass(self):
        fake_output = """
RTL_PROP_START:no_combinational_loops
RTL_PROP_RESULT:PASS:ok
RTL_PROP_START:hierarchy_consistent
RTL_PROP_RESULT:PASS:ok
RTL_PROP_START:synthesis_clean
RTL_PROP_RESULT:PASS:ok
"""
        results = _parse_formal_output(fake_output, UNIVERSAL_PROPERTIES)
        assert len(results) == len(UNIVERSAL_PROPERTIES)
        for r in results:
            assert r.status == "PASS"

    def test_fail_detected(self):
        fail_output = """
RTL_PROP_START:no_combinational_loops
RTL_PROP_RESULT:FAIL:error
RTL_PROP_START:hierarchy_consistent
RTL_PROP_RESULT:PASS:ok
"""
        results = _parse_formal_output(fail_output, UNIVERSAL_PROPERTIES[:2])
        statuses = {r.property_name: r.status for r in results}
        assert statuses["no_combinational_loops"] == "FAIL"
        assert statuses["hierarchy_consistent"] == "PASS"

    def test_skip_for_missing_property(self):
        output = "RTL_FORMAL_START\nRTL_FORMAL_END\n"
        results = _parse_formal_output(output, UNIVERSAL_PROPERTIES[:1])
        assert results[0].status == "SKIP"

    def test_empty_catch_is_pass(self):
        output = "RTL_PROP_START:hierarchy_consistent\nRTL_PROP_RESULT:PASS:ok\n"
        results = _parse_formal_output(output, [UNIVERSAL_PROPERTIES[1]])
        assert results[0].status == "PASS"


class TestFormalReport:
    def test_pass_rate(self):
        report = FormalReport(
            design_name="test", netlist_path="/x", module_name="test",
            total=5, passed=4, failed=1, skipped=0,
        )
        assert report.pass_rate == 80.0
        assert report.overall_status == "FAIL"

    def test_all_pass(self):
        report = FormalReport(
            design_name="test", netlist_path="/x", module_name="test",
            total=3, passed=3, failed=0, skipped=0,
        )
        assert report.pass_rate == 100.0
        assert report.overall_status == "PASS"

    def test_all_skip(self):
        report = FormalReport(
            design_name="test", netlist_path="/x", module_name="test",
            total=3, passed=0, failed=0, skipped=3,
        )
        assert report.pass_rate == 0.0
        assert report.overall_status == "SKIP"

    def test_to_dict(self):
        report = FormalReport(
            design_name="adder", netlist_path="/x", module_name="adder",
            total=2, passed=2, failed=0,
            results=[
                PropertyResult("p1", "desc1", "PASS"),
                PropertyResult("p2", "desc2", "PASS", detail="ok"),
            ],
        )
        d = report.to_dict()
        assert d["design_name"] == "adder"
        assert d["pass_rate"] == 100.0
        assert len(d["results"]) == 2

    def test_zero_denominator(self):
        report = FormalReport(
            design_name="test", netlist_path="/x", module_name="test",
            total=0, passed=0, failed=0, skipped=0,
        )
        assert report.pass_rate == 0.0


class TestRunFormalVerification:
    def test_missing_netlist(self):
        report = run_formal_verification(
            netlist_path=Path("/no/such/file.v"),
            module_name="phantom",
            docker_manager=None,
            work_dir=Path(r"C:\tools\OpenLane"),
        )
        assert report.overall_status == "SKIP"
        assert report.skipped > 0
