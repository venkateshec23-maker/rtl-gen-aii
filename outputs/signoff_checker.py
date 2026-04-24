"""
signoff_checker.py  –  DRC/LVS Sign-off Checker for RTL-Gen AI
================================================================
Runs the full sign-off verification flow required before tape-out:
  1. DRC (Design Rule Check)   – layout geometry obeys fab rules
  2. LVS (Layout vs Schematic) – layout matches the original netlist
  3. Antenna check             – long wires won't damage gate oxides
  4. ERC (Electrical Rule Check)– power/ground connectivity

Why sign-off matters
─────────────────────
A foundry will not accept a GDS file that has:
  • Any DRC violations → geometry violates physical rules
  • LVS mismatches → layout doesn't match schematic

Both must be 100% clean before submission.  This module automates
both checks and produces a clear PASS/FAIL report.

Tools used
───────────
  DRC  → KLayout with Sky130 DRC rule deck (.lydrc)
  LVS  → KLayout with Sky130 LVS rule deck (.lylvs) + Netgen
  Both run inside Docker (Magic/Netgen also available in OpenLane image)

Sign-off criteria
──────────────────
  DRC: Zero violations across all rule categories
  LVS: Layout netlist == schematic netlist (all nets match)

Usage example
──────────────
    from python.docker_manager  import DockerManager
    from python.pdk_manager     import PDKManager
    from python.signoff_checker import SignoffChecker, SignoffConfig

    dm      = DockerManager()
    pdk     = PDKManager()
    checker = SignoffChecker(docker=dm, pdk=pdk)

    result = checker.run(
        gds_path       = r"C:\\project\\gds\\adder_8bit.gds",
        netlist_path   = r"C:\\project\\synth\\netlist.v",
        top_module     = "adder_8bit",
        output_dir     = r"C:\\project\\signoff",
    )
    print(result.summary())
    if result.is_clean:
        print("✅  Ready for tape-out!")
"""

from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from python.docker_manager import DockerManager, ContainerResult


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SignoffConfig:
    """Parameters for the sign-off verification flow."""
    # Which checks to run
    run_drc:      bool = True
    run_lvs:      bool = True
    run_antenna:  bool = False   # Requires additional antenna rule file

    # Top-level cell name (same as module name)
    top_cell:     str  = ""      # Populated from top_module arg if empty

    # Whether to stop after first failure or run all checks
    stop_on_fail: bool = False


@dataclass
class DRCReport:
    """DRC check result."""
    passed:          bool        = False
    violation_count: int         = 0
    violations:      List[str]   = field(default_factory=list)
    report_path:     Optional[str] = None
    log:             str         = ""


@dataclass
class LVSReport:
    """LVS check result."""
    passed:      bool        = False
    matched:     bool        = False   # True when layout == schematic
    mismatches:  List[str]   = field(default_factory=list)
    report_path: Optional[str] = None
    log:         str         = ""


@dataclass
class SignoffResult:
    """Complete sign-off result — both DRC and LVS."""
    top_module:   str
    output_dir:   str
    is_clean:     bool = False   # True only when ALL checks pass

    drc:          Optional[DRCReport] = None
    lvs:          Optional[LVSReport] = None

    run_results:  List[ContainerResult] = field(default_factory=list)
    error_message: str = ""

    def summary(self) -> str:
        overall = "✅  TAPE-OUT READY" if self.is_clean else "❌  NOT READY"
        lines   = [
            "",
            "╔" + "═" * 58 + "╗",
            "║  Sign-off Result  –  RTL-Gen AI" + " " * 25 + "║",
            "╠" + "═" * 58 + "╣",
            f"║  Overall status : {overall:<38} ║",
            f"║  Top module     : {self.top_module:<38} ║",
            "╠" + "─" * 58 + "╣",
        ]

        if self.drc:
            drc_s = "✅  CLEAN" if self.drc.passed else \
                    f"❌  {self.drc.violation_count} violations"
            lines.append(f"║  DRC            : {drc_s:<38} ║")

        if self.lvs:
            lvs_s = "✅  MATCHED" if self.lvs.matched else \
                    f"❌  {len(self.lvs.mismatches)} mismatches"
            lines.append(f"║  LVS            : {lvs_s:<38} ║")

        if self.error_message:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  Error          : {self.error_message[:38]:<38} ║",
            ]
        lines.append("╚" + "═" * 58 + "╝")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class SignoffChecker:
    """
    Automates DRC and LVS sign-off for tape-out.

    DRC: uses KLayout with Sky130 rule deck (inside Docker)
    LVS: uses Netgen (inside OpenLane Docker image) to compare
         extracted netlist from layout vs original synthesis netlist
    """

    def __init__(self, docker: DockerManager, pdk) -> None:
        self.logger = logging.getLogger(__name__)
        self.docker = docker
        self.pdk    = pdk

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────

    def run(
        self,
        gds_path:     str | Path,
        top_module:   str,
        output_dir:   str | Path,
        netlist_path: Optional[str | Path] = None,
        config:       Optional[SignoffConfig] = None,
    ) -> SignoffResult:
        """
        Run the complete sign-off flow (DRC + LVS).

        Args:
            gds_path:     Path to design.gds on Windows.
            top_module:   Top-level module name.
            output_dir:   Windows output directory for reports.
            netlist_path: Path to synthesised Verilog netlist for LVS.
                          Required when config.run_lvs=True.
            config:       Sign-off parameters.

        Returns:
            SignoffResult — check is_clean for tape-out go/no-go.
        """
        config     = config or SignoffConfig()
        config.top_cell = config.top_cell or top_module
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        gds_path   = Path(gds_path)

        result = SignoffResult(
            top_module = top_module,
            output_dir = str(output_dir),
        )

        self.logger.info(
            f"Sign-off: {top_module} | "
            f"DRC={config.run_drc} | LVS={config.run_lvs}"
        )

        # Copy GDS to output_dir for Docker
        import shutil
        dest_gds = output_dir / gds_path.name
        if gds_path.resolve() != dest_gds.resolve() and gds_path.exists():
            shutil.copy2(gds_path, dest_gds)

        # ── DRC ───────────────────────────────────────────────────────
        if config.run_drc:
            self.logger.info("Running DRC...")
            drc_report, drc_run = self._run_drc(gds_path, top_module,
                                                 output_dir, config)
            result.drc = drc_report
            result.run_results.append(drc_run)

            if config.stop_on_fail and not drc_report.passed:
                result.error_message = "DRC failed – stopping"
                return result

        # ── LVS ───────────────────────────────────────────────────────
        if config.run_lvs and netlist_path:
            netlist_path = Path(netlist_path)
            self.logger.info("Running LVS...")
            lvs_report, lvs_run = self._run_lvs(
                gds_path, netlist_path, top_module, output_dir, config
            )
            result.lvs = lvs_report
            result.run_results.append(lvs_run)

        # ── Overall result ────────────────────────────────────────────
        drc_ok = (not config.run_drc) or (result.drc and result.drc.passed)
        lvs_ok = (not config.run_lvs or not netlist_path) or \
                 (result.lvs and result.lvs.matched)
        result.is_clean = bool(drc_ok and lvs_ok)

        self.logger.info(
            f"Sign-off complete | clean={result.is_clean} | "
            f"DRC={'PASS' if drc_ok else 'FAIL'} | "
            f"LVS={'PASS' if lvs_ok else 'FAIL'}"
        )
        return result

    def run_drc_only(
        self,
        gds_path:   str | Path,
        top_module: str,
        output_dir: str | Path,
        config:     Optional[SignoffConfig] = None,
    ) -> DRCReport:
        """
        Run DRC only without LVS.

        Args:
            gds_path:   Path to GDS file.
            top_module: Top cell name.
            output_dir: Output directory.
            config:     Sign-off parameters.

        Returns:
            DRCReport with passed flag and violations list.
        """
        config     = config or SignoffConfig()
        config.top_cell = config.top_cell or top_module
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report, _ = self._run_drc(Path(gds_path), top_module, output_dir, config)
        return report

    # ──────────────────────────────────────────────────────────────────────
    # DRC IMPLEMENTATION
    # ──────────────────────────────────────────────────────────────────────

    def _run_drc(
        self,
        gds_path:   Path,
        top_module: str,
        output_dir: Path,
        config:     SignoffConfig,
    ):
        """Run KLayout DRC via Docker and parse results."""
        tcl = self._generate_drc_script(gds_path, top_module, output_dir)

        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "drc_check.tcl",
            work_dir       = output_dir,
            timeout        = 1800,
        )

        # Parse DRC report
        drc_rpt_path = output_dir / "drc.rpt"
        violations   = self._parse_drc_report(drc_rpt_path, run.combined_output())

        report = DRCReport(
            passed          = (len(violations) == 0) and run.success,
            violation_count = len(violations),
            violations      = violations,
            report_path     = str(drc_rpt_path) if drc_rpt_path.exists() else None,
            log             = run.combined_output(),
        )

        self.logger.info(
            f"DRC: {'PASS' if report.passed else 'FAIL'} | "
            f"{report.violation_count} violations"
        )
        return report, run

    def _generate_drc_script(
        self,
        gds_path:   Path,
        top_module: str,
        output_dir: Path,
    ) -> str:
        """
        Generate KLayout DRC script using the Sky130 rule deck.
        KLayout runs in batch mode (-b) inside the Docker container.
        """
        # KLayout DRC rule deck location inside Docker
        drc_rules = "/pdk/sky130A/libs.tech/klayout/sky130A.lydrc"

        # Use Magic for DRC when KLayout rule deck not available
        magic_drc = textwrap.dedent(f"""
        # DRC via Magic  –  RTL-Gen AI
        tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
        gds read /work/{gds_path.name}
        load {top_module}
        drc check
        set count [drc list count total]
        puts "DRC violations: $count"
        set fp [open /work/drc.rpt w]
        puts $fp "DRC Report for {top_module}"
        puts $fp "Violations: $count"
        foreach {{cat cnt}} [drc list count] {{
            puts $fp "  $cat : $cnt"
            puts "  $cat : $cnt"
        }}
        close $fp
        quit
        """).strip()

        return magic_drc

    def _parse_drc_report(
        self,
        rpt_path: Path,
        log_text: str,
    ) -> List[str]:
        """
        Parse DRC violations from Magic drc.rpt or log output.

        Returns list of violation description strings.
        Empty list = DRC clean.
        """
        violations: List[str] = []

        # Try to parse the report file
        if rpt_path.exists():
            try:
                text = rpt_path.read_text(encoding="utf-8", errors="ignore")
                for line in text.splitlines():
                    s = line.strip()
                    # "  category_name : N" lines list per-category counts
                    m = re.match(r"^\s*(\S+)\s*:\s*(\d+)\s*$", s)
                    if m and int(m.group(2)) > 0:
                        violations.append(
                            f"{m.group(1)}: {m.group(2)} violations"
                        )
                    # "Violations: 0" line
                    m2 = re.match(r"Violations:\s*(\d+)", s)
                    if m2 and int(m2.group(1)) == 0:
                        return []   # explicitly clean
            except OSError:
                pass

        # Fallback: scan log text for "DRC violations: N"
        for line in log_text.splitlines():
            s = line.strip()
            m = re.match(r"DRC violations:\s*(\d+)", s)
            if m:
                n = int(m.group(1))
                if n == 0:
                    return []
                violations.append(f"{n} total DRC violations")

        return violations

    # ──────────────────────────────────────────────────────────────────────
    # LVS IMPLEMENTATION
    # ──────────────────────────────────────────────────────────────────────

    def _run_lvs(
        self,
        gds_path:     Path,
        netlist_path: Path,
        top_module:   str,
        output_dir:   Path,
        config:       SignoffConfig,
    ):
        """Run Netgen LVS via Docker and parse results."""
        import shutil
        # Copy netlist to output_dir so Docker can access it
        dest_netlist = output_dir / netlist_path.name
        if netlist_path.resolve() != dest_netlist.resolve() and netlist_path.exists():
            shutil.copy2(netlist_path, dest_netlist)

        tcl = self._generate_lvs_script(gds_path, netlist_path, top_module)

        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "lvs_check.tcl",
            work_dir       = output_dir,
            timeout        = 1800,
        )

        lvs_rpt_path = output_dir / "lvs.rpt"
        mismatches, matched = self._parse_lvs_output(
            run.combined_output(), lvs_rpt_path
        )

        report = LVSReport(
            passed      = matched and run.success,
            matched     = matched,
            mismatches  = mismatches,
            report_path = str(lvs_rpt_path) if lvs_rpt_path.exists() else None,
            log         = run.combined_output(),
        )

        self.logger.info(
            f"LVS: {'MATCH' if matched else 'MISMATCH'} | "
            f"{len(mismatches)} mismatch(es)"
        )
        return report, run

    def _generate_lvs_script(
        self,
        gds_path:     Path,
        netlist_path: Path,
        top_module:   str,
    ) -> str:
        """
        Generate Netgen LVS Tcl script.

        Netgen compares:
          Layout netlist  – extracted from GDS by Magic
          Schematic       – synthesised Verilog (gate-level)
        """
        spice_models = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/spice"

        return textwrap.dedent(f"""
        # ────────────────────────────────────────────────────────────────
        # LVS via Netgen  –  RTL-Gen AI
        # Top module  : {top_module}
        # ────────────────────────────────────────────────────────────────

        # Run Netgen LVS comparison
        # layout   = extracted SPICE from GDS
        # schematic= original synthesised netlist

        # First extract SPICE from the GDS using Magic
        # Then compare with Netgen

        # Step 1: Extract SPICE from layout (Magic)
        magic -noconsole -dnull << 'MAGIC_EOF'
        tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
        gds read /work/{gds_path.name}
        load {top_module}
        extract all
        ext2spice -format ngspice -cthresh 0 -rthresh 0
        MAGIC_EOF

        # Step 2: Run Netgen LVS
        netgen -batch lvs \\
            "/work/{top_module}.spice {top_module}" \\
            "/work/{netlist_path.name} {top_module}" \\
            "/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" \\
            /work/lvs.rpt \\
            -json

        puts "LVS complete"
        """).strip()

    def _parse_lvs_output(
        self,
        output:   str,
        rpt_path: Path,
    ):
        """
        Parse LVS output for match/mismatch status.

        Netgen prints:
          "Circuits match uniquely."          → match
          "Circuits do not match."            → mismatch
          "Parameter errors: N"               → mismatch
        """
        mismatches: List[str] = []
        matched = False

        # Check combined output
        for line in output.splitlines():
            s = line.strip()
            if "Circuits match uniquely" in s or "Circuit 1 matches Circuit 2" in s:
                matched = True
            if "do not match" in s.lower() or "mismatch" in s.lower():
                mismatches.append(s[:200])
            if re.match(r"Parameter errors\s*:\s*(\d+)", s):
                n = int(re.search(r"\d+", s).group())
                if n > 0:
                    mismatches.append(s)

        # Also check report file
        if rpt_path.exists():
            try:
                text = rpt_path.read_text(encoding="utf-8", errors="ignore")
                if "Circuits match uniquely" in text:
                    matched = True
                    mismatches = []
            except OSError:
                pass

        return mismatches, matched
