"""Unit tests for the harness. No API keys, fully deterministic."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ablations.compare import compare
from ablations.variants import BASELINE, AblationConfig, PromptVariant
from evals.registry import ALL_TASKS, get_task
from harness.agent import ScriptedAgent
from harness.runner import run_suite, run_task
from harness.task import verify
from metrics.aggregate import aggregate

GOOD = "def f(x):\n    return x * 2\n"


def _agent_for(task_id: str, solution: str | None) -> ScriptedAgent:
    return ScriptedAgent("test", {task_id: (solution, 10, 10, 0.0)})


def test_verify_passes_on_correct_solution():
    task = get_task("fizzbuzz-plus")
    from examples.demo import SOL_FIZZBUZZ

    outcome = verify(task, SOL_FIZZBUZZ)
    assert outcome.passed, outcome.detail


def test_verify_fails_on_wrong_solution():
    task = get_task("fizzbuzz-plus")
    outcome = verify(task, "def fizzbuzz_plus(n):\n    return []\n")
    assert not outcome.passed


def test_verify_rejects_empty_solution():
    task = get_task("fizzbuzz-plus")
    assert not verify(task, "").passed
    assert not verify(task, None).passed


def test_runner_records_cost_latency_tokens():
    task = get_task("fizzbuzz-plus")
    from examples.demo import SOL_FIZZBUZZ

    agent = ScriptedAgent("t", {"fizzbuzz-plus": (SOL_FIZZBUZZ, 100, 200, 0.0)})
    r = run_task(agent, task, price_in_per_1k=3.0, price_out_per_1k=15.0)
    assert r.solved
    assert r.input_tokens == 100
    assert r.output_tokens == 200
    assert r.cost_usd == (100 / 1000) * 3.0 + (200 / 1000) * 15.0
    assert r.latency_s >= 0
    assert r.steps > 0


def test_runner_survives_agent_exception():
    class Boom:
        name = "boom"

        def act(self, prompt: str, step_budget: int):
            raise RuntimeError("agent exploded")

    r = run_task(Boom(), get_task("fizzbuzz-plus"))
    assert not r.solved
    assert "RuntimeError" in r.error


def test_aggregate_math():
    task = get_task("fizzbuzz-plus")
    from examples.demo import SOL_FIZZBUZZ

    good = ScriptedAgent("g", {"fizzbuzz-plus": (SOL_FIZZBUZZ, 100, 100, 0.0)})
    bad = ScriptedAgent("b", {"fizzbuzz-plus": ("x = 1\n", 100, 100, 0.0)})
    m_good = aggregate(run_suite(good, [task], repeats=2))
    m_bad = aggregate(run_suite(bad, [task], repeats=2))
    assert m_good.n_tasks == 1
    assert m_good.solve_rate == 1.0
    assert m_good.pass_at_k[2] == 1.0
    assert m_good.reliability == 1.0
    assert m_bad.solve_rate == 0.0
    assert m_bad.pass_at_k[2] == 0.0


def test_all_demo_solutions_pass():
    from examples.demo import CORRECT

    for task in ALL_TASKS:
        outcome = verify(task, CORRECT[task.id])
        assert outcome.passed, f"{task.id}: {outcome.detail}"


def test_ablation_compare_runs():
    from examples.demo import CORRECT

    def make_agent(variant: PromptVariant) -> ScriptedAgent:
        return ScriptedAgent(variant.name, {t.id: (CORRECT[t.id], 10, 10, 0.0) for t in ALL_TASKS})

    cfg = AblationConfig(repeats=1)
    report = compare(make_agent, ALL_TASKS[:2], cfg)
    assert set(report.per_variant) == {v.name for v in cfg.variants}
    assert report.winner() in report.per_variant
