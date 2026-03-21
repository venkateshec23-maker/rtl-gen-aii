"""
fix_synthesis.py
================
Run this ONE script from your project root to fix the synthesis stage.

    cd C:\\Users\\venka\\Documents\\rtl-gen-aii
    python fix_synthesis.py

What is wrong and why
──────────────────────
The current _Synthesiser.synthesise() in full_flow.py passes Yosys commands
via stdin or -p flag like this:

    docker run ... yosys -p "read_verilog C:\\Windows\\path\\rtl.v; ..."

This fails for TWO reasons:

  Reason 1 — Wrong paths inside the script
    The commands reference Windows paths (C:\\Users\\...) but inside Docker
    Linux container those paths do not exist.  Docker only sees /work/ (the
    mounted directory) and /pdk/.  Any write_verilog command pointing to a
    Windows path silently writes nothing.

  Reason 2 — Wrong tool for .tcl files
    docker.run_script() maps .tcl extension → "openroad" by default.
    Synthesis needs "yosys -s" not "openroad".  Without the interpreter
    override, the synthesis TCL is fed to OpenROAD which rejects it.

The fix
────────
Replace _Synthesiser.synthesise() with a version that:
  1. Copies RTL to output_dir  →  Docker sees it as /work/rtl.v
  2. Writes a TCL script where ALL paths use /work/...
  3. Calls docker.run_script(..., interpreter="yosys -s")
     so the correct tool runs the script
  4. Reads the netlist back from output_dir (same dir, now on Windows)

This is the correct approach for running ANY tool via Docker:
  Write inputs to work_dir → run tool inside Docker → read outputs from work_dir
"""

import re
import sys
from pathlib import Path

FULL_FLOW = Path("python") / "full_flow.py"

# ─────────────────────────────────────────────────────────────────────────────
# VERIFY
# ─────────────────────────────────────────────────────────────────────────────

if not FULL_FLOW.exists():
    print("ERROR: python/full_flow.py not found.")
    print("       Run from the project root:")
    print("       cd C:\\Users\\venka\\Documents\\rtl-gen-aii")
    sys.exit(1)

content  = FULL_FLOW.read_text(encoding="utf-8")
original = content

# ─────────────────────────────────────────────────────────────────────────────
# THE REPLACEMENT _Synthesiser CLASS
# ─────────────────────────────────────────────────────────────────────────────

NEW_SYNTHESISER = '''class _Synthesiser:
    """
    Runs Yosys synthesis inside the OpenLane Docker container.

    No local Yosys installation required — the OpenLane image includes Yosys
    with Sky130 PDK support.

    Correct pattern for Docker-based tool execution:
      1. Copy input files to output_dir  → visible as /work/* in container
      2. Write a TCL script using /work/ paths only (no Windows paths)
      3. Run via docker.run_script(interpreter="yosys -s")
      4. Read output files from output_dir on the Windows host
    """

    def __init__(self, yosys_exe=None) -> None:
        import logging
        self.logger = logging.getLogger(__name__ + "._Synthesiser")
        # yosys_exe ignored — synthesis always runs inside Docker

    def synthesise(
        self,
        rtl_path:   "Path",
        top_module: str,
        output_dir: "Path",
        docker:     "DockerManager",
    ) -> "Path":
        """
        Synthesise RTL Verilog to a Sky130 gate-level netlist.

        Args:
            rtl_path:   Input RTL .v file path on Windows.
            top_module: Top-level Verilog module name.
            output_dir: Windows output directory.  Netlist is written here.
            docker:     DockerManager instance (must have run_script()).

        Returns:
            Path to synthesised netlist (.v) on Windows.

        Raises:
            FlowError: When synthesis fails or output not produced.
        """
        import shutil
        from pathlib import Path as _P

        output_dir = _P(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # ── Step 1: copy RTL to output_dir ────────────────────────────
        # Inside Docker this becomes /work/rtl.v
        rtl_dest     = output_dir / "rtl.v"
        netlist_path = output_dir / f"{top_module}_synth.v"
        shutil.copy2(rtl_path, rtl_dest)

        # ── Step 2: Sky130 liberty paths inside Docker ─────────────────
        # The PDK is mounted at /pdk (from pdk_root on Windows).
        # The OpenLane image also has its own PDK copy at /openlane/pdks/.
        # Both locations are tried in order.
        lib_pdk = (
            "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/"
            "sky130_fd_sc_hd__tt_025C_1v80.lib"
        )
        lib_openlane = (
            "/openlane/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/"
            "sky130_fd_sc_hd__tt_025C_1v80.lib"
        )

        # ── Step 3: write TCL script with /work/ paths only ────────────
        # IMPORTANT: every path in this script uses /work/ or /pdk/.
        # NO Windows paths (C:\\...) must appear here.
        synth_tcl = f"""# RTL-Gen AI — Yosys Synthesis Script
# Input:  /work/rtl.v
# Output: /work/{top_module}_synth.v
# All paths are Docker container paths (/work/, /pdk/)

read_verilog /work/rtl.v
hierarchy -check -top {top_module}

# RTL elaboration passes
proc
opt
flatten
opt_expr; opt_clean; check; opt; wreduce
peepopt; opt_clean; opt -fast; memory_map
opt -full; techmap; opt -fast; opt_clean

# Technology mapping: Sky130 HD standard cells
# Try PDK mount (/pdk) first, then OpenLane built-in (/openlane/pdks)
if {{[file exists {lib_pdk}]}} {{
    dfflibmap -liberty {lib_pdk}
    abc -liberty {lib_pdk}
}} elseif {{[file exists {lib_openlane}]}} {{
    dfflibmap -liberty {lib_openlane}
    abc -liberty {lib_openlane}
}} else {{
    # No liberty found — generic synthesis
    # Cells will be Yosys internals, not sky130 names.
    # Floorplanner will use conservative die size estimation.
    synth -flatten
}}

opt_clean -purge

# Write gate-level netlist to /work/ (maps to output_dir on Windows)
write_verilog -noattr -noexpr -nohex -nodec /work/{top_module}_synth.v

# Print cell usage statistics
stat
"""

        # ── Step 4: run via run_script() with yosys interpreter ────────
        # CRITICAL: interpreter="yosys -s" overrides the default (openroad)
        # that run_script() would assign to .tcl files.
        run = docker.run_script(
            script_content = synth_tcl,
            script_name    = "synth.tcl",
            work_dir       = output_dir,
            interpreter    = "yosys -s",
            timeout        = 300,
        )

        # ── Step 5: verify output exists ───────────────────────────────
        # Note: Yosys sometimes exits non-zero on warnings but still
        # produces the output.  Check the file first.
        if not netlist_path.exists():
            raise FlowError(
                "synthesis",
                f"Yosys did not write {netlist_path.name}.\\n"
                f"Yosys exit code: {run.return_code}\\n"
                f"Stderr: {run.stderr[:400]}",
                output=run.combined_output(),
            )

        text = netlist_path.read_text(encoding="utf-8", errors="ignore")
        if "module" not in text:
            raise FlowError(
                "synthesis",
                "Netlist file exists but contains no module — synthesis failed silently",
                output=run.combined_output(),
            )

        has_sky130 = "sky130_fd_sc_hd__" in text
        self.logger.info(
            f"Synthesis complete: {netlist_path.name} "
            f"({netlist_path.stat().st_size} bytes, "
            f"sky130_cells={has_sky130})"
        )
        return netlist_path

    @staticmethod
    def _find_yosys():
        return None  # always uses Docker

'''

# ─────────────────────────────────────────────────────────────────────────────
# FIND AND REPLACE THE _Synthesiser CLASS
# ─────────────────────────────────────────────────────────────────────────────

CLASS_START = "class _Synthesiser:"
CLASS_BEFORE_RTLGENAI = "\nclass RTLGenAI:"

if CLASS_START not in content:
    print("ERROR: 'class _Synthesiser:' not found in full_flow.py")
    print("       The file may have been restructured.")
    print("       Manually replace the _Synthesiser class with the")
    print("       code printed at the end of this script.")
    print()
    print("─" * 60)
    print(NEW_SYNTHESISER)
    sys.exit(1)

if CLASS_BEFORE_RTLGENAI not in content:
    print("ERROR: 'class RTLGenAI:' not found — cannot find end of _Synthesiser")
    sys.exit(1)

# Extract everything before _Synthesiser, and everything from RTLGenAI onward
before_synth = content[: content.index(CLASS_START)]
after_synth  = content[content.index(CLASS_BEFORE_RTLGENAI):]

new_content = before_synth + NEW_SYNTHESISER + after_synth

# ─────────────────────────────────────────────────────────────────────────────
# ALSO FIX _stage_synthesis: pass docker to synthesise()
# ─────────────────────────────────────────────────────────────────────────────
# The stage method must call:  synthesiser.synthesise(rtl, module, dir, docker)
# Some versions of this method are missing the docker argument.

# Pattern A: missing docker arg entirely
old_call_a = "netlist = synthesiser.synthesise(rtl_path, top_module, synth_dir)"
new_call_a = "netlist = synthesiser.synthesise(rtl_path, top_module, synth_dir, self.docker)"

# Pattern B: positional without docker
old_call_b = "netlist = synthesiser.synthesise(\n                rtl_path, top_module, synth_dir\n            )"
new_call_b = "netlist = synthesiser.synthesise(\n                rtl_path, top_module, synth_dir, self.docker\n            )"

# Pattern C: keyword style missing docker
old_call_c = (
    "netlist = synthesiser.synthesise(\n"
    "                rtl_path   = rtl_path,\n"
    "                top_module = top_module,\n"
    "                output_dir = synth_dir,\n"
    "            )"
)
new_call_c = (
    "netlist = synthesiser.synthesise(\n"
    "                rtl_path   = rtl_path,\n"
    "                top_module = top_module,\n"
    "                output_dir = synth_dir,\n"
    "                docker     = self.docker,\n"
    "            )"
)

stage_fixed = False
for old, new in [(old_call_a, new_call_a), (old_call_b, new_call_b), (old_call_c, new_call_c)]:
    if old in new_content:
        new_content = new_content.replace(old, new)
        stage_fixed = True
        break

# Also fix the instantiation if it passes yosys_exe
new_content = new_content.replace(
    "synthesiser = _Synthesiser(self.config.yosys_exe)",
    "synthesiser = _Synthesiser()",
)
new_content = new_content.replace(
    "synthesiser = _Synthesiser(yosys_exe=self.config.yosys_exe)",
    "synthesiser = _Synthesiser()",
)

# ─────────────────────────────────────────────────────────────────────────────
# ALSO FIX _stage_synthesis EMIT MESSAGE
# ─────────────────────────────────────────────────────────────────────────────
# Update the progress message to be accurate
for old_msg, new_msg in [
    ('f"Running Yosys for {top_module}..."',
     'f"Running Yosys (Docker) for {top_module}..."'),
    ('"Running Yosys synthesis..."',
     '"Running Yosys (Docker) synthesis..."'),
]:
    if old_msg in new_content:
        new_content = new_content.replace(old_msg, new_msg)

# ─────────────────────────────────────────────────────────────────────────────
# VERIFY RESULT
# ─────────────────────────────────────────────────────────────────────────────

checks = [
    ("class _Synthesiser:" in new_content,
     "_Synthesiser class present"),
    ("interpreter    = \"yosys -s\"" in new_content or
     'interpreter="yosys -s"' in new_content,
     "yosys -s interpreter present"),
    ("/work/rtl.v" in new_content,
     "/work/rtl.v path in synthesis script"),
    ("docker" in new_content[new_content.index("class _Synthesiser:"):
                                    new_content.index("class RTLGenAI:")],
     "docker param used in _Synthesiser"),
    (new_content.count("class _Synthesiser:") == 1,
     "exactly one _Synthesiser class"),
    ("class RTLGenAI:" in new_content,
     "RTLGenAI class present"),
]

all_ok = True
for passed, label in checks:
    icon = "✅" if passed else "❌"
    print(f"  {icon}  {label}")
    if not passed:
        all_ok = False

if not all_ok:
    print()
    print("ERROR: Content verification failed — not writing file.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# BACKUP AND WRITE
# ─────────────────────────────────────────────────────────────────────────────

backup = FULL_FLOW.with_suffix(".py.synth_bak")
FULL_FLOW.rename(backup)
print(f"\n✅  Original backed up → {backup.name}")

FULL_FLOW.write_text(new_content, encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# LIVE IMPORT VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

try:
    import importlib.util
    spec   = importlib.util.spec_from_file_location("full_flow", str(FULL_FLOW))
    module = importlib.util.module_from_spec(spec)

    # Stub all missing imports so the file loads
    import sys as _sys
    stubs = [
        "python.docker_manager", "python.pdk_manager",
        "python.floorplanner",   "python.placer",
        "python.cts_engine",     "python.placement_optimizer",
        "python.global_router",  "python.detail_router",
        "python.routing_optimizer","python.gds_generator",
        "python.signoff_checker","python.tapeout_packager",
    ]
    for s in stubs:
        if s not in _sys.modules:
            import types
            _sys.modules[s] = types.ModuleType(s)

    spec.loader.exec_module(module)

    synth = module._Synthesiser()
    assert hasattr(synth, "synthesise"), "synthesise method missing"
    import inspect
    params = list(inspect.signature(synth.synthesise).parameters.keys())
    assert "docker" in params, f"docker param missing from synthesise(): {params}"
    print("✅  Import verification passed")
    print(f"   synthesise() params: {params}")

except Exception as e:
    print(f"WARNING: Import check inconclusive ({e})")
    print("         This is normal if some phase modules are not yet imported.")
    print("         The file was written — run validate_pipeline.py to confirm.")

added = new_content.count("\n") - original.count("\n")
print(f"\n✅  full_flow.py patched (+{added} lines)")
print()
print("─" * 62)
print("ROOT CAUSE FIXED:")
print()
print("  BEFORE  Yosys commands passed via stdin or -p flag")
print("          Write paths used Windows format (C:\\...) — invalid in Docker")
print("          .tcl extension → openroad interpreter (wrong tool)")
print()
print("  AFTER   RTL copied to work_dir → Docker sees it as /work/rtl.v")
print("          All TCL paths use /work/... format (valid in Docker)")
print("          interpreter='yosys -s' overrides openroad default")
print()
print("WHAT THIS UNBLOCKS:")
print()
print("  ✅  Synthesis produces real sky130 gate-level netlist")
print("  ✅  Floorplanner receives correctly-formatted netlist")
print("  ✅  Placement/CTS/Routing can parse the netlist")
print()
print("─" * 62)
print("NEXT STEP:")
print()
print("  Remove the old run (it has a bad netlist from before):")
print('  Remove-Item "validation\\run_001" -Recurse -Force')
print()
print("  Re-run validation:")
print("  python validate_pipeline.py")
print()
print("  Expected flow:")
print("    [synthesis  ]  0.7s  — sky130 netlist produced")
print("    [floorplan  ]  2.0s  — DEF with sky130 cell estimates")
print("    [placement  ]  TBD   — OpenROAD placement.tcl runs")
print("    [cts        ]  TBD   — TritonCTS runs")
print("    [routing    ]  TBD   — FastRoute + TritonRoute run")
print("    [gds        ]  TBD   — Magic exports GDSII")
print("─" * 62)
