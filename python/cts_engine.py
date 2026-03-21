"""
cts_engine.py  –  Clock Tree Synthesis Engine for RTL-Gen AI
=============================================================
Runs TritonCTS (inside OpenROAD/Docker) to synthesise a balanced
clock tree after placement.

Why CTS matters
────────────────
After placement, the clock net is one long wire from the clock port
to hundreds of flip-flop clock pins.  Without a clock tree:
  • Clock skew is huge (different FFs see the clock at very different times)
  • Setup/hold violations everywhere
  • The design will not work in silicon

TritonCTS inserts clock buffers in a hierarchical tree structure so
that all FF clock pins receive the clock within a tight time window
(target skew < 100 ps for most designs).

Steps performed
────────────────
Step 1 – Read placed.def
Step 2 – Run TritonCTS (inserts buffers, creates clock tree)
Step 3 – Set propagated clocks (so OpenSTA uses real wire delays)
Step 4 – Repair hold violations (buffer insertion sometimes creates holds)
Step 5 – Write cts.def
Step 6 – Generate skew / timing report

Data flow
──────────
  placed.def  →  cts_engine.py  →  OpenROAD Docker  →  cts.def
                                                         cts.rpt

Usage example
──────────────
    from python.docker_manager import DockerManager
    from python.pdk_manager    import PDKManager
    from python.cts_engine     import CTSEngine, CTSConfig

    dm  = DockerManager()
    pdk = PDKManager()
    cts = CTSEngine(docker=dm, pdk=pdk)

    result = cts.run(
        def_path   = r"C:\\project\\physical\\placed.def",
        top_module = "adder_8bit",
        output_dir = r"C:\\project\\physical",
    )
    print(result.summary())
    # Writes: cts.def, cts.rpt
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
class CTSConfig:
    """
    Parameters for clock tree synthesis.

    The buffer cell names below are standard Sky130 HD clock buffers.
    The root buffer (clkbuf_16) is the strongest; leaf buffers
    (clkbuf_4, clkbuf_8) drive smaller sub-trees.
    """
    # Clock period in nanoseconds
    clock_period_ns:   float = 10.0

    # Name of the clock port / net in the netlist
    clock_net:         str   = "clk"

    # Root buffer (highest drive strength, placed near clock source)
    root_buf:          str   = "sky130_fd_sc_hd__clkbuf_16"

    # Intermediate and leaf buffers (comma-separated list for TritonCTS)
    buf_list:          str   = (
        "sky130_fd_sc_hd__clkbuf_2,"
        "sky130_fd_sc_hd__clkbuf_4,"
        "sky130_fd_sc_hd__clkbuf_8"
    )

    # Target maximum clock skew (ns).  TritonCTS tries to stay below this.
    target_skew_ns:    float = 0.1    # 100 ps

    # Whether to repair hold violations after CTS.
    # TritonCTS buffer insertion changes wire delays and can create holds.
    repair_hold:       bool  = True

    # Hold margin added when repairing holds (ns)
    hold_margin_ns:    float = 0.05   # 50 ps extra margin


@dataclass
class CTSStats:
    """
    Quality metrics extracted from the CTS report.
    """
    max_skew_ns:       float = 0.0   # Measured worst-case clock skew
    avg_skew_ns:       float = 0.0   # Average skew
    buf_count:         int   = 0     # Number of clock buffers inserted
    clock_net_length:  float = 0.0   # Total clock wire length (µm)
    worst_slack_ns:    float = 0.0   # WNS after hold repair
    tns_ns:            float = 0.0   # TNS after hold repair


@dataclass
class CTSResult:
    """Complete result from CTSEngine.run()."""
    top_module:   str
    output_dir:   str
    success:      bool = False

    cts_def:      Optional[str] = None   # Path to cts.def
    report_path:  Optional[str] = None   # Path to cts.rpt
    stats:        CTSStats = field(default_factory=CTSStats)

    run_results:  List[RunResult] = field(default_factory=list)
    error_message: str = ""

    def summary(self) -> str:
        status = "✅  SUCCESS" if self.success else "❌  FAILED"
        s      = self.stats
        lines  = [
            "",
            "╔" + "═" * 56 + "╗",
            "║  CTS Result  –  RTL-Gen AI" + " " * 28 + "║",
            "╠" + "═" * 56 + "╣",
            f"║  Status          : {status:<36} ║",
            f"║  Top module      : {self.top_module:<36} ║",
        ]
        if self.success:
            lines += [
                "╠" + "─" * 56 + "╣",
                f"║  Buffers inserted: {s.buf_count:<36} ║",
                f"║  Max clock skew  : {s.max_skew_ns:.4f} ns"
                + " " * max(0, 30 - len(f"{s.max_skew_ns:.4f} ns")) + " ║",
                f"║  WNS (hold)      : {s.worst_slack_ns:.3f} ns"
                + " " * max(0, 31 - len(f"{s.worst_slack_ns:.3f} ns")) + " ║",
                f"║  Clock wire len  : {s.clock_net_length:.1f} µm"
                + " " * max(0, 32 - len(f"{s.clock_net_length:.1f} µm")) + " ║",
            ]
        if self.cts_def:
            p = Path(self.cts_def).name
            lines.append(f"║  DEF file        : {p:<36} ║")
        if self.error_message:
            lines += [
                "╠" + "─" * 56 + "╣",
                f"║  Error           : {self.error_message[:36]:<36} ║",
            ]
        lines.append("╚" + "═" * 56 + "╝")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class CTSEngine:
    """
    Runs TritonCTS via OpenROAD in Docker for clock tree synthesis.

    Reads  : placed.def  (from Placer)
    Writes : cts.def, cts.rpt
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
        def_path:   str | Path,
        top_module: str,
        output_dir: str | Path,
        config:     Optional[CTSConfig] = None,
    ) -> CTSResult:
        """
        Synthesise a clock tree for the design.

        Args:
            def_path:   Path to placed.def on Windows.
            top_module: Top-level module name.
            output_dir: Windows output directory.
            config:     CTS parameters.

        Returns:
            CTSResult with cts.def path and skew statistics.
        """
        config     = config or CTSConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        def_path   = Path(def_path)

        result = CTSResult(
            top_module = top_module,
            output_dir = str(output_dir),
        )

        self.logger.info(
            f"CTS: {top_module} | "
            f"clk={config.clock_net} @ {config.clock_period_ns}ns | "
            f"target skew={config.target_skew_ns}ns"
        )

        # Copy DEF to output dir for Docker
        dest_def = output_dir / def_path.name
        if def_path.resolve() != dest_def.resolve() and def_path.exists():
            import shutil
            shutil.copy2(def_path, dest_def)

        tcl = self._generate_cts_script(def_path, top_module, config)
        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "cts.tcl",
            work_dir       = output_dir,
            timeout        = 900,
        )
        result.run_results.append(run)

        if not run.success:
            result.error_message = self._extract_error(run.combined_output())
            self.logger.error(f"CTS failed: {result.error_message}")
            return result

        cts_def = output_dir / "cts.def"
        rpt     = output_dir / "cts.rpt"

        result.cts_def      = str(cts_def) if cts_def.exists() else None
        result.report_path  = str(rpt)     if rpt.exists()     else None
        result.success      = cts_def.exists()

        if result.report_path:
            result.stats = self._parse_cts_report(Path(result.report_path))

        if not result.success:
            result.error_message = "cts.def not created"

        self.logger.info(
            f"CTS {'complete' if result.success else 'FAILED'} | "
            f"bufs={result.stats.buf_count} | "
            f"skew={result.stats.max_skew_ns:.4f}ns"
        )
        return result

    def check_skew(
        self,
        def_path:   str | Path,
        top_module: str,
        output_dir: str | Path,
        config:     Optional[CTSConfig] = None,
    ) -> CTSStats:
        """
        Run a skew analysis without modifying the design.
        Reads cts.def and reports clock skew metrics.

        Args:
            def_path:   Path to cts.def.
            top_module: Top module name.
            output_dir: Output directory.
            config:     Clock settings.

        Returns:
            CTSStats with measured skew values.
        """
        config     = config or CTSConfig()
        output_dir = Path(output_dir)
        tcl        = self._generate_skew_check_script(
            Path(def_path), top_module, config
        )
        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "check_skew.tcl",
            work_dir       = output_dir,
            timeout        = 120,
        )
        return self._parse_skew_output(run.stdout)

    # ──────────────────────────────────────────────────────────────────────
    # TCL GENERATORS
    # ──────────────────────────────────────────────────────────────────────

    def _generate_cts_script(
        self,
        def_path:   Path,
        top_module: str,
        config:     CTSConfig,
    ) -> str:
        """
        Full CTS Tcl: read DEF → TritonCTS → hold repair → write DEF + report.
        """
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        lib_ss   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib"

        hold_repair = (
            "\n# ── 5. Repair hold violations ──────────────────────────────\n"
            "# CTS buffer insertion changes net delays → may create holds\n"
            "repair_timing -hold "
            f"-hold_margin {config.hold_margin_ns} "
            f"-max_buffer_percent 20\n"
            if config.repair_hold else ""
        )

        return textwrap.dedent(f"""
        # ────────────────────────────────────────────────────────────────
        # Clock Tree Synthesis  –  RTL-Gen AI
        # Top module  : {top_module}
        # Clock net   : {config.clock_net} @ {config.clock_period_ns} ns
        # Target skew : {config.target_skew_ns} ns
        # ────────────────────────────────────────────────────────────────

        # ── 1. Read PDK files ─────────────────────────────────────────
        read_lef     {tech_lef}
        read_lef     {cell_lef}
        read_liberty {lib_tt}
        read_liberty {lib_ss}

        # ── 2. Read placed DEF ────────────────────────────────────────
        read_def /work/{def_path.name}
        link_design {top_module}

        # ── 3. Clock constraint ───────────────────────────────────────
        create_clock -name {config.clock_net} \\
                     -period {config.clock_period_ns} \\
                     [get_ports {config.clock_net}]

        # ── 4. Clock Tree Synthesis (TritonCTS) ───────────────────────
        # root_buf  = strongest buffer at the root (near clock source)
        # buf_list  = available buffers for intermediate / leaf nodes
        clock_tree_synthesis \\
            -root_buf {config.root_buf} \\
            -buf_list {{{config.buf_list}}} \\
            -sink_clustering_enable \\
            -sink_clustering_size 20
        {hold_repair}
        # ── 6. Propagate clock (use real wire delays for STA) ─────────
        set_propagated_clock [all_clocks]

        # ── 7. Reports ────────────────────────────────────────────────
        # Clock skew report
        report_clock_skew                   > /work/cts.rpt
        # Timing check after CTS
        report_checks -path_delay max      >> /work/cts.rpt
        report_checks -path_delay min      >> /work/cts.rpt
        report_wns                         >> /work/cts.rpt
        report_tns                         >> /work/cts.rpt

        # Buffer count
        set buf_count [llength [get_cells -hierarchical -filter "is_clock_cell == 1"]]
        puts "Clock buffers inserted: $buf_count"
        puts $buf_count >> /work/cts.rpt

        # ── 8. Write output DEF ───────────────────────────────────────
        write_def /work/cts.def

        puts "\\n✅  CTS complete: {top_module}\\n"
        exit
        """).strip()

    def _generate_skew_check_script(
        self,
        def_path:   Path,
        top_module: str,
        config:     CTSConfig,
    ) -> str:
        """Skew-check-only script (no modifications)."""
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"

        return textwrap.dedent(f"""
        read_lef     {tech_lef}
        read_lef     {cell_lef}
        read_liberty {lib_tt}
        read_def /work/{def_path.name}
        link_design {top_module}
        create_clock -name {config.clock_net} -period {config.clock_period_ns} \\
                     [get_ports {config.clock_net}]
        set_propagated_clock [all_clocks]
        report_clock_skew
        exit
        """).strip()

    # ──────────────────────────────────────────────────────────────────────
    # REPORT PARSING
    # ──────────────────────────────────────────────────────────────────────

    def _parse_cts_report(self, rpt_path: Path) -> CTSStats:
        """
        Parse cts.rpt for skew and timing metrics.

        OpenROAD report_clock_skew output:
          "Clock clk"
          "Latency      CRPR       Skew"
          "max 1.234    -0.012     0.089"

        OpenROAD WNS/TNS:
          "wns X.XX"
          "tns X.XX"
        """
        stats = CTSStats()
        if not rpt_path.exists():
            return stats

        try:
            text = rpt_path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()

                # WNS / TNS
                if stripped.startswith("wns "):
                    try:
                        stats.worst_slack_ns = float(stripped.split()[1])
                    except (IndexError, ValueError):
                        pass
                if stripped.startswith("tns "):
                    try:
                        stats.tns_ns = float(stripped.split()[1])
                    except (IndexError, ValueError):
                        pass

                # Skew header line: "Latency      CRPR       Skew" -> skip
                # Skew data line: "0.823        -0.012     0.045" -> last number
                if "Skew" in stripped and not re.search(r"[\d.]", stripped):
                    pass   # this is the header line, skip
                elif "Skew" in stripped or "skew" in stripped:
                    nums = re.findall(r"-?[\d]+\.[\d]+", stripped)
                    if nums:
                        try:
                            stats.max_skew_ns = abs(float(nums[-1]))
                        except ValueError:
                            pass
                # Also parse data rows that follow the "Latency CRPR Skew" header
                # Format: "  0.823        -0.012     0.045"
                elif re.match(r"^\s*[\d.]+\s+[-\d.]+\s+([\d.]+)", stripped):
                    m_sk = re.match(r"^[\d.]+\s+[-\d.]+\s+([\d.]+)", stripped)
                    if m_sk and stats.max_skew_ns == 0.0:
                        try:
                            stats.max_skew_ns = float(m_sk.group(1))
                        except ValueError:
                            pass

                # Buffer count line we wrote: "Clock buffers inserted: N"
                m = re.match(r"Clock buffers inserted:\s*(\d+)", stripped)
                if m:
                    stats.buf_count = int(m.group(1))

        except OSError:
            pass

        return stats

    @staticmethod
    def _parse_skew_output(output: str) -> CTSStats:
        """Parse skew from stdout (used by check_skew())."""
        stats = CTSStats()
        for line in output.splitlines():
            stripped = line.strip()
            if "Skew" in stripped or "skew" in stripped:
                nums = re.findall(r"[-\d]+\.[\d]+", stripped)
                if nums:
                    try:
                        stats.max_skew_ns = abs(float(nums[-1]))
                    except ValueError:
                        pass
        return stats

    @staticmethod
    def _extract_error(output: str) -> str:
        for line in output.splitlines():
            s = line.strip()
            if s.startswith(("[ERROR", "Error:", "ERROR:")):
                return s[:200]
        return "CTS error (check run log)"
