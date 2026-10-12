"""Pydantic schemas for the eval harness API.

Vocabulary follows Anthropic's "Demystifying evals for AI agents":
  task      - input + success criteria
  trial     - one attempt at a task (run multiple per task)
  grader    - scoring logic (code-based here; model/human later)
  transcript- full record of a trial
  outcome   - final environment state, NOT what the agent claimed
  suite     - collection of tasks
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    return uuid4().hex[:12]


# ---------------------------------------------------------------- graders ---

GraderType = Literal["exact", "contains", "regex", "gte", "lte", "all_of", "any_of"]
TaskKind = Literal["capability", "regression"]
TrialStatus = Literal["pending", "running", "passed", "failed", "error"]


class GraderSpec(BaseModel):
    """A code-based grader. It inspects the OUTCOME only, never the
    agent's tool-call path. `field` is a dot-path into the outcome
    object ("" = the whole outcome)."""

    type: GraderType
    field: str = ""
    expected: Any = None
    pattern: str | None = None
    specs: list["GraderSpec"] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class GradeResult(BaseModel):
    passed: bool
    detail: str


# ----------------------------------------------------------------- suites ---

class SuiteCreate(BaseModel):
    name: str
    description: str = ""
    agent_url: str = Field(description="Agent endpoint. POST {trial_id, task_id, input} -> {output, final_state, tool_calls?}")
    reset_url: str | None = Field(default=None, description="Optional. POST {} before each trial for isolation.")
    default_trials: int = Field(default=3, ge=1, le=50)


class SuiteRead(BaseModel):
    id: str
    name: str
    description: str
    agent_url: str
    reset_url: str | None
    default_trials: int
    created_at: datetime


# ------------------------------------------------------------------ tasks ---

class TaskCreate(BaseModel):
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    grader: GraderSpec
    kind: TaskKind = "capability"
    trials: int | None = Field(default=None, ge=1, le=50,
                               description="Trials per task. Defaults to the suite's default_trials.")


class TaskRead(BaseModel):
    id: str
    suite_id: str
    name: str
    input: dict[str, Any]
    grader: GraderSpec
    kind: TaskKind
    trials: int
    created_at: datetime


# ----------------------------------------------------------------- trials ---

class TrialCreate(BaseModel):
    task_id: str | None = None
    suite_id: str | None = None

    model_config = {"extra": "forbid"}


class TranscriptEvent(BaseModel):
    ts: datetime
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TrialRead(BaseModel):
    id: str
    task_id: str
    suite_id: str
    status: TrialStatus
    transcript: list[TranscriptEvent] = Field(default_factory=list)
    outcome: dict[str, Any] | None = None
    passed: bool | None = None
    grade_detail: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TrialsCreated(BaseModel):
    trial_ids: list[str]
    count: int


# ---------------------------------------------------------------- results ---

class TaskMetrics(BaseModel):
    task_id: str
    name: str
    kind: TaskKind
    trials: int
    passes: int
    pass_rate: float
    pass_at_k: float | None = None
    pass_caret_k: float | None = None


class AggregateMetrics(BaseModel):
    tasks: int
    trials: int
    pass_rate: float
    pass_at_k: float | None = None
    pass_caret_k: float | None = None


class ResultsRead(BaseModel):
    suite_id: str
    k: int
    overall: AggregateMetrics
    by_kind: dict[str, AggregateMetrics]
    tasks: list[TaskMetrics]
