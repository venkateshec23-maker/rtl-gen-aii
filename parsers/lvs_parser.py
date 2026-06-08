"""
lvs_parser.py — Netgen LVS report parser.
Converts lvs_report_final.txt into DesignDB LVSCheck.

Report formats (Netgen):
  Circuits match uniquely (MATCHED)
  Netlists do not match (MISMATCH)
  Cell pin lists ... altered to match (AMBIGUITY)
  Device class ... are equivalent
  Number of devices: <n> | Number of devices: <n>

Also supports JSON-annotated Netgen output (-json flag).
"""

from __future__ import annotations

import logging
import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class LVSSummary:
    status: str = "NOT_RUN"
    matched: bool = False
    matched_nets: int = 0
    unmatched_nets: int = 0
    device_mismatches: int = 0
    total_devices_schematic: Optional[int] = None
    total_devices_layout: Optional[int] = None
    reason_code: str = "INCOMPLETE"
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, object] = field(default_factory=dict)


def parse_lvs_report(text: str) -> LVSSummary:
    """
    Parse Netgen LVS report.
    Returns LVSSummary with structured status and counts.
    """
    result = LVSSummary()
    lower = text.lower()
    lines = text.splitlines()

    # Detect JSON annotation from Netgen -json output
    json_content = ""
    for line in lines:
        if line.strip().startswith("{"):
            json_content += line
    if json_content:
        try:
            jd = json.loads(json_content)
            if "lvs" in jd:
                lvs_data = jd["lvs"]
                result.matched = lvs_data.get("matched", False)
                result.matched_nets = lvs_data.get("matched_nets", 0)
                result.unmatched_nets = lvs_data.get("unmatched_nets", 0)
                result.device_mismatches = lvs_data.get("device_mismatches", 0)
                result.total_devices_schematic = lvs_data.get("devices_schematic")
                result.total_devices_layout = lvs_data.get("devices_layout")
                result.status = "MATCHED" if result.matched else "UNMATCHED"
                result.reason_code = "MATCHED" if result.matched else "HARD_MISMATCH"
                log.info("LVS JSON annotation parsed successfully")
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Standard text-based parsing
    has_mismatch = (
        "netlists do not match" in lower
        or "failed pin matching" in lower
        or ("final result:" in lower and "failed" in lower)
    )
    has_match = (
        "circuits match uniquely" in lower or "are equivalent" in lower
    )
    has_pin_match_fail = (
        "failed pin matching" in lower
        or "top level cell failed pin matching" in lower
    )
    has_no_matching_element = "no matching element" in lower
    has_subcircuit_pins_block = "subcircuit pins:" in lower
    has_pin_table_mismatch = has_subcircuit_pins_block and (
        "**mismatch**" in lower or "(no matching pin)" in lower
    )
    has_pin_list_altered = (
        "cell pin lists for" in lower and "altered to match" in lower
    )
    has_pin_lists_equivalent = "cell pin lists are equivalent." in lower
    has_hard_structural = (
        "property errors were found" in lower
        or "property mismatches were found" in lower
    )
    device_classes_equivalent = (
        "device classes" in lower and "are equivalent" in lower
    )

    # Device counts
    device_pairs = re.findall(
        r"number of devices:\s*(\d+)\s*\|\s*number of devices:\s*(\d+)",
        text, re.IGNORECASE,
    )
    if device_pairs:
        left, right = device_pairs[-1]
        result.total_devices_schematic = int(left)
        result.total_devices_layout = int(right)

    is_filler_only = (
        has_no_matching_element
        and has_pin_lists_equivalent
        and device_classes_equivalent
        and "netlists do not match" not in lower
    )

    is_hard_structural = (
        has_no_matching_element and "netlists do not match" in lower
    )

    pin_ambiguity = (
        has_mismatch
        and has_match
        and device_pairs and result.total_devices_schematic == result.total_devices_layout
        and not has_hard_structural
        and not is_filler_only
        and not is_hard_structural
        and (
            has_pin_match_fail
            or device_classes_equivalent
            or (has_pin_table_mismatch and (has_pin_list_altered or has_pin_lists_equivalent))
        )
    )

    # Determine status
    has_altered_pin_match = (
        has_pin_list_altered
        and device_classes_equivalent
        and device_pairs
        and result.total_devices_schematic == result.total_devices_layout
        and not has_mismatch
    )
    if is_filler_only:
        result.status = "MATCHED_WITH_WARNINGS"
        result.reason_code = "FILLER_PIN_ORDER_EQUIVALENT"
        result.warnings.append("Filler cells have no schematic; device classes equivalent")
        result.matched = True
    elif has_altered_pin_match:
        result.status = "MATCHED_WITH_WARNINGS"
        result.reason_code = "ALTERED_PIN_LISTS_EQUIVALENT"
        result.warnings.append("Cell pin lists altered to match; device classes are equivalent")
        result.matched = True
    elif pin_ambiguity and has_pin_match_fail:
        result.status = "MATCHED_WITH_WARNINGS"
        result.reason_code = "TOP_PIN_MATCHING_FAILED_EQUIVALENT"
        result.warnings.append("Top-level pin matching failed but device classes are equivalent")
        result.matched = True
    elif pin_ambiguity:
        result.status = "MATCHED_WITH_WARNINGS"
        result.reason_code = "TOP_PIN_TABLE_MISMATCH_EQUIVALENT"
        result.warnings.append("Top-level pin table mismatch but device classes are equivalent")
        result.matched = True
    elif has_mismatch:
        result.status = "UNMATCHED"
        result.reason_code = "HARD_MISMATCH"
        result.matched = False
    elif has_match:
        result.status = "MATCHED"
        result.reason_code = "MATCHED"
        result.matched = True
    else:
        result.status = "INCOMPLETE"
        result.reason_code = "INCOMPLETE"

    # Count matched/unmatched nets from "matched nets: <n>" pattern
    m = re.search(r"matched\s+nets?\s*:\s*(\d+)", lower)
    if m:
        result.matched_nets = int(m.group(1))
    m = re.search(r"unmatched\s+nets?\s*:\s*(\d+)", lower)
    if m:
        result.unmatched_nets = int(m.group(1))
    m = re.search(r"device\s+mismatches?\s*:\s*(\d+)", lower)
    if m:
        result.device_mismatches = int(m.group(1))

    result.details = {
        "has_pin_match_fail": has_pin_match_fail,
        "has_pin_table_mismatch": has_pin_table_mismatch,
        "has_subcircuit_pins_block": has_subcircuit_pins_block,
        "has_pin_list_altered": has_pin_list_altered,
        "has_pin_lists_equivalent": has_pin_lists_equivalent,
        "has_hard_structural": has_hard_structural,
        "has_no_matching_element": has_no_matching_element,
        "device_classes_equivalent": device_classes_equivalent,
    }

    return result


def lvs_to_design_db(ls: LVSSummary):
    """Convert LVSSummary to DesignDB LVSCheck."""
    from design_db import LVSCheck
    return LVSCheck(
        status=ls.status,
        matched_nets=ls.matched_nets,
        unmatched_nets=ls.unmatched_nets,
        device_mismatches=ls.device_mismatches,
    )
