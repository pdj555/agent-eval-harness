"""The hidden-input check separates a real solve from a special-cased one."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from evals.registry import ALL_TASKS  # noqa: E402
from harness.agent import ScriptedAgent  # noqa: E402
from harness.runner import run_task  # noqa: E402
from metrics.hidden import REFERENCES, hidden_check  # noqa: E402
from tests_vs_hidden import HONEST, SPECIAL_CASED  # noqa: E402


def _task(task_id):
    return next(t for t in ALL_TASKS if t.id == task_id)


def test_every_reference_passes_its_own_task_tests():
    for task_id, (_, reference, _) in REFERENCES.items():
        agent = ScriptedAgent(name="ref", behavior={task_id: (reference.strip() + "\n", 1, 1, 0.0)})
        assert run_task(agent, _task(task_id)).solved, task_id


def test_special_cased_solutions_pass_the_tests_and_fail_hidden_inputs():
    for task_id in REFERENCES:
        agent = ScriptedAgent(name="cheat", behavior={task_id: (SPECIAL_CASED[task_id], 1, 1, 0.0)})
        assert run_task(agent, _task(task_id)).solved, task_id
        result = hidden_check(task_id, SPECIAL_CASED[task_id])
        assert not result.passed and result.mismatches, task_id


def test_honest_solutions_pass_hidden_inputs():
    for task_id in REFERENCES:
        result = hidden_check(task_id, HONEST[task_id])
        assert result.passed and result.checked >= 200, (task_id, result.example())


def test_unknown_task_has_no_reference():
    assert hidden_check("lru-cache", "x = 1") is None


def test_solution_that_hangs_times_out_instead_of_blocking():
    result = hidden_check("fizzbuzz-plus", "def fizzbuzz_plus(n):\n    while True:\n        pass\n", timeout=2)
    assert not result.passed and "timed out" in result.mismatches[0][2]
