"""Regression tests for the filesystem guard on candidate code.

Until this guard existed, verify() ran generated code in a temporary
directory but with the host user's full filesystem access: a solution
could read any file the harness user could read and write anywhere the
harness user could write. These tests fail on that verify(). The
solution below tries to escape at import time in six different ways and
records what happened; the task's suite then checks each attempt, and
this file checks the host side afterwards: the secret still holds its
original text and the file the solution tried to create outside its
directory does not exist.

The hidden-input check runs solution code in its own interpreter, so
the last test proves the same refusal there.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.task import Task, verify
from metrics.hidden import hidden_check

_SOLUTION_TEMPLATE = """
import os
import subprocess

SECRET_PATH = {secret!r}
OUTSIDE_WRITE_PATH = {outside_write!r}
OUTSIDE_DIR = {outside_dir!r}
RESULTS = {{}}


def _attempt(name, fn):
    try:
        fn()
    except Exception as exc:
        RESULTS[name] = type(exc).__name__
    else:
        RESULTS[name] = "not blocked"


_attempt("read_outside", lambda: open(SECRET_PATH).read())
_attempt("write_outside", lambda: open(OUTSIDE_WRITE_PATH, "w").write("escaped"))
_attempt("list_outside", lambda: os.listdir(OUTSIDE_DIR))
_attempt("delete_outside", lambda: os.remove(SECRET_PATH))
_attempt("start_process", lambda: subprocess.run(["true"]))
# Native code would run outside the guard, so importing ctypes is
# refused with ImportError, the refusal the standard library's own
# optional ctypes uses already know how to fall back from.
_attempt("load_native_code", lambda: __import__("ctypes").CDLL("libc.so.6"))
"""

_EXPECTED = {
    "read_outside": "PermissionError",
    "write_outside": "PermissionError",
    "list_outside": "PermissionError",
    "delete_outside": "PermissionError",
    "start_process": "PermissionError",
    "load_native_code": "ImportError",
}


def _attempts_tests() -> str:
    checks = "\n".join(
        f"""
def test_{name}_was_blocked():
    assert RESULTS["{name}"] == "{expected}", RESULTS["{name}"]
"""
        for name, expected in _EXPECTED.items()
    )
    return (
        """
from solution import RESULTS


def test_sandbox_itself_still_works():
    # The guard must leave the candidate a working directory: reading
    # and writing inside it, including through pytest's tmp_path, works.
    with open("notes.txt", "w") as fh:
        fh.write("inside")
    with open("notes.txt") as fh:
        assert fh.read() == "inside"


def test_tmp_path_is_writable(tmp_path):
    target = tmp_path / "scratch.txt"
    target.write_text("fixture")
    assert target.read_text() == "fixture"
"""
        + checks
    )


def test_verify_blocks_candidate_filesystem_escape(tmp_path):
    secret = tmp_path / "host-secret.txt"
    secret.write_text("host secret")
    outside_write = tmp_path / "escaped.txt"
    solution = _SOLUTION_TEMPLATE.format(
        secret=str(secret),
        outside_write=str(outside_write),
        outside_dir=str(tmp_path),
    )
    task = Task(
        id="filesystem-isolation",
        title="candidate code stays inside its sandbox",
        prompt="",
        tests=_attempts_tests(),
    )
    outcome = verify(task, solution)
    assert outcome.passed, outcome.stdout or outcome.detail
    # Host side proof, checked outside the candidate process entirely.
    assert secret.read_text() == "host secret"
    assert not outside_write.exists()


def test_verify_still_passes_a_solution_that_stays_inside():
    task = Task(
        id="filesystem-inside",
        title="a solution that only uses its sandbox passes",
        prompt="",
        tests="""
from solution import add


def test_add():
    assert add(2, 3) == 5
""",
    )
    outcome = verify(task, "def add(a, b):\n    return a + b\n")
    assert outcome.passed, outcome.stdout or outcome.detail


def test_hidden_check_blocks_candidate_filesystem_escape(tmp_path):
    secret = tmp_path / "hidden-secret.txt"
    secret.write_text("hidden secret")
    solution = (
        "def fizzbuzz_plus(n):\n"
        f"    return open({str(secret)!r}).read()\n"
    )
    result = hidden_check("fizzbuzz-plus", solution)
    assert result is not None
    assert not result.passed
    assert result.checked == 201
    # Every call was refused by the guard. Without the guard the calls
    # return the secret text instead, and this assertion fails.
    assert all(got == repr("raises PermissionError") for _, _, got in result.mismatches)
    assert secret.read_text() == "hidden secret"
