"""Trial execution.

Each trial is isolated: an optional reset hook fires first (the agent is
expected to return to a clean environment), then the trial gets a unique
trial_id the agent can key its own state on. The full request/response
exchange is recorded as the transcript; the OUTCOME (final environment
state) is what gets graded, never the tool-call path.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from . import db
from .graders import evaluate
from .models import GraderSpec, new_id

AGENT_TIMEOUT = 60.0


def _ts() -> datetime:
    return datetime.now(timezone.utc)


async def call_agent(agent_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST to the agent endpoint. Separated for test monkeypatching."""
    async with httpx.AsyncClient(timeout=AGENT_TIMEOUT, trust_env=False) as client:
        resp = await client.post(agent_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError(f"agent returned non-object: {data!r:.200}")
        return data


async def call_reset(reset_url: str) -> None:
    async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
        resp = await client.post(reset_url, json={})
        resp.raise_for_status()


def extract_outcome(agent_response: dict[str, Any]) -> dict[str, Any]:
    """The outcome is the final environment state. Agents report it as
    `final_state`; if absent, the whole response body is the outcome."""
    state = agent_response.get("final_state")
    if isinstance(state, dict):
        return state
    return {k: v for k, v in agent_response.items() if k != "tool_calls"}


async def run_trial(db_path: str, suite: dict, task: dict) -> dict:
    """Run one trial of a task against the suite's agent. Returns the trial record."""
    trial_id = new_id()
    transcript: list[dict] = []

    def log(type_: str, payload: dict[str, Any]) -> None:
        transcript.append({"ts": _ts().isoformat(), "type": type_, "payload": payload})

    await db.insert_trial(db_path, {
        "id": trial_id, "task_id": task["id"], "suite_id": suite["id"],
        "status": "running", "transcript": transcript,
        "started_at": _ts().isoformat(),
    })
    log("trial_started", {"trial_id": trial_id, "task_id": task["id"]})

    # --- isolation: reset hook + unique trial context ---------------------
    if suite.get("reset_url"):
        try:
            await call_reset(suite["reset_url"])
            log("reset", {"url": suite["reset_url"], "ok": True})
        except Exception as e:  # reset failure is recorded, not fatal
            log("reset", {"url": suite["reset_url"], "ok": False, "error": str(e)[:300]})

    payload = {"trial_id": trial_id, "task_id": task["id"], "input": task["input"]}
    log("agent_request", {"url": suite["agent_url"], "payload": payload})

    try:
        response = await call_agent(suite["agent_url"], payload)
    except Exception as e:
        log("agent_error", {"error": str(e)[:500]})
        await db.update_trial(db_path, trial_id, status="error",
                              transcript=transcript,
                              grade_detail=f"agent call failed: {e}"[:500],
                              finished_at=_ts().isoformat())
        return await db.get_trial(db_path, trial_id)  # type: ignore[return-value]

    # Record what the agent did (observability), but grade only the outcome.
    log("agent_response", {
        "output": response.get("output"),
        "tool_calls": response.get("tool_calls", []),
        "final_state_keys": list((response.get("final_state") or {}).keys()),
    })

    outcome = extract_outcome(response)
    log("outcome_extracted", {"outcome": outcome})

    grader = GraderSpec.model_validate(task["grader"])
    grade = evaluate(grader, outcome)
    log("graded", {"passed": grade.passed, "detail": grade.detail})

    status = "passed" if grade.passed else "failed"
    await db.update_trial(
        db_path, trial_id, status=status, transcript=transcript,
        outcome=outcome, passed=grade.passed, grade_detail=grade.detail,
        finished_at=_ts().isoformat(),
    )
    log("trial_finished", {"status": status})
    await db.update_trial(db_path, trial_id, transcript=transcript)
    return await db.get_trial(db_path, trial_id)  # type: ignore[return-value]
