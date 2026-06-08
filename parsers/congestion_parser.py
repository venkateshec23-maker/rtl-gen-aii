"""
congestion_parser.py — OpenROAD global route congestion report parser.
Converts congestion_report.txt into DesignDB CongestionData.

Report format (OpenROAD report_congestion):
  Overflow : <value>%
  Max density : <value>%
  ...
  Also handles:
  - report_design_area output appended to same file
  - CONGESTION_NOT_AVAILABLE marker
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class CongestionSummary:
    h_overflow_pct: Optional[float] = None
    v_overflow_pct: Optional[float] = None
    max_density_pct: Optional[float] = None
    utilization_pct: Optional[float] = None
    unrouted_nets: int = 0
    total_nets: Optional[int] = None
    available: bool = False
    overflow_score: Optional[float] = None
    design_area_um2: Optional[float] = None


def parse_congestion_report(text: str) -> CongestionSummary:
    """
    Parse OpenROAD congestion report.
    Handles both global_route congestion output and report_design_area.
    """
    result = CongestionSummary()

    if "CONGESTION_NOT_AVAILABLE" in text:
        return result

    has_data = False

    for line in text.splitlines():
        l = line.strip()

        # Global route overflow
        m = re.search(r"Overflow\s*:\s*([\d.]+)%", l, re.IGNORECASE)
        if m:
            result.h_overflow_pct = float(m.group(1))
            result.v_overflow_pct = float(m.group(1))
            has_data = True
            continue

        # Per-direction overflow if present
        m = re.search(r"Horizontal\s+overflow\s*:\s*([\d.]+)%", l, re.IGNORECASE)
        if m:
            result.h_overflow_pct = float(m.group(1))
        m = re.search(r"Vertical\s+overflow\s*:\s*([\d.]+)%", l, re.IGNORECASE)
        if m:
            result.v_overflow_pct = float(m.group(1))

        # Max density
        m = re.search(r"Max\s+density\s*:\s*([\d.]+)%", l, re.IGNORECASE)
        if m:
            result.max_density_pct = float(m.group(1))

        # Congestion score
        m = re.search(r"Score\s*:\s*([\d.]+)", l, re.IGNORECASE)
        if m:
            result.overflow_score = float(m.group(1))

        # Design area
        m = re.search(
            r"Design\s+area\s+([\d.]+)\s+u\^2\s+([\d.]+)%\s+utilization",
            l, re.IGNORECASE,
        )
        if m:
            result.design_area_um2 = float(m.group(1))
            result.utilization_pct = float(m.group(2))

        # Unrouted nets
        m = re.search(r"Unrouted\s*(nets?)?\s*:\s*(\d+)", l, re.IGNORECASE)
        if m:
            result.unrouted_nets = int(m.group(2))

        # Total nets
        m = re.search(r"Total\s+nets?\s*:\s*(\d+)", l, re.IGNORECASE)
        if m:
            result.total_nets = int(m.group(1))

        # Mark data found for non-continue matched fields
        if re.search(r"(Horizontal|Vertical|Max density|Design area|Unrouted|Score)", l, re.IGNORECASE):
            has_data = True

    result.available = has_data or any([
        result.h_overflow_pct is not None,
        result.v_overflow_pct is not None,
        result.max_density_pct is not None,
        result.design_area_um2 is not None,
        result.overflow_score is not None,
    ])

    # Compute congestion score (0-100, higher = worse)
    if result.h_overflow_pct is not None or result.v_overflow_pct is not None:
        h = result.h_overflow_pct or 0
        v = result.v_overflow_pct or 0
        result.overflow_score = min(100, round((h + v) * 5, 1))

    return result


def congestion_to_design_db(cs: CongestionSummary):
    """Convert CongestionSummary to DesignDB CongestionData."""
    from design_db import CongestionData
    if not cs.available:
        return None
    cd = CongestionData(
        h_overflow_pct=cs.h_overflow_pct,
        v_overflow_pct=cs.v_overflow_pct,
        max_density_pct=cs.max_density_pct,
        utilization_pct=cs.utilization_pct,
        unrouted_nets=cs.unrouted_nets,
    )
    cd.compute_score()
    return cd
