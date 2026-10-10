"""Statistical rigor for eval results.

Solve rates on small suites are noisy. This module answers the questions
that matter before a team acts on a number: how wide is the uncertainty,
is the ablation gain real or noise, and how many tasks would it take to
know.
"""

from __future__ import annotations

import math

from harness.runner import RunResult


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. z=1.96 is 95%."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def solve_rate_ci(
    results: list[RunResult], z: float = 1.96
) -> tuple[float, float, float]:
    """(solve_rate, ci_low, ci_high) with a Wilson interval."""
    n = len(results)
    k = sum(1 for r in results if r.solved)
    lo, hi = wilson_interval(k, n, z)
    return (k / n if n else 0.0, lo, hi)


def _chi2_sf_1df(x: float) -> float:
    """Survival function of chi-square with 1 degree of freedom."""
    if x <= 0:
        return 1.0
    return math.erfc(math.sqrt(x / 2.0))


def _paired_outcomes(
    results_a: list[RunResult], results_b: list[RunResult]
) -> list[tuple[bool, bool]]:
    """Align two result lists by (task_id, repeat index) into pairs."""
    def grouped(results: list[RunResult]) -> dict[str, list[bool]]:
        g: dict[str, list[bool]] = {}
        for r in results:
            g.setdefault(r.task_id, []).append(r.solved)
        return g

    ga, gb = grouped(results_a), grouped(results_b)
    pairs: list[tuple[bool, bool]] = []
    for task_id in ga:
        if task_id not in gb:
            continue
        for a_solved, b_solved in zip(ga[task_id], gb[task_id]):
            pairs.append((a_solved, b_solved))
    return pairs


def mcnemar(
    results_a: list[RunResult], results_b: list[RunResult]
) -> dict[str, float | int]:
    """McNemar's test on paired binary outcomes.

    b = A solved and B failed; c = A failed and B solved. The test asks
    whether the discordant pairs skew one way. Use it to decide if an
    ablation's solve-rate gain is real or noise.
    """
    pairs = _paired_outcomes(results_a, results_b)
    b = sum(1 for a, bb in pairs if a and not bb)
    c = sum(1 for a, bb in pairs if not a and bb)
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "chi2": 0.0, "p_value": 1.0, "n_pairs": len(pairs)}
    chi2 = (abs(b - c) - 1.0) ** 2 / n  # continuity correction
    return {
        "b": b,
        "c": c,
        "chi2": chi2,
        "p_value": _chi2_sf_1df(chi2),
        "n_pairs": len(pairs),
    }


def min_sample_size(
    delta: float,
    baseline: float = 0.5,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    """Tasks per variant needed to detect an absolute solve-rate `delta`.

    Two-proportion power calculation, two-sided `alpha`. Answers "how many
    tasks before we trust a 10-point gain" before you pay for the runs.
    """
    if not 0 < delta < 1:
        raise ValueError("delta must be in (0, 1)")
    # Normal quantiles for the common cases; good to 1e-3 for planning.
    z_alpha = {0.10: 1.645, 0.05: 1.96, 0.01: 2.576}[alpha] if alpha in (0.10, 0.05, 0.01) else 1.96
    z_beta = {0.8: 0.842, 0.9: 1.282}.get(power, 0.842)
    p1, p2 = baseline, min(1.0, baseline + delta)
    p_bar = (p1 + p2) / 2.0
    n = (
        z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
        + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2 / delta**2
    return math.ceil(n)


def render_ci_table(
    labeled: dict[str, list[RunResult]], z: float = 1.96
) -> str:
    """Markdown table of solve rates with 95% Wilson intervals."""
    lines = ["| variant | solve rate | 95% CI | n |", "|---|---|---|---|"]
    for label, results in labeled.items():
        rate, lo, hi = solve_rate_ci(results, z)
        lines.append(
            f"| {label} | {rate:.1%} | [{lo:.1%}, {hi:.1%}] | {len(results)} |"
        )
    return "\n".join(lines)
