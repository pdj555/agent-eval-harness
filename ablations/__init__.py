"""ablations: prompt variants, tool-use strategies, comparisons."""

from .compare import ComparisonReport, compare
from .variants import (
    BASELINE,
    CHAIN_OF_THOUGHT,
    PLAN_THEN_ACT,
    READ_ONLY_FIRST,
    SELF_CRITIQUE,
    AblationConfig,
    PromptVariant,
    VARIANTS,
    apply_variant,
)

__all__ = [
    "AblationConfig",
    "BASELINE",
    "CHAIN_OF_THOUGHT",
    "ComparisonReport",
    "PLAN_THEN_ACT",
    "PromptVariant",
    "READ_ONLY_FIRST",
    "SELF_CRITIQUE",
    "VARIANTS",
    "apply_variant",
    "compare",
]
