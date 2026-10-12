"""Code-based graders.

The single hard rule, from Anthropic: grade the OUTCOME (the final
environment state), never the PATH (the agent's tool-call sequence).
Every grader below inspects only the outcome object handed to it.
"""
from __future__ import annotations

import re
from typing import Any

from .models import GraderSpec, GradeResult


def get_field(outcome: Any, field: str) -> Any:
    """Dot-path lookup into the outcome. '' returns the whole outcome."""
    if not field:
        return outcome
    current = outcome
    for part in field.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return _MISSING
    return current


class _Missing:
    def __repr__(self) -> str:  # pragma: no cover
        return "<missing>"


_MISSING = _Missing()


def evaluate(spec: GraderSpec, outcome: Any) -> GradeResult:
    """Evaluate one grader spec against an outcome. Returns (passed, detail)."""
    if spec.type == "all_of":
        details = []
        for sub in spec.specs:
            r = evaluate(sub, outcome)
            details.append(r.detail)
            if not r.passed:
                return GradeResult(passed=False, detail=f"all_of failed: {r.detail}")
        return GradeResult(passed=True, detail=f"all_of passed ({len(details)} checks)")

    if spec.type == "any_of":
        details = []
        for sub in spec.specs:
            r = evaluate(sub, outcome)
            details.append(r.detail)
            if r.passed:
                return GradeResult(passed=True, detail=f"any_of passed: {r.detail}")
        return GradeResult(passed=False, detail=f"any_of failed: {'; '.join(details)}")

    value = get_field(outcome, spec.field)
    label = f"field '{spec.field}'" if spec.field else "outcome"

    if value is _MISSING:
        return GradeResult(passed=False, detail=f"{label} is missing from outcome")

    if spec.type == "exact":
        ok = value == spec.expected
        return GradeResult(passed=ok, detail=f"{label}: {value!r} {'==' if ok else '!='} {spec.expected!r}")

    if spec.type == "contains":
        ok = spec.expected in value if isinstance(value, (str, list, dict)) else False
        return GradeResult(passed=ok, detail=f"{label} {'contains' if ok else 'does not contain'} {spec.expected!r}")

    if spec.type == "regex":
        if not isinstance(value, str) or spec.pattern is None:
            return GradeResult(passed=False, detail=f"{label} is not a string or no pattern given")
        ok = re.search(spec.pattern, value) is not None
        return GradeResult(passed=ok, detail=f"{label} {'matches' if ok else 'does not match'} /{spec.pattern}/")

    if spec.type == "gte":
        try:
            ok = float(value) >= float(spec.expected)
        except (TypeError, ValueError):
            return GradeResult(passed=False, detail=f"{label}={value!r} is not comparable to {spec.expected!r}")
        return GradeResult(passed=ok, detail=f"{label}={value!r} {'>=' if ok else '<'} {spec.expected!r}")

    if spec.type == "lte":
        try:
            ok = float(value) <= float(spec.expected)
        except (TypeError, ValueError):
            return GradeResult(passed=False, detail=f"{label}={value!r} is not comparable to {spec.expected!r}")
        return GradeResult(passed=ok, detail=f"{label}={value!r} {'<=' if ok else '>'} {spec.expected!r}")

    return GradeResult(passed=False, detail=f"unknown grader type: {spec.type}")
