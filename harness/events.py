"""Event types recorded during an agent trajectory."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventKind(Enum):
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOKEN_USAGE = "token_usage"
    ERROR = "error"


@dataclass(frozen=True)
class TrajectoryEvent:
    """One observable step in an agent run.

    t_ms is milliseconds since the run started. payload carries
    kind-specific data (e.g. tool name and args for TOOL_CALL).
    """

    kind: EventKind
    step: int
    payload: dict[str, Any] = field(default_factory=dict)
    t_ms: float = 0.0
