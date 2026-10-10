"""Every hard task ships with a verified oracle solution."""

from evals.oracles import ORACLES
from evals.tasks_hard import HARD_TASKS
from harness.task import verify


def test_every_hard_task_has_an_oracle():
    ids = {t.id for t in HARD_TASKS}
    assert set(ORACLES) == ids


def test_oracles_pass():
    for task in HARD_TASKS:
        outcome = verify(task, ORACLES[task.id])
        assert outcome.passed, f"oracle failed for {task.id}: {outcome.detail}"


def test_broken_solutions_fail():
    # Sanity: the harness actually discriminates. A syntax-broken
    # solution must fail every hard task.
    for task in HARD_TASKS:
        outcome = verify(task, "def broken(:\n")
        assert not outcome.passed, f"broken solution passed {task.id}"
