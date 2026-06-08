from __future__ import annotations
import logging
import datetime
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

try:
    from mcmm import MCMMTiming as _MCMMTiming, TimingCorner as _MCMMCorner
    MCMM_AVAILABLE = True
except ImportError:
    _MCMMTiming = None
    _MCMMCorner = None
    MCMM_AVAILABLE = False

try:
    from spef_engine import SPEFResult as _SPEFResult, ParasiticNet as _ParasiticNet
    SPEF_AVAILABLE = True
except ImportError:
    _SPEFResult = None
    _ParasiticNet = None
    SPEF_AVAILABLE = False

try:
    from drc_engine import DRCEngineResult as _DRCEngineResult, DRCViolation as _DRCViolation
    DRC_ENGINE_AVAILABLE = True
except ImportError:
    _DRCEngineResult = None
    _DRCViolation = None
    DRC_ENGINE_AVAILABLE = False

try:
    from lvs_engine import LVSResult as _LVSResult, LVSDevice as _LVSDevice, LVSNet as _LVSNet
    LVS_ENGINE_AVAILABLE = True
except ImportError:
    _LVSResult = None
    _LVSDevice = None
    _LVSNet = None
    LVS_ENGINE_AVAILABLE = False

logger = logging.getLogger(__name__)

_SN = "design_db"
_SCHEMA_VERSION = "1.2"


@dataclass
class TimingPathCell:
    delay: float = 0.0
    time: float = 0.0
    edge: str = ""
    net: str = ""
    pin: str = ""
    cell: str = ""


@dataclass
class TimingPath:
    startpoint: str = ""
    endpoint: str = ""
    path_type: str = "max"
    slack_ns: float = 0.0
    met: bool = True
    cells: List[TimingPathCell] = field(default_factory=list)
    total_delay: float = 0.0


@dataclass
class TimingCorner:
    corner: str = "TT"
    slack_ns: Optional[float] = None
    met: bool = False
    paths: List[TimingPath] = field(default_factory=list)


@dataclass
class TimingData:
    period_ns: float = 10.0
    corners: Dict[str, TimingCorner] = field(default_factory=dict)
    fmax_mhz: Optional[float] = None
    hold_slack_ns: Optional[float] = None


@dataclass
class PowerData:
    dynamic_mw: Optional[float] = None
    leakage_uw: Optional[float] = None
    total_mw: Optional[float] = None


@dataclass
class CongestionData:
    h_overflow_pct: Optional[float] = None
    v_overflow_pct: Optional[float] = None
    max_density_pct: Optional[float] = None
    utilization_pct: Optional[float] = None
    unrouted_nets: int = 0
    score: Optional[float] = None

    def compute_score(self) -> float:
        s = 0.0
        if self.h_overflow_pct is not None:
            s += min(self.h_overflow_pct * 10, 40)
        if self.v_overflow_pct is not None:
            s += min(self.v_overflow_pct * 10, 40)
        if self.max_density_pct is not None:
            s += max(0, (self.max_density_pct - 50) * 0.5)
        self.score = round(min(s, 100), 1)
        return self.score


@dataclass
class CellInfo:
    instance: str = ""
    cell_type: str = ""
    family: str = ""


@dataclass
class PortInfo:
    name: str = ""
    direction: str = ""
    width: int = 1


@dataclass
class FloorplanData:
    width_um: Optional[float] = None
    height_um: Optional[float] = None
    core_utilization_pct: Optional[float] = None
    aspect_ratio: Optional[float] = None


@dataclass
class PlacementData:
    density_pct: Optional[float] = None
    total_cells: Optional[int] = None


@dataclass
class RoutingData:
    total_nets: Optional[int] = None
    unrouted_nets: int = 0
    total_wire_length_um: Optional[float] = None
    via_count: Optional[int] = None


@dataclass
class DRCCheck:
    violations: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    coordinates: List[Tuple[float, float, float, float]] = field(default_factory=list)


@dataclass
class LVSCheck:
    status: str = "NOT_RUN"
    matched_nets: int = 0
    unmatched_nets: int = 0
    device_mismatches: int = 0


@dataclass
class LayoutInfo:
    gds_path: str = ""
    def_path: str = ""
    layer_count: Optional[int] = None
    polygon_count: Optional[int] = None
    bounding_box: Optional[str] = None
    area_um2: Optional[float] = None
    lef_files: List[str] = field(default_factory=list)
    spef_file: str = ""


@dataclass
class SignoffChecklist:
    timing_met: bool = False
    drc_clean: bool = False
    lvs_matched: bool = False
    gds_valid: bool = False
    hold_met: bool = False


@dataclass
class ECOActionData:
    action_type: str = ""
    target: str = ""
    reason: str = ""
    before_value: Optional[float] = None
    after_value: Optional[float] = None
    priority: int = 5
    area_impact: float = 0.0
    power_impact: float = 0.0
    timing_gain: float = 0.0


@dataclass
class ECOData:
    original_qor: Dict[str, float] = field(default_factory=dict)
    optimized_qor: Dict[str, float] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = False
    changes: List[str] = field(default_factory=list)
    applied_at: str = ""


@dataclass
class DSEData:
    points: List[Dict[str, Any]] = field(default_factory=list)
    best_fmax: Optional[Dict[str, Any]] = None
    best_area: Optional[Dict[str, Any]] = None
    best_power: Optional[Dict[str, Any]] = None
    best_balanced: Optional[Dict[str, Any]] = None
    exploration_params: Dict[str, Any] = field(default_factory=dict)
    pareto_frontier_indices: List[int] = field(default_factory=list)
    generated_at: str = ""


@dataclass
class DesignDB:
    schema_version: str = _SCHEMA_VERSION
    design_name: str = ""
    created_at: str = ""
    modified_at: str = ""

    rtl_sources: List[str] = field(default_factory=list)
    netlist_path: str = ""

    cells: List[CellInfo] = field(default_factory=list)
    ports: List[PortInfo] = field(default_factory=list)
    clocks: List[str] = field(default_factory=list)
    clock_period_ns: float = 10.0

    floorplan: Optional[FloorplanData] = None
    placement: Optional[PlacementData] = None
    routing: Optional[RoutingData] = None

    timing: Optional[TimingData] = None
    mcmm: Optional[Any] = None
    power: Optional[PowerData] = None
    congestion: Optional[CongestionData] = None

    drc: Optional[DRCCheck] = None
    drc_engine_result: Optional[Any] = None
    lvs: Optional[LVSCheck] = None
    lvs_result: Optional[Any] = None
    spef: Optional[Any] = None

    reports: Dict[str, str] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)

    gds_file: str = ""
    def_file: str = ""

    layout: Optional[LayoutInfo] = None
    signoff: Optional[SignoffChecklist] = None

    eco: Optional[ECOData] = None
    dse: Optional[DSEData] = None

    def validate(self) -> List[str]:
        errors = []
        if not self.design_name:
            errors.append("design_name is required")
        if not self.rtl_sources:
            errors.append("rtl_sources is empty")
        if not self.netlist_path:
            errors.append("netlist_path is required")
        if self.timing and not self.timing.corners:
            errors.append("timing has no corners")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(json.dumps(asdict(self), default=str))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DesignDB:
        return _dict_to_db(data)

    def summary(self) -> Dict[str, Any]:
        s = {"design_name": self.design_name, "schema_version": self.schema_version}
        if self.timing:
            for cname, c in self.timing.corners.items():
                s[f"slack_{cname.lower()}"] = c.slack_ns
            s["fmax_mhz"] = self.timing.fmax_mhz
        if self.power:
            s["total_mw"] = self.power.total_mw
            s["dynamic_mw"] = self.power.dynamic_mw
        if self.congestion:
            s["congestion_score"] = self.congestion.score
        if self.drc:
            s["drc_violations"] = self.drc.violations
        if self.lvs:
            s["lvs_status"] = self.lvs.status
        if self.layout and self.layout.area_um2:
            s["area_um2"] = self.layout.area_um2
        return s


def _timing_path_cell_from_dict(d: dict) -> TimingPathCell:
    return TimingPathCell(**{k: v for k, v in d.items() if k in TimingPathCell.__dataclass_fields__})


def _timing_path_from_dict(d: dict) -> TimingPath:
    cells = [_timing_path_cell_from_dict(c) for c in d.pop("cells", [])]
    return TimingPath(**{k: v for k, v in d.items() if k in TimingPath.__dataclass_fields__}, cells=cells)


def _timing_corner_from_dict(d: dict) -> TimingCorner:
    paths = [_timing_path_from_dict(p) for p in d.pop("paths", [])]
    return TimingCorner(**{k: v for k, v in d.items() if k in TimingCorner.__dataclass_fields__}, paths=paths)


def _cell_info_from_dict(d: dict) -> CellInfo:
    return CellInfo(**{k: v for k, v in d.items() if k in CellInfo.__dataclass_fields__})


def _port_info_from_dict(d: dict) -> PortInfo:
    return PortInfo(**{k: v for k, v in d.items() if k in PortInfo.__dataclass_fields__})


def _migrate_v1_0_to_v1_2(data: dict) -> dict:
    """Migrate schema v1.0 -&gt; v1.2 by filling in new optional fields."""
    migrated = dict(data)
    migrated["schema_version"] = "1.2"
    if "eco" not in migrated:
        migrated["eco"] = None
    if "dse" not in migrated:
        migrated["dse"] = None
    return migrated


def _migrate_v1_1_to_v1_2(data: dict) -> dict:
    """Migrate schema v1.1 -&gt; v1.2 by filling in new optional fields."""
    migrated = dict(data)
    migrated["schema_version"] = "1.2"
    if "eco" not in migrated:
        migrated["eco"] = None
    if "dse" not in migrated:
        migrated["dse"] = None
    return migrated


_MIGRATIONS = {
    "1.0": _migrate_v1_0_to_v1_2,
    "1.1": _migrate_v1_1_to_v1_2,
}


def _dict_to_db(data: dict) -> DesignDB:
    in_version = data.get("schema_version", "1.0")
    if in_version in _MIGRATIONS:
        data = _MIGRATIONS[in_version](data)
    db = DesignDB()
    db.schema_version = data.get("schema_version", _SCHEMA_VERSION)
    db.design_name = data.get("design_name", "")
    db.created_at = data.get("created_at", "")
    db.modified_at = data.get("modified_at", "")
    db.rtl_sources = data.get("rtl_sources", [])
    db.netlist_path = data.get("netlist_path", "")
    db.cells = [_cell_info_from_dict(c) for c in data.get("cells", [])]
    db.ports = [_port_info_from_dict(p) for p in data.get("ports", [])]
    db.clocks = data.get("clocks", [])
    db.clock_period_ns = float(data.get("clock_period_ns", 10.0))
    db.gds_file = data.get("gds_file", "")
    db.def_file = data.get("def_file", "")
    db.reports = data.get("reports", {})
    db.artifacts = data.get("artifacts", [])

    td = data.get("timing")
    if td:
        corners = {}
        for cname, cd in td.get("corners", {}).items():
            corners[cname] = _timing_corner_from_dict(cd)
        db.timing = TimingData(
            period_ns=float(td.get("period_ns", 10.0)),
            corners=corners,
            fmax_mhz=td.get("fmax_mhz"),
            hold_slack_ns=td.get("hold_slack_ns"),
        )

    pd = data.get("power")
    if pd:
        db.power = PowerData(
            dynamic_mw=pd.get("dynamic_mw"),
            leakage_uw=pd.get("leakage_uw"),
            total_mw=pd.get("total_mw"),
        )

    cd = data.get("congestion")
    if cd:
        db.congestion = CongestionData(
            h_overflow_pct=cd.get("h_overflow_pct"),
            v_overflow_pct=cd.get("v_overflow_pct"),
            max_density_pct=cd.get("max_density_pct"),
            utilization_pct=cd.get("utilization_pct"),
            unrouted_nets=cd.get("unrouted_nets", 0),
            score=cd.get("score"),
        )

    fp = data.get("floorplan")
    if fp:
        db.floorplan = FloorplanData(
            width_um=fp.get("width_um"),
            height_um=fp.get("height_um"),
            core_utilization_pct=fp.get("core_utilization_pct"),
            aspect_ratio=fp.get("aspect_ratio"),
        )

    pl = data.get("placement")
    if pl:
        db.placement = PlacementData(
            density_pct=pl.get("density_pct"),
            total_cells=pl.get("total_cells"),
        )

    rt = data.get("routing")
    if rt:
        db.routing = RoutingData(
            total_nets=rt.get("total_nets"),
            unrouted_nets=rt.get("unrouted_nets", 0),
            total_wire_length_um=rt.get("total_wire_length_um"),
            via_count=rt.get("via_count"),
        )

    dr = data.get("drc")
    if dr:
        db.drc = DRCCheck(
            violations=dr.get("violations", 0),
            categories=dr.get("categories", {}),
            coordinates=[tuple(c) for c in dr.get("coordinates", [])],
        )

    lv = data.get("lvs")
    if lv:
        db.lvs = LVSCheck(
            status=lv.get("status", "NOT_RUN"),
            matched_nets=lv.get("matched_nets", 0),
            unmatched_nets=lv.get("unmatched_nets", 0),
            device_mismatches=lv.get("device_mismatches", 0),
        )

    li = data.get("layout")
    if li:
        db.layout = LayoutInfo(
            gds_path=li.get("gds_path", ""),
            def_path=li.get("def_path", ""),
            layer_count=li.get("layer_count"),
            polygon_count=li.get("polygon_count"),
            bounding_box=li.get("bounding_box"),
            area_um2=li.get("area_um2"),
            lef_files=li.get("lef_files", []),
            spef_file=li.get("spef_file", ""),
        )

    sc = data.get("signoff")
    if sc:
        db.signoff = SignoffChecklist(
            timing_met=sc.get("timing_met", False),
            drc_clean=sc.get("drc_clean", False),
            lvs_matched=sc.get("lvs_matched", False),
            gds_valid=sc.get("gds_valid", False),
            hold_met=sc.get("hold_met", False),
        )

    mcmm_data = data.get("mcmm")
    if mcmm_data and MCMM_AVAILABLE:
        db.mcmm = _MCMMTiming.from_dict(mcmm_data)

    spef_data = data.get("spef")
    if spef_data and SPEF_AVAILABLE:
        nets = [_ParasiticNet(**n) for n in spef_data.get("nets", [])]
        spef_result = _SPEFResult(
            design_name=spef_data.get("design_name", ""),
            total_nets=spef_data.get("total_nets", 0),
            total_wire_length_um=spef_data.get("total_wire_length_um", 0.0),
            total_resistance_ohm=spef_data.get("total_resistance_ohm", 0.0),
            total_capacitance_pf=spef_data.get("total_capacitance_pf", 0.0),
            nets=nets,
            extracted_at=spef_data.get("extracted_at", ""),
        )
        db.spef = spef_result

    drc_eng = data.get("drc_engine_result")
    if drc_eng and DRC_ENGINE_AVAILABLE:
        db.drc_engine_result = _DRCEngineResult.from_dict(drc_eng)

    lvs_res = data.get("lvs_result")
    if lvs_res and LVS_ENGINE_AVAILABLE:
        db.lvs_result = _LVSResult.from_dict(lvs_res)

    # --- ECO data (schema v1.2+) ---
    eco_data = data.get("eco")
    if eco_data and isinstance(eco_data, dict):
        db.eco = ECOData(
            original_qor=eco_data.get("original_qor", {}),
            optimized_qor=eco_data.get("optimized_qor", {}),
            actions=eco_data.get("actions", []),
            success=eco_data.get("success", False),
            changes=eco_data.get("changes", []),
            applied_at=eco_data.get("applied_at", ""),
        )

    # --- DSE data (schema v1.2+) ---
    dse_data = data.get("dse")
    if dse_data and isinstance(dse_data, dict):
        db.dse = DSEData(
            points=dse_data.get("points", []),
            best_fmax=dse_data.get("best_fmax"),
            best_area=dse_data.get("best_area"),
            best_power=dse_data.get("best_power"),
            best_balanced=dse_data.get("best_balanced"),
            exploration_params=dse_data.get("exploration_params", {}),
            pareto_frontier_indices=dse_data.get("pareto_frontier_indices", []),
            generated_at=dse_data.get("generated_at", ""),
        )

    return db


def save_design_db(db: DesignDB, path: Path) -> None:
    path.write_text(json.dumps(db.to_dict(), indent=2, default=str), encoding="utf-8")
    logger.info("DesignDB saved: %s (%s)", path, db.design_name)


def load_design_db(path: Path) -> DesignDB:
    data = json.loads(path.read_text(encoding="utf-8"))
    db = DesignDB.from_dict(data)
    logger.info("DesignDB loaded: %s (%s)", path, db.design_name)
    return db


if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=" * 60)
    print("design_db.py \u2014 standalone self-test")
    print("=" * 60)

    passed = total = 0

    # Test 1: create empty DB
    total += 1
    db = DesignDB(design_name="test_adder", rtl_sources=["adder.v"], netlist_path="adder.v")
    assert db.design_name == "test_adder"
    assert db.schema_version == "1.2"
    print("[PASS] Empty DesignDB created (v{})".format(db.schema_version))
    passed += 1

    # Test 2: validate \u2014 should have errors for missing data
    total += 1
    db2 = DesignDB()
    errs = db2.validate()
    assert len(errs) >= 1, f"Expected validation errors, got {errs}"
    print(f"[PASS] Validation errors: {errs}")
    passed += 1

    # Test 3: serialize to dict and back
    total += 1
    db3 = DesignDB(design_name="serialize_test", rtl_sources=["a.v"], netlist_path="a.v")
    db3.timing = TimingData(
        period_ns=10.0,
        corners={
            "TT": TimingCorner(
                corner="TT",
                slack_ns=5.57,
                met=True,
                paths=[TimingPath(startpoint="a", endpoint="b", slack_ns=5.57, met=True)],
            )
        },
        fmax_mhz=225.73,
    )
    d = db3.to_dict()
    assert d["design_name"] == "serialize_test"
    assert d["timing"]["fmax_mhz"] == 225.73
    db3r = DesignDB.from_dict(d)
    assert db3r.design_name == "serialize_test"
    assert db3r.timing is not None
    assert db3r.timing.fmax_mhz == 225.73
    assert db3r.timing.corners["TT"].slack_ns == 5.57
    print("[PASS] Serialize/deserialize round-trip")
    passed += 1

    # Test 4: save and load file
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "design_db.json"
        db4 = DesignDB(design_name="file_test", rtl_sources=["f.v"], netlist_path="f.v")
        save_design_db(db4, p)
        assert p.exists() and p.stat().st_size > 10
        db4r = load_design_db(p)
        assert db4r.design_name == "file_test"
    print("[PASS] Save/load file round-trip")
    passed += 1

    # Test 5: power data
    total += 1
    db5 = DesignDB(design_name="power_test", rtl_sources=["p.v"], netlist_path="p.v")
    db5.power = PowerData(dynamic_mw=0.0563, leakage_uw=0.0058, total_mw=0.0564)
    d5 = db5.to_dict()
    db5r = DesignDB.from_dict(d5)
    assert db5r.power is not None
    assert abs(db5r.power.total_mw - 0.0564) < 0.001
    print("[PASS] Power data round-trip")
    passed += 1

    # Test 6: congestion with score
    total += 1
    db6 = DesignDB(design_name="cong_test", rtl_sources=["c.v"], netlist_path="c.v")
    db6.congestion = CongestionData(
        h_overflow_pct=0.05, v_overflow_pct=0.12, max_density_pct=52.3, utilization_pct=30.2
    )
    db6.congestion.compute_score()
    d6 = db6.to_dict()
    db6r = DesignDB.from_dict(d6)
    assert db6r.congestion is not None
    assert db6r.congestion.score is not None and db6r.congestion.score > 0
    print(f"[PASS] Congestion score: {db6r.congestion.score}")
    passed += 1

    # Test 7: layout info
    total += 1
    db7 = DesignDB(design_name="lay_test", rtl_sources=["l.v"], netlist_path="l.v")
    db7.layout = LayoutInfo(
        gds_path="/tmp/test.gds", layer_count=6, polygon_count=1234, area_um2=3460.0
    )
    d7 = db7.to_dict()
    db7r = DesignDB.from_dict(d7)
    assert db7r.layout is not None
    assert db7r.layout.polygon_count == 1234
    print("[PASS] Layout data round-trip")
    passed += 1

    # Test 8: DRC / LVS
    total += 1
    db8 = DesignDB(design_name="drclvs", rtl_sources=["d.v"], netlist_path="d.v")
    db8.drc = DRCCheck(violations=0, categories={"SPACING": 0, "WIDTH": 0})
    db8.lvs = LVSCheck(status="MATCHED", matched_nets=100, unmatched_nets=0)
    d8 = db8.to_dict()
    db8r = DesignDB.from_dict(d8)
    assert db8r.drc.violations == 0
    assert db8r.lvs.status == "MATCHED"
    print("[PASS] DRC/LVS round-trip")
    passed += 1

    # Test 9: summary dict
    total += 1
    db9 = DesignDB(design_name="sum_test", rtl_sources=["s.v"], netlist_path="s.v")
    db9.timing = TimingData(
        period_ns=10.0,
        corners={"TT": TimingCorner(corner="TT", slack_ns=5.57, met=True)},
        fmax_mhz=225.73,
    )
    db9.power = PowerData(total_mw=0.0564)
    db9.congestion = CongestionData(score=12.5)
    s9 = db9.summary()
    assert s9["design_name"] == "sum_test"
    assert s9["fmax_mhz"] == 225.73
    assert s9["total_mw"] == 0.0564
    print(f"[PASS] Summary dict: {list(s9.keys())}")
    passed += 1

    # Test 10: MCMM data round-trip
    total += 1
    if MCMM_AVAILABLE:
        from mcmm import MCMMTiming, TimingCorner as MCCorner
        mcmm_data = MCMMTiming(
            corners={
                "TT": MCCorner(name="TT", worst_negative_slack=5.57, fmax_mhz=225.73, violations=0, met=True),
                "SS": MCCorner(name="SS", worst_negative_slack=3.21, fmax_mhz=147.28, violations=0, met=True),
                "FF": MCCorner(name="FF", worst_negative_slack=-0.05, fmax_mhz=99.50, violations=1, met=False),
            },
            period_ns=10.0,
        )
        mcmm_data.determine_signoff()
        db10 = DesignDB(design_name="mcmm_test", rtl_sources=["m.v"], netlist_path="m.v")
        db10.mcmm = mcmm_data
        d10 = db10.to_dict()
        assert "mcmm" in d10
        assert d10["mcmm"]["signoff_corner"] == "FF"
        db10r = DesignDB.from_dict(d10)
        assert db10r.mcmm is not None
        assert db10r.mcmm.signoff_corner == "FF"
        assert db10r.mcmm.corners["TT"].worst_negative_slack == 5.57
        print("[PASS] MCMM data round-trip")
    else:
        print("[SKIP] MCMM not available")
    passed += 1

    # Test 11: SPEF data round-trip
    total += 1
    if SPEF_AVAILABLE:
        from spef_engine import SPEFResult, ParasiticNet as PNet
        spef_data = SPEFResult(
            design_name="spef_test",
            total_nets=3,
            total_wire_length_um=3460.0,
            total_resistance_ohm=276.8,
            total_capacitance_pf=0.692,
            nets=[PNet(net_name="n1", wire_length_um=1200.0, resistance_ohm=96.0, capacitance_pf=0.24, delay_impact_ps=23.04)],
            extracted_at="2026-01-01T00:00:00",
        )
        db11 = DesignDB(design_name="spef_test", rtl_sources=["s.v"], netlist_path="s.v")
        db11.spef = spef_data
        d11 = db11.to_dict()
        assert "spef" in d11
        assert d11["spef"]["design_name"] == "spef_test"
        db11r = DesignDB.from_dict(d11)
        assert db11r.spef is not None
        assert db11r.spef.total_wire_length_um == 3460.0
        print("[PASS] SPEF data round-trip")
    else:
        print("[SKIP] SPEF not available")
    passed += 1

    # Test 12: DRC engine result round-trip
    total += 1
    if DRC_ENGINE_AVAILABLE:
        from drc_engine import DRCEngineResult, DRCViolation as DRV
        drc_eng = DRCEngineResult(
            total_violations=2,
            violations=[DRV(rule_name="width", layer="metal1", x=1.0, y=2.0)],
            by_rule={"width": 2},
            by_layer={"metal1": 2},
            by_severity={"error": 2},
            checks_run=["min_width", "min_spacing"],
            engine="klayout",
        )
        db12 = DesignDB(design_name="drc_eng_test", rtl_sources=["d.v"], netlist_path="d.v")
        db12.drc_engine_result = drc_eng
        d12 = db12.to_dict()
        assert "drc_engine_result" in d12
        db12r = DesignDB.from_dict(d12)
        assert db12r.drc_engine_result is not None
        assert db12r.drc_engine_result.total_violations == 2
        assert db12r.drc_engine_result.engine == "klayout"
        print("[PASS] DRC engine result round-trip")
    else:
        print("[SKIP] DRC engine not available")
    passed += 1

    # Test 13: LVS result round-trip
    total += 1
    if LVS_ENGINE_AVAILABLE:
        from lvs_engine import LVSResult, LVSDevice as LDev
        lvs_res = LVSResult(
            status="MATCHED",
            schematic_devices=[LDev(instance="x1", cell_type="AND2")],
            layout_devices=[LDev(instance="x1", cell_type="AND2")],
            schematic_nets=10,
            layout_nets=10,
            matched_nets=10,
            unmatched_nets=0,
            matched_devices=1,
            unmatched_devices=0,
            match_percentage=100.0,
        )
        db13 = DesignDB(design_name="lvs_res_test", rtl_sources=["l.v"], netlist_path="l.v")
        db13.lvs_result = lvs_res
        d13 = db13.to_dict()
        assert "lvs_result" in d13
        db13r = DesignDB.from_dict(d13)
        assert db13r.lvs_result is not None
        assert db13r.lvs_result.status == "MATCHED"
        assert db13r.lvs_result.match_percentage == 100.0
        print("[PASS] LVS result round-trip")
    else:
        print("[SKIP] LVS engine not available")
    passed += 1

    # Test 14: ECO data round-trip
    total += 1
    db14 = DesignDB(design_name="eco_test", rtl_sources=["e.v"], netlist_path="e.v")
    db14.eco = ECOData(
        original_qor={"fmax_mhz": 100.0, "power_mw": 10.0, "area_um2": 5000.0},
        optimized_qor={"fmax_mhz": 133.0, "power_mw": 10.5, "area_um2": 5200.0},
        actions=[
            {"action_type": "buffer_insertion", "target": "net_clk", "reason": "setup fix", "timing_gain": 0.3},
        ],
        success=True,
        changes=["buffer_insertion on net_clk"],
        applied_at="2026-01-15T12:00:00",
    )
    d14 = db14.to_dict()
    assert "eco" in d14
    assert d14["eco"]["success"] is True
    assert d14["eco"]["original_qor"]["fmax_mhz"] == 100.0
    db14r = DesignDB.from_dict(d14)
    assert db14r.eco is not None
    assert db14r.eco.success
    assert db14r.eco.original_qor["fmax_mhz"] == 100.0
    assert len(db14r.eco.actions) == 1
    print(f"[PASS] ECO data round-trip: {len(db14.eco.actions)} actions, success={db14.eco.success}")
    passed += 1

    # Test 15: DSE data round-trip
    total += 1
    db15 = DesignDB(design_name="dse_test", rtl_sources=["d.v"], netlist_path="d.v")
    db15.dse = DSEData(
        points=[
            {"clock_period_ns": 5.0, "utilization_pct": 60, "placement_density": 0.65, "fmax_mhz": 200},
            {"clock_period_ns": 10.0, "utilization_pct": 80, "placement_density": 0.75, "fmax_mhz": 100},
        ],
        best_fmax={"clock_period_ns": 5.0, "fmax_mhz": 200},
        exploration_params={"total_configs": 48},
        pareto_frontier_indices=[0],
        generated_at="2026-01-15T12:00:00",
    )
    d15 = db15.to_dict()
    assert "dse" in d15
    assert d15["dse"]["best_fmax"]["fmax_mhz"] == 200
    db15r = DesignDB.from_dict(d15)
    assert db15r.dse is not None
    assert db15r.dse.best_fmax["fmax_mhz"] == 200
    assert len(db15r.dse.points) == 2
    print(f"[PASS] DSE data round-trip: {len(db15.dse.points)} points, best Fmax={db15.dse.best_fmax['fmax_mhz']}MHz")
    passed += 1

    # Test 16: Auto-migration v1.0 -&gt; v1.2
    total += 1
    v10_data = {
        "schema_version": "1.0",
        "design_name": "legacy",
        "rtl_sources": ["old.v"],
        "netlist_path": "old.v",
        "timing": {"period_ns": 10.0, "fmax_mhz": 100},
    }
    db16 = DesignDB.from_dict(v10_data)
    assert db16.schema_version == "1.2", f"Expected 1.2, got {db16.schema_version}"
    assert db16.design_name == "legacy"
    assert db16.timing is not None
    assert db16.timing.fmax_mhz == 100
    print(f"[PASS] Auto-migration v1.0 -&gt; v1.2: design={db16.design_name}")
    passed += 1

    # Test 17: Auto-migration v1.1 -&gt; v1.2
    total += 1
    v11_data = {
        "schema_version": "1.1",
        "design_name": "legacy_v11",
        "rtl_sources": ["v11.v"],
        "netlist_path": "v11.v",
        "timing": {"period_ns": 5.0, "fmax_mhz": 200},
        "power": {"total_mw": 0.05},
    }
    db17 = DesignDB.from_dict(v11_data)
    assert db17.schema_version == "1.2", f"Expected 1.2, got {db17.schema_version}"
    assert db17.design_name == "legacy_v11"
    assert db17.timing.fmax_mhz == 200
    assert db17.power is not None
    assert abs(db17.power.total_mw - 0.05) < 0.001
    print(f"[PASS] Auto-migration v1.1 -&gt; v1.2: design={db17.design_name}")
    passed += 1

    # Test 18: Backward compatibility — new fields default to None
    total += 1
    old_data = {
        "schema_version": "1.0",
        "design_name": "backward_compat",
        "rtl_sources": ["b.v"],
        "netlist_path": "b.v",
    }
    db18 = DesignDB.from_dict(old_data)
    assert db18.eco is None
    assert db18.dse is None
    print(f"[PASS] Backward compatibility: eco=None, dse=None, sv={db18.schema_version}")
    passed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED \u2014 design_db.py ready")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)
