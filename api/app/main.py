"""Eval harness API.

Anthropic's eval vocabulary, OpenAI's harness discipline:
  POST /suites                  create a suite (agent_url + optional reset_url)
  POST /suites/{id}/tasks       add a task (input + grader + kind)
  POST /trials                  run trial(s): {task_id} or {suite_id}
  GET  /trials/{id}             transcript + outcome
  GET  /suites/{id}/results     pass rates, pass@k, pass^k, capability/regression split
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from . import db, metrics, runner
from .models import (
    AggregateMetrics,
    GraderSpec,
    ResultsRead,
    SuiteCreate,
    SuiteRead,
    TaskCreate,
    TaskMetrics,
    TaskRead,
    TrialCreate,
    TrialRead,
    TrialsCreated,
    new_id,
)

DB_PATH = str(db.DB_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db(DB_PATH)
    yield


app = FastAPI(
    title="Eval Harness API",
    description="Eval-driven agent engineering: tasks, isolated trials, outcome grading, pass@k.",
    version="0.1.0",
    lifespan=lifespan,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------- suites ---

@app.post("/suites", response_model=SuiteRead, status_code=201)
async def create_suite(body: SuiteCreate):
    suite = {
        "id": new_id(),
        "name": body.name,
        "description": body.description,
        "agent_url": body.agent_url,
        "reset_url": body.reset_url,
        "default_trials": body.default_trials,
        "created_at": _now(),
    }
    await db.insert_suite(DB_PATH, suite)
    return SuiteRead(**suite)


@app.get("/suites/{suite_id}", response_model=SuiteRead)
async def get_suite(suite_id: str):
    suite = await db.get_suite(DB_PATH, suite_id)
    if not suite:
        raise HTTPException(404, "suite not found")
    return SuiteRead(**suite)


# ------------------------------------------------------------------ tasks ---

@app.post("/suites/{suite_id}/tasks", response_model=TaskRead, status_code=201)
async def create_task(suite_id: str, body: TaskCreate):
    suite = await db.get_suite(DB_PATH, suite_id)
    if not suite:
        raise HTTPException(404, "suite not found")
    task = {
        "id": new_id(),
        "suite_id": suite_id,
        "name": body.name,
        "input": body.input,
        "grader": body.grader.model_dump(),
        "kind": body.kind,
        "trials": body.trials or suite["default_trials"],
        "created_at": _now(),
    }
    await db.insert_task(DB_PATH, task)
    return TaskRead(**task)


@app.get("/suites/{suite_id}/tasks", response_model=list[TaskRead])
async def list_tasks(suite_id: str):
    if not await db.get_suite(DB_PATH, suite_id):
        raise HTTPException(404, "suite not found")
    return [TaskRead(**t) for t in await db.list_tasks(DB_PATH, suite_id)]


# ----------------------------------------------------------------- trials ---

@app.post("/trials", response_model=TrialsCreated, status_code=201)
async def create_trials(body: TrialCreate):
    """Run trials. {task_id} runs one trial; {suite_id} runs every task
    in the suite for its configured trial count."""
    targets: list[dict] = []
    if body.task_id:
        task = await db.get_task(DB_PATH, body.task_id)
        if not task:
            raise HTTPException(404, "task not found")
        targets = [(task, 1)]
    elif body.suite_id:
        suite = await db.get_suite(DB_PATH, body.suite_id)
        if not suite:
            raise HTTPException(404, "suite not found")
        tasks = await db.list_tasks(DB_PATH, body.suite_id)
        if not tasks:
            raise HTTPException(400, "suite has no tasks")
        targets = [(t, t["trials"]) for t in tasks]
    else:
        raise HTTPException(400, "provide task_id or suite_id")

    trial_ids: list[str] = []
    for task, count in targets:
        suite = await db.get_suite(DB_PATH, task["suite_id"])
        assert suite is not None
        for _ in range(count):
            trial = await runner.run_trial(DB_PATH, suite, task)
            trial_ids.append(trial["id"])
    return TrialsCreated(trial_ids=trial_ids, count=len(trial_ids))


@app.get("/trials/{trial_id}", response_model=TrialRead)
async def get_trial(trial_id: str):
    trial = await db.get_trial(DB_PATH, trial_id)
    if not trial:
        raise HTTPException(404, "trial not found")
    return TrialRead(**trial)


# ---------------------------------------------------------------- results ---

@app.get("/suites/{suite_id}/results", response_model=ResultsRead)
async def get_results(suite_id: str, k: int = 3):
    suite = await db.get_suite(DB_PATH, suite_id)
    if not suite:
        raise HTTPException(404, "suite not found")
    tasks = await db.list_tasks(DB_PATH, suite_id)

    task_rows: list[TaskMetrics] = []
    all_passes: list[bool] = []
    by_kind: dict[str, list[bool]] = {}
    for t in tasks:
        trials = await db.list_trials_for_task(DB_PATH, t["id"])
        passes = [bool(tr["passed"]) for tr in trials if tr["passed"] is not None]
        m = metrics.task_metrics(passes, k)
        task_rows.append(TaskMetrics(
            task_id=t["id"], name=t["name"], kind=t["kind"], **m,
        ))
        all_passes.extend(passes)
        by_kind.setdefault(t["kind"], []).extend(passes)

    def agg(passes: list[bool], n_tasks: int) -> AggregateMetrics:
        m = metrics.task_metrics(passes, k)
        return AggregateMetrics(tasks=n_tasks, trials=m["trials"],
                                pass_rate=m["pass_rate"],
                                pass_at_k=m["pass_at_k"],
                                pass_caret_k=m["pass_caret_k"])

    kinds = {t["kind"] for t in tasks}
    return ResultsRead(
        suite_id=suite_id,
        k=k,
        overall=agg(all_passes, len(tasks)),
        by_kind={kind: agg(by_kind.get(kind, []),
                           sum(1 for t in tasks if t["kind"] == kind))
                 for kind in sorted(kinds)},
        tasks=task_rows,
    )


@app.get("/health")
async def health():
    return {"ok": True, "version": "0.1.0"}


def _validate_grader(spec: dict) -> None:
    GraderSpec.model_validate(spec)  # raises on bad spec
