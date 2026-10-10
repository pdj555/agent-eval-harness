"""metrics: from raw runs to the numbers that matter."""

from .aggregate import SuiteMetrics, aggregate
from .report import (
    render_comparison_table,
    render_per_task_table,
    render_suite_table,
)

__all__ = [
    "SuiteMetrics",
    "aggregate",
    "render_comparison_table",
    "render_per_task_table",
    "render_suite_table",
]
