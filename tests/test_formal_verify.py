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
        assert "=FORMAL_START=" in tcl
        assert "=FORMAL_END=" in tcl

    def test_property_markers(self):
        tcl = _build_formal_tcl("/work/test.v", "top", UNIVERSAL_PROPERTIES)
        for prop in UNIVERSAL_PROPERTIES:
            assert f"=PROP:{prop.name}=" in tcl
            assert "=RESULT:" in tcl

    def test_empty_properties(self):
        tcl = _build_formal_tcl("/work/test.v", "top", [])
        assert "read_verilog /work/test.v" in tcl
        assert "=FORMAL_START=" in tcl


class TestParser:
    def test_all_pass(self):
        fake_output = """
=FORMAL_START=
=PROP:no_combinational_loops=
No combinational loops
=RESULT:=
=PROP:hierarchy_consistent=
End of script
=RESULT:=
=PROP:synthesis_clean=
End of script.
=RESULT:=
=FORMAL_END=
"""
        results = _parse_formal_output(fake_output, UNIVERSAL_PROPERTIES)
        assert len(results) == len(UNIVERSAL_PROPERTIES)
        for r in results:
            assert r.status == "PASS"

    def test_fail_detected(self):
        fail_output = """
=PROP:no_combinational_loops=
ERROR: Found combinational loop
=RESULT:Found combinational loop=
=PROP:hierarchy_consistent=
=RESULT:=
"""
        results = _parse_formal_output(fail_output, UNIVERSAL_PROPERTIES[:2])
        statuses = {r.property_name: r.status for r in results}
        assert statuses["no_combinational_loops"] == "FAIL"
        assert statuses["hierarchy_consistent"] == "PASS"

    def test_skip_for_missing_property(self):
        output = "=FORMAL_START=\n=FORMAL_END=\n"
        results = _parse_formal_output(output, UNIVERSAL_PROPERTIES[:1])
        assert results[0].status == "SKIP"

    def test_empty_catch_is_pass(self):
        output = "=PROP:hierarchy_consistent=\n=RESULT:=\n"
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
