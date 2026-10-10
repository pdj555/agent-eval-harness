"""Regression tracking: an append-only JSONL log of suite runs.

Every scored run gets one line: when, what agent and variant, the headline
metrics, and enough context to reproduce. `render_trend` turns the log
into a table so a team can see whether a prompt change helped or hurt
across runs instead of trusting one afternoon's numbers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from metrics.aggregate import SuiteMetrics


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_run(
    path: str | Path,
    *,
    agent_name: str,
    variant: str,
    metrics: SuiteMetrics,
    git_sha: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one run record to the JSONL log. Returns the record."""
    record: dict[str, Any] = {
        "ts": _utc_now(),
        "agent": agent_name,
        "variant": variant,
        "n_tasks": metrics.n_tasks,
        "n_runs": metrics.n_runs,
        "solve_rate": round(metrics.solve_rate, 4),
        "cost_per_solve_usd": (
            round(metrics.cost_per_solve_usd, 4)
            if metrics.cost_per_solve_usd is not None
            else None
        ),
        "p50_latency_s": round(metrics.p50_latency_s, 3),
        "p90_latency_s": round(metrics.p90_latency_s, 3),
        "reliability": round(metrics.reliability, 4),
        "git_sha": git_sha,
    }
    if extra:
        record["extra"] = extra
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record


def load_history(path: str | Path) -> list[dict[str, Any]]:
    """Read all records from the JSONL log, oldest first."""
    p = Path(path)
    if not p.exists():
        return []
    records = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def render_trend(path: str | Path, metric: str = "solve_rate") -> str:
    """Markdown table of one metric across logged runs."""
    records = load_history(path)
    lines = [
        f"# Trend: {metric}",
        "",
        "| time | agent | variant | " + metric + " |",
        "|---|---|---|---|",
    ]
    for r in records:
        val = r.get(metric)
        cell = f"{val:.1%}" if isinstance(val, float) and metric == "solve_rate" else str(val)
        lines.append(f"| {r['ts']} | {r['agent']} | {r['variant']} | {cell} |")
    return "\n".join(lines)


def render_delta(old: dict[str, Any], new: dict[str, Any]) -> str:
    """Markdown delta table comparing two run records."""
    keys = ["solve_rate", "cost_per_solve_usd", "p50_latency_s", "reliability"]
    lines = ["# Run delta", "", "| metric | before | after | delta |", "|---|---|---|---|"]
    for k in keys:
        a, b = old.get(k), new.get(k)
        if a is None or b is None:
            lines.append(f"| {k} | {a} | {b} | n/a |")
            continue
        d = b - a
        sign = "+" if d >= 0 else ""
        lines.append(f"| {k} | {a} | {b} | {sign}{d:.4f} |")
    return "\n".join(lines)


def latest_for(path: str | Path, agent: str, variant: str) -> dict[str, Any] | None:
    """Most recent record matching an agent and variant, or None."""
    matches = [
        r for r in load_history(path) if r["agent"] == agent and r["variant"] == variant
    ]
    return matches[-1] if matches else None
