"""Tests for statistical rigor helpers."""

import pytest

from harness.runner import RunResult
from metrics.stats import (
    mcnemar,
    min_sample_size,
    render_ci_table,
    solve_rate_ci,
    wilson_interval,
)


def _results(solved_flags, variant="baseline"):
    return [
        RunResult(
            task_id=f"t{i}",
            task_title="t",
            agent_name="a",
            variant=variant,
            solved=s,
            detail="",
            latency_s=0.1,
            steps=3,
            input_tokens=10,
            output_tokens=20,
            cost_usd=0.01,
        )
        for i, s in enumerate(solved_flags)
    ]


def test_wilson_interval_sane():
    lo, hi = wilson_interval(60, 100)
    assert 0.0 <= lo <= 0.60 <= hi <= 1.0
    assert hi - lo < 0.25  # reasonably tight at n=100


def test_wilson_empty():
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_solve_rate_ci():
    rate, lo, hi = solve_rate_ci(_results([True] * 8 + [False] * 2))
    assert rate == pytest.approx(0.8)
    assert lo <= 0.8 <= hi


def test_mcnemar_identical():
    r = _results([True, False, True])
    out = mcnemar(r, r)
    assert out["p_value"] == 1.0
    assert out["b"] == 0 and out["c"] == 0


def test_mcnemar_detects_skew():
    a = _results([True] * 9 + [False])
    b = _results([True] * 2 + [False] * 8)
    out = mcnemar(a, b)
    assert out["b"] == 7
    assert out["c"] == 0
    assert out["p_value"] < 0.05


def test_min_sample_size_grows_as_delta_shrinks():
    assert min_sample_size(0.20) < min_sample_size(0.05)


def test_min_sample_size_positive():
    assert min_sample_size(0.10, baseline=0.6) > 0


def test_render_ci_table():
    table = render_ci_table({"baseline": _results([True, False])})
    assert "baseline" in table and "95% CI" in table
