"""Prompt variants and tool-use strategies for ablations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptVariant:
    """A named change to how the agent is instructed.

    system_addendum is appended to the task prompt. tool_strategy names
    the tool-use policy (documented, enforced by the agent implementation).
    """

    name: str
    system_addendum: str
    tool_strategy: str = "unrestricted"
    notes: str = ""


BASELINE = PromptVariant(
    name="baseline",
    system_addendum="",
    tool_strategy="unrestricted",
    notes="No extra instruction. Control condition.",
)

CHAIN_OF_THOUGHT = PromptVariant(
    name="cot",
    system_addendum=(
        "Before writing code, reason step by step about the requirements, "
        "edge cases, and the test assertions you must satisfy. Then write "
        "the final code."
    ),
    tool_strategy="unrestricted",
    notes="More output tokens; expected to trade cost for solve rate.",
)

PLAN_THEN_ACT = PromptVariant(
    name="plan-then-act",
    system_addendum=(
        "First write a numbered plan (at most 5 steps). Then implement "
        "exactly that plan. Do not deviate from the plan once written."
    ),
    tool_strategy="unrestricted",
    notes="Constrains wandering; expected to cut steps on multi-part tasks.",
)

READ_ONLY_FIRST = PromptVariant(
    name="read-only-first",
    system_addendum=(
        "You may only read and inspect for your first 3 tool calls. "
        "Writing code is forbidden until step 4."
    ),
    tool_strategy="read-only-first",
    notes="Forces comprehension before action; expected to help on bug-fix tasks.",
)

SELF_CRITIQUE = PromptVariant(
    name="self-critique",
    system_addendum=(
        "After drafting your solution, critique it against the task "
        "requirements, list any flaw you find, then submit the corrected version."
    ),
    tool_strategy="unrestricted",
    notes="Second pass; expected to raise reliability at higher token cost.",
)

VARIANTS: list[PromptVariant] = [
    BASELINE,
    CHAIN_OF_THOUGHT,
    PLAN_THEN_ACT,
    READ_ONLY_FIRST,
    SELF_CRITIQUE,
]


def apply_variant(prompt: str, variant: PromptVariant) -> str:
    if not variant.system_addendum:
        return prompt
    return f"{prompt}\n\n[prompt-variant:{variant.name}]\n{variant.system_addendum}"


@dataclass(frozen=True)
class AblationConfig:
    variants: tuple[PromptVariant, ...] = field(default_factory=lambda: tuple(VARIANTS))
    repeats: int = 3
    price_in_per_1k: float = 3.0
    price_out_per_1k: float = 15.0
