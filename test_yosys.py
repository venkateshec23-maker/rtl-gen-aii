#!/usr/bin/env python3
"""Test Yosys synthesis in Docker to debug the issue."""

import subprocess
import sys
from pathlib import Path

work_dir = Path('validation/run_001/02_synthesis').absolute()
print(f"Work directory: {work_dir}")
print(f"RTL file exists: {(work_dir / 'rtl.v').exists()}")

# Windows path to Docker path conversion
docker_work = str(work_dir).replace('C:\\', '/c/').replace('\\', '/')

cmd = [
    'docker', 'run', '--rm',
    '-v', f'{docker_work}:/work',
    '-w', '/work',
    '-i',
    'efabless/openlane:latest',
    'yosys'
]

yosys_script = """\
read_verilog /work/rtl.v
hierarchy -top adder_8bit
synth -flatten
write_verilog /work/synth.v
"""

print(f"\n{'='*60}")
print(f"Running Yosys synthesis...")
print(f"{'='*60}")
print(f"Docker command: docker run --rm -v {docker_work}:/work ... yosys\n")

result = subprocess.run(cmd, input=yosys_script, capture_output=True, text=True, timeout=60)

print(f"Return code: {result.returncode}\n")
print(f"--- STDOUT (last 1500 chars) ---")
print(result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout)

print(f"\n--- STDERR (last 1500 chars) ---")
print(result.stderr[-1500:] if len(result.stderr) > 1500 else result.stderr)

print(f"\n{'='*60}")
print(f"Output files:")
for f in work_dir.glob("*"):
    size = f.stat().st_size if f.is_file() else "DIR"
    print(f"  {f.name:30} {size}")

print(f"{'='*60}")
