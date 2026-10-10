"""Tests for failure classification."""

from harness.runner import RunResult
from harness.task import TestOutcome, verify
from evals.tasks import FIZZBUZZ_PLUS
from metrics.failures import (
    breakdown,
    classify,
    failure_rates,
    fixes_report,
    render_breakdown_table,
)


def _run(solved, detail="", stdout="", variant="v", error=""):
    return RunResult(
        task_id="t",
        task_title="t",
        agent_name="a",
        variant=variant,
        solved=solved,
        detail=detail,
        latency_s=0.1,
        steps=3,
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.01,
        error=error,
        stdout=stdout,
    )


def test_classify_solved():
    assert classify(_run(True)) == "solved"


def test_classify_agent_crash():
    assert classify(_run(False, error="ValueError: boom")) == "agent_crash"


def test_classify_no_output():
    assert classify(_run(False, detail="no solution produced")) == "no_output"


def test_classify_timeout():
    assert classify(_run(False, detail="tests timed out after 60.0s")) == "timeout"


def test_classify_syntax_error_real():
    outcome = verify(FIZZBUZZ_PLUS, "def broken(:\n")
    r = _run(False, detail=outcome.detail, stdout=outcome.stdout)
    assert classify(r) == "syntax_error"


def test_classify_assertion_failure_real():
    outcome = verify(FIZZBUZZ_PLUS, "def fizzbuzz_plus(n):\n    return []\n")
    r = _run(False, detail=outcome.detail, stdout=outcome.stdout)
    assert classify(r) == "assertion_failure"


def test_breakdown_counts():
    results = [
        _run(False, detail="no solution produced", variant="a"),
        _run(False, detail="no solution produced", variant="a"),
        _run(True, variant="a"),
        _run(False, error="x", variant="b"),
    ]
    b = breakdown(results)
    assert b["a"]["no_output"] == 2
    assert b["b"]["agent_crash"] == 1
    assert "solved" not in str(b)


def test_failure_rates():
    results = [_run(False, detail="no solution produced", variant="a"), _run(True, variant="a")]
    rates = failure_rates(results)
    assert rates["a"]["no_output"] == 0.5


def test_fixes_report_names_best_variant():
    results = [
        _run(False, detail="no solution produced", variant="sloppy"),
        _run(True, variant="steady"),
    ]
    report = fixes_report(results)
    assert "no_output" in report
    assert "steady" in report


def test_render_breakdown_table():
    results = [_run(False, detail="no solution produced", variant="a")]
    assert "| a |" in render_breakdown_table(results)
