"""Head-to-head comparison across prompt variants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ablations.variants import AblationConfig, PromptVariant, apply_variant
from harness.agent import Agent
from harness.runner import RunResult, run_task
from harness.task import Task
from metrics.aggregate import SuiteMetrics, aggregate
from metrics.report import render_comparison_table


@dataclass
class ComparisonReport:
    per_variant: dict[str, SuiteMetrics] = field(default_factory=dict)
    all_results: dict[str, list[RunResult]] = field(default_factory=dict)

    def markdown(self) -> str:
        return "# Ablation comparison\n\n" + render_comparison_table(self.per_variant)

    def winner(self, metric: str = "solve_rate") -> str:
        return max(self.per_variant, key=lambda v: getattr(self.per_variant[v], metric))


def compare(
    make_agent: Callable[[PromptVariant], Agent],
    tasks: list[Task],
    config: AblationConfig | None = None,
) -> ComparisonReport:
    """Run every variant over every task `repeats` times.

    make_agent builds an agent bound to a variant. The variant prompt is
    applied by the runner; agents that ignore it are still comparable as
    long as the binding is consistent.
    """
    cfg = config or AblationConfig()
    report = ComparisonReport()
    for variant in cfg.variants:
        agent = make_agent(variant)
        results: list[RunResult] = []
        for _ in range(cfg.repeats):
            for task in tasks:
                results.append(
                    _run_with_variant(
                        agent,
                        task,
                        variant,
                        price_in_per_1k=cfg.price_in_per_1k,
                        price_out_per_1k=cfg.price_out_per_1k,
                    )
                )
        report.per_variant[variant.name] = aggregate(results)
        report.all_results[variant.name] = results
    return report


def _run_with_variant(
    agent: Agent,
    task: Task,
    variant: PromptVariant,
    *,
    price_in_per_1k: float,
    price_out_per_1k: float,
) -> RunResult:
    from harness.task import Task as T

    wrapped = T(
        id=task.id,
        title=task.title,
        prompt=apply_variant(task.prompt, variant),
        tests=task.tests,
        timeout_s=task.timeout_s,
        max_steps=task.max_steps,
    )
    result = run_task(
        agent,
        wrapped,
        variant=variant.name,
        price_in_per_1k=price_in_per_1k,
        price_out_per_1k=price_out_per_1k,
    )
    # Keep the canonical task id for aggregation.
    result.task_id = task.id
    return result
