#!/usr/bin/env python3
"""Debug TCL string generation."""

from pathlib import Path
import tempfile
from python.detail_router import DetailRouter, DetailRouteConfig
from python.docker_manager import DockerManager
from python.pdk_manager import PDKManager

dm = DockerManager()
pdk = PDKManager()
dr = DetailRouter(docker=dm, pdk=pdk)
config = DetailRouteConfig()

with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir = Path(tmpdir)
    def_path = tmpdir / 'dummy.def'
    guide_path = tmpdir / 'dummy_guides.txt'
    def_path.write_text('DESIGN test\nEND DESIGN', encoding='utf-8')
    
    tcl = dr._generate_detail_route_script(def_path, guide_path, 'test_module', config)
    
    print("="*70)
    print("TCL GENERATION DEBUG")
    print("="*70)
    
    # Check what's actually in the TCL
    test_patterns = [
        "if {{ [catch {{",
        "catch {{ write_def /work/routed.def }}",
        "detailed_route",
        "WARNING: route guides not found",
    ]
    
    for pattern in test_patterns:
        if pattern in tcl:
            print(f"✅ FOUND: {pattern}")
        else:
            print(f"❌ NOT FOUND: {pattern}")
    
    # Find lines around catch block
    print("\n" + "="*70)
    print("LINES CONTAINING 'catch':")
    print("="*70)
    lines = tcl.split('\n')
    for i, line in enumerate(lines):
        if 'catch' in line.lower():
            print(f"Line {i:3d}: {line}")
    
    print("\n" + "="*70)
    print("FIRST 50 LINES OF TCL:")
    print("="*70)
    for i, line in enumerate(lines[:50]):
        print(f"{i:3d}: {line}")
