"""Regression tests for the credential boundary in verify().

The adapters keep OPENAI_API_KEY / ANTHROPIC_API_KEY in this process's
environment. The candidate subprocess must never inherit them: generated
code runs with an allowlist environment only (see harness/task.py).
These tests fail on the pre-fix verify(), which passed no env argument
and inherited the full process environment.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.task import Task, verify

_SOLUTION = (
    "import os\n"
    "LEAKED_OPENAI = os.environ.get('OPENAI_API_KEY')\n"
    "LEAKED_ANTHROPIC = os.environ.get('ANTHROPIC_API_KEY')\n"
    "LEAKED_OTHER = os.environ.get('HARNESS_TEST_SECRET')\n"
)

_TESTS = """
import os

from solution import LEAKED_ANTHROPIC, LEAKED_OPENAI, LEAKED_OTHER


def test_solution_saw_no_openai_key():
    assert LEAKED_OPENAI is None, LEAKED_OPENAI


def test_solution_saw_no_anthropic_key():
    assert LEAKED_ANTHROPIC is None, LEAKED_ANTHROPIC


def test_solution_saw_no_other_harness_secret():
    assert LEAKED_OTHER is None, LEAKED_OTHER


def test_candidate_env_has_no_keys_directly():
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("ANTHROPIC_API_KEY") is None


def test_candidate_env_is_functional():
    # The allowlist must still give the candidate a working environment.
    assert os.environ.get("PATH")
"""


def test_verify_does_not_leak_credentials_to_candidate(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-must-not-leak-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-must-not-leak-anthropic")
    monkeypatch.setenv("HARNESS_TEST_SECRET", "must-not-leak-either")
    task = Task(
        id="credential-boundary",
        title="candidate subprocess receives an allowlist environment",
        prompt="",
        tests=_TESTS,
    )
    outcome = verify(task, _SOLUTION)
    assert outcome.passed, outcome.stdout or outcome.detail
