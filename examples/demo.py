"""Worked example: three scripted agents, six tasks, two prompt variants.

Runs with no API keys. Prints suite tables and an ablation comparison,
then writes the same output to examples/run_report.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ablations.compare import compare
from ablations.variants import BASELINE, CHAIN_OF_THOUGHT, AblationConfig, PromptVariant
from evals.registry import ALL_TASKS
from harness.agent import ScriptedAgent
from harness.runner import run_suite
from metrics.aggregate import aggregate
from metrics.report import render_per_task_table, render_suite_table

# ---------------------------------------------------------------------------
# Correct solutions (what a strong agent would produce)
# ---------------------------------------------------------------------------

SOL_FIZZBUZZ = '''\
def fizzbuzz_plus(n: int) -> list[str]:
    out = []
    for i in range(1, n + 1):
        s = ""
        if i % 3 == 0:
            s += "Fizz"
        if i % 5 == 0:
            s += "Buzz"
        if not s:
            s = str(i)
        if sum(int(d) for d in str(i)) % 7 == 0:
            s += "!"
        out.append(s)
    return out
'''

SOL_BINARY_SEARCH = '''\
def binary_search(arr, x):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == x:
            return mid
        elif arr[mid] < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
'''

SOL_RETRY = '''\
import functools
import time


def retry(max_attempts=3, base_delay=0.1, exceptions=(Exception,)):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last = None
            for k in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last = e
                    if k < max_attempts - 1:
                        time.sleep(base_delay * 2 ** k)
            raise last
        return wrapper
    return deco
'''

SOL_LRU = '''\
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._d = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self._d:
            return -1
        self._d.move_to_end(key)
        return self._d[key]

    def put(self, key: int, value: int) -> None:
        if key in self._d:
            self._d.move_to_end(key)
        self._d[key] = value
        if len(self._d) > self.capacity:
            self._d.popitem(last=False)
'''

SOL_CSV = '''\
import csv


def summarize_csv(path: str) -> dict:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        vals = {c: [] for c in cols}
        nulls = {c: 0 for c in cols}
        for row in reader:
            for c in cols:
                v = row.get(c, "")
                if v == "":
                    nulls[c] += 1
                else:
                    vals[c].append(v)
    out = {}
    for c in cols:
        non_null = vals[c]
        mean = None
        if non_null:
            try:
                nums = [float(v) for v in non_null]
                mean = sum(nums) / len(nums)
            except ValueError:
                mean = None
        out[c] = {
            "count": len(non_null),
            "nulls": nulls[c],
            "unique": len(set(non_null)),
            "mean": mean,
        }
    return out
'''

SOL_PARENS = '''\
def is_balanced(src: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    opening = set("([{")
    stack = []
    i, n = 0, len(src)
    triple_single = "'" * 3
    triple_double = '"' * 3
    while i < n:
        if src.startswith(triple_single, i) or src.startswith(triple_double, i):
            q = src[i:i + 3]
            i += 3
            while i < n and not src.startswith(q, i):
                if src[i] == "\\\\":
                    i += 1
                i += 1
            i += 3
            continue
        ch = src[i]
        if ch in ("'", '"'):
            i += 1
            while i < n and src[i] != ch:
                if src[i] == "\\\\":
                    i += 1
                i += 1
            i += 1
            continue
        if ch == "#":
            while i < n and src[i] != "\\n":
                i += 1
            continue
        if ch in opening:
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        i += 1
    return not stack
'''

# Plausible-but-wrong solutions, to show the tests catching failures.
WRONG_RETRY = '''\
def retry(max_attempts=3, base_delay=0.1, exceptions=(Exception,)):
    def deco(fn):
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return deco
'''

WRONG_PARENS = '''\
def is_balanced(src: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in src:
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
'''

CORRECT = {
    "fizzbuzz-plus": SOL_FIZZBUZZ,
    "fix-binary-search": SOL_BINARY_SEARCH,
    "retry-backoff": SOL_RETRY,
    "lru-cache": SOL_LRU,
    "csv-summary": SOL_CSV,
    "balanced-parens": SOL_PARENS,
}


def behavior(solved: set[str], in_tok: int, out_tok: int, latency: float) -> dict:
    wrong = {"retry-backoff": WRONG_RETRY, "balanced-parens": WRONG_PARENS}
    b: dict[str, tuple] = {}
    for tid, sol in CORRECT.items():
        if tid in solved:
            b[tid] = (sol, in_tok, out_tok, latency)
        else:
            b[tid] = (wrong.get(tid, "x = 1\n"), in_tok, out_tok, latency)
    return b


def make_agents():
    golden = ScriptedAgent(
        "golden", behavior(set(CORRECT), 800, 1200, 0.05)
    )
    steady = ScriptedAgent(
        "steady",
        behavior(
            {"fizzbuzz-plus", "fix-binary-search", "lru-cache", "csv-summary"},
            1500,
            2500,
            0.15,
        ),
    )
    weak = ScriptedAgent("weak", behavior({"fizzbuzz-plus"}, 3000, 5000, 0.30))
    return [golden, steady, weak]


def main() -> None:
    out: list[str] = ["# agent-eval-harness: worked example", ""]
    agents = make_agents()
    for agent in agents:
        results = run_suite(agent, ALL_TASKS, repeats=2)
        out.append(render_suite_table(results))
        out.append("")
        out.append(render_per_task_table(results))
        out.append("")

    # Ablation: does chain-of-thought help the steady agent?
    def make_agent(variant: PromptVariant) -> ScriptedAgent:
        if variant.name == "cot":
            solved = {
                "fizzbuzz-plus",
                "fix-binary-search",
                "lru-cache",
                "csv-summary",
                "retry-backoff",
            }
            return ScriptedAgent(
                f"steady+{variant.name}", behavior(solved, 1500, 5200, 0.22)
            )
        return ScriptedAgent(
            f"steady+{variant.name}", behavior(
                {"fizzbuzz-plus", "fix-binary-search", "lru-cache", "csv-summary"},
                1500, 2500, 0.15,
            )
        )

    cfg = AblationConfig(variants=(BASELINE, CHAIN_OF_THOUGHT), repeats=2)
    report = compare(make_agent, ALL_TASKS, cfg)
    out.append(report.markdown())
    out.append("")
    out.append(f"Winner by solve rate: **{report.winner()}**")
    out.append("")

    text = "\n".join(out)
    print(text)
    Path(__file__).with_name("run_report.md").write_text(text + "\n")
    print("wrote examples/run_report.md")


if __name__ == "__main__":
    main()
