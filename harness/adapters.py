"""Real-model agent adapters: plug OpenAI or Anthropic into the Agent protocol.

Optional dependencies: `pip install openai anthropic`. The harness core
stays stdlib-only; these adapters import their SDKs lazily and raise a
clear error if the package (or API key) is missing.

The adapters are single-turn baselines: they ask the model to write the
solution in one shot and extract the fenced code block. They exist so a
team can go from "scripted demo" to "real model, real dollars" without
rewriting the harness. Multi-turn tool-use loops are left to the caller:
subclass and override act().
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .agent import AgentResult
from .events import EventKind, TrajectoryEvent

# Public list-price defaults, USD per 1M tokens. Verify current pricing
# before budgeting; override per-instance if your contract differs.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-haiku-4": (0.80, 4.00),
    "claude-sonnet-4": (3.00, 15.00),
}

SYSTEM_PROMPT = (
    "You are a coding agent. Reply with ONLY a fenced python code block "
    "containing the complete solution module. No explanation outside the "
    "code block."
)

_CODE_BLOCK = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str | None:
    """Pull the first fenced code block out of model output."""
    m = _CODE_BLOCK.search(text)
    if m:
        return m.group(1).strip()
    text = text.strip()
    return text or None


def price_for(model: str) -> tuple[float, float]:
    """(price_in_per_1k, price_out_per_1k) for a model name."""
    per_1m_in, per_1m_out = MODEL_PRICES.get(model, (3.0, 15.0))
    return per_1m_in / 1000.0, per_1m_out / 1000.0


@dataclass
class OpenAIAgent:
    """Single-turn coding agent backed by the OpenAI API."""

    model: str = "gpt-4o-mini"
    system_prompt: str = SYSTEM_PROMPT
    max_tokens: int = 2048
    temperature: float = 0.2
    api_key: str | None = None
    _events_extra: list = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package not installed; pip install openai"
            ) from exc
        key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY is not set")
        self._client = OpenAI(api_key=key)

    @property
    def name(self) -> str:
        return f"openai/{self.model}"

    @property
    def price_in_per_1k(self) -> float:
        return price_for(self.model)[0]

    @property
    def price_out_per_1k(self) -> float:
        return price_for(self.model)[1]

    def act(self, prompt: str, step_budget: int) -> AgentResult:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0
        events = [
            TrajectoryEvent(EventKind.MESSAGE, 0, {"role": "user"}, 0.0),
            TrajectoryEvent(
                EventKind.TOOL_CALL, 1, {"tool": "llm", "model": self.model}, 0.0
            ),
            TrajectoryEvent(
                EventKind.TOKEN_USAGE,
                2,
                {"input_tokens": in_tok, "output_tokens": out_tok},
                0.0,
            ),
        ]
        return AgentResult(
            solution=extract_code(text),
            events=events,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )


@dataclass
class AnthropicAgent:
    """Single-turn coding agent backed by the Anthropic API."""

    model: str = "claude-sonnet-4"
    system_prompt: str = SYSTEM_PROMPT
    max_tokens: int = 2048
    temperature: float = 0.2
    api_key: str | None = None

    def __post_init__(self) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed; pip install anthropic"
            ) from exc
        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=key)

    @property
    def name(self) -> str:
        return f"anthropic/{self.model}"

    @property
    def price_in_per_1k(self) -> float:
        return price_for(self.model)[0]

    @property
    def price_out_per_1k(self) -> float:
        return price_for(self.model)[1]

    def act(self, prompt: str, step_budget: int) -> AgentResult:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in resp.content if hasattr(block, "text")
        )
        in_tok = resp.usage.input_tokens if resp.usage else 0
        out_tok = resp.usage.output_tokens if resp.usage else 0
        events = [
            TrajectoryEvent(EventKind.MESSAGE, 0, {"role": "user"}, 0.0),
            TrajectoryEvent(
                EventKind.TOOL_CALL, 1, {"tool": "llm", "model": self.model}, 0.0
            ),
            TrajectoryEvent(
                EventKind.TOKEN_USAGE,
                2,
                {"input_tokens": in_tok, "output_tokens": out_tok},
                0.0,
            ),
        ]
        return AgentResult(
            solution=extract_code(text),
            events=events,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
