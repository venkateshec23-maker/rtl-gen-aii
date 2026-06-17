"""Quick script to check existing run directories for validation results."""
from pathlib import Path

runs_dir = Path("C:/tools/OpenLane/runs")
designs = ["adder_8bit","simple_alu","counter","uart_tx","spi_master","i2c_master","reg_file","fifo","memory"]

for d in designs:
    candidates = sorted(runs_dir.glob(f"{d}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print(f"{d:15s} | NO RUN FOUND")
        continue
    rd = candidates[0]
    gds = list(rd.rglob("*.gds"))
    routed = list(rd.rglob("routed.def"))
    cts = list(rd.rglob("cts.def"))
    gds_ok = "YES" if gds else "NO"
    gds_kb = gds[0].stat().st_size // 1024 if gds else 0
    routed_kb = routed[0].stat().st_size // 1024 if routed else 0
    cts_kb = cts[0].stat().st_size // 1024 if cts else 0
    print(f"{d:15s} | {rd.name:45s} | GDS:{gds_ok:3s} {gds_kb:>5}KB | routed:{routed_kb:>5}KB | cts:{cts_kb:>5}KB")
