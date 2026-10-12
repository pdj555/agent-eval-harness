"""Unit tests for code-based graders. The rule under test: graders see the
outcome only, never the agent's path."""
from app.graders import evaluate
from app.models import GraderSpec


def g(**kw):
    return GraderSpec(**kw)


def test_exact_pass():
    r = evaluate(g(type="exact", field="result", expected=42), {"result": 42})
    assert r.passed


def test_exact_fail():
    r = evaluate(g(type="exact", field="result", expected=42), {"result": 43})
    assert not r.passed


def test_exact_whole_outcome():
    r = evaluate(g(type="exact", expected={"a": 1}), {"a": 1})
    assert r.passed


def test_missing_field_fails():
    r = evaluate(g(type="exact", field="nope", expected=1), {"result": 1})
    assert not r.passed
    assert "missing" in r.detail


def test_contains_string():
    assert evaluate(g(type="contains", field="msg", expected="world"),
                    {"msg": "hello world"}).passed
    assert not evaluate(g(type="contains", field="msg", expected="mars"),
                       {"msg": "hello world"}).passed


def test_contains_list():
    assert evaluate(g(type="contains", field="items", expected="b"),
                    {"items": ["a", "b"]}).passed


def test_regex():
    assert evaluate(g(type="regex", field="id", pattern=r"^user_\d+$"),
                    {"id": "user_123"}).passed
    assert not evaluate(g(type="regex", field="id", pattern=r"^user_\d+$"),
                        {"id": "admin"}).passed


def test_gte_lte():
    assert evaluate(g(type="gte", field="score", expected=0.8), {"score": 0.9}).passed
    assert not evaluate(g(type="gte", field="score", expected=0.8), {"score": 0.7}).passed
    assert evaluate(g(type="lte", field="latency_ms", expected=500), {"latency_ms": 120}).passed


def test_nested_dot_path():
    r = evaluate(g(type="exact", field="a.b.c", expected=7), {"a": {"b": {"c": 7}}})
    assert r.passed


def test_list_index_path():
    r = evaluate(g(type="exact", field="items.0", expected="x"), {"items": ["x", "y"]})
    assert r.passed


def test_all_of():
    spec = g(type="all_of", specs=[
        g(type="exact", field="a", expected=1),
        g(type="gte", field="b", expected=5),
    ])
    assert evaluate(spec, {"a": 1, "b": 9}).passed
    assert not evaluate(spec, {"a": 1, "b": 2}).passed


def test_any_of():
    spec = g(type="any_of", specs=[
        g(type="exact", field="a", expected=1),
        g(type="exact", field="a", expected=2),
    ])
    assert evaluate(spec, {"a": 2}).passed
    assert not evaluate(spec, {"a": 3}).passed


def test_grader_ignores_tool_calls():
    # The path is visible in the response but the grader only sees outcome.
    outcome = {"result": 42}
    assert evaluate(g(type="exact", field="result", expected=42), outcome).passed
