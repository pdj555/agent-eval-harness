"""Built-in task suite: small, sharp, discriminating.

Each task is a realistic slice of coding-agent work: implement to spec,
fix a bug, handle edge cases. Tests are the judge, not an LLM.
"""

from __future__ import annotations

from harness.task import Task

FIZZBUZZ_PLUS = Task(
    id="fizzbuzz-plus",
    title="FizzBuzz with digit-sum rule",
    prompt=(
        "Write a module-level function `fizzbuzz_plus(n: int) -> list[str]`.\n"
        "For i in 1..n: 'Fizz' if divisible by 3, 'Buzz' if divisible by 5, "
        "'FizzBuzz' if both. Additionally, if the digit sum of i is divisible "
        "by 7, append '!' to that entry. Return the list of strings."
    ),
    tests='''\
from solution import fizzbuzz_plus

def test_basic():
    assert fizzbuzz_plus(5) == ["1", "2", "Fizz", "4", "Buzz"]

def test_fizzbuzz():
    assert fizzbuzz_plus(15)[14] == "FizzBuzz"

def test_digit_sum_rule():
    # 7 -> digit sum 7 -> "7!"
    out = fizzbuzz_plus(7)
    assert out[6] == "7!"
    # 16 -> digit sum 7 -> "16!"
    out = fizzbuzz_plus(16)
    assert out[15] == "16!"

def test_combined():
    # 21: divisible by 3 -> Fizz, digit sum 3 -> no bang
    assert fizzbuzz_plus(21)[20] == "Fizz"

def test_empty():
    assert fizzbuzz_plus(0) == []
''',
)

FIX_BINARY_SEARCH = Task(
    id="fix-binary-search",
    title="Fix the off-by-one in binary search",
    prompt=(
        "The function below has an off-by-one bug. Return the corrected "
        "full source defining `binary_search(arr: list[int], x: int) -> int`, "
        "returning the index of x or -1 if absent. `arr` is sorted ascending.\n\n"
        "def binary_search(arr, x):\n"
        "    lo, hi = 0, len(arr)\n"
        "    while lo < hi:\n"
        "        mid = (lo + hi) // 2\n"
        "        if arr[mid] == x:\n"
        "            return mid\n"
        "        elif arr[mid] < x:\n"
        "            lo = mid\n"
        "        else:\n"
        "            hi = mid - 1\n"
        "    return -1\n"
    ),
    tests='''\
from solution import binary_search

def test_found():
    assert binary_search([1, 3, 5, 7, 9], 5) == 2

def test_first():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0

def test_last():
    assert binary_search([1, 3, 5, 7, 9], 9) == 4

def test_absent_low():
    assert binary_search([1, 3, 5, 7, 9], 0) == -1

def test_absent_high():
    assert binary_search([1, 3, 5, 7, 9], 10) == -1

def test_absent_middle():
    assert binary_search([1, 3, 5, 7, 9], 6) == -1

def test_empty():
    assert binary_search([], 1) == -1

def test_single():
    assert binary_search([4], 4) == 0
    assert binary_search([4], 5) == -1

def test_terminates_large():
    arr = list(range(0, 20000, 2))
    assert binary_search(arr, 19998) == 9999
    assert binary_search(arr, 19999) == -1
''',
)

RETRY_BACKOFF = Task(
    id="retry-backoff",
    title="Retry decorator with exponential backoff",
    prompt=(
        "Write a decorator `retry(max_attempts: int = 3, base_delay: float = 0.1, "
        "exceptions: tuple = (Exception,))` that retries the wrapped function on "
        "the given exceptions. Delay between attempt k and k+1 is "
        "base_delay * 2**k seconds. Re-raise the last exception when attempts "
        "are exhausted. Use `time.sleep` for delays so it is testable via "
        "monkeypatching. Preserve the wrapped function's name and docstring."
    ),
    tests='''\
import time
from solution import retry

def test_eventual_success(monkeypatch):
    calls = []
    monkeypatch.setattr(time, "sleep", lambda s: calls.append(s))

    attempts = {"n": 0}
    @retry(max_attempts=3, base_delay=0.1)
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ValueError("boom")
        return "ok"

    assert flaky() == "ok"
    assert calls == [0.1, 0.2]

def test_exhaustion_reraises(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    @retry(max_attempts=2, base_delay=0.05)
    def always_fails():
        raise RuntimeError("nope")

    try:
        always_fails()
    except RuntimeError:
        pass
    else:
        raise AssertionError("should have raised")

def test_non_matching_exception_not_retried(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = {"n": 0}

    @retry(max_attempts=3, exceptions=(ValueError,))
    def raises_type():
        calls["n"] += 1
        raise TypeError("different")

    try:
        raises_type()
    except TypeError:
        pass
    assert calls["n"] == 1

def test_preserves_metadata():
    @retry()
    def documented():
        """My docs."""
        return 1
    assert documented.__name__ == "documented"
    assert documented.__doc__ == "My docs."
''',
)

LRU_CACHE = Task(
    id="lru-cache",
    title="LRU cache with O(1) operations",
    prompt=(
        "Implement `class LRUCache` with `__init__(self, capacity: int)`, "
        "`get(self, key: int) -> int`, and `put(self, key: int, value: int) -> None`. "
        "get returns -1 on miss. put evicts the least recently used entry when "
        "over capacity. Both operations must be O(1) amortized; do not use "
        "functools.lru_cache."
    ),
    tests='''\
from solution import LRUCache

def test_basic():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == 1
    c.put(3, 3)
    assert c.get(2) == -1
    c.put(4, 4)
    assert c.get(1) == -1
    assert c.get(3) == 3
    assert c.get(4) == 4

def test_update_refreshes():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(1, 10)
    c.put(3, 3)
    assert c.get(2) == -1
    assert c.get(1) == 10

def test_capacity_one():
    c = LRUCache(1)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == -1
    assert c.get(2) == 2

def test_miss():
    c = LRUCache(3)
    assert c.get(99) == -1

def test_no_functools():
    import inspect
    src = inspect.getsource(LRUCache)
    assert "lru_cache" not in src
''',
)

CSV_SUMMARY = Task(
    id="csv-summary",
    title="CSV column summarizer",
    prompt=(
        "Write `summarize_csv(path: str) -> dict` that reads a CSV file with a "
        "header row and returns {column: {\"count\": n, \"nulls\": m, "
        "\"unique\": u, \"mean\": f or None}}. count is non-null values, nulls "
        "is empty-string count, unique is distinct non-null values, mean is the "
        "float mean for columns where every non-null value parses as float, "
        "else None. Use only the standard library."
    ),
    tests='''\
import csv
from solution import summarize_csv

def _write(tmp_path, rows):
    p = tmp_path / "d.csv"
    with open(p, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    return str(p)

def test_mixed(tmp_path):
    p = _write(tmp_path, [
        ["name", "age", "city"],
        ["a", "30", "x"],
        ["b", "", "y"],
        ["a", "40", "x"],
    ])
    out = summarize_csv(p)
    assert out["name"] == {"count": 3, "nulls": 0, "unique": 2, "mean": None}
    assert out["age"] == {"count": 2, "nulls": 1, "unique": 2, "mean": 35.0}
    assert out["city"]["unique"] == 2

def test_all_null_column(tmp_path):
    p = _write(tmp_path, [["a"], [""], [""]])
    out = summarize_csv(p)
    assert out["a"]["count"] == 0
    assert out["a"]["mean"] is None
''',
)

BALANCED_PARENS = Task(
    id="balanced-parens",
    title="Balanced delimiters ignoring string literals",
    prompt=(
        "Write `is_balanced(src: str) -> bool` returning True iff every "
        "opening bracket ({[( is matched by the correct closing bracket "
        ")]}, ignoring brackets inside single-quoted, double-quoted, and "
        "triple-quoted string literals. Handle escaped quotes (\\\\' and "
        '\\\\") inside strings. A # starts a line comment: ignore the rest '
        "of the line unless inside a string."
    ),
    tests='''\
from solution import is_balanced

def test_simple():
    assert is_balanced("([]{})")
    assert not is_balanced("([)]")

def test_strings_ignored():
    assert is_balanced('x = "("')
    assert is_balanced("y = ']'")

def test_escaped_quotes():
    assert is_balanced('s = "a\\\\"(" + ")"')

def test_triple_quoted():
    assert is_balanced('s = """([{"'') + ""')

def test_comment():
    assert is_balanced("x = 1  # )")
    assert not is_balanced("x = (1  # )")

def test_empty():
    assert is_balanced("")
''',
)

ALL_TASKS: list[Task] = [
    FIZZBUZZ_PLUS,
    FIX_BINARY_SEARCH,
    RETRY_BACKOFF,
    LRU_CACHE,
    CSV_SUMMARY,
    BALANCED_PARENS,
]


def get_task(task_id: str) -> Task:
    for t in ALL_TASKS:
        if t.id == task_id:
            return t
    raise KeyError(f"unknown task: {task_id}")
