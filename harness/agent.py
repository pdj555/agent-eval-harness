"""Agent interface and deterministic stand-ins for tests and demos."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from .events import EventKind, TrajectoryEvent


@dataclass
class AgentResult:
    solution: str | None
    events: list[TrajectoryEvent] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class Agent(Protocol):
    """Anything that can attempt a task.

    Implementations receive the task prompt and a step budget, and return
    a solution plus the trajectory that produced it. Token counts are
    self-reported; the runner trusts them and records them.
    """

    name: str

    def act(self, prompt: str, step_budget: int) -> AgentResult: ...


@dataclass
class ScriptedAgent:
    """Deterministic agent for tests, CI, and demos. No API keys needed.

    behavior maps task_id -> (solution_source, input_tokens, output_tokens,
    latency_s). Unknown tasks return no solution.
    """

    name: str
    behavior: dict[str, tuple[str | None, int, int, float]]
    default_latency_s: float = 0.0

    def act(self, prompt: str, step_budget: int) -> AgentResult:
        task_id = _task_id_from_prompt(prompt)
        solution, in_tok, out_tok, latency = self.behavior.get(
            task_id, (None, 50, 20, self.default_latency_s)
        )
        if latency > 0:
            time.sleep(latency)
        events = [
            TrajectoryEvent(EventKind.MESSAGE, 0, {"role": "user"}, 0.0),
            TrajectoryEvent(
                EventKind.TOOL_CALL, 1, {"tool": "write_file", "target": "solution.py"}, 10.0
            ),
            TrajectoryEvent(
                EventKind.TOOL_RESULT, 2, {"tool": "write_file", "ok": solution is not None}, 20.0
            ),
            TrajectoryEvent(
                EventKind.TOKEN_USAGE,
                3,
                {"input_tokens": in_tok, "output_tokens": out_tok},
                25.0,
            ),
        ]
        return AgentResult(
            solution=solution, events=events, input_tokens=in_tok, output_tokens=out_tok
        )


def _task_id_from_prompt(prompt: str) -> str:
    # Prompts are prefixed with "[task:<id>]" by the runner.
    if prompt.startswith("[task:"):
        return prompt[6:].split("]", 1)[0]
    return ""
