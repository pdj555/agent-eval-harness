"""Task registry: one place to list, fetch, and extend the suite.

ALL_TASKS is the original 6-task suite (kept stable so the basic demo
stays reproducible). HARD_TASKS is the 6-task hard suite. EXTENDED_TASKS
is both.
"""

from __future__ import annotations

from harness.task import Task
from .tasks import ALL_TASKS
from .tasks_hard import HARD_TASKS

EXTENDED_TASKS: list[Task] = ALL_TASKS + HARD_TASKS

__all__ = [
    "ALL_TASKS",
    "HARD_TASKS",
    "EXTENDED_TASKS",
    "Task",
    "get_task",
    "list_tasks",
]


def get_task(task_id: str) -> Task:
    for t in EXTENDED_TASKS:
        if t.id == task_id:
            return t
    raise KeyError(f"unknown task: {task_id}")


def list_tasks() -> list[str]:
    return [t.id for t in EXTENDED_TASKS]
