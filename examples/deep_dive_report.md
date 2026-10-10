# agent-eval-harness: deep dive

Suite: 12 tasks (6 base + 6 hard).

## Solve rates with 95% Wilson intervals

| variant | solve rate | 95% CI | n |
|---|---|---|---|
| steady | 100.0% | [90.4%, 100.0%] | 36 |
| buggy | 33.3% | [20.2%, 49.7%] | 36 |

The buggy agent's solve rate is 33.3% [20.2%, 49.7%]: wide, but the interval already excludes the steady agent's 100%.

## Is the gap real? (McNemar's test, paired by task)

discordant pairs: steady-right/buggy-wrong=24, steady-wrong/buggy-right=0; chi2=22.04, p=0.0000
p < 0.05, so the gap is not noise. On 12 tasks x 3 repeats the harness can already separate these agents with confidence.

# Failure breakdown

| variant | syntax_error | import_error |
|---|---|---|
| buggy | 18 | 6 |
| steady | 0 | 0 |

# Failure analysis

- **syntax_error**: steady 0.0%, buggy 50.0%
- **import_error**: steady 0.0%, buggy 16.7%

## Regression history

# Trend: solve_rate

| time | agent | variant | solve_rate |
|---|---|---|---|
| 2026-10-10T17:37:32+00:00 | steady | steady | 100.0% |
| 2026-10-10T17:37:32+00:00 | buggy | buggy | 33.3% |

One JSONL line per scored run. Compare any two runs with `harness.render_delta` to see if a change helped or hurt.

# Projected eval cost

12 tasks x 5 repeats, 900 in / 1400 out tokens per run

| tier | per run | full suite |
|---|---|---|
| budget (small fast models) | $0.0010 | $0.06 |
| mid (capable general models) | $0.0163 | $0.98 |
| frontier (largest reasoning models) | $0.1185 | $7.11 |

# Breakeven analysis

- Eval cost per run: $18.75
- Expected incident loss per deploy: $1000.00
- Required catch rate: **1.9%**

The eval pays for itself even if it catches a small share of bad deploys.

# Eval report: steady (steady)

| metric | value |
|---|---|
| tasks | 12 |
| runs | 36 |
| solve rate | 100.0% |
| pass@3 | 100.0% |
| mean cost / task | $23.7000 |
| cost per solve | $23.7000 |
| latency p50 | 0.30s |
| latency p90 | 0.32s |
| reliability | 100.0% |
| mean steps | 4.0 |

# Eval report: buggy (buggy)

| metric | value |
|---|---|
| tasks | 12 |
| runs | 36 |
| solve rate | 33.3% |
| pass@3 | 33.3% |
| mean cost / task | $23.7000 |
| cost per solve | $71.1000 |
| latency p50 | 0.45s |
| latency p90 | 0.53s |
| reliability | 33.3% |
| mean steps | 4.0 |

