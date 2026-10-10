"""Hard task suite: the tasks that separate real agents from demos.

Each task targets a failure mode the base suite does not cover:
misleading stack traces, multi-file refactors, dependency planning,
concurrency, spec-heavy validation, and messy real-world data.

Every task ships with a verified oracle in evals/oracles.py; the test
suite proves each one is solvable.
"""

from __future__ import annotations

from harness.task import Task

FIX_MISLEADING_TRACEBACK = Task(
    id="fix-misleading-traceback",
    title="Fix the bug the traceback blames on the wrong function",
    prompt=(
        "The traceback below blames `_chunks`, but the real defect is "
        "elsewhere. Return the corrected full source.\n\n"
        "def _chunks(data, n):\n"
        "    return [data[i:i + n] for i in range(0, len(data), n)]\n\n"
        "def batch_process(records, batch_size):\n"
        '    """Split records into batches and return per-batch checksums."""\n'
        "    results = []\n"
        "    for chunk in _chunks(records, batch_size):\n"
        '        checksum = sum(r["value"] for r in chunk) % 1000\n'
        "        results.append(checksum)\n"
        "    return results\n\n"
        "Traceback (most recent call last):\n"
        '  File "app.py", line 12, in <module>\n'
        "    batch_process(records, 0)\n"
        '  File "app.py", line 8, in batch_process\n'
        "    for chunk in _chunks(records, batch_size):\n"
        '  File "app.py", line 2, in _chunks\n'
        "    return [data[i:i + n] for i in range(0, len(data), n)]\n"
        "ValueError: range() arg 3 must not be zero\n\n"
        "Fix the defect at the right layer: validate at the public API "
        "boundary and raise a clear ValueError naming batch_size."
    ),
    tests='''\
import pytest
from solution import batch_process

def test_batches():
    recs = [{"value": i} for i in range(10)]
    assert batch_process(recs, 3) == [3, 12, 21, 9]

def test_single_batch():
    recs = [{"value": 5}, {"value": 7}]
    assert batch_process(recs, 10) == [12]

def test_empty():
    assert batch_process([], 3) == []

def test_zero_batch_size_rejected():
    with pytest.raises(ValueError, match="batch_size"):
        batch_process([{"value": 1}], 0)

def test_negative_batch_size_rejected():
    with pytest.raises(ValueError, match="batch_size"):
        batch_process([{"value": 1}], -1)
''',
)

CONSOLIDATE_ORDER_MODULE = Task(
    id="consolidate-order-module",
    title="Consolidate duplicated accumulation into one pass",
    prompt=(
        "Two modules duplicate the same accumulation loop:\n\n"
        "# module_a.py\n"
        "def total_price(items):\n"
        "    total = 0.0\n"
        "    for it in items:\n"
        '        total += it["price"] * it["qty"]\n'
        "    return round(total, 2)\n\n"
        "# module_b.py\n"
        "def total_weight(items):\n"
        "    total = 0.0\n"
        "    for it in items:\n"
        '        total += it["weight"] * it["qty"]\n'
        "    return round(total, 2)\n\n"
        "Write ONE module exposing `summarize_order(items) -> dict` that "
        'returns {"total_price": ..., "total_weight": ..., "line_count": ...}. '
        "Accumulate both totals in a single pass over items (exactly one "
        "`for` loop). Round money and weight to 2 decimals."
    ),
    tests='''\
import inspect
from solution import summarize_order

def test_totals():
    items = [
        {"price": 10.0, "weight": 2.0, "qty": 3},
        {"price": 4.5, "weight": 1.0, "qty": 2},
    ]
    out = summarize_order(items)
    assert out["total_price"] == 39.0
    assert out["total_weight"] == 8.0
    assert out["line_count"] == 2

def test_empty():
    out = summarize_order([])
    assert out == {"total_price": 0.0, "total_weight": 0.0, "line_count": 0}

def test_rounding():
    items = [{"price": 0.1, "weight": 0.2, "qty": 3}]
    out = summarize_order(items)
    assert out["total_price"] == 0.3
    assert out["total_weight"] == 0.6

def test_single_pass():
    src = inspect.getsource(summarize_order)
    assert src.count("for ") == 1, "must accumulate in a single pass"
''',
)

DEPENDENCY_TOPOSORT = Task(
    id="dependency-toposort",
    title="Topological install order with cycle detection",
    prompt=(
        "Write `install_order(packages: dict[str, list[str]]) -> list[str]`.\n"
        "`packages` maps a package name to its dependency names. Return an "
        "order where every package appears after its dependencies.\n"
        "Define and raise `CircularDependencyError` on any cycle "
        "(including self-dependencies). Define and raise "
        "`UnknownPackageError` when a dependency is not a key in `packages`."
    ),
    tests='''\
import pytest
from solution import install_order, CircularDependencyError, UnknownPackageError

def _valid(order, packages):
    pos = {name: i for i, name in enumerate(order)}
    assert set(order) == set(packages)
    for name, deps in packages.items():
        for d in deps:
            assert pos[d] < pos[name]

def test_chain():
    pkgs = {"a": ["b"], "b": ["c"], "c": []}
    _valid(install_order(pkgs), pkgs)

def test_diamond():
    pkgs = {"app": ["lib", "util"], "lib": ["base"], "util": ["base"], "base": []}
    _valid(install_order(pkgs), pkgs)

def test_empty():
    assert install_order({}) == []

def test_cycle():
    with pytest.raises(CircularDependencyError):
        install_order({"a": ["b"], "b": ["a"]})

def test_self_cycle():
    with pytest.raises(CircularDependencyError):
        install_order({"a": ["a"]})

def test_unknown():
    with pytest.raises(UnknownPackageError):
        install_order({"a": ["ghost"]})
''',
)

FIX_RACE_CONDITION = Task(
    id="fix-race-condition",
    title="Fix the lost-update race in Counter",
    prompt=(
        "This counter loses updates under threads because the read and the "
        "write are separate steps:\n\n"
        "class Counter:\n"
        "    def __init__(self):\n"
        "        self.value = 0\n"
        "    def increment(self):\n"
        "        current = self.value\n"
        "        self.value = current + 1\n\n"
        "Return the corrected full source defining `class Counter` with "
        "`__init__` (value starts at 0) and a thread-safe `increment`. "
        "8 threads x 500 increments must always total 4000."
    ),
    tests='''\
import threading
from solution import Counter

def test_sequential():
    c = Counter()
    c.increment()
    c.increment()
    assert c.value == 2

def test_initial_value():
    assert Counter().value == 0

def test_concurrent_no_lost_updates():
    c = Counter()
    def worker():
        for _ in range(500):
            c.increment()
    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert c.value == 4000
''',
)

JSON_SCHEMA_VALIDATOR = Task(
    id="json-schema-validator",
    title="JSON Schema subset validator",
    prompt=(
        "Write `validate(data, schema) -> list[str]` returning a list of "
        "human-readable error strings; an empty list means valid. Each error "
        "must name the offending path (e.g. `$.address.zip`).\n"
        "Support: `type` (object, array, string, integer, number, boolean, "
        "null), `required`, `properties`, `items`, `enum`, `minimum`, "
        "`maximum`, `minLength`, `maxLength`. Validate recursively."
    ),
    tests='''\
from solution import validate

USER_SCHEMA = {
    "type": "object",
    "required": ["name", "age"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "age": {"type": "integer", "minimum": 0, "maximum": 150},
        "email": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "address": {
            "type": "object",
            "required": ["zip"],
            "properties": {"zip": {"type": "string", "maxLength": 10}},
        },
    },
}

def test_valid():
    doc = {"name": "Ann", "age": 30, "tags": ["a"], "address": {"zip": "12345"}}
    assert validate(doc, USER_SCHEMA) == []

def test_missing_required():
    errs = validate({"age": 30}, USER_SCHEMA)
    assert any("name" in e for e in errs)

def test_wrong_type():
    errs = validate({"name": "Ann", "age": "thirty"}, USER_SCHEMA)
    assert any("age" in e for e in errs)

def test_range():
    errs = validate({"name": "Ann", "age": 200}, USER_SCHEMA)
    assert any("age" in e for e in errs)

def test_nested_required():
    errs = validate({"name": "Ann", "age": 30, "address": {}}, USER_SCHEMA)
    assert any("zip" in e for e in errs)

def test_array_items():
    errs = validate({"name": "Ann", "age": 30, "tags": ["ok", 5]}, USER_SCHEMA)
    assert any("tags" in e for e in errs)

def test_enum():
    schema = {"type": "string", "enum": ["red", "green"]}
    assert validate("red", schema) == []
    assert validate("blue", schema) != []

def test_min_length():
    errs = validate({"name": "", "age": 30}, USER_SCHEMA)
    assert any("name" in e for e in errs)
''',
)

LOG_PARSER_AGGREGATOR = Task(
    id="log-parser-aggregator",
    title="Web log parser with malformed-line tolerance",
    prompt=(
        "Write `summarize_logs(lines: list[str]) -> dict`. Each line looks "
        "like `GET /api/users?page=2 200 42` (METHOD PATH STATUS "
        "LATENCY_MS). Skip malformed lines silently. Return "
        "`{endpoint: {\"count\": n, \"mean_latency_ms\": f, "
        "\"error_rate\": f}}` where endpoint is the path with the query "
        "string stripped, and error_rate is the fraction of responses with "
        "status >= 500."
    ),
    tests='''\
import pytest
from solution import summarize_logs

def test_basic():
    lines = [
        "GET /api/users 200 42",
        "GET /api/users 200 58",
        "POST /api/users 500 120",
    ]
    out = summarize_logs(lines)
    u = out["/api/users"]
    assert u["count"] == 3
    assert u["mean_latency_ms"] == pytest.approx(73.333, rel=1e-3)
    assert u["error_rate"] == pytest.approx(1 / 3)

def test_query_stripped():
    lines = ["GET /search?q=x 200 10", "GET /search?q=y 200 20"]
    assert summarize_logs(lines)["/search"]["count"] == 2

def test_malformed_skipped():
    lines = ["GET /ok 200 10", "garbage line", "GET /ok notanumber 200", ""]
    assert summarize_logs(lines)["/ok"]["count"] == 1

def test_empty():
    assert summarize_logs([]) == {}

def test_error_rate_zero():
    lines = ["GET /a 200 5", "GET /a 404 6"]
    assert summarize_logs(lines)["/a"]["error_rate"] == 0.0
''',
)

HARD_TASKS: list[Task] = [
    FIX_MISLEADING_TRACEBACK,
    CONSOLIDATE_ORDER_MODULE,
    DEPENDENCY_TOPOSORT,
    FIX_RACE_CONDITION,
    JSON_SCHEMA_VALIDATOR,
    LOG_PARSER_AGGREGATOR,
]
