"""Run agents on tasks and record everything."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .agent import Agent
from .events import TrajectoryEvent
from .task import Task, TestOutcome, verify


@dataclass
class RunResult:
    task_id: str
    task_title: str
    agent_name: str
    variant: str
    solved: bool
    detail: str
    latency_s: float
    steps: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    events: list[TrajectoryEvent] = field(default_factory=list)
    error: str = ""
    stdout: str = ""  # pytest output, truncated; feeds failure analysis


def run_task(
    agent: Agent,
    task: Task,
    *,
    variant: str = "baseline",
    price_in_per_1k: float = 3.0,
    price_out_per_1k: float = 15.0,
) -> RunResult:
    """Execute one agent on one task. Never raises on agent failure."""
    prompt = f"[task:{task.id}]\n{task.prompt}"
    start = time.perf_counter()
    try:
        result = agent.act(prompt, task.max_steps)
        outcome = verify(task, result.solution)
        error = ""
    except Exception as exc:  # noqa: BLE001 - harness must not die on agent bugs
        result = None
        outcome = TestOutcome(False, "agent raised")
        error = f"{type(exc).__name__}: {exc}"
    latency = time.perf_counter() - start

    in_tok = result.input_tokens if result else 0
    out_tok = result.output_tokens if result else 0
    cost = (in_tok / 1000) * price_in_per_1k + (out_tok / 1000) * price_out_per_1k
    return RunResult(
        task_id=task.id,
        task_title=task.title,
        agent_name=agent.name,
        variant=variant,
        solved=outcome.passed,
        detail=outcome.detail,
        latency_s=latency,
        steps=len(result.events) if result else 0,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=cost,
        events=result.events if result else [],
        error=error,
        stdout=outcome.stdout,
    )


def run_suite(
    agent: Agent,
    tasks: list[Task],
    *,
    variant: str = "baseline",
    repeats: int = 1,
    price_in_per_1k: float = 3.0,
    price_out_per_1k: float = 15.0,
) -> list[RunResult]:
    """Run every task `repeats` times. Deterministic order, no parallelism."""
    results: list[RunResult] = []
    for _ in range(repeats):
        for task in tasks:
            results.append(
                run_task(
                    agent,
                    task,
                    variant=variant,
                    price_in_per_1k=price_in_per_1k,
                    price_out_per_1k=price_out_per_1k,
                )
            )
    return results
