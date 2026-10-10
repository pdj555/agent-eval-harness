"""Failure analysis: what went wrong, and which variants fix what.

A solve rate hides the mechanism. Two variants can tie at 70% while
failing for completely different reasons. Classifying failures by type
shows which prompt changes fix which failure modes, which is the actual
decision a team needs to make.
"""

from __future__ import annotations

from harness.runner import RunResult

FAILURE_TYPES = (
    "agent_crash",
    "no_output",
    "timeout",
    "syntax_error",
    "import_error",
    "name_error",
    "assertion_failure",
    "unknown",
)


def classify(result: RunResult) -> str:
    """Classify a single run's failure mode. Returns 'solved' on success."""
    if result.solved:
        return "solved"
    if result.error:
        return "agent_crash"
    detail = (result.detail or "").lower()
    if "no solution" in detail:
        return "no_output"
    if "timed out" in detail:
        return "timeout"
    out = ((getattr(result, "stdout", "") or "") + "\n" + detail).lower()
    if "syntaxerror" in out:
        return "syntax_error"
    if "importerror" in out or "modulenotfounderror" in out:
        return "import_error"
    if "nameerror" in out:
        return "name_error"
    if "assertionerror" in out or "failed" in detail or "error" in detail:
        return "assertion_failure"
    return "unknown"


def breakdown(results: list[RunResult]) -> dict[str, dict[str, int]]:
    """variant -> failure_type -> count (failures only)."""
    table: dict[str, dict[str, int]] = {}
    for r in results:
        kind = classify(r)
        if kind == "solved":
            continue
        table.setdefault(r.variant, {}).setdefault(kind, 0)
        table[r.variant][kind] += 1
    return table


def failure_rates(results: list[RunResult]) -> dict[str, dict[str, float]]:
    """variant -> failure_type -> fraction of that variant's runs."""
    totals: dict[str, int] = {}
    counts: dict[str, dict[str, int]] = {}
    for r in results:
        totals[r.variant] = totals.get(r.variant, 0) + 1
        kind = classify(r)
        if kind == "solved":
            continue
        counts.setdefault(r.variant, {}).setdefault(kind, 0)
        counts[r.variant][kind] += 1
    return {
        variant: {
            kind: counts.get(variant, {}).get(kind, 0) / totals[variant]
            for kind in FAILURE_TYPES
        }
        for variant in totals
    }


def fixes_report(results: list[RunResult]) -> str:
    """For each failure type, rank variants by failure rate, best first."""
    rates = failure_rates(results)
    variants = sorted(rates)
    lines = ["# Failure analysis", ""]
    for kind in FAILURE_TYPES:
        ranked = sorted(variants, key=lambda v: rates[v][kind])
        if all(rates[v][kind] == 0 for v in variants):
            continue
        cells = ", ".join(f"{v} {rates[v][kind]:.1%}" for v in ranked)
        lines.append(f"- **{kind}**: {cells}")
    if len(lines) == 2:
        lines.append("No failures observed.")
    return "\n".join(lines)


def render_breakdown_table(results: list[RunResult]) -> str:
    """Markdown cross-tab: variants as rows, failure types as columns."""
    table = breakdown(results)
    variants = sorted({r.variant for r in results})
    kinds = [k for k in FAILURE_TYPES if any(table.get(v, {}).get(k) for v in variants)]
    header = "| variant | " + " | ".join(kinds) + " |"
    sep = "|" + "---|" * (len(kinds) + 1)
    lines = ["# Failure breakdown", "", header, sep]
    for v in variants:
        row = " | ".join(str(table.get(v, {}).get(k, 0)) for k in kinds)
        lines.append(f"| {v} | {row} |")
    return "\n".join(lines)
