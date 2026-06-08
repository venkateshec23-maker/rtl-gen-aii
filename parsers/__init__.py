"""
parsers — OpenROAD report parsers for RTL-Gen AI Phase 10.
Each parser converts a raw tool report into a DesignDB-compatible dataclass.
Robust parsing with graceful malformed-report handling.
"""

from .sta_parser import parse_sta_report, parse_sta_corner
from .power_parser import parse_power_report
from .congestion_parser import parse_congestion_report
from .drc_parser import parse_drc_report, parse_klayout_drc
from .lvs_parser import parse_lvs_report
from .metrics_parser import AggregateMetrics, collect_all_metrics

__all__ = [
    "parse_sta_report", "parse_sta_corner",
    "parse_power_report",
    "parse_congestion_report",
    "parse_drc_report", "parse_klayout_drc",
    "parse_lvs_report",
    "AggregateMetrics", "collect_all_metrics",
]
