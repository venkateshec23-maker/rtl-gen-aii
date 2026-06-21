"""
dataset_builder.py — Phase 3 Training Data Pipeline
RTL-Gen AI

Collects (description, RTL, metrics) from every successful pipeline run.
Builds a high-quality JSONL dataset for fine-tuning a custom RTL model.

Integration: called automatically at end of every guaranteed_flow run.
At 500+ examples: export and move to Phase 4 fine-tuning.

Usage:
    # Auto-called from guaranteed_flow.py (add the hook)
    from dataset_builder import collect_example
    collect_example(description, rtl_code, pipeline_result)

    # Export full dataset
    python dataset_builder.py --export --output training_data/

    # View statistics
    python dataset_builder.py --stats

    # Browse examples in Streamlit
    from dataset_builder import render_dataset_browser_streamlit
    render_dataset_browser_streamlit()
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_DATA_DIR   = Path("training_data")
_JSONL_FILE = _DATA_DIR / "rtl_dataset.jsonl"
_INDEX_FILE = _DATA_DIR / "index.json"

# Phase 3 target
MIN_EXAMPLES_FOR_TRAINING = 500


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class TrainingExample:
    """One training example: a verified RTL design."""
    example_id:    str
    description:   str          # natural language input
    rtl_code:      str          # output Verilog
    module_name:   str
    collected_at:  str          = field(default_factory=lambda: datetime.now().isoformat())

    # Quality metrics (all required for inclusion in dataset)
    gds_size_kb:   float        = 0.0
    drc_violations: int         = 0
    lvs_status:    str          = ""
    fmax_mhz:      Optional[float] = None
    total_mw:      Optional[float] = None
    hold_slack_ns: Optional[float] = None
    cell_count:    Optional[int]   = None
    tapeout_ready: bool         = False

    # Metadata
    llm_provider:  str          = ""
    rtl_lines:     int          = 0
    complexity:    str          = ""   # simple/medium/complex
    template_used: str          = ""

    def quality_score(self) -> float:
        """0.0 to 1.0 score based on available metrics."""
        score = 0.0
        if self.tapeout_ready:           score += 0.4
        if self.drc_violations == 0:     score += 0.2
        if "MATCHED" in self.lvs_status: score += 0.2
        if self.fmax_mhz is not None:    score += 0.1
        if self.total_mw is not None:    score += 0.1
        return score

    def to_jsonl(self) -> str:
        """Format as one JSONL line for HuggingFace dataset loading."""
        return json.dumps({
            "id":          self.example_id,
            "instruction": "Generate synthesizable Verilog RTL for the following hardware design specification.",
            "input":       self.description,
            "output":      self.rtl_code,
            "metadata": {
                "module_name":    self.module_name,
                "collected_at":   self.collected_at,
                "gds_size_kb":    self.gds_size_kb,
                "drc_violations": self.drc_violations,
                "lvs_status":     self.lvs_status,
                "fmax_mhz":       self.fmax_mhz,
                "total_mw":       self.total_mw,
                "cell_count":     self.cell_count,
                "tapeout_ready":  self.tapeout_ready,
                "llm_provider":   self.llm_provider,
                "quality_score":  round(self.quality_score(), 2),
                "complexity":     self.complexity,
                "template_used":  self.template_used,
            },
        }, ensure_ascii=False)

    def to_alpaca(self) -> Dict:
        """Alpaca format for standard fine-tuning."""
        return {
            "instruction": "Generate synthesizable Verilog RTL for the following hardware design specification.",
            "input":       self.description,
            "output":      self.rtl_code,
        }

    def to_chat(self) -> Dict:
        """ChatML format for instruction-tuned models."""
        return {
            "messages": [
                {
                    "role":    "system",
                    "content": (
                        "You are an expert RTL hardware designer. "
                        "Generate clean, synthesizable Verilog 2005 code. "
                        "Always include: synchronous reset (active-low), "
                        "clock (posedge), proper port declarations, and comments. "
                        "Output ONLY the complete Verilog module."
                    ),
                },
                {
                    "role":    "user",
                    "content": self.description,
                },
                {
                    "role":    "assistant",
                    "content": self.rtl_code,
                },
            ]
        }


# ── Quality filter ─────────────────────────────────────────────────────────────

def _classify_design_family(name_or_desc: str) -> str:
    """Map design name/description to a broad functional family."""
    n = name_or_desc.lower()
    for family, keywords in {
        "uart":       ["uart", "serial", "baud"],
        "spi":        ["spi", "mosi", "miso", "sck"],
        "i2c":        ["i2c", "sda", "scl", "twi"],
        "memory":     ["memory", "sram", "ram", "fifo", "buffer"],
        "arithmetic": ["adder", "alu", "multiplier", "adder"],
        "counter":    ["counter", "gray", "bcd", "lfsr"],
        "crc":        ["crc", "checksum"],
        "encoder":    ["encoder", "encode"],
        "decoder":    ["decoder", "decode"],
        "arbiter":    ["arbiter", "arb", "round_robin"],
        "pwm":        ["pwm", "pulse", "duty"],
        "shift":      ["shift", "barrel", "rotate"],
    }.items():
        if any(k in n for k in keywords):
            return family
    return "generic"


def _passes_quality_filter(ex: TrainingExample) -> bool:
    """
    Only include examples that are genuinely verified silicon designs.
    This ensures the model learns from proven, correct RTL.
    """
    if not ex.tapeout_ready:           return False   # must be tape-out ready
    if ex.drc_violations > 0:          return False   # no DRC violations
    if "MATCHED" not in ex.lvs_status: return False   # LVS must match
    if ex.gds_size_kb < 50:            return False   # real GDS (not stub)
    if len(ex.rtl_code) < 100:         return False   # non-trivial RTL
    if "endmodule" not in ex.rtl_code: return False   # complete module
    if ex.rtl_lines < 5:               return False   # at least 5 lines

    # Reject if cell count seems wrong for design type
    name = ex.module_name.lower()
    cells = ex.cell_count or 0

    # SRAM designs should have many more cells than simple logic
    if ("sram" in name or "memory" in name) and cells < 500:
        log.debug("Rejecting %s: SRAM with only %d cells is suspicious",
                  ex.module_name, cells)
        return False

    # FIFO with 0 cells is wrong
    if "fifo" in name and cells < 50:
        return False

    # Design intent must match (no CRC using I2C template)
    if ex.llm_provider != "seed" and getattr(ex, "template_used", ""):
        desc_family     = _classify_design_family(ex.description)
        template_family = _classify_design_family(ex.template_used)
        if (desc_family != "generic" and template_family != "generic"
                and desc_family != template_family):
            log.debug("Rejecting %s: template mismatch (%s vs %s)",
                      ex.module_name, template_family, desc_family)
            return False

    return True


def _classify_complexity(cell_count: Optional[int]) -> str:
    if cell_count is None: return "unknown"
    if cell_count < 100:   return "simple"
    if cell_count < 500:   return "medium"
    return "complex"


def _make_id(description: str, rtl_code: str) -> str:
    payload = (description + rtl_code).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


# ── Collector ─────────────────────────────────────────────────────────────────

def collect_example(
    description:     str,
    rtl_code:        str,
    pipeline_result: Dict,
    llm_provider:    str = "",
) -> Optional[TrainingExample]:
    """
    Collect one training example from a pipeline run result.
    Returns the example if it passes quality filter, None otherwise.

    Add this call at the end of generate_guaranteed_gds() in guaranteed_flow.py:
        from dataset_builder import collect_example
        collect_example(description, rtl_code, result, provider)
    """
    _DATA_DIR.mkdir(exist_ok=True)

    steps    = pipeline_result.get("steps", {})
    qor      = steps.get("qor", {})
    module   = pipeline_result.get("module_name", "unknown")

    # Also check top-level QOR keys that guaranteed_flow.py returns directly
    if not qor:
        qor = {
            "drc_violations": pipeline_result.get("drc_violations"),
            "lvs_status":     pipeline_result.get("lvs_status", ""),
            "fmax_mhz":       pipeline_result.get("fmax_mhz"),
            "total_mw":       pipeline_result.get("total_mw"),
            "hold_slack_ns":  pipeline_result.get("hold_slack_ns"),
            "cell_count":     pipeline_result.get("cell_count"),
        }

    rtl_code = rtl_code.strip()

    # Resolve LVS status from multiple possible locations
    lvs_status = str(
        qor.get("lvs_status")
        or steps.get("lvs_status")
        or pipeline_result.get("lvs_status")
        or ""
    )

    ex = TrainingExample(
        example_id     = _make_id(description, rtl_code),
        description    = description.strip(),
        rtl_code       = rtl_code,
        module_name    = module,
        gds_size_kb    = float(pipeline_result.get("gds_size_kb") or 0),
        drc_violations = int(qor.get("drc_violations") or 0),
        lvs_status     = lvs_status,
        fmax_mhz       = qor.get("fmax_mhz") or pipeline_result.get("fmax_mhz"),
        total_mw       = qor.get("total_mw") or pipeline_result.get("total_mw"),
        hold_slack_ns  = qor.get("hold_slack_ns") or pipeline_result.get("hold_slack_ns"),
        cell_count     = qor.get("cell_count"),
        tapeout_ready  = bool(pipeline_result.get("tapeout_ready")),
        llm_provider   = llm_provider,
        rtl_lines      = rtl_code.count("\n"),
        complexity     = _classify_complexity(qor.get("cell_count")),
        template_used  = pipeline_result.get("template_used", ""),
    )

    if not _passes_quality_filter(ex):
        log.debug("Example rejected: quality filter. tapeout=%s drc=%s lvs=%s",
                  ex.tapeout_ready, ex.drc_violations, ex.lvs_status)
        return None

    # Check for duplicate
    if _is_duplicate(ex.example_id):
        log.debug("Example skipped: duplicate ID %s", ex.example_id)
        return None

    # Save to JSONL
    with open(_JSONL_FILE, "a", encoding="utf-8") as f:
        f.write(ex.to_jsonl() + "\n")

    # Update index
    _update_index(ex)

    count = get_count()
    log.info("Dataset: collected example #%d — %s (quality=%.2f)",
             count, module, ex.quality_score())

    if count >= MIN_EXAMPLES_FOR_TRAINING and count % 10 == 0:
        log.info("Dataset ready for training: %d examples. Run: python dataset_builder.py --export",
                 count)

    return ex


def _is_duplicate(example_id: str) -> bool:
    if not _INDEX_FILE.exists():
        return False
    try:
        index = json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
        return example_id in index.get("ids", [])
    except Exception:
        return False


def _update_index(ex: TrainingExample) -> None:
    index = {"ids": [], "count": 0, "last_updated": ""}
    if _INDEX_FILE.exists():
        try:
            index = json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    index["ids"].append(ex.example_id)
    index["count"] = len(index["ids"])
    index["last_updated"] = datetime.now().isoformat()
    _INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")


# ── Loader ────────────────────────────────────────────────────────────────────

def load_all_examples() -> List[TrainingExample]:
    """Load all collected examples from the JSONL file."""
    if not _JSONL_FILE.exists():
        return []
    examples = []
    for line in _JSONL_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d    = json.loads(line)
            meta = d.get("metadata", {})
            ex   = TrainingExample(
                example_id    = d["id"],
                description   = d["input"],
                rtl_code      = d["output"],
                module_name   = meta.get("module_name", ""),
                collected_at  = meta.get("collected_at", ""),
                gds_size_kb   = meta.get("gds_size_kb", 0),
                drc_violations= meta.get("drc_violations", 0),
                lvs_status    = meta.get("lvs_status", ""),
                fmax_mhz      = meta.get("fmax_mhz"),
                total_mw      = meta.get("total_mw"),
                cell_count    = meta.get("cell_count"),
                tapeout_ready = meta.get("tapeout_ready", False),
                llm_provider  = meta.get("llm_provider", ""),
                complexity    = meta.get("complexity", "unknown"),
                rtl_lines     = d["output"].count("\n"),
                template_used = meta.get("template_used", ""),
            )
            examples.append(ex)
        except Exception as e:
            log.warning("Skip malformed example: %s", e)
    return examples


def get_count() -> int:
    if not _INDEX_FILE.exists():
        return 0
    try:
        return json.loads(_INDEX_FILE.read_text())["count"]
    except Exception:
        return sum(1 for line in open(_JSONL_FILE) if line.strip()) if _JSONL_FILE.exists() else 0


# ── Exporter ──────────────────────────────────────────────────────────────────

def export_dataset(output_dir: Path, format: str = "all") -> Dict:
    """
    Export the dataset in multiple formats for fine-tuning.

    Formats:
      jsonl     — HuggingFace datasets compatible (description → RTL)
      alpaca    — Alpaca instruction format (JSON)
      chat      — ChatML format for instruction-tuned models (JSONL)
      summary   — Human-readable stats

    Returns dict with export stats.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    examples = load_all_examples()

    if not examples:
        return {"error": "No examples in dataset"}

    # Split train/val/test: 80/10/10
    n      = len(examples)
    n_val  = max(1, n // 10)
    n_test = max(1, n // 10)
    n_train= n - n_val - n_test

    train = examples[:n_train]
    val   = examples[n_train:n_train + n_val]
    test  = examples[n_train + n_val:]

    stats = {
        "total":   n,
        "train":   n_train,
        "val":     n_val,
        "test":    n_test,
        "files":   [],
    }

    def _write_jsonl(path: Path, exs: List[TrainingExample]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for ex in exs:
                f.write(ex.to_jsonl() + "\n")

    def _write_chat_jsonl(path: Path, exs: List[TrainingExample]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for ex in exs:
                f.write(json.dumps(ex.to_chat(), ensure_ascii=False) + "\n")

    def _write_alpaca_json(path: Path, exs: List[TrainingExample]) -> None:
        data = [ex.to_alpaca() for ex in exs]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write all formats
    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        # Standard JSONL
        p = output_dir / f"rtl_{split_name}.jsonl"
        _write_jsonl(p, split_data)
        stats["files"].append(str(p))

        # Chat format (for instruction-tuned models)
        p2 = output_dir / f"rtl_{split_name}_chat.jsonl"
        _write_chat_jsonl(p2, split_data)
        stats["files"].append(str(p2))

        # Alpaca format
        p3 = output_dir / f"rtl_{split_name}_alpaca.json"
        _write_alpaca_json(p3, split_data)
        stats["files"].append(str(p3))

    # Write summary
    complexity_dist = {}
    for ex in examples:
        complexity_dist[ex.complexity] = complexity_dist.get(ex.complexity, 0) + 1

    provider_dist = {}
    for ex in examples:
        provider_dist[ex.llm_provider] = provider_dist.get(ex.llm_provider, 0) + 1

    avg_quality = sum(ex.quality_score() for ex in examples) / n if n > 0 else 0
    avg_lines   = sum(ex.rtl_lines for ex in examples) / n if n > 0 else 0

    summary = {
        "total_examples":     n,
        "train_val_test":     f"{n_train}/{n_val}/{n_test}",
        "avg_quality_score":  round(avg_quality, 3),
        "avg_rtl_lines":      round(avg_lines, 1),
        "complexity_dist":    complexity_dist,
        "provider_dist":      provider_dist,
        "ready_for_training": n >= MIN_EXAMPLES_FOR_TRAINING,
        "need_more":          max(0, MIN_EXAMPLES_FOR_TRAINING - n),
    }

    summary_path = output_dir / "dataset_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    stats["summary"] = summary

    print(f"\nDataset exported to {output_dir}")
    print(f"  Total    : {n} examples")
    print(f"  Split    : train={n_train} val={n_val} test={n_test}")
    print(f"  Avg quality: {avg_quality:.2f}")
    print(f"  Avg RTL lines: {avg_lines:.0f}")
    print(f"  Complexity: {complexity_dist}")
    if n >= MIN_EXAMPLES_FOR_TRAINING:
        print(f"  READY FOR TRAINING — proceed to Phase 4")
    else:
        print(f"  Need {MIN_EXAMPLES_FOR_TRAINING - n} more examples before training")

    return stats


# ── Bulk seed from existing runs ───────────────────────────────────────────────

def seed_from_existing_runs(work_dir: Path = Path(r"C:\tools\OpenLane")) -> int:
    """
    Retrospectively collect training examples from all existing pipeline runs.
    Call once to seed the dataset with your 9+ proven designs.

    Returns: number of examples added.
    """
    from pathlib import Path as _Path

    runs_dir    = work_dir / "runs"
    results_dir = work_dir / "results"
    added       = 0

    if not runs_dir.exists():
        log.warning("runs_dir not found: %s", runs_dir)
        return 0

    for run_dir in sorted(runs_dir.iterdir(), key=lambda d: d.stat().st_mtime):
        if not run_dir.is_dir():
            continue

        # Find the Verilog source
        verilog_files = list(run_dir.rglob("*.v"))
        design_vf = [f for f in verilog_files
                     if not f.name.endswith("_tb.v")
                     and not "synth" in f.name.lower()
                     and not "sky130" in f.name.lower()]
        if not design_vf:
            continue

        rtl_path = design_vf[0]
        rtl_code = rtl_path.read_text(errors="replace")
        if "module" not in rtl_code:
            continue

        # Extract module name
        m = re.search(r"module\s+(\w+)\s*\(", rtl_code)
        if not m:
            continue
        module_name = m.group(1)

        # Check if this was a successful tape-out
        gds_candidates = list(results_dir.glob(f"{module_name}*.gds")) if results_dir.exists() else []
        if not gds_candidates:
            gds_candidates = list(run_dir.rglob("*.gds"))

        if not gds_candidates:
            continue

        gds_path = max(gds_candidates, key=lambda p: p.stat().st_size)
        gds_kb   = gds_path.stat().st_size / 1024

        if gds_kb < 50:
            continue

        # Check for DRC/LVS reports
        drc_ok  = True
        lvs_ok  = False
        drc_files = list(run_dir.rglob("*drc*"))
        lvs_files = list(run_dir.rglob("*lvs*"))

        for df in drc_files:
            if "violation" in df.read_text(errors="replace").lower():
                txt = df.read_text(errors="replace")
                if re.search(r"[1-9]\d* violation", txt):
                    drc_ok = False
                    break

        for lf in lvs_files:
            if "match" in lf.read_text(errors="replace").lower():
                lvs_ok = True
                break

        # Build a reasonable description from module name
        desc_map = {
            "adder_8bit":   "8-bit synchronous adder with carry output",
            "simple_alu":   "8-bit ALU with add subtract and or xor operations",
            "uart_tx":      "UART transmitter 8N1 at 115200 baud",
            "spi_master":   "SPI master controller",
            "i2c_master":   "I2C master controller",
            "reg_file":     "8x8 register file with dual read ports",
            "fifo":         "16-entry 8-bit synchronous FIFO",
            "memory":       "256x8-bit synchronous SRAM",
            "counter":      "4-bit synchronous counter with enable",
        }
        description = desc_map.get(module_name, f"RTL design: {module_name}")

        fake_result = {
            "module_name":  module_name,
            "gds_size_kb":  gds_kb,
            "tapeout_ready": drc_ok and lvs_ok and gds_kb > 50,
            "steps": {
                "qor": {
                    "drc_violations": 0 if drc_ok else 1,
                    "lvs_status": "MATCHED" if lvs_ok else "UNKNOWN",
                    "fmax_mhz": None,
                    "total_mw": None,
                }
            }
        }

        ex = collect_example(description, rtl_code, fake_result, llm_provider="seed")
        if ex:
            added += 1
            print(f"  Seeded: {module_name} ({gds_kb:.0f} KB)")

    print(f"\nSeeded {added} examples from existing runs")
    return added


# ── Streamlit UI ───────────────────────────────────────────────────────────────

def render_dataset_browser_streamlit(key: str = "ds") -> None:
    """
    Browse the collected training dataset in Streamlit.
    Add to app.py sidebar as 'Training Dataset' page.
    """
    import streamlit as st

    st.title("🗃️ RTL Training Dataset")
    st.caption(
        "Every tape-out ready design is automatically saved here "
        "as a training example for the custom RTL model."
    )

    examples = load_all_examples()
    n        = len(examples)
    needed   = max(0, MIN_EXAMPLES_FOR_TRAINING - n)

    # Progress toward training threshold
    progress = min(1.0, n / MIN_EXAMPLES_FOR_TRAINING)
    st.progress(progress, f"{n} / {MIN_EXAMPLES_FOR_TRAINING} examples collected")

    if needed > 0:
        st.warning(f"Need {needed} more tape-out ready designs before training.")
    else:
        st.success(f"Dataset ready for training! {n} verified examples collected.")

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Examples",  n)
    m2.metric("Simple",    sum(1 for e in examples if e.complexity == "simple"))
    m3.metric("Medium",    sum(1 for e in examples if e.complexity == "medium"))
    m4.metric("Complex",   sum(1 for e in examples if e.complexity == "complex"))

    # Seed + export buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌱 Seed from existing runs", key=f"{key}_seed"):
            with st.spinner("Scanning runs directory..."):
                added = seed_from_existing_runs()
            st.success(f"Added {added} examples from existing runs")
            st.rerun()

    with col2:
        if st.button("📦 Export dataset", key=f"{key}_export"):
            with st.spinner("Exporting..."):
                stats = export_dataset(Path("training_data/export"))
            st.success(f"Exported {stats.get('total', 0)} examples")
            if stats.get("summary", {}).get("ready_for_training"):
                st.info("Dataset is ready for Phase 4 fine-tuning!")

    # Browse examples
    if examples:
        st.divider()
        st.markdown(f"#### Examples ({n} total)")

        search = st.text_input("Search by description", key=f"{key}_search")
        filtered = [e for e in examples
                    if not search or search.lower() in e.description.lower()]

        for i, ex in enumerate(filtered[:20]):
            with st.expander(
                f"[{ex.complexity.upper()}] {ex.module_name} — "
                f"Q={ex.quality_score():.2f} | {ex.rtl_lines} lines | "
                f"GDS {ex.gds_size_kb:.0f} KB"
            ):
                st.caption(f"**Description:** {ex.description}")
                st.caption(
                    f"DRC={ex.drc_violations} | LVS={ex.lvs_status} | "
                    f"Fmax={ex.fmax_mhz} | Provider={ex.llm_provider}"
                )
                st.code(ex.rtl_code[:1000], language="verilog")

        if len(filtered) > 20:
            st.caption(f"Showing 20 of {len(filtered)} examples. Use search to filter.")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="RTL Training Dataset Builder")
    parser.add_argument("--stats",  action="store_true", help="Show dataset statistics")
    parser.add_argument("--export", action="store_true", help="Export dataset for training")
    parser.add_argument("--seed",   action="store_true", help="Seed from existing pipeline runs")
    parser.add_argument("--output", type=str, default="training_data/export",
                        help="Export output directory")
    args = parser.parse_args()

    if args.seed:
        seed_from_existing_runs()

    if args.stats:
        examples = load_all_examples()
        n = len(examples)
        print(f"\nDataset Statistics")
        print(f"  Total examples : {n}")
        print(f"  Need for Phase 4: {MIN_EXAMPLES_FOR_TRAINING}")
        print(f"  Progress       : {min(100, n*100//MIN_EXAMPLES_FOR_TRAINING)}%")
        if examples:
            print(f"  Avg quality    : {sum(e.quality_score() for e in examples)/n:.2f}")
            print(f"  Complexity     : {dict((c, sum(1 for e in examples if e.complexity==c)) for c in ['simple','medium','complex'])}")
            print(f"  Providers      : {dict((p, sum(1 for e in examples if e.llm_provider==p)) for p in set(e.llm_provider for e in examples))}")
        if n >= MIN_EXAMPLES_FOR_TRAINING:
            print(f"\n  READY FOR TRAINING — run: python dataset_builder.py --export")
        else:
            print(f"\n  Need {MIN_EXAMPLES_FOR_TRAINING - n} more examples.")
            print(f"  Run more designs through the pipeline to collect examples.")

    if args.export:
        export_dataset(Path(args.output))
