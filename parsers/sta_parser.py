"""
sta_parser.py — OpenROAD/OpenSTA timing report parser.
Converts sta_final.txt / sta_{corner}.txt into DesignDB TimingData/TimingCorner.

Report format (OpenROAD report_checks):
  Startpoint: <name>
  Endpoint: <name>
  Path type: max/min
  -------------------------------------------------------------------------
  |  Cell type     |  Delay  |  Time  |  Edge  |  Net  |  Pin
  -------------------------------------------------------------------------
  <cell>            <d>      <t>      <e>      <n>     <p>
  slack (MET|VIOLATED)  <value>
  ...

Also handles:
  report_wns:  wns <value>
  report_tns:  tns <value>
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


@dataclass
class STAPathCell:
    delay: float = 0.0
    time: float = 0.0
    edge: str = ""
    net: str = ""
    pin: str = ""
    cell: str = ""


@dataclass
class STAPath:
    startpoint: str = ""
    endpoint: str = ""
    path_type: str = "max"
    slack_ns: float = 0.0
    met: bool = True
    cells: List[STAPathCell] = field(default_factory=list)


@dataclass
class STACorner:
    corner: str = "TT"
    wns_ns: Optional[float] = None
    tns_ns: Optional[float] = None
    slack_ns: Optional[float] = None
    met: bool = False
    paths: List[STAPath] = field(default_factory=list)


@dataclass
class STASummary:
    corners: Dict[str, STACorner] = field(default_factory=dict)
    preroute: Optional[STACorner] = None
    postroute: Optional[STACorner] = None
    signoff: Optional[STACorner] = None
    timing_degradation_ns: Optional[float] = None


def _find_slack(line: str) -> Optional[Tuple[float, bool]]:
    """Parse 'slack (MET|VIOLATED)  <value>' or '<value> slack (MET|VIOLATED)'."""
    m = re.search(r"slack\s+\((MET|VIOLATED)\)\s+([-\d.]+)", line)
    if m:
        return float(m.group(2)), m.group(1) == "MET"
    m = re.search(r"([-\d.]+)\s+slack\s+\((MET|VIOLATED)\)", line)
    if m:
        return float(m.group(1)), m.group(2) == "MET"
    return None


def _find_wns(line: str) -> Optional[float]:
    m = re.search(r"wns\s+([-\d.]+)", line)
    if m:
        return float(m.group(1))
    return None


def _find_tns(line: str) -> Optional[float]:
    m = re.search(r"tns\s+([-\d.]+)", line)
    if m:
        return float(m.group(1))
    return None


def _parse_path_block(lines: List[str]) -> Optional[STAPath]:
    """Parse a single timing path block from report_checks output."""
    if not lines:
        return None
    path = STAPath()
    for i, line in enumerate(lines):
        l = line.strip()
        if l.startswith("Startpoint:"):
            path.startpoint = l.split(":", 1)[1].strip()
        elif l.startswith("Endpoint:"):
            path.endpoint = l.split(":", 1)[1].strip()
        elif l.startswith("Path type:"):
            path.path_type = l.split(":", 1)[1].strip().lower()
        elif "slack" in l.lower() and ("(MET" in l or "(VIOLATED" in l):
            r = _find_slack(l)
            if r:
                path.slack_ns, path.met = r
        else:
            # Cell delay line: <cell>  <delay>  <time>  <edge>  <net>  <pin>
            cols = l.split()
            if len(cols) >= 3 and cols[0].startswith("sky130"):
                cell = STAPathCell()
                cell.cell = cols[0]
                try:
                    if len(cols) >= 2:
                        cell.delay = float(cols[1])
                    if len(cols) >= 3:
                        cell.time = float(cols[2])
                except ValueError:
                    pass
                if len(cols) >= 4:
                    cell.edge = cols[3]
                if len(cols) >= 5:
                    cell.net = cols[4]
                if len(cols) >= 6:
                    cell.pin = cols[5]
                path.cells.append(cell)
    return path


def parse_sta_corner(text: str, corner_name: str = "TT") -> STACorner:
    """
    Parse a single STA corner report.
    Returns STACorner with paths, WNS, TNS.
    """
    corner = STACorner(corner=corner_name)
    lines = text.splitlines()
    i = 0
    path_lines: List[str] = []
    in_path = False

    while i < len(lines):
        line = lines[i]

        # Check for WNS/TNS
        wns = _find_wns(line)
        tns = _find_tns(line)
        if wns is not None:
            corner.wns_ns = wns
            if corner.slack_ns is None:
                corner.slack_ns = wns
                corner.met = wns >= 0
        if tns is not None:
            corner.tns_ns = tns

        # Standalone slack (overall corner slack outside path blocks)
        sr = _find_slack(line)
        if sr is not None:
            corner.slack_ns, corner.met = sr

        # Track path blocks
        if line.strip().startswith("Startpoint:"):
            if path_lines:
                p = _parse_path_block(path_lines)
                if p:
                    corner.paths.append(p)
            path_lines = [line]
            in_path = True
        elif in_path:
            # End of a path block: blank line or new section
            if line.strip() == "" and path_lines:
                p = _parse_path_block(path_lines)
                if p:
                    corner.paths.append(p)
                path_lines = []
                in_path = False
            else:
                path_lines.append(line)

        i += 1

    # Last path
    if path_lines:
        p = _parse_path_block(path_lines)
        if p:
            corner.paths.append(p)

    return corner


def parse_sta_report(
    text: str,
    preroute_text: Optional[str] = None,
    postroute_text: Optional[str] = None,
    signoff_text: Optional[str] = None,
) -> STASummary:
    """
    Parse STA report(s) and return STASummary.
    Supports pre-route, post-route, and signoff (post-SPEF) timing.
    """
    summary = STASummary()

    # Primary TT corner
    if text:
        summary.corners["TT"] = parse_sta_corner(text, "TT")

    # Optional pre-route and post-route
    if preroute_text:
        summary.preroute = parse_sta_corner(preroute_text, "PREROUTE")
    if postroute_text:
        summary.postroute = parse_sta_corner(postroute_text, "POSTROUTE")
    if signoff_text:
        summary.signoff = parse_sta_corner(signoff_text, "SIGNOFF")

    # Compute timing degradation (post-route vs signoff)
    tt = summary.corners.get("TT")
    sf = summary.signoff
    if tt and sf and tt.slack_ns is not None and sf.slack_ns is not None:
        summary.timing_degradation_ns = round(tt.slack_ns - sf.slack_ns, 4)

    return summary


def convert_to_design_db_timing(summary: STASummary, period_ns: float = 10.0):
    """
    Convert STASummary into the DesignDB TimingData format.
    """
    from design_db import TimingData, TimingCorner, TimingPath

    corners = {}
    for name, sc in summary.corners.items():
        tc = TimingCorner(
            corner=sc.corner,
            slack_ns=sc.slack_ns,
            met=sc.met,
        )
        for sp in sc.paths:
            # Convert path cells
            from design_db import TimingPathCell
            cells = [
                TimingPathCell(
                    delay=c.delay, time=c.time, edge=c.edge,
                    net=c.net, pin=c.pin, cell=c.cell,
                )
                for c in sp.cells
            ]
            tp = TimingPath(
                startpoint=sp.startpoint,
                endpoint=sp.endpoint,
                path_type=sp.path_type,
                slack_ns=sp.slack_ns,
                met=sp.met,
                total_delay=sum(c.delay for c in sp.cells),
            )
            tp.cells = cells
            tc.paths.append(tp)
        corners[name] = tc

    tt = summary.corners.get("TT")
    hold_slack = None
    fmax = None
    if tt and tt.slack_ns is not None:
        margin = period_ns - tt.slack_ns
        if margin > 0:
            fmax = round(1000.0 / margin, 1)

    td = TimingData(
        period_ns=period_ns,
        corners=corners,
        fmax_mhz=fmax,
        hold_slack_ns=hold_slack,
    )

    return td
