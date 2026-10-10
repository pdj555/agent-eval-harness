# agent-eval-harness

Eval harness for coding agents. Runs agents on a task suite and measures what actually matters: solve rate, latency, cost, and reliability, with an ablation framework across prompts and tool-use strategies.

## The problem

Coding-agent progress is gated by evaluation, not model size. Teams ship prompt changes, tool-use policies, and context strategies without knowing which ones move solve rate or what they cost. This harness makes those tradeoffs legible: every run is timed, token-counted, and test-verified, so a prompt variant either earns its tokens or it does not.

## Quickstart

No API keys. The demo runs three scripted agents against six coding tasks.

```bash
pip install -e .
python examples/demo.py
```

The deep dive runs the full 12-task suite with statistical rigor, failure analysis, regression history, and cost modeling:

```bash
python examples/deep_dive.py
```

Bring your own agent by implementing the protocol:

```python
from harness import Agent, AgentResult

class MyAgent:
    name = "my-agent"

    def act(self, prompt: str, step_budget: int) -> AgentResult:
        # ... run your agent loop ...
        return AgentResult(
            solution=code,
            events=trajectory,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
```

Then run the suite:

```python
from harness import run_suite
from evals import ALL_TASKS
from metrics import aggregate
from metrics.report import render_suite_table

results = run_suite(MyAgent(), ALL_TASKS, repeats=3)
print(render_suite_table(results))
```

Compare prompt variants head to head:

```python
from ablations import compare, AblationConfig, VARIANTS, PromptVariant

def make_agent(variant: PromptVariant):
    return MyAgent(system_addendum=variant.system_addendum)

report = compare(make_agent, ALL_TASKS, AblationConfig(repeats=3))
print(report.markdown())
print("winner:", report.winner())
```

## Real models

Plug in OpenAI or Anthropic with one import. Optional deps: `pip install openai anthropic`.

```python
from harness.adapters import OpenAIAgent, AnthropicAgent
from harness import run_suite
from evals import EXTENDED_TASKS

agent = OpenAIAgent(model="gpt-4o-mini")  # reads OPENAI_API_KEY
results = run_suite(
    agent, EXTENDED_TASKS, repeats=3,
    price_in_per_1k=agent.price_in_per_1k,
    price_out_per_1k=agent.price_out_per_1k,
)
```

Per-model list prices ship in `harness.adapters.MODEL_PRICES`; override per instance if your contract differs.

## Example output

From `examples/demo.py` (real run, scripted agents):

```
# Eval report: steady (baseline)

| metric | value |
|---|---|
| tasks | 6 |
| runs | 12 |
| solve rate | 66.7% |
| pass@2 | 66.7% |
| mean cost / task | $42.0000 |
| cost per solve | $63.0000 |
| latency p50 | 0.44s |
| latency p90 | 0.46s |
| reliability | 66.7% |

# Ablation comparison

| variant | solve rate | cost/solve | p50 latency | reliability |
|---|---|---|---|---|
| baseline | 66.7% | $63.0000 | 0.43s | 66.7% |
| cot | 83.3% | $99.0000 | 0.51s | 83.3% |

Winner by solve rate: **cot**
```

Chain-of-thought buys 16.6 points of solve rate for a 57% cost increase. That is the kind of sentence this repo exists to produce. Full worked example: [examples/run_report.md](examples/run_report.md).

From `examples/deep_dive.py` (12 tasks, statistical rigor):

```
| variant | solve rate | 95% CI | n |
|---|---|---|---|
| steady | 100.0% | [90.4%, 100.0%] | 36 |
| buggy | 33.3% | [20.2%, 49.7%] | 36 |

discordant pairs: steady-right/buggy-wrong=24, steady-wrong/buggy-right=0;
chi2=22.04, p=0.0000
```

The gap is not noise. Full deep dive: [examples/deep_dive_report.md](examples/deep_dive_report.md).

## The task suites

**Base suite** (`evals.ALL_TASKS`, 6 tasks): fizzbuzz-plus, fix-binary-search, retry-backoff, lru-cache, csv-summary, balanced-parens. Small, sharp, discriminating.

**Hard suite** (`evals.HARD_TASKS`, 6 tasks): the tasks that separate real agents from demos.

| task | what it tests |
|---|---|
| fix-misleading-traceback | the stack trace blames `_chunks`; the fix belongs at the API boundary |
| consolidate-order-module | merge duplicated accumulation into one pass (structurally verified) |
| dependency-toposort | topological order with cycle and unknown-package errors |
| fix-race-condition | lost-update race; 8 threads x 500 increments must total 4000 |
| json-schema-validator | recursive spec implementation: types, required, enum, ranges |
| log-parser-aggregator | messy real-world data: malformed lines, query strings, error rates |

Every hard task ships with a verified oracle in `evals/oracles.py`; `tests/test_hard_tasks.py` proves each one is solvable and that broken solutions fail.

## Architecture

```
                    +------------------+
                    |  evals/          |   task definitions:
                    |  12 tasks        |   prompt + pytest suite + oracle
                    +--------+---------+
                             |
                    +--------v---------+
                    | harness/runner.py|   executes agent.act(),
                    |  run_task()      |   times it, captures the
                    |  run_suite()     |   trajectory, runs tests
                    +--------+---------+
                             |  RunResult per (agent, task, repeat)
              +--------------+--------------+
              |              |              |
     +--------v-----+ +-------v------+ +-----v--------+
     | metrics/     | | metrics/     | | harness/     |
     | aggregate.py | | stats.py     | | history.py   |
     | report.py    | | failures.py  | |  JSONL run   |
     | failures.py  | |  Wilson CI,  | |  log, trends |
     | costing.py   | |  McNemar     | |  deltas      |
     +--------------+ +--------------+ +--------------+
              |
     +--------v---------+
     | ablations/       |   prompt variants x tasks x
     | compare.py       |   repeats -> winner by metric
     +------------------+
```

The `Agent` protocol is the only integration point. Everything else — tasks, metrics, ablations — is pure Python over `RunResult`.

## Concepts

**Task.** A prompt plus an executable pytest suite. Tests are the judge, not an LLM. A task is solved iff every test passes.

**RunResult.** One agent attempt: solved flag, pytest detail, full pytest output, wall-clock latency, token counts, dollar cost, full event trajectory, and any error. The runner never raises on agent failure; failures are data.

**Metrics.** Solve rate is the headline. `pass@k` answers "does it ever get there." Cost per solve answers "what does a win cost." Reliability answers "does it win every time." Latency p50/p90 answers "how long do users wait."

**Statistical rigor** (`metrics/stats.py`). Wilson confidence intervals on every solve rate. McNemar's test on paired outcomes to decide if an ablation gain is real or noise. A sample-size calculator that answers "how many tasks before we trust a 10-point gain" before you pay for the runs.

**Failure analysis** (`metrics/failures.py`). Every failure classified: syntax_error, import_error, name_error, assertion_failure, timeout, agent_crash, no_output. The variant x failure-type cross-tab shows which prompt changes fix which failure modes.

**Regression history** (`harness/history.py`). Append-only JSONL log of scored runs. Trend tables and run-to-run deltas, so a team sees whether a prompt change helped or hurt across runs instead of trusting one afternoon's numbers.

**Cost modeling** (`metrics/costing.py`). Projected suite cost across price tiers, and a breakeven analysis: the eval pays for itself if it catches even a small share of bad deploys.

**Ablations.** Five built-in prompt variants (`baseline`, `cot`, `plan-then-act`, `read-only-first`, `self-critique`), each with a documented hypothesis about what it trades. `compare()` runs every variant over every task N times and names a winner per metric.

## Design principles

1. Tests decide. No LLM-as-judge anywhere in the loop.
2. Stdlib only in the core. Adapters are the only optional deps.
3. Deterministic. Scripted agents make CI green without API keys.
4. Cost is a first-class metric. Tokens have prices; the harness does the arithmetic.
5. Failures are data. The runner catches agent exceptions and records them.
6. Uncertainty is reported, not hidden. Every rate ships with an interval.

## Roadmap

- Sandboxed execution per task (containers instead of temp dirs)
- Trajectory replay and step-level attribution
- Multi-turn tool-use adapter (planner + executor loop)
- More tasks: repo-scale bug fixes, cross-file refactors

## License

MIT.
