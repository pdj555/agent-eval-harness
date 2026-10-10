"""Aggregate run results into the numbers that matter."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from harness.runner import RunResult


@dataclass(frozen=True)
class SuiteMetrics:
    n_tasks: int
    n_runs: int
    solve_rate: float
    pass_at_k: dict[int, float]
    mean_latency_s: float
    p50_latency_s: float
    p90_latency_s: float
    mean_cost_usd: float
    cost_per_solve_usd: float | None
    mean_steps: float
    reliability: float  # fraction of tasks solved on every repeat

    def summary(self) -> str:
        cps = f"${self.cost_per_solve_usd:.4f}" if self.cost_per_solve_usd is not None else "n/a"
        lines = [
            f"solve_rate      {self.solve_rate:.3f}",
            f"cost_per_solve  {cps}",
            f"latency_p50     {self.p50_latency_s:.2f}s",
            f"latency_p90     {self.p90_latency_s:.2f}s",
            f"reliability     {self.reliability:.3f}",
        ]
        for k, v in sorted(self.pass_at_k.items()):
            lines.append(f"pass@{k}         {v:.3f}")
        return "\n".join(lines)


def aggregate(results: list[RunResult]) -> SuiteMetrics:
    if not results:
        raise ValueError("no results to aggregate")
    by_task: dict[str, list[RunResult]] = {}
    for r in results:
        by_task.setdefault(r.task_id, []).append(r)

    n_tasks = len(by_task)
    solved_runs = sum(1 for r in results if r.solved)
    solve_rate = solved_runs / len(results)

    latencies = sorted(r.latency_s for r in results)
    costs = [r.cost_usd for r in results]
    steps = [r.steps for r in results]
    total_cost = sum(costs)
    solves = sum(1 for runs in by_task.values() for r in runs if r.solved)

    # pass@k: fraction of tasks solved at least once in k repeats.
    ks = sorted({len(runs) for runs in by_task.values()})
    pass_at_k = {}
    for k in ks:
        ok = sum(1 for runs in by_task.values() if any(r.solved for r in runs[:k]))
        pass_at_k[k] = ok / n_tasks

    reliability = sum(
        1 for runs in by_task.values() if all(r.solved for r in runs)
    ) / n_tasks

    return SuiteMetrics(
        n_tasks=n_tasks,
        n_runs=len(results),
        solve_rate=solve_rate,
        pass_at_k=pass_at_k,
        mean_latency_s=statistics.fmean(latencies),
        p50_latency_s=_percentile(latencies, 50),
        p90_latency_s=_percentile(latencies, 90),
        mean_cost_usd=statistics.fmean(costs),
        cost_per_solve_usd=(total_cost / solves) if solves else None,
        mean_steps=statistics.fmean(steps) if steps else 0.0,
        reliability=reliability,
    )


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * pct / 100))
    return sorted_vals[idx]
