"""
drc_parser.py — Magic/OpenROAD DRC report parser.
Converts drc_report.txt / klayout_drc.xml into DesignDB DRCCheck.

Report formats:
  Magic: "DRC violations: <count>"
  KLayout XML: structured violation XML
  OpenROAD: "Found <count> DRC violations"
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


@dataclass
class DRCViolation:
    rule: str = ""
    layer: str = ""
    x: float = 0.0
    y: float = 0.0
    description: str = ""


@dataclass
class DRCSummary:
    total_violations: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)
    violations: List[DRCViolation] = field(default_factory=list)
    engine: str = "magic"  # "magic", "klayout", "openroad"
    clean: bool = True
    coordinates: List[Tuple[float, float, float, float]] = field(default_factory=list)


def parse_drc_report(text: str, engine: str = "magic") -> DRCSummary:
    """
    Parse DRC report text.
    Supports Magic, KLayout text, and OpenROAD formats.
    """
    result = DRCSummary(engine=engine)

    # Magic format: "DRC violations: <count>"
    m = re.search(r"DRC\s+violations?\s*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        result.total_violations = int(m.group(1))
        result.clean = result.total_violations == 0

    # OpenROAD format: "Found <count> DRC violations", "<count> violations found"
    if result.total_violations == 0:
        m = re.search(r"Found\s+(\d+)\s+DRC\s+violations?", text, re.IGNORECASE)
        if m:
            result.total_violations = int(m.group(1))
            result.clean = result.total_violations == 0
            result.engine = "openroad"

    if result.total_violations == 0:
        m = re.search(r"(\d+)\s+violations?\s+found", text, re.IGNORECASE)
        if m:
            result.total_violations = int(m.group(1))
            result.clean = result.total_violations == 0
            result.engine = "openroad"

    # Extract per-category violations from detail lines
    # Pattern: "<rule> : <count>" or "<layer>: <count> violation(s)"
    cat_pattern = re.compile(
        r"([A-Za-z0-9_./]+)\s*:\s*(\d+)\s+violation", re.IGNORECASE
    )
    for m in cat_pattern.finditer(text):
        cat = m.group(1).strip()
        cnt = int(m.group(2))
        result.by_category[cat] = result.by_category.get(cat, 0) + cnt

    # Extract individual violation coordinates
    # Pattern: "Violation at (<x>,<y>)" or "@ (<x>,<y>)"
    coord_pattern = re.compile(
        r"(?:Violation\s+at|@)\s*\(?\s*([\d.]+)\s*[,:]\s*([\d.]+)\s*\)?"
    )
    for m in coord_pattern.finditer(text):
        try:
            x, y = float(m.group(1)), float(m.group(2))
            result.coordinates.append((x, y, x, y))
        except ValueError:
            pass

    # Pattern: "bbox (<x1>,<y1>) (<x2>,<y2>)"
    bbox_pattern = re.compile(
        r"bbox\s*\(([\d.]+),([\d.]+)\)\s*\(([\d.]+),([\d.]+)\)"
    )
    for m in bbox_pattern.finditer(text):
        try:
            x1, y1, x2, y2 = (float(m.group(i)) for i in range(1, 5))
            result.coordinates.append((x1, y1, x2, y2))
        except ValueError:
            pass

    return result


def parse_klayout_drc(xml_text: str) -> DRCSummary:
    """
    Parse KLayout DRC XML output.
    KLayout XML format:
      <drc-report>
        <violation rule="..." layer="..." x="..." y="..." description="..."/>
      </drc-report>
    """
    result = DRCSummary(engine="klayout")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        log.warning("KLayout DRC XML parse error; falling back to text parsing")
        return parse_drc_report(xml_text, engine="klayout")

    ns = {"k": "http://www.klayout.de/drc_report"}
    violations = root.findall(".//k:violation", ns)
    if not violations:
        violations = root.iter("violation")
    for v in violations:
        dv = DRCViolation(
            rule=v.get("rule", ""),
            layer=v.get("layer", ""),
            x=float(v.get("x", 0)),
            y=float(v.get("y", 0)),
            description=v.get("description", ""),
        )
        result.violations.append(dv)
        cat = dv.rule or dv.layer
        result.by_category[cat] = result.by_category.get(cat, 0) + 1

    result.total_violations = len(result.violations)
    result.clean = result.total_violations == 0
    return result


def drc_to_design_db(ds: DRCSummary):
    """Convert DRCSummary to DesignDB DRCCheck."""
    from design_db import DRCCheck
    return DRCCheck(
        violations=ds.total_violations,
        categories=ds.by_category,
        coordinates=ds.coordinates,
    )
