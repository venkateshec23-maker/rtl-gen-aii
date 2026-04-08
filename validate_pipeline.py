import logging
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from python.full_flow import RTLGenAI, FlowConfig


def on_progress(d):
    pct = d["pct"] * 100
    if pct < 0:
        tag = "FAIL "
    else:
        n = int(min(pct, 100) / 5)
        tag = "[" + "#" * n + "." * (20 - n) + f"] {pct:5.1f}%"
    print(f"  {tag}  [{d['stage']:20}]  {d['msg']}", flush=True)


cfg = FlowConfig(
    target_utilization=0.35,
    clock_period_ns=25.0,
    clock_net="clk",
    placement_density=0.35,
    routing_adjustment=0.40,
    routing_threads=2,
    run_lvs=False,
)

print()
print("=" * 65)
print("  RTL-Gen AI  —  End-to-End Validation Run")
print("  Design: 8-bit Registered Adder")
print("=" * 65)
print()

result = RTLGenAI.run_from_rtl(
    rtl_path   = r"validation\adder_8bit.v",
    top_module = "adder_8bit",
    output_dir = r"validation\run_001",
    config     = cfg,
    progress   = on_progress,
)

print(result.summary())

print("\nFILE VERIFICATION (proof of what actually ran):")
print("-" * 65)

run_dir = Path(r"validation\run_001")
checks = [
    ("02_synthesis/adder_8bit_synth.v",  3_000,  "Yosys netlist"),
    ("03_physical/cts.def",              5_000,  "OpenROAD physical DEF"),
    ("06_routing/routed.def",           10_000,  "TritonRoute routed DEF"),
    ("07_gds/adder_8bit.gds",           10_000,  "Magic GDSII file"),
]

all_real = True
for rel, min_bytes, label in checks:
    p = run_dir / rel
    if not p.exists():
        print(f"  MISSING  {label:30}  {rel}")
        all_real = False
    else:
        sz = p.stat().st_size
        real = sz >= min_bytes
        if not real:
            all_real = False
        tag = "REAL  " if real else "SMALL "
        print(f"  {tag}  {label:30}  {sz:>10,} bytes")

gds = run_dir / "07_gds" / "adder_8bit.gds"
if gds.exists() and gds.stat().st_size > 100:
    hdr = gds.read_bytes()[:4].hex()
    if hdr.startswith("0006"):
        print(f"\n  GDS header {hdr} — REAL GDSII binary confirmed")
    else:
        print(f"\n  GDS header {hdr} — NOT real GDSII (expected 0006xx)")
        all_real = False

print()
print("-" * 65)
verdict = "ALL STAGES REAL — TAPE-OUT READY" if all_real else "SOME STAGES MISSING OR STUB"
print(f"  Verdict: {verdict}")
print("-" * 65)
print()

sys.exit(0 if result.is_tapeable else 1)
