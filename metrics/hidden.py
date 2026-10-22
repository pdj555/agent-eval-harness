"""Hidden-input check: does a solution that passes its tests agree with a reference elsewhere?

The task's pytest suite is the solve criterion everywhere else in this repo. Tests only
look at the inputs they name, so an agent can pass them by special-casing those inputs.
This check runs the solution and a reference implementation on hundreds of inputs the
tests never use and reports where they disagree.

The solution runs in a separate, isolated interpreter with a timeout, never in-process.
References cover the tasks with a pure function to compare; other tasks return None.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# task_id -> (function name, reference source, input generator source).
# The generator is a function `inputs(rng)` returning a list of argument tuples.
REFERENCES: dict[str, tuple[str, str, str]] = {
    "fizzbuzz-plus": (
        "fizzbuzz_plus",
        '''
def fizzbuzz_plus(n):
    out = []
    for i in range(1, n + 1):
        s = ("Fizz" if i % 3 == 0 else "") + ("Buzz" if i % 5 == 0 else "")
        s = s or str(i)
        if sum(int(d) for d in str(i)) % 7 == 0:
            s += "!"
        out.append(s)
    return out
''',
        '''
def inputs(rng):
    return [(n,) for n in range(0, 201)]
''',
    ),
    "fix-binary-search": (
        "binary_search",
        '''
def binary_search(arr, x):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == x:
            return mid
        if arr[mid] < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
        '''
def inputs(rng):
    cases = []
    for _ in range(400):
        arr = sorted(rng.sample(range(-50, 50), rng.randint(0, 12)))
        x = rng.choice(arr) if arr and rng.random() < 0.6 else rng.randint(-60, 60)
        cases.append((arr, x))
    return cases
''',
    ),
}

_RUNNER = r'''
import json, random, sys
spec = json.loads(sys.stdin.read())
ref, sol, gen = {}, {}, {}
exec(spec["reference"], ref)
exec(spec["generator"], gen)
try:
    exec(spec["solution"], sol)
    fn = sol[spec["name"]]
except Exception as exc:
    print(json.dumps({"checked": 0, "mismatches": [["import", "a working module", repr(exc)]]}))
    raise SystemExit
want_fn = ref[spec["name"]]
mismatches, checked = [], 0
for args in gen["inputs"](random.Random(spec["seed"])):
    checked += 1
    want = want_fn(*args)
    try:
        got = fn(*args)
    except Exception as exc:
        got = "raises " + type(exc).__name__
    if got != want:
        mismatches.append([repr(args), repr(want), repr(got)])
print(json.dumps({"checked": checked, "mismatches": mismatches}))
'''


@dataclass
class HiddenResult:
    task_id: str
    passed: bool
    checked: int
    mismatches: list[list[str]] = field(default_factory=list)  # [args, expected, got]

    def example(self) -> str:
        if not self.mismatches:
            return ""
        args, want, got = self.mismatches[0]
        return f"{args}: expected {_near_diff(want, got)[0]}, got {_near_diff(want, got)[1]}"


def _near_diff(want: str, got: str, context: int = 12) -> tuple[str, str]:
    """Trim two long reprs to the region where they first differ."""
    if len(want) <= 40 and len(got) <= 40:
        return want, got
    i = next((k for k, (a, b) in enumerate(zip(want, got)) if a != b), min(len(want), len(got)))
    start = max(0, i - context)
    lead = "..." if start else ""
    return lead + want[start : i + context] + ("..." if i + context < len(want) else ""), (
        lead + got[start : i + context] + ("..." if i + context < len(got) else "")
    )


def has_reference(task_id: str) -> bool:
    return task_id in REFERENCES


def hidden_check(task_id: str, solution: str | None, *, seed: int = 0, timeout: float = 30.0) -> HiddenResult | None:
    """Compare a solution with the task's reference on inputs its tests never use."""
    if task_id not in REFERENCES:
        return None
    if not solution:
        return HiddenResult(task_id, False, 0, [["-", "a solution", "none"]])
    name, reference, generator = REFERENCES[task_id]
    payload = json.dumps(
        {"name": name, "reference": reference, "generator": generator, "solution": solution, "seed": seed}
    )
    with tempfile.TemporaryDirectory() as box:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", _RUNNER],
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path(box),
                env={"PATH": "/usr/bin:/bin"},
            )
        except subprocess.TimeoutExpired:
            return HiddenResult(task_id, False, 0, [["-", f"finish within {timeout:g}s", "timed out"]])
    try:
        out = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return HiddenResult(task_id, False, 0, [["-", "a result", (proc.stderr or "no output").strip()[-200:]]])
    return HiddenResult(task_id, not out["mismatches"], out["checked"], out["mismatches"])
