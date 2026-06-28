"""Tests for verification_pipeline.py"""

import pytest
from verification_pipeline import (
    StageResult,
    VerificationReport,
    _build_sim_result_enhanced,
    self_test,
)


class TestStageResult:
    def test_create(self):
        sr = StageResult(stage="compile", passed=True, detail="ok")
        assert sr.stage == "compile"
        assert sr.passed is True
        assert sr.detail == "ok"
        assert sr.errors == []
        assert sr.warnings == []

    def test_with_errors(self):
        sr = StageResult(stage="sim", passed=False, detail="fail", errors=["error 1"])
        assert sr.passed is False
        assert "error 1" in sr.errors


class TestVerificationReport:
    def test_create(self):
        report = VerificationReport(module_name="test")
        assert report.module_name == "test"
        assert report.status == "PENDING"

    def test_all_stages_passed(self):
        report = VerificationReport(module_name="test")
        report.stages["s1"] = StageResult(stage="s1", passed=True)
        report.stages["s2"] = StageResult(stage="s2", passed=True)
        assert report.all_stages_passed is True
        assert report.failed_stages == []

    def test_some_failed(self):
        report = VerificationReport(module_name="test")
        report.stages["s1"] = StageResult(stage="s1", passed=True)
        report.stages["s2"] = StageResult(stage="s2", passed=False)
        report.stages["s3"] = StageResult(stage="s3", passed=True)
        assert report.all_stages_passed is False
        assert report.failed_stages == ["s2"]

    def test_to_dict(self):
        report = VerificationReport(module_name="m", description="d", status="PASS")
        report.stages["compile"] = StageResult(stage="compile", passed=True, detail="ok")
        d = report.to_dict()
        assert d["module_name"] == "m"
        assert d["status"] == "PASS"
        assert "compile" in d["stages"]
        assert d["stages"]["compile"]["passed"] is True

    def test_empty_report(self):
        report = VerificationReport(module_name="empty")
        assert report.all_stages_passed is True  # no stages = all passed vacuously
        assert report.failed_stages == []


class TestSimResultEnhanced:
    def test_all_pass(self):
        out = "PASS Test 1\nPASS Test 2\nALL_TESTS_PASSED"
        d = _build_sim_result_enhanced(out, 0, "docker")
        assert d["success"] is True
        assert d["pass_count"] == 2
        assert d["fail_count"] == 0
        assert len(d["vectors"]) == 2

    def test_some_fail(self):
        out = "PASS Test 1\nFAIL Test 2: got 0, expected 1\nFAIL Test 3: got 30, expected 10"
        d = _build_sim_result_enhanced(out, 1, "docker")
        assert d["success"] is False
        assert d["pass_count"] == 1
        assert d["fail_count"] == 2
        assert len(d["vectors"]) == 3
        assert d["vectors"][1]["actual"] == "0"
        assert d["vectors"][1]["expected"] == "1"

    def test_empty_output(self):
        d = _build_sim_result_enhanced("", 0, "docker")
        # Empty output has no ALL_TESTS_PASSED marker → not successful
        assert d["success"] is False
        assert d["pass_count"] == 0
        assert d["fail_count"] == 0

    def test_xz_detection(self):
        out = "FAIL Test 1: got X, expected 0\nFAIL Test 2: got z, expected 1"
        d = _build_sim_result_enhanced(out, 1, "docker")
        assert d["success"] is False
        assert d["fail_count"] == 2

    def test_no_test_lines(self):
        out = "some random output\nno pass or fail here"
        d = _build_sim_result_enhanced(out, 0, "docker")
        assert d["pass_count"] == 0
        assert d["fail_count"] == 0
        assert d["vectors"] == []

    def test_tool_tracking(self):
        out = "PASS Test 1\nALL_TESTS_PASSED"
        d = _build_sim_result_enhanced(out, 0, "icarus")
        assert d["tool"] == "icarus"


class TestPipelineSelfTest:
    def test_self_test(self):
        assert self_test() is True
