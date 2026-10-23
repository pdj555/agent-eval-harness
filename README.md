# agent-eval-harness

Passing is not solving. An agent that hardcodes the tested answers passes 2 of 2 tasks by the tests and 0 of 2 on inputs the tests never use.

This repo checks two things: whether the agent actually solved the task, and whether it stays within the rules when it cannot.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
  <img alt="A fizzbuzz solution that hardcodes the tested answers, checked on every n from 0 to 200: right for 0 to 24, wrong for 25 to 200. The tests only check n 0, 5, 7, 15, 16 and 21. Solved 2 of 2 by tests, 0 of 2 on hidden inputs." src="docs/assets/hero-light.svg" width="100%">
</picture>

<sub>Related repos:
[agent-harness](https://github.com/pdj555/agent-harness) · **agent-eval-harness** · [trajectory-to-training](https://github.com/pdj555/trajectory-to-training) · [hard-rag-evals](https://github.com/pdj555/hard-rag-evals)</sub>

## The findings

Tests only check the inputs they name. An agent can pass every test in front of it and still not implement the rule. So each solution also runs against a reference on hundreds of inputs the tests never use, and the two scores stand side by side.

| Agent | Solved by tests | Solved on hidden inputs |
| --- | --- | --- |
| Honest | 2 of 2 | 2 of 2 |
| Special-casing | 2 of 2 | **0 of 2** |

The cheat is wrong on 176 of 201 fizzbuzz inputs and 74 of 400 binary searches.

Four checks replay incidents from Anthropic's October 2026 report on unintended model actions. With the guard on, all four are blocked and the honest agent still finishes. With the guard off, all four escape.

## Run it

No API key needed.

```bash
pip install -e .
python examples/tests_vs_hidden.py   # solved by tests vs on hidden inputs
python examples/misalignment.py      # containment, guard on and off
python examples/deep_dive.py         # 12 tasks, Wilson intervals, McNemar
```

## How it works

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/flow-animated-dark.svg">
  <img alt="A solution that passes the task tests is compared with a reference on hidden inputs. If they agree, it is solved. If they disagree, the solution is special-cased: it passes 2 of 2 tasks and is still wrong on 176 of 201 and 74 of 400 hidden inputs." src="docs/assets/flow-animated-light.svg" width="100%">
</picture>

- 12 coding tasks, each graded by its own pytest suite, never by a model.
- Each solution runs against a reference in an isolated interpreter with a timeout.
- Every solve rate carries a Wilson interval, the range that shows how far the number can be trusted. McNemar's test decides whether a gain is real.
- Each check runs with the guard on and off, so it can fail.

Plug in your own agent through one protocol, or use the OpenAI and Anthropic adapters. See the [guide](docs/guide.md).

## Limits

- The check on hidden inputs covers 2 of the 12 tasks so far.
- Every number here comes from scripted agents.
- The containment checks replay known incidents, the ones already on record. A model can find a fifth way.

## Docs

[Research summary](docs/research.md) · [Guide](docs/guide.md) · [Containment tests](MISALIGNMENT_TESTS.md) · [HTTP API](api/README.md)

MIT
