"""Render results as markdown tables."""

from __future__ import annotations

from harness.runner import RunResult
from .aggregate import SuiteMetrics, aggregate


def render_suite_table(results: list[RunResult]) -> str:
    m = aggregate(results)
    agent = results[0].agent_name
    variant = results[0].variant
    rows = [
        f"# Eval report: {agent} ({variant})",
        "",
        "| metric | value |",
        "|---|---|",
        f"| tasks | {m.n_tasks} |",
        f"| runs | {m.n_runs} |",
        f"| solve rate | {m.solve_rate:.1%} |",
    ]
    for k, v in sorted(m.pass_at_k.items()):
        rows.append(f"| pass@{k} | {v:.1%} |")
    cps = f"${m.cost_per_solve_usd:.4f}" if m.cost_per_solve_usd is not None else "n/a"
    rows += [
        f"| mean cost / task | ${m.mean_cost_usd:.4f} |",
        f"| cost per solve | {cps} |",
        f"| latency p50 | {m.p50_latency_s:.2f}s |",
        f"| latency p90 | {m.p90_latency_s:.2f}s |",
        f"| reliability | {m.reliability:.1%} |",
        f"| mean steps | {m.mean_steps:.1f} |",
    ]
    return "\n".join(rows)


def render_per_task_table(results: list[RunResult]) -> str:
    rows = ["| task | solved | latency | cost | detail |", "|---|---|---|---|---|"]
    for r in results:
        mark = "yes" if r.solved else "no"
        rows.append(
            f"| {r.task_id} | {mark} | {r.latency_s:.2f}s "
            f"| ${r.cost_usd:.4f} | {r.detail[:60]} |"
        )
    return "\n".join(rows)


def render_comparison_table(named: dict[str, SuiteMetrics]) -> str:
    rows = [
        "| variant | solve rate | cost/solve | p50 latency | reliability |",
        "|---|---|---|---|---|",
    ]
    for name, m in named.items():
        cps = f"${m.cost_per_solve_usd:.4f}" if m.cost_per_solve_usd is not None else "n/a"
        rows.append(
            f"| {name} | {m.solve_rate:.1%} | {cps} "
            f"| {m.p50_latency_s:.2f}s | {m.reliability:.1%} |"
        )
    return "\n".join(rows)
