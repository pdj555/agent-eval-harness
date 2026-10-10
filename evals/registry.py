"""Task registry: one place to list, fetch, and extend the suite."""

from __future__ import annotations

from harness.task import Task
from .tasks import ALL_TASKS, get_task

__all__ = ["ALL_TASKS", "Task", "get_task", "list_tasks"]


def list_tasks() -> list[str]:
    return [t.id for t in ALL_TASKS]
