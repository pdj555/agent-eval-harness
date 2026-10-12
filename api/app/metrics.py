"""Metrics: pass rate, pass@k, pass^k, capability vs regression split.

Definitions (Anthropic's taxonomy):
  pass@k  - probability that at least one of k attempts succeeds.
            Unbiased estimator over n trials with c passes:
            1 - C(n-c, k) / C(n, k). With n == k this is "any pass".
  pass^k  - probability that all k attempts succeed (consistency).
            Unbiased estimator: C(c, k) / C(n, k). With n == k this is
            "every trial passed".

Capability evals start at a low pass rate (a hill to climb); regression
evals should sit near 100% (a backsliding alarm). High-passing capability
evals graduate into the regression suite.
"""
from __future__ import annotations

import math


def _comb(n: int, k: int) -> int:
    if k < 0 or k > n or n < 0:
        return 0
    return math.comb(n, k)


def pass_at_k(n: int, c: int, k: int) -> float | None:
    """Unbiased pass@k. None when fewer than k trials exist."""
    if n < k or k <= 0:
        return None
    denom = _comb(n, k)
    if denom == 0:
        return None
    return 1.0 - _comb(n - c, k) / denom


def pass_caret_k(n: int, c: int, k: int) -> float | None:
    """Unbiased pass^k (all-k consistency). None when fewer than k trials exist."""
    if n < k or k <= 0:
        return None
    denom = _comb(n, k)
    if denom == 0:
        return None
    return _comb(c, k) / denom


def task_metrics(passes: list[bool], k: int) -> dict:
    n = len(passes)
    c = sum(1 for p in passes if p)
    return {
        "trials": n,
        "passes": c,
        "pass_rate": (c / n) if n else 0.0,
        "pass_at_k": pass_at_k(n, c, k),
        "pass_caret_k": pass_caret_k(n, c, k),
    }
