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

## Architecture

```
                    +------------------+
                    |  evals/tasks.py  |   task definitions:
                    |  6 coding tasks  |   prompt + pytest suite
                    +--------+---------+
                             |
                    +--------v---------+
                    | harness/runner.py|   executes agent.act(),
                    |  run_task()      |   times it, captures the
                    |  run_suite()     |   trajectory, runs tests
                    +--------+---------+
                             |  RunResult per (agent, task, repeat)
                    +--------v---------+
                    | metrics/         |   solve rate, pass@k,
                    | aggregate.py     |   cost/solve, latency p50/p90,
                    | report.py        |   reliability, markdown tables
                    +--------+---------+
                             |
                    +--------v---------+
                    | ablations/       |   prompt variants x tasks x
                    | compare.py       |   repeats -> winner by metric
                    +------------------+
```

The `Agent` protocol is the only integration point. Everything else — tasks, metrics, ablations — is pure Python over `RunResult`.

## Concepts

**Task.** A prompt plus an executable pytest suite. Tests are the judge, not an LLM. A task is solved iff every test passes.

**RunResult.** One agent attempt: solved flag, pytest detail, wall-clock latency, token counts, dollar cost, full event trajectory, and any error. The runner never raises on agent failure; failures are data.

**Metrics.** Solve rate is the headline. `pass@k` answers "does it ever get there." Cost per solve answers "what does a win cost." Reliability answers "does it win every time." Latency p50/p90 answers "how long do users wait."

**Ablations.** Five built-in prompt variants (`baseline`, `cot`, `plan-then-act`, `read-only-first`, `self-critique`), each with a documented hypothesis about what it trades. `compare()` runs every variant over every task N times and names a winner per metric.

## Design principles

1. Tests decide. No LLM-as-judge anywhere in the loop.
2. Stdlib only. Zero dependencies; installs anywhere.
3. Deterministic. Scripted agents make CI green without API keys.
4. Cost is a first-class metric. Tokens have prices; the harness does the arithmetic.
5. Failures are data. The runner catches agent exceptions and records them.

## Roadmap

- Real agent adapters (bring-your-own-model via OpenAI/Anthropic APIs)
- Sandboxed execution per task (containers instead of temp dirs)
- Trajectory replay and step-level attribution
- More tasks: multi-file refactors, repo-scale bug fixes

## License

MIT.
