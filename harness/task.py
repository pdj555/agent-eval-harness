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
#
# The environment is only half of the boundary. The candidate also runs
# under the filesystem guard in _CANDIDATE_RUNNER below: it may read and
# write inside its own temporary directory, it may read the Python
# installation so imports keep working, and every other file operation
# is refused. Starting another process or loading native code is also
# refused, because either one would let candidate code act outside the
# interpreter the guard watches. metrics/hidden.py installs the same
# guard before it runs a solution.
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


# The candidate entry point, written into the candidate's directory and
# run instead of pytest directly. It installs a Python audit hook that
# checks every file operation and process start, then runs pytest.
# Audit hooks cannot be removed or replaced by the code they watch, and
# every way Python opens, lists, creates, moves, or deletes a file
# reports to the hook first. Process starts and native code loads also
# report to the hook, and the hook refuses all of them: a second process
# or a native library would run outside the hook's view.
_CANDIDATE_RUNNER = r'''
import os
import site
import sys
import sysconfig

SANDBOX = os.path.realpath(sys.argv[1])


def _read_roots():
    found = [
        SANDBOX,
        sys.prefix,
        sys.base_prefix,
        os.path.dirname(os.path.realpath(sys.executable)),
        "/usr/share/zoneinfo",  # the time zone data some systems keep outside Python
    ]
    found += list(sysconfig.get_paths().values())
    for getter_name in ("getsitepackages", "getusersitepackages"):
        getter = getattr(site, getter_name, None)
        if getter is None:
            continue
        try:
            value = getter()
        except Exception:
            continue
        found += value if isinstance(value, list) else [value]
    return tuple(os.path.realpath(p) for p in found if p and os.path.exists(p))


READ_ROOTS = _read_roots()


def _inside(path, roots):
    return any(path == root or path.startswith(root + os.sep) for root in roots)


def _resolve(raw):
    if isinstance(raw, int):  # a file descriptor, opened through a checked path
        return None
    if isinstance(raw, bytes):
        raw = os.fsdecode(raw)
    if not isinstance(raw, (str, os.PathLike)):
        return None
    return os.path.realpath(os.fspath(raw))


def _check(raw, write):
    path = _resolve(raw)
    if path is None or path == os.path.realpath("/dev/null"):
        return
    if _inside(path, (SANDBOX,)):
        return
    if not write and _inside(path, READ_ROOTS):
        return
    action = "write" if write else "read"
    raise PermissionError(f"candidate code may not {action} outside its sandbox: {path}")


_WRITE_ONLY_EVENTS = (
    "os.mkdir",
    "os.rmdir",
    "os.remove",
    "os.unlink",
    "os.chmod",
    "os.chown",
    "os.truncate",
    "os.utime",
)

_REFUSED_EVENTS = (
    "subprocess.Popen",
    "os.system",
    "os.posix_spawn",
    "os.exec",
    "os.startfile",
    "ctypes.dlopen",
    "ctypes.dlsym",
)


def _guard(event, args):
    if event == "import":
        # Native code runs outside this guard, so candidate code may not
        # bring it in: no ctypes, and no shared library files imported
        # from the sandbox. Raising ImportError keeps the standard
        # library working: modules that try ctypes and fall back when
        # it is missing take the fallback, exactly as on a Python
        # built without ctypes.
        module = args[0] if args and isinstance(args[0], str) else ""
        if module.split(".")[0] in ("ctypes", "_ctypes"):
            raise ImportError("candidate code may not import ctypes: native code runs outside the filesystem guard")
        filename = _resolve(args[1]) if len(args) > 1 else None
        if filename and _inside(filename, (SANDBOX,)) and filename.endswith((".so", ".dylib", ".pyd", ".dll")):
            raise ImportError("candidate code may not import a shared library from its sandbox")
    elif event == "open":
        mode = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
        _check(args[0], any(flag in mode for flag in "wxa+"))
    elif event in ("os.listdir", "os.scandir"):
        _check(args[0], False)
    elif event in _WRITE_ONLY_EVENTS:
        _check(args[0], True)
    elif event in ("os.rename", "os.replace"):
        _check(args[0], True)
        _check(args[1], True)
    elif event == "os.link":
        _check(args[0], False)
        _check(args[1], True)
    elif event == "os.symlink":
        _check(args[1], True)
    elif event in _REFUSED_EVENTS:
        raise PermissionError(f"candidate code may not use {event}: it would run outside the filesystem guard")


sys.addaudithook(_guard)

import pytest

sys.exit(
    pytest.main(
        [
            "test_solution.py",
            "-q",
            "--tb=short",
            "--basetemp=" + os.path.join(SANDBOX, ".pytest-tmp"),
        ]
    )
)
'''


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
        (root / "_candidate_runner.py").write_text(_CANDIDATE_RUNNER)
        env = _candidate_env()
        # Temporary files the candidate creates belong inside its own
        # directory too, so point the temp variables at it instead of
        # the host temp directory the allowlist would otherwise pass on.
        scratch = root / ".tmp"
        scratch.mkdir()
        env["TMPDIR"] = str(scratch)
        env["TEMP"] = str(scratch)
        env["TMP"] = str(scratch)
        try:
            proc = subprocess.run(
                [sys.executable, str(root / "_candidate_runner.py"), str(root)],
                cwd=root,
                env=env,
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
