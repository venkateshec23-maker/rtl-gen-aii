import pytest
from pathlib import Path
from formal_verify import (
    Property,
    PropertyResult,
    FormalReport,
    UNIVERSAL_PROPERTIES,
    _build_formal_tcl,
    _parse_formal_output,
    run_formal_verification_simple,
)


class TestProperties:
    def test_universal_properties_defined(self):
        assert len(UNIVERSAL_PROPERTIES) >= 3

    def test_universal_properties_count(self):
        assert len(UNIVERSAL_PROPERTIES) == 5

    def test_property_fields(self):
        for p in UNIVERSAL_PROPERTIES:
            assert p.name
            assert p.description
            assert p.yosys_cmd
            assert p.kind == "safety"


class TestTCLBuilder:
    def test_basic_tcl(self):
        tcl = _build_formal_tcl("/work/test.v", "my_design", UNIVERSAL_PROPERTIES)
        assert "read_verilog /work/test.v" in tcl
        assert "hierarchy -top my_design" in tcl
        assert "=FORMAL_START=" in tcl
        assert "=FORMAL_END=" in tcl
        assert "log " in tcl
        assert "puts " not in tcl

    def test_property_markers(self):
        tcl = _build_formal_tcl("/work/test.v", "top", UNIVERSAL_PROPERTIES)
        for prop in UNIVERSAL_PROPERTIES:
            assert "=PROP_BEGIN:" + prop.name + "=" in tcl
            assert "=PROP_DONE:" + prop.name + "=" in tcl

    def test_no_double_brace_artifacts(self):
        tcl = _build_formal_tcl("/work/test.v", "top", UNIVERSAL_PROPERTIES)
        assert "{{" not in tcl
        assert "}}" not in tcl
        assert "prove-asserts" not in tcl

    def test_empty_properties(self):
        tcl = _build_formal_tcl("/work/test.v", "top", [])
        assert "read_verilog /work/test.v" in tcl
        assert "=FORMAL_START=" in tcl


class TestParser:
    def test_all_pass(self):
        fake_output = """
=FORMAL_START=
=PROP_BEGIN:no_combinational_loops=
OK
=PROP_DONE:no_combinational_loops=
=PROP_BEGIN:hierarchy_consistent=
OK
=PROP_DONE:hierarchy_consistent=
=PROP_BEGIN:synthesis_clean=
OK
=PROP_DONE:synthesis_clean=
=FORMAL_END=
"""
        results = _parse_formal_output(fake_output, UNIVERSAL_PROPERTIES[:3])
        assert len(results) == 3
        for r in results:
            assert r.status == "PASS", f"{r.property_name}: {r.status}"

    def test_fail_no_done(self):
        """BEGIN found but DONE missing -> Yosys exited early -> FAIL"""
        fail_output = """
=PROP_BEGIN:no_combinational_loops=
ERROR: Combinational loop detected
=FORMAL_END=
"""
        results = _parse_formal_output(fail_output, UNIVERSAL_PROPERTIES[:1])
        assert results[0].status == "FAIL"

    def test_skip_for_not_reached(self):
        output = "=FORMAL_START=\n=FORMAL_END=\n"
        results = _parse_formal_output(output, UNIVERSAL_PROPERTIES[:1])
        assert results[0].status == "SKIP"

    def test_begins_and_done_pass(self):
        output = "=PROP_BEGIN:hierarchy_consistent=\nOK\n=PROP_DONE:hierarchy_consistent=\n"
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


class TestRunFormalVerificationSimple:
    def test_missing_netlist(self):
        report = run_formal_verification_simple(
            netlist_path=Path("/no/such/file.v"),
            module_name="phantom",
            work_dir=Path(r"C:\tools\OpenLane"),
        )
        assert report.overall_status == "SKIP"
        assert report.total == 0
