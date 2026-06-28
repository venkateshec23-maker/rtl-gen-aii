"""
provider_orchestrator.py — Intelligent Provider Scheduling & Quality Evaluation
RTL-Gen AI

Replaces the sequential provider loop with:
  - ProviderHealthManager (health states, cooldowns, rate-limit parsing)
  - QualityEvaluator (scores RTL 0-100 with detailed breakdown)
  - ReflectionLoop (quality-feedback-driven repair)
  - ProviderMemory (disk persistence of provider statistics)
  - Smart scheduling (ranks providers by health × quality - latency - failures)

Usage:
    from provider_orchestrator import run_smart_generation
    result = run_smart_generation(description, module_name)

Maintains backward compatibility with existing _provider_health API.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Re-export the module-level singleton for backward compatibility

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

PROVIDER_NAMES = ["groq", "openrouter", "gemini", "github", "nvidia", "local", "opencode"]
"""All known provider names."""

MEMORY_FILE = Path(os.getenv("PROVIDER_MEMORY_FILE", "")) or (
    Path(os.getenv("OPENLANE_WORK", r"C:\tools\OpenLane")) / "provider_memory.json"
)
"""Path to persisted provider statistics."""

HEALTH_STATES = ["healthy", "degraded", "rate_limited", "daily_limit", "timeout", "unavailable"]

COOLDOWN_SECONDS = {
    "rate_limited": 60,
    "daily_limit": 3600,
    "timeout": 300,
    "unavailable": 120,
    "ssl_error": 300,
    "auth_error": 86400,
    "unknown": 30,
}

QUALITY_THRESHOLD = 70
"""Minimum quality score to accept RTL (0-100)."""

# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class ProviderStats:
    """Persistent statistics for one provider."""
    name: str = ""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rate_limited_count: int = 0
    timeout_count: int = 0
    total_latency_sec: float = 0.0
    compile_success_count: int = 0
    compile_total_count: int = 0
    simulation_success_count: int = 0
    simulation_total_count: int = 0
    total_quality_score: float = 0.0
    quality_entries: int = 0
    last_used: Optional[float] = None
    last_error: str = ""
    consecutive_failures: int = 0

    @property
    def avg_latency(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_sec / self.total_calls

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.5  # neutral prior
        return self.successful_calls / self.total_calls

    @property
    def avg_quality(self) -> float:
        if self.quality_entries == 0:
            return 50.0  # neutral prior
        return self.total_quality_score / self.quality_entries

    @property
    def compile_rate(self) -> float:
        if self.compile_total_count == 0:
            return 0.5
        return self.compile_success_count / self.compile_total_count

    @property
    def simulation_rate(self) -> float:
        if self.simulation_total_count == 0:
            return 0.5
        return self.simulation_success_count / self.simulation_total_count


@dataclass
class QualityReport:
    """Detailed quality evaluation of generated RTL."""
    score: float = 0.0
    always_block_count: int = 0
    pipeline_register_count: int = 0
    fsm_state_count: int = 0
    control_logic_signals: int = 0
    module_count: int = 0
    assign_statement_count: int = 0
    reset_logic_present: bool = False
    signal_connectivity_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        parts = [f"Quality: {self.score:.0f}/100"]
        if self.issues:
            details = "; ".join(self.issues[:3])
            if len(self.issues) > 3:
                details += f" (+{len(self.issues) - 3} more)"
            parts.append(f"Issues: {details}")
        return " | ".join(parts)


@dataclass
class ProviderRecord:
    """Runtime state for a single provider."""
    name: str
    health: str = "healthy"  # healthy | degraded | rate_limited | daily_limit | timeout | unavailable
    last_failure_reason: str = ""
    retry_after: float = 0.0  # timestamp
    consecutive_failures: int = 0
    avg_response_time: float = 0.0
    avg_quality_score: float = 50.0
    total_calls: int = 0
    successful_calls: int = 0
    model: str = ""

    @property
    def in_cooldown(self) -> bool:
        if self.retry_after == 0:
            return False
        return time.time() < self.retry_after

    @property
    def remaining_cooldown(self) -> float:
        return max(0.0, self.retry_after - time.time())

    @property
    def health_score(self) -> float:
        mapping = {
            "healthy": 1.0,
            "degraded": 0.6,
            "rate_limited": 0.0,
            "daily_limit": 0.0,
            "timeout": 0.2,
            "unavailable": 0.0,
        }
        return mapping.get(self.health, 0.0)

    @property
    def is_available(self) -> bool:
        if self.in_cooldown:
            return False
        return self.health_score > 0.0


# ── ProviderHealthManager ─────────────────────────────────────────────────────


class ProviderHealthManager:
    """
    Tracks provider health with full state machine.

    States: healthy → degraded → rate_limited | daily_limit | timeout | unavailable

    Features:
      - Per-provider cooldown with Retry-After header parsing
      - Exponential backoff for 429s
      - Consecutive failure tracking
      - Average response time tracking
      - Average quality score tracking
      - Disk persistence via ProviderMemory
    """

    def __init__(self, memory: Optional["ProviderMemory"] = None):
        self._providers: Dict[str, ProviderRecord] = {}
        self._memory = memory
        self._response_times: Dict[str, List[float]] = {}
        for name in PROVIDER_NAMES:
            self._providers[name] = ProviderRecord(name=name)
            self._response_times[name] = []
        self._load_from_memory()

    def _load_from_memory(self) -> None:
        if self._memory is None:
            return
        stats = self._memory.load_all()
        for name, s in stats.items():
            if name in self._providers:
                p = self._providers[name]
                p.total_calls = s.total_calls
                p.successful_calls = s.successful_calls
                p.avg_response_time = s.avg_latency
                if s.quality_entries > 0:
                    p.avg_quality_score = s.avg_quality
                if s.consecutive_failures > 0:
                    p.consecutive_failures = s.consecutive_failures
                    if s.consecutive_failures >= 3:
                        p.health = "degraded"

    def get(self, name: str) -> ProviderRecord:
        """Get or create a provider record."""
        if name not in self._providers:
            self._providers[name] = ProviderRecord(name=name)
            self._response_times[name] = []
        return self._providers[name]

    def record_success(self, name: str, latency: float = 0.0, quality: float = 50.0) -> None:
        """Record a successful generation."""
        p = self.get(name)
        p.total_calls += 1
        p.successful_calls += 1
        p.consecutive_failures = 0
        p.health = "healthy"
        p.retry_after = 0.0
        if latency > 0:
            self._response_times[name].append(latency)
            if len(self._response_times[name]) > 10:
                self._response_times[name] = self._response_times[name][-10:]
            p.avg_response_time = sum(self._response_times[name]) / len(self._response_times[name])
        p.avg_quality_score = 0.9 * p.avg_quality_score + 0.1 * quality
        self._persist(name)

    def record_failure(self, name: str, error_str: str) -> None:
        """Record a failure with error classification."""
        p = self.get(name)
        p.total_calls += 1
        p.consecutive_failures += 1
        p.last_failure_reason = error_str[:200]
        error_type = self._classify_error(error_str)

        cooldown = COOLDOWN_SECONDS.get(error_type, 30)
        if error_type == "rate_limit_429":
            # Exponential backoff: 60s, 120s, 240s, ...
            cooldown = 60 * (2 ** min(p.consecutive_failures - 1, 5))
        p.retry_after = time.time() + cooldown
        p.health = "rate_limited" if error_type == "rate_limit_429" else error_type

        log.info(
            "Provider %s → %s (cooldown %ds, consecutive=%d)",
            name, error_type, cooldown, p.consecutive_failures,
        )
        self._persist(name)

    def _classify_error(self, error_str: str) -> str:
        """Classify an error string into a health state."""
        e = error_str.lower()
        if "429" in e or "rate limit" in e or "rate_limit" in e or "too many requests" in e:
            return "rate_limit_429"
        if "daily" in e or "token" in e or "quota" in e or "insufficient_quota" in e:
            return "daily_limit"
        if "timed out" in e or "timeout" in e or "deadline" in e:
            return "timeout"
        if "ssl" in e or "handshake" in e or "certificate" in e:
            return "ssl_error"
        if "401" in e or "403" in e or "auth" in e or "unauthorized" in e or "api key" in e:
            return "auth_error"
        if "503" in e or "502" in e or "unavailable" in e or "service" in e:
            return "unavailable"
        return "unknown"

    def is_available(self, name: str) -> bool:
        """Check if a provider is available right now."""
        p = self.get(name)
        if p.in_cooldown:
            return False
        return p.is_available

    def skip_reason(self, name: str) -> str:
        """Human-readable reason why a provider is skipped."""
        p = self.get(name)
        if p.in_cooldown:
            return f"{p.health} (cooldown {p.remaining_cooldown:.0f}s)"
        if not p.is_available:
            return p.health
        return ""

    def rank_providers(self, use_model: Optional[str] = None) -> List[Tuple[str, str, float]]:
        """
        Rank available providers by score.
        Returns list of (provider_name, model, score) sorted descending.
        """
        scored: List[Tuple[str, str, float]] = []

        for name, p in self._providers.items():
            if not p.is_available:
                continue

            # Provider score = health × quality - latency penalty - failure penalty
            health = p.health_score
            quality = p.avg_quality_score / 100.0
            latency_penalty = min(p.avg_response_time / 60.0, 1.0) * 0.2
            failure_penalty = min(p.consecutive_failures / 5.0, 1.0) * 0.3

            score = (health * 0.4 + quality * 0.4) - latency_penalty - failure_penalty
            if score < 0:
                score = 0.0

            model = ""
            if name == "openrouter":
                model = use_model or os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

            scored.append((name, model, round(score, 3)))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored

    def status(self) -> Dict[str, str]:
        """Return current health status of all providers."""
        return {n: p.health for n, p in self._providers.items()}

    def all_unavailable(self) -> bool:
        """Return True if every provider is unavailable."""
        return all(not p.is_available for p in self._providers.values())

    def _persist(self, name: str) -> None:
        if self._memory is None:
            return
        p = self.get(name)
        stats = ProviderStats(
            name=name,
            total_calls=p.total_calls,
            successful_calls=p.successful_calls,
            failed_calls=p.total_calls - p.successful_calls,
            avg_latency=self._avg_latency_from_records(),
            consecutive_failures=p.consecutive_failures,
            last_error=p.last_failure_reason,
        )
        self._memory.save(name, stats)

    def _avg_latency_from_records(self) -> float:
        all_times = []
        for tl in self._response_times.values():
            all_times.extend(tl)
        if not all_times:
            return 0.0
        return sum(all_times) / len(all_times)


# ── QualityEvaluator ──────────────────────────────────────────────────────────


class QualityEvaluator:
    """
    Evaluates generated RTL quality on a 0-100 scale.

    Scoring dimensions:
      - always blocks         (max 15)
      - pipeline registers    (max 15)
      - FSM states            (max 10)
      - control logic signals (max 10)
      - module count          (max 10)
      - assign statements     (max 10)
      - reset logic           (max 15)
      - signal connectivity   (max 15)
    """

    def evaluate(self, rtl_code: str, description: str = "") -> QualityReport:
        report = QualityReport()
        if not rtl_code or len(rtl_code.strip()) < 20:
            report.issues.append("RTL code is empty or too short")
            report.score = 0.0
            report.passed = False
            return report

        rtl_lower = rtl_code.lower()
        total = 0.0

        # 1. Always blocks (max 15)
        always_count = len(re.findall(r"\balways\s*@", rtl_code))
        report.always_block_count = always_count
        if always_count == 0:
            report.issues.append("No always blocks — likely not sequential logic")
            total += 0
        elif always_count == 1:
            report.warnings.append("Only one always block — verify this is intentional")
            total += 8
        elif always_count >= 5:
            total += 15
        else:
            total += 10 + always_count

        # 2. Pipeline registers (max 15)
        pipeline_sigs = ["if_id", "id_ex", "ex_mem", "mem_wb", "pipeline_reg",
                         "stage_reg", "fetch_reg", "decode_reg", "execute_reg"]
        pipe_count = sum(1 for s in pipeline_sigs if s in rtl_lower)
        report.pipeline_register_count = pipe_count
        total += min(pipe_count * 3, 15)

        # 3. FSM states (max 10)
        state_patterns = [
            r"\bstate\b", r"\bnext_state\b", r"\bidle\b",
            r"\bcstate\b", r"\bnstate\b", r"\bcurrent_state\b",
        ]
        fsm_count = sum(1 for p in state_patterns if re.search(p, rtl_lower))
        report.fsm_state_count = fsm_count
        total += min(fsm_count * 2.5, 10)

        # 4. Control logic signals (max 10)
        control_sigs = ["enable", "start", "done", "ready", "valid",
                        "busy", "sel", "mode", "wr_en", "rd_en", "we", "re"]
        ctrl_count = sum(1 for s in control_sigs if re.search(rf"\b{s}\b", rtl_lower))
        report.control_logic_signals = ctrl_count
        total += min(ctrl_count, 10)

        # 5. Module count (max 10)
        module_count = len(re.findall(r"\bmodule\s+\w+", rtl_code))
        report.module_count = module_count
        if module_count >= 3:
            total += 10
        elif module_count == 2:
            total += 7
        else:
            total += 3

        # 6. Assign statements (max 10)
        assign_count = len(re.findall(r"\bassign\b", rtl_code))
        report.assign_statement_count = assign_count
        total += min(assign_count, 10)

        # 7. Reset logic (max 15)
        has_reset = bool(re.search(r"\b(reset_n|reset|rst|rst_n)\b", rtl_lower))
        has_async_reset = bool(re.search(r"negedge\s+(reset_n|rst_n|reset)", rtl_lower))
        report.reset_logic_present = has_reset
        if has_async_reset:
            total += 15
        elif has_reset:
            total += 10
        else:
            report.issues.append("No reset logic detected")
            total += 0

        # 8. Signal connectivity (max 15)
        port_count = len(re.findall(r"\b(input|output|inout)\s+", rtl_code))
        wire_reg_count = len(re.findall(r"\b(wire|reg)\s+", rtl_code))
        connectivity = port_count + wire_reg_count
        report.signal_connectivity_score = min(connectivity / 20.0 * 15, 15)
        total += report.signal_connectivity_score

        report.score = min(round(total, 1), 100.0)
        report.passed = report.score >= QUALITY_THRESHOLD

        if not report.passed:
            report.issues.append(f"Quality score {report.score:.0f}/100 below threshold {QUALITY_THRESHOLD}")

        return report


# ── ReflectionLoop ────────────────────────────────────────────────────────────


class ReflectionLoop:
    """
    Quality-feedback-driven repair loop.
    When RTL fails quality checks, provides the quality report and
    explicit repair instructions instead of asking "generate again".
    """

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def build_reflection_prompt(
        self,
        description: str,
        module_name: str,
        rtl_code: str,
        quality_report: QualityReport,
        original_error: str = "",
    ) -> str:
        """Build a prompt with quality feedback and explicit repair instructions."""
        instructions = []
        if quality_report.always_block_count < 2:
            instructions.append("Need more always blocks for sequential logic")
        if quality_report.pipeline_register_count < 2:
            instructions.append("Missing pipeline registers — add IF/ID, ID/EX, EX/MEM, MEM/WB registers")
        if quality_report.fsm_state_count < 2:
            instructions.append("Need FSM state encoding (parameter states + case statement)")
        if not quality_report.reset_logic_present:
            instructions.append("Missing reset logic — add async reset (negedge reset_n)")
        if quality_report.module_count < 2:
            instructions.append("Consider splitting into sub-modules for better structure")
        if quality_report.assign_statement_count < 2:
            instructions.append("Add assign statements for combinational logic")

        if not instructions:
            instructions.append("Improve overall quality — increase test coverage and robustness")

        prompt = f"""You are repairing existing Verilog RTL. Do NOT regenerate from scratch.
Fix the SPECIFIC issues listed below while keeping the existing structure.

MODULE: {module_name}
DESCRIPTION: {description}

PREVIOUS RTL (needs repair):
```verilog
{rtl_code[:5000]}
```

QUALITY REPORT (score: {quality_report.score:.0f}/100 — minimum is 70):
  Issues found:
"""
        for issue in quality_report.issues[:5]:
            prompt += f"    - {issue}\n"
        prompt += "\n  Warnings:\n"
        for w in quality_report.warnings[:3]:
            prompt += f"    - {w}\n"

        prompt += f"""
EXPLICIT REPAIR INSTRUCTIONS:
"""
        for inst in instructions:
            prompt += f"  - {inst}\n"

        if original_error:
            prompt += f"""
PREVIOUS ERROR:
{original_error[:1000]}
"""
        prompt += """
Repair the existing RTL. Keep the module interface (ports) the same.
Fix ONLY the issues listed above. Output the complete repaired module.

Respond with ONLY the Verilog code in a ```verilog block.
"""
        return prompt

    def should_retry(self, attempt: int, quality_report: QualityReport) -> bool:
        """Decide whether to retry based on attempt count and quality."""
        if attempt >= self.max_attempts:
            return False
        if quality_report.score >= QUALITY_THRESHOLD:
            return False
        return True


# ── ProviderMemory ────────────────────────────────────────────────────────────


class ProviderMemory:
    """
    Persists provider statistics to a JSON file on disk.
    Tracks success rate, compile rate, simulation rate, average quality, etc.
    """

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or MEMORY_FILE
        self._cache: Dict[str, ProviderStats] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self.filepath and self.filepath.exists():
                data = json.loads(self.filepath.read_text(encoding="utf-8"))
                for name, d in data.items():
                    s = ProviderStats(**d)
                    self._cache[name] = s
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    def _save_cache(self) -> None:
        try:
            if self.filepath:
                data = {n: asdict(s) for n, s in self._cache.items()}
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
                self.filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except OSError as e:
            log.debug("ProviderMemory save error: %s", e)

    def save(self, name: str, stats: ProviderStats) -> None:
        self._cache[name] = stats
        self._save_cache()

    def load(self, name: str) -> Optional[ProviderStats]:
        return self._cache.get(name)

    def load_all(self) -> Dict[str, ProviderStats]:
        return dict(self._cache)

    def clear(self) -> None:
        self._cache.clear()
        self._save_cache()


# ── Smart generation ──────────────────────────────────────────────────────────


def build_quality_feedback(
    description: str,
    module_name: str,
    rtl_code: str,
    quality_report: QualityReport,
) -> str:
    """Build a structured quality feedback string for logs and UI."""
    lines = [
        f"Quality feedback for {module_name}:",
        f"  Score: {quality_report.score:.0f}/100 (threshold: {QUALITY_THRESHOLD})",
        f"  Always blocks: {quality_report.always_block_count}",
        f"  Pipeline registers: {quality_report.pipeline_register_count}",
        f"  FSM states: {quality_report.fsm_state_count}",
        f"  Control signals: {quality_report.control_logic_signals}",
        f"  Reset logic: {'Yes' if quality_report.reset_logic_present else 'No'}",
    ]
    if quality_report.issues:
        for issue in quality_report.issues:
            lines.append(f"  Issue: {issue}")
    return "\n".join(lines)


def run_smart_generation(
    description: str,
    module_name: str,
    llm_provider: str = "groq",
    openrouter_model: Optional[str] = None,
    max_attempts: int = 3,
    provider_health: Optional[ProviderHealthManager] = None,
    quality_evaluator: Optional[QualityEvaluator] = None,
    reflection_loop: Optional[ReflectionLoop] = None,
    generate_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Run intelligent provider scheduling with quality evaluation.

    This replaces the sequential provider loop in generate_and_validate().
    Returns the same result dict format for backward compatibility.

    Args:
        description: Natural language design description
        module_name: Verilog module name
        llm_provider: Preferred provider
        openrouter_model: Specific OpenRouter model
        max_attempts: Maximum generation attempts
        provider_health: ProviderHealthManager instance
        quality_evaluator: QualityEvaluator instance
        reflection_loop: ReflectionLoop instance
        generate_fn: Callable(provider, model) -> (rtl, tb)

    Returns:
        Dict with status, rtl, testbench, provider, attempts, etc.
    """
    ph = provider_health or ProviderHealthManager()
    qe = quality_evaluator or QualityEvaluator()
    rl = reflection_loop or ReflectionLoop()

    last_error: Optional[str] = None
    best_rtl = ""
    best_tb = ""
    attempts_made = 0
    used_providers: List[str] = []

    # Early abort: if every provider is unavailable, return immediately
    if ph.all_unavailable():
        statuses = {n: f"{p.health} (cooldown {p.remaining_cooldown:.0f}s)" if p.in_cooldown else p.health
                     for n, p in ph._providers.items()}
        return {
            "status": "GENERATION_UNAVAILABLE",
            "module_name": module_name,
            "rtl": "",
            "testbench": "",
            "error": f"All providers unavailable: {statuses}",
            "attempts": 0,
            "provider": "",
            "quality_report": None,
        }

    for attempt in range(1, max_attempts + 1):
        ranked = ph.rank_providers(use_model=openrouter_model)
        if not ranked:
            log.warning("No ranked providers available at attempt %d", attempt)
            break

        best_provider, best_model, best_score = ranked[0]
        used_providers.append(best_provider)
        attempts_made = attempt

        log.info(
            "Attempt %d/%d | Provider: %s (score=%.3f) | Model: %s",
            attempt, max_attempts, best_provider, best_score, best_model or "default",
        )

        # Generate
        t0 = time.time()
        try:
            if generate_fn:
                rtl, tb = generate_fn(best_provider, best_model)
            else:
                rtl, tb = _call_provider(best_provider, best_model, description, module_name)
            latency = time.time() - t0
        except Exception as e:
            latency = time.time() - t0
            err_str = str(e)
            last_error = err_str
            ph.record_failure(best_provider, err_str)
            log.warning("Generation failed: %s | provider=%s | latency=%.1fs", err_str[:100], best_provider, latency)
            continue

        if not rtl:
            ph.record_failure(best_provider, "Empty RTL generated")
            log.warning("Empty RTL from %s", best_provider)
            continue

        # Quality evaluation
        quality_report = qe.evaluate(rtl, description)
        ph.record_success(best_provider, latency, quality_report.score)

        log.info(
            "Quality: %.1f/100 | provider=%s | latency=%.1fs | issues=%d",
            quality_report.score, best_provider, latency, len(quality_report.issues),
        )

        if quality_report.passed:
            best_rtl = rtl
            best_tb = tb or ""
            return {
                "status": "QUALITY_PASSED",
                "module_name": module_name,
                "rtl": best_rtl,
                "testbench": best_tb,
                "provider": best_provider,
                "attempts": attempts_made,
                "error": None,
                "quality_report": quality_report.to_dict(),
                "quality_summary": quality_report.summary(),
            }

        # Failed quality — run reflection loop
        if rl.should_retry(attempt, quality_report):
            log.info("Reflection loop: attempt %d quality=%.1f — repairing", attempt, quality_report.score)
            reflection_prompt = rl.build_reflection_prompt(
                description, module_name, rtl, quality_report,
                original_error=last_error or "",
            )
            try:
                fixed_rtl, fixed_tb = _call_reflection(
                    best_provider, best_model, reflection_prompt, module_name
                )
                if fixed_rtl:
                    fixed_quality = qe.evaluate(fixed_rtl, description)
                    log.info("Reflection quality: %.1f/100 (was %.1f)", fixed_quality.score, quality_report.score)
                    if fixed_quality.score > quality_report.score:
                        rtl = fixed_rtl
                        tb = fixed_tb or tb
                        quality_report = fixed_quality
                        if quality_report.passed:
                            best_rtl = rtl
                            best_tb = tb or ""
                            return {
                                "status": "QUALITY_PASSED",
                                "module_name": module_name,
                                "rtl": best_rtl,
                                "testbench": best_tb,
                                "provider": best_provider,
                                "attempts": attempts_made,
                                "error": None,
                                "quality_report": quality_report.to_dict(),
                                "quality_summary": quality_report.summary(),
                            }
            except Exception as ref_err:
                log.warning("Reflection repair error: %s", ref_err)

    # All attempts exhausted
    return {
        "status": "GENERATION_FAILED",
        "module_name": module_name,
        "rtl": best_rtl,
        "testbench": best_tb,
        "provider": used_providers[-1] if used_providers else "",
        "attempts": attempts_made,
        "error": last_error or "All providers failed or unavailable",
        "quality_report": None,
    }


def _call_provider(
    provider: str, model: str, description: str, module_name: str
) -> Tuple[str, str]:
    """Dispatch to the correct provider function."""
    from verilog_generator import (
        generate_verilog_groq,
        generate_verilog_openrouter,
        generate_verilog_github,
        generate_verilog_gemini,
        generate_verilog_nvidia,
        generate_verilog_opencode,
        generate_verilog_local_model,
    )

    dispatch = {
        "groq": lambda: generate_verilog_groq(description, module_name),
        "openrouter": lambda: generate_verilog_openrouter(description, module_name, model=model),
        "github": lambda: generate_verilog_github(description, module_name),
        "gemini": lambda: generate_verilog_gemini(description, module_name),
        "nvidia": lambda: generate_verilog_nvidia(description, module_name),
        "opencode": lambda: generate_verilog_opencode(description, module_name),
        "local": lambda: generate_verilog_local_model(description, module_name),
    }
    fn = dispatch.get(provider)
    if fn is None:
        raise ValueError(f"Unknown provider '{provider}'")
    return fn()


def _call_reflection(
    provider: str, model: str, prompt: str, module_name: str
) -> Tuple[str, str]:
    """Call LLM with reflection prompt for quality-driven repair."""
    import httpx

    keys = {
        "groq": os.getenv("GROQ_API_KEY"),
        "github": os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_KEY"),
        "openrouter": os.getenv("OPENROUTER_API_KEY"),
    }
    api_key = keys.get(provider, "")
    if not api_key:
        return "", ""

    urls = {
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "github": "https://models.inference.ai.azure.com/chat/completions",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    }
    url = urls.get(provider)
    if not url:
        return "", ""

    payload = {
        "model": model or "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.3,
    }
    try:
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            m = re.search(r"```verilog\s*\n(.*?)```", content, re.DOTALL)
            rtl = m.group(1).strip() if m else content.strip()
            return rtl, ""
    except Exception as e:
        log.debug("Reflection call failed: %s", e)
    return "", ""


# ── Structured logging ────────────────────────────────────────────────────────


def log_provider_decision(
    provider: str,
    health: str,
    latency: float,
    quality: float,
    compile_ok: bool = False,
    sim_ok: bool = False,
    reason: str = "",
    retry_decision: str = "",
) -> None:
    """Produce a structured log line for provider decisions."""
    log.info(
        "PROVIDER | %s | health=%s | latency=%.1fs | quality=%.1f | "
        "compile=%s | sim=%s | reason=%s | retry=%s",
        provider, health, latency, quality,
        "OK" if compile_ok else "FAIL",
        "OK" if sim_ok else "FAIL",
        reason or "-",
        retry_decision or "-",
    )


# ── Self-test ─────────────────────────────────────────────────────────────────


def self_test() -> bool:
    """Run self-tests."""
    passed = 0
    failed = 0

    # Test ProviderHealthManager
    ph = ProviderHealthManager()
    assert ph.is_available("groq") is True
    assert ph.all_unavailable() is False
    passed += 1

    # Test failure recording
    ph.record_failure("groq", "429 Too Many Requests")
    assert ph.get("groq").health == "rate_limited"
    assert ph.get("groq").in_cooldown is True
    assert ph.is_available("groq") is False
    passed += 1

    # Test ranking (groq is in cooldown, others should rank)
    ranked = ph.rank_providers()
    assert len(ranked) >= 5  # at least 5 other providers
    assert ranked[0][0] != "groq"  # groq should not be first
    passed += 1

    # Test QualityEvaluator
    qe = QualityEvaluator()
    sample_rtl = """\
module test (
    input clk,
    input reset_n,
    input enable,
    output reg [7:0] count
);
    reg [7:0] state;
    wire [7:0] next_count;
    assign next_count = count + 1;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            count <= 0;
            state <= 0;
        end else if (enable) begin
            count <= next_count;
            state <= state + 1;
        end
    end

    always @(*) begin
        case (state)
            0: count = 0;
            1: count = 1;
            default: count = 0;
        endcase
    end
endmodule"""
    qr = qe.evaluate(sample_rtl)
    assert qr.score >= 70, f"Score too low: {qr.score}"
    assert qr.passed is True
    assert qr.always_block_count >= 1
    assert qr.reset_logic_present is True
    passed += 1

    # Test empty RTL
    qr = qe.evaluate("")
    assert qr.score == 0
    assert qr.passed is False
    passed += 1

    # Test stub RTL
    stub = "module test (input a, output b); assign b = a; endmodule"
    qr = qe.evaluate(stub)
    assert qr.score < 70, f"Stub score too high: {qr.score}"
    assert qr.passed is False
    passed += 1

    # Test ReflectionLoop
    rl = ReflectionLoop(max_attempts=2)
    assert rl.should_retry(1, qr) is True  # score < 70, attempt 1 < 2
    assert rl.should_retry(2, qr) is False  # attempt 2 >= 2
    qr_high = QualityReport(score=85.0, passed=True)
    assert rl.should_retry(1, qr_high) is False  # already passed
    passed += 1

    # Test reflection prompt generation
    prompt = rl.build_reflection_prompt("test", "test", sample_rtl, qr)
    assert "REPAIR INSTRUCTIONS" in prompt
    assert "```verilog" not in prompt  # prompt should not contain code fence for the instructions
    passed += 1

    # Test ProviderMemory
    mem = ProviderMemory(filepath=None)  # In-memory only
    stats = ProviderStats(name="test_provider", total_calls=10, successful_calls=8)
    mem.save("test_provider", stats)
    loaded = mem.load("test_provider")
    assert loaded is not None
    assert loaded.total_calls == 10
    assert loaded.successful_calls == 8
    passed += 1

    total = passed + failed
    print(f"[provider_orchestrator] Self-test: {passed}/{total} passed")
    return failed == 0


if __name__ == "__main__":
    import sys
    ok = self_test()
    print()
    print("provider_orchestrator.py — all tests passed" if ok else "provider_orchestrator.py — TESTS FAILED")
    sys.exit(0 if ok else 1)
