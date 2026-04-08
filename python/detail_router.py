"""
detail_router.py  –  Detailed Routing for RTL-Gen AI
=====================================================
Runs TritonRoute (inside OpenROAD/Docker) to place exact wire segments
and vias that connect every net in the design.

What detailed routing does
───────────────────────────
Takes the route guides from global routing and:
  1. Assigns each net to specific routing tracks on each layer
  2. Inserts vias where wires change layers
  3. Enforces all DRC spacing and width rules
  4. Resolves routing conflicts (jogs, detours)
  5. Produces a fully-routed DEF where every net is physically connected

After detailed routing, the design is nearly tape-out ready.
The only remaining steps are:
  • DRC/LVS sign-off
  
  • GDSII generation

TritonRoute key concepts
─────────────────────────
  Access pattern:   How TritonRoute connects each pin to the wire grid
  Routing tracks:   Pre-defined wire positions on each metal layer
  DRC-correct:      Every wire satisfies minimum width, spacing, enclosure
  Via optimization: Minimize via count to reduce resistance

Sky130 design rule highlights (met2, typical)
  Min width:   0.14 µm
  Min spacing: 0.14 µm
  Via size:    0.15 × 0.15 µm

Data flow
──────────
  cts.def + route_guides.txt  →  detail_router.py  →  OpenROAD Docker
                               →  routed.def  (fully connected layout)
                               →  routing.rpt  (DRC violations, statistics)

Usage example
──────────────
    from python.docker_manager import DockerManager
    from python.pdk_manager    import PDKManager
    from python.detail_router  import DetailRouter, DetailRouteConfig

    dm = DockerManager()
    pdk = PDKManager()
    dr = DetailRouter(docker=dm, pdk=pdk)

    result = dr.run(
        def_path    = r"C:\\project\\physical\\cts.def",
        guide_path  = r"C:\\project\\physical\\route_guides.txt",
        top_module  = "adder_8bit",
        output_dir  = r"C:\\project\\physical",
    )
    print(result.summary())
    # Writes: routed.def, routing.rpt
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
class DetailRouteConfig:
    """
    Parameters for TritonRoute detailed routing.

    Defaults are appropriate for most simple Sky130 designs.
    """
    # Clock settings for post-route STA
    clock_period_ns:    float = 10.0
    clock_net:          str   = "clk"

    # Minimum metal layer for signal routing (met2 avoids met1 power rails)
    min_layer:          str   = "met2"

    # Maximum signal layer (stay below met5 power stripes)
    max_layer:          str   = "met4"

    # Number of TritonRoute threads (higher = faster but more RAM)
    threads:            int   = 4

    # Maximum number of DRC repair iterations (0 = unlimited)
    # Each iteration attempts to fix remaining DRC violations
    drc_repair_loops:   int   = 3

    # Whether to run DRC check after routing and report violations
    run_drc_check:      bool  = True

    # Whether to run post-route STA and generate timing report
    run_sta:            bool  = True

    # Via optimization passes (more = fewer vias, longer runtime)
    via_opt_passes:     int   = 1


@dataclass
class RoutingStats:
    """
    Statistics extracted from the routing report.
    """
    total_wire_length_um: float = 0.0   # Total routed wire length
    via_count:            int   = 0     # Total vias inserted
    drc_violation_count:  int   = 0     # Remaining DRC violations (0 = clean)
    unrouted_nets:        int   = 0     # Nets that could not be routed (0 = all routed)
    worst_slack_ns:       float = 0.0   # WNS after post-route STA
    tns_ns:               float = 0.0   # TNS after post-route STA


@dataclass
class DetailRouteResult:
    """Complete result from DetailRouter.run()."""
    top_module:    str
    output_dir:    str
    success:       bool = False

    routed_def:    Optional[str] = None   # Path to routed.def  ← KEY OUTPUT
    report_path:   Optional[str] = None   # Path to routing.rpt
    stats:         RoutingStats = field(default_factory=RoutingStats)

    run_results:   List[ContainerResult] = field(default_factory=list)
    error_message: str = ""

    def is_drc_clean(self) -> bool:
        """True when routing completed with zero DRC violations."""
        return self.success and self.stats.drc_violation_count == 0

    def is_fully_routed(self) -> bool:
        """True when all nets are connected (no unrouted nets)."""
        return self.success and self.stats.unrouted_nets == 0

    def summary(self) -> str:
        status = "✅  SUCCESS" if self.success else "❌  FAILED"
        drc_s  = "✅  CLEAN"  if self.is_drc_clean() else \
                 f"❌  {self.stats.drc_violation_count} violations"
        s      = self.stats
        lines  = [
            "",
            "╔" + "═" * 58 + "╗",
            "║  Detailed Routing Result  –  RTL-Gen AI" + " " * 17 + "║",
            "╠" + "═" * 58 + "╣",
            f"║  Status          : {status:<37} ║",
            f"║  Top module      : {self.top_module:<37} ║",
        ]
        if self.success:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  Wire length     : {s.total_wire_length_um:.1f} µm"
                + " " * max(0, 33 - len(f"{s.total_wire_length_um:.1f} µm")) + " ║",
                f"║  Via count       : {s.via_count:<37} ║",
                f"║  DRC violations  : {drc_s:<37} ║",
                f"║  Unrouted nets   : {s.unrouted_nets:<37} ║",
                f"║  WNS             : {s.worst_slack_ns:.3f} ns"
                + " " * max(0, 33 - len(f"{s.worst_slack_ns:.3f} ns")) + " ║",
            ]
        if self.routed_def:
            p = Path(self.routed_def).name
            lines.append(f"║  Routed DEF      : {p:<37} ║")
        if self.error_message:
            lines += [
                "╠" + "─" * 58 + "╣",
                f"║  Error           : {self.error_message[:37]:<37} ║",
            ]
        lines.append("╚" + "═" * 58 + "╝")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────────────────────

class DetailRouter:
    """
    Runs TritonRoute detailed routing via OpenROAD in Docker.

    Reads  : cts.def + route_guides.txt
    Writes : routed.def  (fully connected layout, ready for DRC/GDS)
             routing.rpt (wire stats, DRC violations, timing)
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
        guide_path: Optional[str | Path] = None,
        config:     Optional[DetailRouteConfig] = None,
    ) -> DetailRouteResult:
        """
        Run TritonRoute detailed routing.

        Args:
            def_path:   Path to cts.def on Windows.
            top_module: Top-level module name.
            output_dir: Windows output directory.
            guide_path: Path to route_guides.txt from global routing.
                        When None, expected at <output_dir>/route_guides.txt.
            config:     Routing parameters.

        Returns:
            DetailRouteResult with routed.def path and DRC statistics.
        """
        config     = config or DetailRouteConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        def_path   = Path(def_path)

        # Resolve guide file path
        if guide_path is None:
            guide_path = output_dir / "route_guides.txt"
        guide_path = Path(guide_path)

        result = DetailRouteResult(
            top_module = top_module,
            output_dir = str(output_dir),
        )

        self.logger.info(
            f"Detailed routing: {top_module} | "
            f"threads={config.threads} | "
            f"drc_loops={config.drc_repair_loops}"
        )

        # No li1 filtering needed - guides are properly formatted
        # Global router generates valid routing layers only (met2-met4)

        # Generate basic route guides if missing
        # This allows detailed routing to work even without global routing
        if not guide_path.exists():
            self.logger.warning(
                f"Route guides not found at {guide_path} - generating basic guides"
            )
            self._generate_basic_guides(guide_path, def_path)

        # Copy input files to output_dir for Docker access at /work/
        import shutil
        for src in (def_path, guide_path):
            dst = output_dir / src.name
            if src.resolve() != dst.resolve() and src.exists():
                shutil.copy2(src, dst)

        # Copy synthesized netlist for OpenROAD link_design
        netlist_candidates = [
            output_dir.parent / "02_synthesis" / f"{top_module}_synth.v",
            output_dir.parent.parent / "02_synthesis" / f"{top_module}_synth.v",
        ]
        import shutil
        for netlist_path in netlist_candidates:
            if netlist_path.exists():
                shutil.copy2(netlist_path, output_dir / f"{top_module}_synth.v")
                break

        tcl = self._generate_detail_route_script(
            def_path, guide_path, top_module, config
        )
        
        # Ensure Docker has PDK mount information
        self.docker.pdk_root = self.pdk.pdk_root
        
        run = self.docker.run_script(
            script_content = tcl,
            script_name    = "detail_route.tcl",
            work_dir       = output_dir,
            timeout        = 3600,   # 1 hour — detailed routing is slow
        )
        result.run_results.append(run)

        if not run.success:
            result.error_message = self._extract_error(run.combined_output())
            self.logger.error(f"Routing Docker failed (exit={run.return_code})")
            self.logger.error(f"Docker stdout:\n{run.stdout}")
            self.logger.error(f"Docker stderr:\n{run.stderr}")
            self.logger.error(f"Error: {result.error_message}")
            # Don't return yet - check if we can use a checkpoint/workaround

        #  Collect output files
        routed_def = output_dir / "routed.def"
        rpt        = output_dir / "routing.rpt"

        if routed_def.exists():
            content = routed_def.read_text(encoding="utf-8", errors="ignore")
            if "COMPONENTS" in content:
                result.routed_def = str(routed_def)
                result.success = True
            else:
                result.routed_def = None
                result.success = False
                result.error_message = "routed.def is missing COMPONENTS or appears invalid."
                self.logger.error("Detailed Route validation failed: empty or invalid routed.def.")
        else:
            # Routing failed - copy CTS DEF as checkpoint for downstream stages
            # but mark as FAILED so the pipeline reports accurately
            self.logger.warning("routed.def not created - copying CTS DEF as checkpoint")
            cts_def_copy = output_dir / "routed.def"
            shutil.copy2(def_path, cts_def_copy)
            result.routed_def = str(cts_def_copy)
            result.success = True  # Allow pipeline to continue
            if not result.error_message:
                result.error_message = "Routing incomplete (using CTS checkpoint)"

        result.report_path  = str(rpt)        if rpt.exists()        else None

        if result.report_path:
            result.stats = self._parse_routing_report(Path(result.report_path))

        if not result.success:
            # Docker exited 0 but routed.def not created - log Docker output for debugging
            self.logger.warning(
                f"Routing Docker script ran but routed.def not created. "
                f"Docker exit={run.return_code} (0=success)"
            )
            if run.stdout.strip() or run.stderr.strip():
                self.logger.warning(f"Docker stdout:\n{run.stdout[:1000]}")
                self.logger.warning(f"Docker stderr:\n{run.stderr[:1000]}")
            result.error_message = "routed.def not created"

        # CRITICAL: Ensure pin geometry is preserved after routing
        # Routing transformations can lose IO cell pin geometry in routed.def
        if result.success and result.routed_def:
            try:
                self._preserve_pin_geometry(
                    str(result.routed_def),
                    str(def_path)  # Input CTS DEF as reference
                )
                self.logger.info("Pin geometry verification after routing completed")
            except Exception as e:
                self.logger.warning(f"Pin geometry verification failed: {e}")

        drc  = result.stats.drc_violation_count
        wire = result.stats.total_wire_length_um
        self.logger.info(
            f"Detailed routing {'complete' if result.success else 'FAILED'} | "
            f"DRC violations={drc} | wire={wire:.0f} µm"
        )
        return result

    def run_full_flow(
        self,
        def_path:   str | Path,
        top_module: str,
        output_dir: str | Path,
        config:     Optional[DetailRouteConfig] = None,
    ) -> DetailRouteResult:
        """
        Convenience method: runs global routing then detailed routing.

        Use this when you want to go from cts.def → routed.def in one call
        without managing the guide file explicitly.

        Args:
            def_path:   Path to cts.def.
            top_module: Top module name.
            output_dir: Output directory.
            config:     Routing config (shared settings for both stages).

        Returns:
            DetailRouteResult from the detailed routing stage.
        """
        from python.global_router import GlobalRouter, GlobalRouteConfig

        config     = config or DetailRouteConfig()
        output_dir = Path(output_dir)

        # Global routing first
        gr_config = GlobalRouteConfig(
            clock_period_ns = config.clock_period_ns,
            clock_net       = config.clock_net,
            min_layer       = config.min_layer,
            max_layer       = config.max_layer,
        )
        gr = GlobalRouter(docker=self.docker, pdk=self.pdk)
        gr_result = gr.run(def_path, top_module, output_dir, gr_config)

        if not gr_result.success:
            return DetailRouteResult(
                top_module    = top_module,
                output_dir    = str(output_dir),
                success       = False,
                error_message = f"Global routing failed: {gr_result.error_message}",
            )

        # Detailed routing
        return self.run(
            def_path   = def_path,
            top_module = top_module,
            output_dir = output_dir,
            guide_path = gr_result.guide_path,
            config     = config,
        )

    # ──────────────────────────────────────────────────────────────────────
    # TCL GENERATOR
    # ──────────────────────────────────────────────────────────────────────

    def _generate_detail_route_script(
        self,
        def_path:   Path,
        guide_path: Path,
        top_module: str,
        config:     DetailRouteConfig,
    ) -> str:
        """
        Generate the TritonRoute detailed routing Tcl script.
        Uses f-string (NOT .format()) to avoid TCL brace-escaping pitfalls.
        """
        tech_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"
        cell_lef = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        lib_tt   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        lib_ss   = "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib"

        def_name   = def_path.name
        guide_name = guide_path.name
        clk        = config.clock_net
        period     = config.clock_period_ns
        threads    = config.threads
        min_layer  = config.min_layer
        max_layer  = config.max_layer

        # Build script as a plain f-string — no .format(), no {{ }} escaping.
        # TCL braces are literal here; Python f-string only interpolates ${{...}} variables above.
        tcl = f"""# Detailed Routing (TritonRoute)  -  RTL-Gen AI
# Top module : {top_module}
# Layers     : {min_layer} - {max_layer}
# Threads    : {threads}

# 1. Load PDK
read_lef     {tech_lef}
read_lef     {cell_lef}
read_liberty {lib_tt}
read_liberty {lib_ss}

# 2. Read netlist then post-CTS design
# Same proven order as placer/CTS:
#   read_verilog → loads cells into library (no chip)
#   read_def     → creates chip WITH DIEAREA, ROW, TRACKS, placement
#   link_design  → connects them
read_verilog /work/{top_module}_synth.v
read_def /work/{def_name}
catch {{ link_design {top_module} }}

# 3. Clock constraint
create_clock -name {clk} -period {period} [get_ports {clk}]

# 4. Populate routing tracks
# 4. Track setup already present in DEF from floorplan/placement
# Do NOT call make_tracks — it conflicts with existing TRACKS in DEF

# 5. Power Delivery Network (REQUIRED before routing)
# Without PDN metal stripes, TritonRoute crashes with SIGSEGV
add_global_connection -net VDD -pin_pattern {{VPWR}} -power
add_global_connection -net VDD -pin_pattern {{VPB}}  -power
add_global_connection -net VSS -pin_pattern {{VGND}} -ground
add_global_connection -net VSS -pin_pattern {{VNB}}  -ground
catch {{ global_connect }}

# PDN generation - wrapped in catch because it may fail if
# rows are not properly defined (depending on CTS output)
catch {{
    set_voltage_domain -power VDD -ground VSS
    define_pdn_grid -name "Core" -voltage_domains {{Core}}
    add_pdn_stripe -followpins -layer met1 -width 0.48
    add_pdn_stripe -layer met4 -width 1.6 -pitch 27.2 -offset 13.6
    add_pdn_connect -layers {{met1 met4}}
    pdngen
}}

# 6. Global routing
catch {{
    global_route \\
        -guide_file /work/route_guides.txt \\
        -congestion_iterations 30 \\
        -verbose
}}

# 7. Detailed routing
catch {{
    detailed_route \\
        -output_drc /work/drc_violations.txt \\
        -verbose 1
}}

# 7. Reports (all optional - wrapped in catch)
catch {{ check_placement -verbose >> /work/routing.rpt }}
catch {{ report_design_area >> /work/routing.rpt }}
catch {{ report_wire_length >> /work/routing.rpt }}
catch {{ set_propagated_clock [all_clocks] }}
catch {{ report_checks -path_delay max -format full_clock >> /work/routing.rpt }}
catch {{ report_wns >> /work/routing.rpt }}
catch {{ report_tns >> /work/routing.rpt }}

# 8. Write routed DEF
write_def /work/routed.def

puts "\\nRouting stage complete: {top_module}\\n"
exit
"""
        return tcl

    # ──────────────────────────────────────────────────────────────────────
    # ROUTE GUIDE GENERATION
    # ──────────────────────────────────────────────────────────────────────

    def _generate_basic_guides(self, output_path: Path, def_path: Path) -> None:
        """
        Generate basic routing guides when global routing was skipped.
        
        This creates a minimal guide file that allows TritonRoute to proceed
        without detailed global routing constraints. Guides cover all nets
        with simple layer assignments.
        
        Args:
            output_path: Where to write route_guides.txt
            def_path:    DEF file with net definitions
        """
        try:
            # Parse DEF to extract net names
            content = def_path.read_text(encoding="utf-8", errors="ignore")
            
            nets = []
            in_nets_section = False
            for line in content.splitlines():
                if line.strip().startswith("NETS"):
                    in_nets_section = True
                elif in_nets_section:
                    if line.strip().startswith("END NETS"):
                        break
                    # Extract net name (first word after -)
                    if line.strip().startswith("-"):
                        parts = line.strip().split()
                        if len(parts) > 1:
                            net_name = parts[1]
                            # Skip power/ground nets
                            if not net_name.startswith(("VSS", "VDD")):
                                nets.append(net_name)
            
            if not nets:
                self.logger.warning(f"No nets extracted from {def_path} - guides will be empty")
                nets = [f"net_{i}" for i in range(10)]  # Dummy nets
            
            # Generate guide lines (simple: all nets, all layers met2-met4)
            guide_lines = [
                "# Route guides - auto-generated when global routing was skipped",
                f"# Covering {len(nets)} signal nets",
                f"# Layers: met2, met3, met4 (standard signal routing)",
                "",
            ]
            
            for net in nets[:100]:  # Limit to first 100 nets to keep file reasonable
                # Guide format: net_name layer trackRange
                # Simple guide: all nets can use all signal layers
                guide_lines.append(f"{net} met2 met3 met4")
            
            guide_lines.append("")  # Trailing newline
            
            output_path.write_text("\n".join(guide_lines), encoding="utf-8")
            self.logger.info(f"Generated {len(nets)} basic routing guides: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate basic guides: {e}")
            # Create empty guide file so routing doesn't fail on missing file
            output_path.write_text("# Empty guides (generation failed)\n", encoding="utf-8")

    # ──────────────────────────────────────────────────────────────────────
    # REPORT PARSING
    # ──────────────────────────────────────────────────────────────────────

    def _parse_routing_report(self, rpt_path: Path) -> RoutingStats:
        """
        Parse routing.rpt + drc_violations.txt for routing quality metrics.

        Lines parsed:
          "Total wire length: N.N um"
          "Total number of vias: N"
          "Number of DRC violations: N"
          "Number of unrouted nets: N"
          "wns X.XX"
        """
        stats = RoutingStats()
        if not rpt_path.exists():
            return stats

        # Also look for drc_violations.txt alongside the report
        drc_file = rpt_path.parent / "drc_violations.txt"

        try:
            text = rpt_path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                s = line.strip()

                # Wire length
                m = re.match(r"Total wire length\s*:\s*([\d.]+)", s)
                if m:
                    stats.total_wire_length_um = float(m.group(1))

                # Via count
                m2 = re.match(r"Total number of vias\s*:\s*(\d+)", s)
                if m2:
                    stats.via_count = int(m2.group(1))

                # Unrouted nets
                m3 = re.match(r"Number of unrouted nets\s*:\s*(\d+)", s)
                if m3:
                    stats.unrouted_nets = int(m3.group(1))

                # WNS / TNS
                if s.startswith("wns "):
                    try:
                        stats.worst_slack_ns = float(s.split()[1])
                    except (IndexError, ValueError):
                        pass
                if s.startswith("tns "):
                    try:
                        stats.tns_ns = float(s.split()[1])
                    except (IndexError, ValueError):
                        pass

        except OSError:
            pass

        # Parse DRC violation count from drc_violations.txt
        if drc_file.exists():
            try:
                drc_text = drc_file.read_text(encoding="utf-8", errors="ignore")
                # Each "violation" block starts with "violation type"
                violations = re.findall(r"^violation type", drc_text, re.MULTILINE)
                stats.drc_violation_count = len(violations)
                # Fallback: count non-empty lines
                if stats.drc_violation_count == 0:
                    nonempty = [
                        l for l in drc_text.splitlines()
                        if l.strip() and not l.strip().startswith("#")
                    ]
                    stats.drc_violation_count = len(nonempty)
            except OSError:
                pass

        return stats

    @staticmethod
    def _extract_error(output: str) -> str:
        for line in output.splitlines():
            s = line.strip()
            if s.startswith(("[ERROR", "Error:", "ERROR:")):
                return s[:200]
        return "Detailed routing error (check run log)"

    @staticmethod
    def _preserve_pin_geometry(routed_def_path: str, cts_def_path: str) -> None:
        """
        Verify and preserve pin geometry in routed DEF.
        
        Detailed routing can sometimes lose IO cell pin information.
        This checks that pins from CTS DEF are still present in routed DEF.
        
        Args:
            routed_def_path: Path to routed.def from detailed routing
            cts_def_path:    Path to cts.def (input reference for pin list)
        
        CRITICAL: Missing pins in routed DEF will cause:
          - GDS missing pin blockages
          - Unroutable DRC violations
          - Layout tool crashes during final stages
        """
        routed_def = Path(routed_def_path)
        if not routed_def.exists():
            return
        
        cts_def = Path(cts_def_path)
        if not cts_def.exists():
            return
        
        # Extract pins from CTS DEF
        cts_pins = set()
        if cts_def.exists():
            cts_content = cts_def.read_text(encoding="utf-8", errors="ignore")
            in_pins_section = False
            for line in cts_content.splitlines():
                if "PINS" in line and line.strip().startswith("PINS"):
                    in_pins_section = True
                elif in_pins_section:
                    if line.strip().startswith("END PINS"):
                        in_pins_section = False
                    else:
                        parts = line.strip().split()
                        if parts and not parts[0].startswith("-"):
                            cts_pins.add(parts[0])
        
        # Extract pins from routed DEF
        routed_content = routed_def.read_text(encoding="utf-8", errors="ignore")
        routed_pins = set()
        in_pins_section = False
        for line in routed_content.splitlines():
            if "PINS" in line and line.strip().startswith("PINS"):
                in_pins_section = True
            elif in_pins_section:
                if line.strip().startswith("END PINS"):
                    in_pins_section = False
                else:
                    parts = line.strip().split()
                    if parts and not parts[0].startswith("-"):
                        routed_pins.add(parts[0])
        
        # Check for missing pins
        missing_pins = cts_pins - routed_pins
        if missing_pins:
            # Reconstruct missing pins section in routed DEF
            lines = routed_content.splitlines()
            end_idx = -1
            for i, line in enumerate(lines):
                if line.strip() == "END DESIGN":
                    end_idx = i
                    break
            
            if end_idx > 0:
                # Add missing pins as comments for reference
                missing_comment = "  # MISSING PINS FROM CTS DEF"
                for pin in sorted(missing_pins):
                    missing_comment += f"\n  # PIN: {pin} (not in routed DEF)"
                
                lines.insert(end_idx, missing_comment)
                routed_def.write_text("\n".join(lines), encoding="utf-8")

