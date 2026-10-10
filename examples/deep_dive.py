"""Deep dive: the full harness on the 12-task extended suite.

Runs with no API keys. Demonstrates everything beyond the basic demo:
  - the 6 hard tasks alongside the original 6
  - Wilson confidence intervals on solve rates
  - McNemar significance testing between variants
  - failure classification and the variant x failure cross-tab
  - regression history logging and trend rendering
  - cost projections and breakeven analysis

Writes examples/deep_dive_report.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo import CORRECT  # noqa: E402  (base-task oracle solutions)
from evals.oracles import ORACLES  # noqa: E402
from evals.registry import EXTENDED_TASKS  # noqa: E402
from harness import (  # noqa: E402
    ScriptedAgent,
    log_run,
    render_trend,
    run_suite,
)
from metrics.aggregate import aggregate  # noqa: E402
from metrics.costing import cost_table, render_breakeven  # noqa: E402
from metrics.failures import (  # noqa: E402
    fixes_report,
    render_breakdown_table,
)
from metrics.report import render_suite_table  # noqa: E402
from metrics.stats import mcnemar, render_ci_table, solve_rate_ci  # noqa: E402

ALL_SOLUTIONS = {**CORRECT, **ORACLES}
BROKEN = "def broken(:\n"


def _behavior(solutions: dict[str, str], in_tok: int, out_tok: int) -> dict:
    return {
        tid: (sol, in_tok, out_tok, 0.02) for tid, sol in solutions.items()
    }


def main() -> None:
    out: list[str] = ["# agent-eval-harness: deep dive", ""]
    out.append(f"Suite: {len(EXTENDED_TASKS)} tasks (6 base + 6 hard).")
    out.append("")

    steady = ScriptedAgent("steady", _behavior(ALL_SOLUTIONS, 900, 1400))
    buggy = ScriptedAgent(
        "buggy",
        {
            **{tid: (BROKEN, 900, 1400, 0.02) for tid in ORACLES},
            **{tid: ("x = 1\n", 900, 1400, 0.02) for tid in ("retry-backoff", "lru-cache")},
            **{tid: (sol, 900, 1400, 0.02) for tid, sol in CORRECT.items()
               if tid not in ("retry-backoff", "lru-cache")},
        },
    )

    steady_runs = run_suite(steady, EXTENDED_TASKS, variant="steady", repeats=3)
    buggy_runs = run_suite(buggy, EXTENDED_TASKS, variant="buggy", repeats=3)
    all_runs = steady_runs + buggy_runs

    # 1. Headline metrics with confidence intervals.
    out.append("## Solve rates with 95% Wilson intervals")
    out.append("")
    out.append(render_ci_table({"steady": steady_runs, "buggy": buggy_runs}))
    out.append("")
    rate, lo, hi = solve_rate_ci(buggy_runs)
    out.append(
        f"The buggy agent's solve rate is {rate:.1%} [{lo:.1%}, {hi:.1%}]: "
        "wide, but the interval already excludes the steady agent's 100%."
    )
    out.append("")

    # 2. Is the gap real? McNemar on paired outcomes.
    out.append("## Is the gap real? (McNemar's test, paired by task)")
    out.append("")
    mc = mcnemar(steady_runs, buggy_runs)
    out.append(
        f"discordant pairs: steady-right/buggy-wrong={mc['b']}, "
        f"steady-wrong/buggy-right={mc['c']}; "
        f"chi2={mc['chi2']:.2f}, p={mc['p_value']:.4f}"
    )
    out.append(
        "p < 0.05, so the gap is not noise. On 12 tasks x 3 repeats the "
        "harness can already separate these agents with confidence."
    )
    out.append("")

    # 3. Failure analysis.
    out.append(render_breakdown_table(all_runs))
    out.append("")
    out.append(fixes_report(all_runs))
    out.append("")

    # 4. Regression history.
    hist_path = Path("/tmp/agent-eval-harness-history.jsonl")
    if hist_path.exists():
        hist_path.unlink()
    for agent_runs, label in ((steady_runs, "steady"), (buggy_runs, "buggy")):
        log_run(
            hist_path,
            agent_name=label,
            variant=label,
            metrics=aggregate(agent_runs),
        )
    out.append("## Regression history")
    out.append("")
    out.append(render_trend(hist_path))
    out.append("")
    out.append("One JSONL line per scored run. Compare any two runs with "
               "`harness.render_delta` to see if a change helped or hurt.")
    out.append("")

    # 5. Cost projections.
    out.append(cost_table(
        n_tasks=len(EXTENDED_TASKS), repeats=5,
        mean_in_tokens=900, mean_out_tokens=1400,
    ))
    out.append("")
    out.append(render_breakeven(
        eval_cost_usd=18.75, incident_cost_usd=20000.0, incident_probability=0.05,
    ))
    out.append("")

    # 6. Per-agent suite tables.
    for label, runs in (("steady", steady_runs), ("buggy", buggy_runs)):
        out.append(render_suite_table(runs))
        out.append("")

    text = "\n".join(out)
    print(text)
    Path(__file__).with_name("deep_dive_report.md").write_text(text + "\n")
    print("wrote examples/deep_dive_report.md")


if __name__ == "__main__":
    main()
