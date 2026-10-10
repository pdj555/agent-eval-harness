"""Cost modeling: what evals cost at real model prices, and when they pay off.

Two questions teams actually ask: "what will it cost to run this suite
properly?" and "is the eval spend worth it?" This module answers both
with arithmetic, not vibes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PricePoint:
    name: str
    price_in_per_1k: float
    price_out_per_1k: float
    blurb: str = ""


# Illustrative tiers from public list prices. Verify current pricing
# before budgeting; the math below takes any PricePoint.
PRICE_POINTS: tuple[PricePoint, ...] = (
    PricePoint("budget", 0.00015, 0.00060, "small fast models"),
    PricePoint("mid", 0.00250, 0.01000, "capable general models"),
    PricePoint("frontier", 0.01500, 0.07500, "largest reasoning models"),
)


def project_cost(
    n_tasks: int,
    repeats: int,
    mean_in_tokens: float,
    mean_out_tokens: float,
    price_in_per_1k: float,
    price_out_per_1k: float,
) -> float:
    """Projected USD for one full suite run."""
    runs = n_tasks * repeats
    return runs * (
        mean_in_tokens / 1000.0 * price_in_per_1k
        + mean_out_tokens / 1000.0 * price_out_per_1k
    )


def cost_table(
    n_tasks: int,
    repeats: int,
    mean_in_tokens: float,
    mean_out_tokens: float,
    price_points: tuple[PricePoint, ...] = PRICE_POINTS,
) -> str:
    """Markdown: projected suite cost across price tiers."""
    lines = [
        "# Projected eval cost",
        "",
        f"{n_tasks} tasks x {repeats} repeats, "
        f"{mean_in_tokens:.0f} in / {mean_out_tokens:.0f} out tokens per run",
        "",
        "| tier | per run | full suite |",
        "|---|---|---|",
    ]
    for pp in price_points:
        full = project_cost(
            n_tasks, repeats, mean_in_tokens, mean_out_tokens,
            pp.price_in_per_1k, pp.price_out_per_1k,
        )
        per_run = full / (n_tasks * repeats)
        lines.append(f"| {pp.name} ({pp.blurb}) | ${per_run:.4f} | ${full:.2f} |")
    return "\n".join(lines)


def breakeven(
    eval_cost_usd: float,
    incident_cost_usd: float,
    incident_probability: float,
) -> dict[str, float]:
    """How much risk must the eval remove to pay for itself?

    A bad prompt change causes an incident costing `incident_cost_usd`
    with probability `incident_probability` per deploy. The eval costs
    `eval_cost_usd` per run. Returns the minimum fraction of that risk
    the eval must catch (required_catch_rate) for the spend to break even.
    """
    if incident_cost_usd <= 0 or not 0 < incident_probability <= 1:
        raise ValueError("need positive incident cost and a probability in (0, 1]")
    expected_loss = incident_cost_usd * incident_probability
    return {
        "eval_cost_usd": eval_cost_usd,
        "expected_loss_usd": expected_loss,
        "required_catch_rate": eval_cost_usd / expected_loss,
    }


def render_breakeven(
    eval_cost_usd: float,
    incident_cost_usd: float,
    incident_probability: float,
) -> str:
    """One-paragraph breakeven analysis in markdown."""
    b = breakeven(eval_cost_usd, incident_cost_usd, incident_probability)
    rate = b["required_catch_rate"]
    verdict = (
        "The eval pays for itself even if it catches a small share of bad deploys."
        if rate < 0.2
        else "The eval needs to catch a meaningful share of bad deploys to justify the spend."
        if rate < 1.0
        else "The eval costs more than the risk it can remove at this incident rate. "
        "Run it cheaper (fewer repeats, budget tier) or reserve it for high-stakes changes."
    )
    return "\n".join(
        [
            "# Breakeven analysis",
            "",
            f"- Eval cost per run: ${b['eval_cost_usd']:.2f}",
            f"- Expected incident loss per deploy: ${b['expected_loss_usd']:.2f}",
            f"- Required catch rate: **{rate:.1%}**",
            "",
            verdict,
        ]
    )
