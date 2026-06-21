"""
batch_generate.py — Overnight Batch Design Runner
RTL-Gen AI

Runs multiple designs through the pipeline unattended.
Each successful result is automatically saved to the training dataset.

Usage:
    python batch_generate.py                    # runs built-in 50 designs
    python batch_generate.py --designs my.json  # runs designs from JSON file
    python batch_generate.py --count 20         # runs first 20 designs only
"""

import json, time, sys, argparse, logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BATCH_DESIGNS = [
    ("8-bit synchronous adder with carry",                     "adder_8bit_b"),
    ("16-bit synchronous adder with overflow flag",            "adder_16bit_b"),
    ("4-bit synchronous up counter with enable",               "counter_4bit_b"),
    ("8-bit synchronous up counter with enable and load",      "counter_8bit_b"),
    ("16-bit up-down counter with direction control",          "counter_updown_b"),
    ("8-bit ALU with add subtract and or xor",                 "alu_8bit_b"),
    ("4-to-1 multiplexer with 8-bit data",                    "mux_4to1_b"),
    ("3-to-8 binary decoder",                                  "decoder_3to8_b"),
    ("8-to-3 priority encoder with valid output",              "encoder_8to3_b"),
    ("8-bit magnitude comparator",                             "comparator_8_b"),
    ("8x8 register file with dual read ports",                 "reg_file_8x8_b"),
    ("UART transmitter 8N1 at 115200 baud",                    "uart_tx_b"),
    ("SPI master with chip select",                            "spi_master_b"),
    ("I2C master controller",                                  "i2c_master_b"),
    ("8-bit PWM generator",                                    "pwm_8bit_b"),
    ("CRC-8 streaming calculator",                             "crc8_b"),
    ("16-bit LFSR pseudo-random number generator",             "lfsr_16_b"),
    ("4-bit gray code counter",                                "gray_cnt_4_b"),
    ("8-bit barrel shifter",                                   "barrel_8_b"),
    ("button debouncer with configurable delay",               "debounce_b"),
    ("8-bit shift register with serial input",                 "shift_reg_8_b"),
    ("16-entry 8-bit FIFO with full and empty flags",          "fifo_16_b"),
    ("32-entry 8-bit FIFO with almost-full flag",              "fifo_32_b"),
    ("256x8-bit synchronous SRAM",                             "sram_256_b"),
    ("512x8-bit synchronous SRAM with byte enable",            "sram_512_b"),
    ("8-bit multiplier with registered output",                "mult_8_b"),
    ("4-way round-robin arbiter",                              "arb_rr4_b"),
    ("8-way round-robin arbiter with grant hold",              "arb_rr8_b"),
    ("traffic light FSM with timed transitions",               "fsm_traffic_b"),
    ("vending machine FSM accepting 5 and 10 cent coins",      "fsm_vend_b"),
    ("16-bit CRC checksum calculator",                         "crc16_b"),
    ("BCD counter 4-digit with carry chain",                   "bcd_4d_b"),
    ("8-channel PWM generator with independent duty cycles",   "pwm_8ch_b"),
    ("rising and falling edge detector",                       "edge_det_b"),
    ("UART receiver 8N1 at 115200 baud",                       "uart_rx_b"),
    ("SPI slave controller",                                   "spi_slave_b"),
    ("I2C slave with 8-byte receive buffer",                   "i2c_slave_b"),
    ("8-bit synchronous FIFO with handshake protocol",         "fifo_hs_b"),
    ("configurable clock divider with integer ratio",          "clkdiv_b"),
    ("8-bit parity generator and checker",                     "parity_b"),
    ("16-bit barrel shifter with rotate support",              "barrel_16_b"),
    ("dual-port RAM 256x8",                                    "dpram_256_b"),
    ("priority encoder 16-to-4 with valid signal",             "enc_16_b"),
    ("8-bit comparator with equal greater less outputs",       "cmp_8_b"),
    ("synchronous FIFO with valid ready handshake",            "fifo_vr_b"),
    ("4-stage pipeline adder with forwarding",                 "pipe_add_b"),
    ("8-bit serial to parallel converter",                     "s2p_8_b"),
    ("8-bit parallel to serial converter",                     "p2s_8_b"),
    ("8-channel round-robin multiplexer",                      "mux_rr8_b"),
    ("16-bit linear feedback shift register with tap select",  "lfsr_tap_b"),
]

def run_batch(designs, count=None):
    from guaranteed_flow import generate_guaranteed_gds

    targets = designs[:count] if count else designs
    results = {"pass": 0, "fail": 0, "total": len(targets), "details": []}

    log.info("Starting batch: %d designs", len(targets))
    start = time.time()

    for i, (desc, name) in enumerate(targets, 1):
        log.info("[%d/%d] %s", i, len(targets), name)
        t0 = time.time()
        try:
            r = generate_guaranteed_gds(desc, name)
            ok = r.get("tapeout_ready", False) and r.get("gds_size_kb", 0) > 50
            elapsed = time.time() - t0
            status = "PASS" if ok else "FAIL"
            results["pass" if ok else "fail"] += 1
            log.info("  %s: %s GDS=%.0fKB in %.0fs",
                     status, name, r.get("gds_size_kb", 0), elapsed)
            results["details"].append({
                "name": name, "ok": ok,
                "gds_kb": r.get("gds_size_kb", 0), "elapsed": elapsed
            })
            # Cleanup run directory to prevent disk exhaustion
            run_dir_str = r.get("run_dir")
            if run_dir_str and Path(run_dir_str).exists():
                log.info("  Cleaning up run directory to save disk space: %s", run_dir_str)
                try:
                    import shutil
                    shutil.rmtree(run_dir_str, ignore_errors=True)
                except Exception as e:
                    log.warning("  Cleanup warning: %s", e)
        except Exception as e:
            log.error("  ERROR %s: %s", name, e)
            results["fail"] += 1
            results["details"].append({"name": name, "ok": False, "error": str(e)})

    total_elapsed = time.time() - start
    log.info("\n=== BATCH COMPLETE ===")
    log.info("Pass: %d/%d in %.0f min", results["pass"], results["total"], total_elapsed/60)

    # Save report
    report_path = Path(f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    report_path.write_text(json.dumps(results, indent=2))
    log.info("Report: %s", report_path)

    from dataset_builder import get_count
    log.info("Dataset now has %d examples", get_count())
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--designs", type=str, help="JSON file with designs list")
    parser.add_argument("--count",   type=int, help="Run only first N designs")
    args = parser.parse_args()

    if args.designs:
        data    = json.loads(Path(args.designs).read_text())
        designs = [(d["description"], d["name"]) for d in data]
    else:
        designs = BATCH_DESIGNS

    # Enable sleep prevention on Windows
    if sys.platform == "win32":
        try:
            import ctypes
            # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001)
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            log.info("System sleep prevention enabled.")
        except Exception as e:
            log.warning("Could not enable sleep prevention: %s", e)

    results = run_batch(designs, args.count)

    # Restore sleep settings
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            log.info("System sleep settings restored.")
        except Exception:
            pass

    sys.exit(0 if results["fail"] == 0 else 1)
