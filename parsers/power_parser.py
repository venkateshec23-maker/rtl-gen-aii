"""
power_parser.py — OpenROAD report_power parser.
Converts power_report.txt into DesignDB PowerData.

Report format:
  -------------------------------------------------------------------------
  | Group      | Internal  | Switching | Leakage   | Total
  | (power in W)
  -------------------------------------------------------------------------
  | Sequential | <internal>| <switching>| <leakage>| <total>
  | Combinational| ...     |           |          |
  | Macro      | ...       |           |          |
  | Pad        | ...       |           |          |
  | Total      | <internal>| <switching>| <leakage>| <total>
  -------------------------------------------------------------------------
  Design area <value> u^2 <value>% utilization

Also handles:
  - report_power -corner {tt,ss,ff}
  - Corner-specific reports
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class PowerGroup:
    name: str = ""
    internal_w: float = 0.0
    switching_w: float = 0.0
    leakage_w: float = 0.0
    total_w: float = 0.0


@dataclass
class PowerSummary:
    total_power_mw: Optional[float] = None
    dynamic_power_mw: Optional[float] = None
    static_power_mw: Optional[float] = None
    core_area_um2: Optional[float] = None
    utilization_pct: Optional[float] = None
    groups: List[PowerGroup] = field(default_factory=list)
    corner: str = "tt"


def parse_power_report(text: str, corner: str = "tt") -> PowerSummary:
    """
    Parse OpenROAD report_power output.
    Returns PowerSummary with structured data.
    """
    result = PowerSummary(corner=corner)
    lines = text.splitlines()

    # Master pattern for power rows:
    # Group  Internal  Switching  Leakage  Total  (all in Watts)
    # Total  <val>     <val>      <val>    <val>
    power_pattern = re.compile(
        r"^\s*(Total|Sequential|Combinational|Macro|Pad)\s+"
        r"([\d.eE+-]+)\s+([\d.eE+-]+)\s+"
        r"([\d.eE+-]+)\s+([\d.eE+-]+)"
    )

    for line in lines:
        # Total power row
        m = re.search(
            r"Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+"
            r"([\d.eE+-]+)\s+([\d.eE+-]+)",
            line,
        )
        if m:
            internal = float(m.group(1))
            switching = float(m.group(2))
            leakage = float(m.group(3))
            total = float(m.group(4))

            result.total_power_mw = round(total * 1000, 4)
            result.dynamic_power_mw = round((internal + switching) * 1000, 4)
            result.static_power_mw = round(leakage * 1000, 6)
            continue

        # Design area
        m = re.search(
            r"Design area\s+([\d.]+)\s+u\^2\s+([\d.]+)%\s+utilization",
            line,
        )
        if m:
            result.core_area_um2 = float(m.group(1))
            result.utilization_pct = float(m.group(2))
            continue

        # Per-group power (for detail)
        pm = power_pattern.match(line)
        if pm:
            g = PowerGroup(
                name=pm.group(1),
                internal_w=float(pm.group(2)),
                switching_w=float(pm.group(3)),
                leakage_w=float(pm.group(4)),
                total_w=float(pm.group(5)),
            )
            result.groups.append(g)

    # Fallback: try to find any power values if pattern didn't match
    if result.total_power_mw is None:
        # Look for "Total power = <value>"
        m = re.search(r"Total\s+power\s*=\s*([\d.eE+-]+)\s*([mu]?)W", text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            unit = m.group(2).lower()
            if unit == "m":
                result.total_power_mw = val
            elif unit == "u":
                result.total_power_mw = val / 1000
            else:
                result.total_power_mw = val * 1000  # assume Watts

        # Try simpler "Internal + Switching + Leakage = Total" format
        m = re.search(
            r"([\d.eE+-]+)\s*\+\s*([\d.eE+-]+)\s*\+\s*([\d.eE+-]+)\s*=\s*([\d.eE+-]+)",
            text,
        )
        if m and result.total_power_mw is None:
            result.total_power_mw = round(float(m.group(4)) * 1000, 4)
            result.dynamic_power_mw = round((float(m.group(1)) + float(m.group(2))) * 1000, 4)
            result.static_power_mw = round(float(m.group(3)) * 1000, 6)

    return result


def power_summary_to_dict(ps: PowerSummary) -> dict:
    """Convert PowerSummary to a plain dict for DesignDB consumption."""
    return {
        "total_power_mw": ps.total_power_mw,
        "dynamic_power_mw": ps.dynamic_power_mw,
        "static_power_mw": ps.static_power_mw,
        "core_area_um2": ps.core_area_um2,
        "utilization_pct": ps.utilization_pct,
        "corner": ps.corner,
        "groups": [{"name": g.name, "internal_w": g.internal_w,
                     "switching_w": g.switching_w, "leakage_w": g.leakage_w,
                     "total_w": g.total_w} for g in ps.groups],
    }
