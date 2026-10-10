"""evals: task definitions with executable test suites."""

from .registry import ALL_TASKS, get_task, list_tasks
from .tasks import (
    BALANCED_PARENS,
    CSV_SUMMARY,
    FIX_BINARY_SEARCH,
    FIZZBUZZ_PLUS,
    LRU_CACHE,
    RETRY_BACKOFF,
)

__all__ = [
    "ALL_TASKS",
    "BALANCED_PARENS",
    "CSV_SUMMARY",
    "FIX_BINARY_SEARCH",
    "FIZZBUZZ_PLUS",
    "LRU_CACHE",
    "RETRY_BACKOFF",
    "get_task",
    "list_tasks",
]
