"""Tests for regression history and cost modeling."""

import pytest

from harness.history import (
    latest_for,
    load_history,
    log_run,
    render_delta,
    render_trend,
)
from metrics.aggregate import aggregate
from harness.runner import RunResult
from metrics.costing import breakeven, cost_table, project_cost, render_breakeven


def _results():
    return [
        RunResult(
            task_id="t1", task_title="t", agent_name="a", variant="v",
            solved=True, detail="", latency_s=0.2, steps=3,
            input_tokens=100, output_tokens=200, cost_usd=0.01,
        ),
        RunResult(
            task_id="t2", task_title="t", agent_name="a", variant="v",
            solved=False, detail="x", latency_s=0.3, steps=3,
            input_tokens=100, output_tokens=200, cost_usd=0.01,
        ),
    ]


def test_history_round_trip(tmp_path):
    p = tmp_path / "hist.jsonl"
    m = aggregate(_results())
    rec = log_run(p, agent_name="a", variant="v", metrics=m)
    assert rec["solve_rate"] == 0.5
    loaded = load_history(p)
    assert len(loaded) == 1
    assert loaded[0]["variant"] == "v"


def test_history_trend_and_delta(tmp_path):
    p = tmp_path / "hist.jsonl"
    m = aggregate(_results())
    r1 = log_run(p, agent_name="a", variant="v", metrics=m)
    r2 = log_run(p, agent_name="a", variant="v", metrics=m)
    assert "solve_rate" in render_trend(p)
    assert "delta" in render_delta(r1, r2)
    assert latest_for(p, "a", "v")["ts"] == r2["ts"]
    assert latest_for(p, "a", "missing") is None


def test_project_cost_math():
    # 10 tasks x 2 repeats x (1000 in @ $1/1k + 2000 out @ $2/1k)
    c = project_cost(10, 2, 1000, 2000, 1.0, 2.0)
    assert c == pytest.approx(20 * (1.0 + 4.0))


def test_cost_table_lists_tiers():
    t = cost_table(12, 3, 800, 1200)
    assert "budget" in t and "frontier" in t


def test_breakeven_math():
    b = breakeven(eval_cost_usd=50.0, incident_cost_usd=10000.0, incident_probability=0.1)
    assert b["expected_loss_usd"] == pytest.approx(1000.0)
    assert b["required_catch_rate"] == pytest.approx(0.05)


def test_breakeven_rejects_bad_inputs():
    with pytest.raises(ValueError):
        breakeven(10.0, 0.0, 0.1)


def test_render_breakeven():
    out = render_breakeven(50.0, 10000.0, 0.1)
    assert "Required catch rate" in out
