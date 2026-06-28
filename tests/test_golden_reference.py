"""Tests for golden_reference.py"""

import pytest
from golden_reference import (
    _GOLDEN_MODELS,
    classify_design_for_golden,
    get_golden_model,
    has_golden_model,
    parse_simulation_test_vectors,
    compare_with_golden,
    self_test,
)


class TestGoldenModels:
    def test_all_models_registered(self):
        assert len(_GOLDEN_MODELS) >= 10

    def test_adder(self):
        m = get_golden_model("adder")
        assert m({"a": 5, "b": 3, "_width": 8})["sum"] == 8
        assert m({"a": 255, "b": 1, "_width": 8})["sum"] == 256  # 9-bit

    def test_subtractor(self):
        m = get_golden_model("subtractor")
        assert m({"a": 10, "b": 3, "_width": 8})["diff"] == 7

    def test_counter(self):
        m = get_golden_model("counter")
        r = m({"enable": 1, "reset_n": 1, "_count": 0, "_width": 8})
        assert r["_next_count"] == 1
        r = m({"enable": 0, "reset_n": 1, "_count": 5, "_width": 8})
        assert r["_next_count"] == 5  # unchanged
        r = m({"enable": 1, "reset_n": 0, "_count": 5, "_width": 8})
        assert r["_next_count"] == 0  # reset

    def test_shift_reg(self):
        m = get_golden_model("shift_reg")
        r = m({"serial_in": 1, "shift_en": 1, "reset_n": 1, "_parallel_out": 0, "_width": 8})
        assert r["_next_parallel_out"] == 1
        r = m({"serial_in": 0, "shift_en": 1, "reset_n": 1, "_parallel_out": 1, "_width": 8})
        assert r["_next_parallel_out"] == 2

    def test_mux(self):
        m = get_golden_model("mux")
        assert m({"a": 10, "b": 20, "sel": 0, "_width": 8})["y"] == 10
        assert m({"a": 10, "b": 20, "sel": 1, "_width": 8})["y"] == 20

    def test_demux(self):
        m = get_golden_model("demux")
        r = m({"in": 42, "sel": 0, "_num_outputs": 4, "_width": 8})
        assert r["out0"] == 42
        assert r["out1"] == 0
        r = m({"in": 42, "sel": 2, "_num_outputs": 4, "_width": 8})
        assert r["out2"] == 42

    def test_decoder(self):
        m = get_golden_model("decoder")
        r = m({"sel": 0, "_width": 2})
        assert r["out0"] == 1
        assert r["out1"] == 0
        assert r["out2"] == 0
        assert r["out3"] == 0
        r = m({"sel": 2, "_width": 2})
        assert r["out2"] == 1

    def test_encoder(self):
        m = get_golden_model("encoder")
        r = m({"in0": 1, "in1": 0, "in2": 0, "in3": 0, "_num_inputs": 4, "_priority": 0})
        assert r["code"] == 0
        assert r["valid"] == 1
        r = m({"in0": 0, "in1": 0, "in2": 0, "in3": 0, "_num_inputs": 4, "_priority": 0})
        assert r["valid"] == 0

    def test_comparator(self):
        m = get_golden_model("comparator")
        assert m({"a": 5, "b": 5})["eq"] == 1
        assert m({"a": 3, "b": 7})["lt"] == 1
        assert m({"a": 9, "b": 2})["gt"] == 1

    def test_alu(self):
        m = get_golden_model("alu")
        assert m({"a": 10, "b": 3, "op": 0, "_width": 8})["result"] == 13  # add
        assert m({"a": 10, "b": 3, "op": 1, "_width": 8})["result"] == 7   # sub
        assert m({"a": 10, "b": 3, "op": 2, "_width": 8})["result"] == 2   # and
        assert m({"a": 10, "b": 3, "op": 3, "_width": 8})["result"] == 11  # or
        assert m({"a": 10, "b": 3, "op": 4, "_width": 8})["result"] == 9   # xor
        assert m({"a": 10, "b": 3, "op": 5, "_width": 8})["result"] == 245  # not

    def test_multiplier(self):
        m = get_golden_model("multiplier")
        assert m({"a": 7, "b": 6, "_width": 8})["product"] == 42

    def test_register_file(self):
        m = get_golden_model("register_file")
        regs = [0] * 8
        r = m({"wr_en": 1, "wr_addr": 3, "wr_data": 99, "rd_addr_a": 3,
               "rd_addr_b": 0, "_regs": regs, "_num_regs": 8, "_width": 8})
        assert r["rd_data_a"] == 99
        assert r["rd_data_b"] == 0

    def test_fifo(self):
        m = get_golden_model("fifo")
        state = {"_depth": 4, "_width": 8, "_mem": [0] * 4, "_head": 0, "_tail": 0, "_count": 0}
        r = m({"wr_en": 1, "rd_en": 0, "wr_data": 42, "reset_n": 1, **state})
        assert r["empty"] == 0
        # Read back
        r2 = m({"wr_en": 0, "rd_en": 1, "wr_data": 0, "reset_n": 1,
                "_mem": r["_mem"], "_head": r["_head"],
                "_tail": r["_tail"], "_count": r["_count"], "_depth": 4, "_width": 8})
        assert r2["rd_data"] == 42
        assert r2["empty"] == 1

    def test_ram(self):
        m = get_golden_model("ram")
        mem = [0] * 256
        r = m({"wr_en": 1, "addr": 10, "wr_data": 55, "_mem": mem, "_depth": 256, "_width": 8})
        assert r["rd_data"] == 0  # read-before-write
        r2 = m({"wr_en": 0, "addr": 10, "wr_data": 0, "_mem": r["_mem"], "_depth": 256, "_width": 8})
        assert r2["rd_data"] == 55

    def test_rom(self):
        m = get_golden_model("rom")
        r = m({"addr": 5, "_content": [i % 256 for i in range(256)], "_depth": 256})
        assert r["rd_data"] == 5

    def test_self_test(self):
        assert self_test() is True


class TestDesignClassification:
    def test_classify_adder(self):
        assert classify_design_for_golden("8-bit adder") == "adder"
        assert classify_design_for_golden("add two 8-bit numbers") == "adder"

    def test_classify_counter(self):
        assert classify_design_for_golden("4-bit counter") == "counter"
        assert classify_design_for_golden("up counter with enable") == "counter"

    def test_classify_alu(self):
        assert classify_design_for_golden("8-bit ALU with add/sub") == "alu"

    def test_classify_fifo(self):
        assert classify_design_for_golden("16-entry FIFO") == "fifo"
        assert classify_design_for_golden("synchronous FIFO") == "fifo"

    def test_classify_register_file(self):
        assert classify_design_for_golden("register file 8x8") == "register_file"

    def test_classify_shift_reg(self):
        assert classify_design_for_golden("shift register 8-bit") == "shift_reg"

    def test_classify_mux(self):
        assert classify_design_for_golden("4-to-1 multiplexer") == "mux"

    def test_classify_demux(self):
        assert classify_design_for_golden("1-to-4 demultiplexer") == "demux"

    def test_classify_decoder(self):
        assert classify_design_for_golden("3-to-8 decoder") == "decoder"

    def test_classify_encoder(self):
        assert classify_design_for_golden("8-to-3 encoder") == "encoder"

    def test_classify_comparator(self):
        assert classify_design_for_golden("magnitude comparator") == "comparator"

    def test_classify_multiplier(self):
        assert classify_design_for_golden("8-bit multiplier") == "multiplier"

    def test_classify_ram(self):
        assert classify_design_for_golden("256x8 SRAM") == "ram"

    def test_classify_rom(self):
        assert classify_design_for_golden("read only memory 256x8") == "rom"

    def test_no_match_for_complex(self):
        assert classify_design_for_golden("RISC-V CPU") is None
        assert classify_design_for_golden("5-stage pipeline processor") is None

    def test_has_golden_model(self):
        assert has_golden_model("adder") is True
        assert has_golden_model("counter") is True
        assert has_golden_model("riscv") is False
        assert has_golden_model("pipeline") is False


class TestTestVectorParsing:
    def test_parse_pass(self):
        vecs = parse_simulation_test_vectors("PASS Test 1\nPASS Test 2\nPASS Test 3")
        assert len(vecs) == 3
        assert all(v["passed"] for v in vecs)

    def test_parse_fail_with_values(self):
        vecs = parse_simulation_test_vectors("FAIL Test 2: got 30, expected 10")
        assert len(vecs) == 1
        assert vecs[0]["passed"] is False
        assert vecs[0]["actual"] == "30"
        assert vecs[0]["expected"] == "10"

    def test_parse_fail_hex(self):
        vecs = parse_simulation_test_vectors("FAIL Test 3: got 0x00000000, expected 0x00000004")
        assert len(vecs) == 1
        assert vecs[0]["passed"] is False

    def test_parse_mixed(self):
        out = "PASS Test 1\nFAIL Test 2: got 0, expected 1\nPASS Test 3\nALL_TESTS_PASSED"
        vecs = parse_simulation_test_vectors(out)
        assert len(vecs) == 3
        assert vecs[0]["passed"] is True
        assert vecs[1]["passed"] is False
        assert vecs[2]["passed"] is True

    def test_parse_empty(self):
        assert parse_simulation_test_vectors("") == []

    def test_parse_no_tests(self):
        assert parse_simulation_test_vectors("some random output\nno tests here") == []

    def test_parse_xz_propagation(self):
        vecs = parse_simulation_test_vectors("FAIL: output has X on data_bus")
        assert len(vecs) >= 1

    def test_compare_with_golden_adder(self):
        out = "PASS Test 1\nFAIL Test 2: got 30, expected 10"
        result = compare_with_golden(out, "adder")
        assert result["total"] == 2
        assert result["failed"] >= 1

    def test_compare_with_golden_no_model(self):
        out = "PASS Test 1"
        result = compare_with_golden(out, "nonexistent")
        assert result["match"] is True  # gracefully degrades

    def test_compare_with_golden_all_pass(self):
        out = "PASS Test 1\nPASS Test 2"
        result = compare_with_golden(out, "adder")
        assert result["match"] is True
