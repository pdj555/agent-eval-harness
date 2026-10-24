"""Task definitions and solution verification."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# The candidate subprocess runs untrusted, model-generated code. It gets
# only the variables a Python process needs to run - never the harness's
# environment, which holds the adapters' API keys (harness/adapters.py
# reads OPENAI_API_KEY / ANTHROPIC_API_KEY from it). Same rule the hidden
# check already follows in metrics/hidden.py.
_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "SYSTEMROOT",  # Windows Python needs this to find system DLLs
    "PATHEXT",  # Windows executable lookup, alongside PATH
)


def _candidate_env() -> dict[str, str]:
    """The full environment a candidate subprocess is allowed to see."""
    return {name: os.environ[name] for name in _ENV_ALLOWLIST if name in os.environ}


@dataclass(frozen=True)
class Task:
    """A coding task with an executable test suite.

    prompt: what the agent sees (runner prefixes "[task:<id>]").
    tests: pytest source, run against a module named `solution`
           containing the agent's code.
    """

    id: str
    title: str
    prompt: str
    tests: str
    timeout_s: float = 60.0
    max_steps: int = 25


@dataclass(frozen=True)
class TestOutcome:
    passed: bool
    detail: str
    stdout: str = ""  # full pytest output, truncated; used by failure analysis


def verify(task: Task, solution_source: str | None) -> TestOutcome:
    """Write the solution to a temp dir and run the task's pytest suite."""
    if not solution_source or not solution_source.strip():
        return TestOutcome(False, "no solution produced")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "solution.py").write_text(solution_source)
        (root / "test_solution.py").write_text(task.tests)
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "test_solution.py", "-q", "--tb=short"],
                cwd=root,
                env=_candidate_env(),
                capture_output=True,
                text=True,
                timeout=task.timeout_s,
            )
        except subprocess.TimeoutExpired:
            return TestOutcome(False, f"tests timed out after {task.timeout_s}s")
        raw = (proc.stdout or "") + "\n" + (proc.stderr or "")
        raw = raw[:4000]
        if proc.returncode == 0:
            return TestOutcome(True, _last_line(proc.stdout) or "all tests passed", raw)
        detail = _last_line(proc.stdout) or _last_line(proc.stderr) or "tests failed"
        return TestOutcome(False, detail, raw)


def _last_line(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ""
