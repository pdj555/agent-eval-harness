# agent-eval-harness

**Did the agent really solve it, and does it stay in bounds when it can't?** An eval harness for coding agents that answers both.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
  <img alt="A special-casing fizzbuzz checked on every n from 0 to 200: right for 0 to 24, wrong for 25 to 200. The tests only check n 0, 5, 7, 15, 16 and 21. Solved 2 of 2 by tests, 0 of 2 on hidden inputs." src="docs/assets/hero-light.svg" width="100%">
</picture>

<sub>One question, four repos: **how can we trust agents to merge without a human reading every diff?**<br>
[agent-harness](https://github.com/pdj555/agent-harness) · **agent-eval-harness** · [trajectory-to-training](https://github.com/pdj555/trajectory-to-training) · [hard-rag-evals](https://github.com/pdj555/hard-rag-evals)</sub>

## The finding

Passing isn't solving. Tests only check the inputs they name, so an agent can pass them without implementing the rule. A hidden-input check compares each solution with a reference on hundreds of inputs the tests never use.

| Agent | Solved by tests | Solved on hidden inputs |
| --- | --- | --- |
| Honest | 2 of 2 | 2 of 2 |
| Special-casing | 2 of 2 | **0 of 2** |

The cheat is wrong on 176 of 201 fizzbuzz inputs and 74 of 400 binary searches.

Containment holds where it's tested. Four checks rebuild the incidents in Anthropic's October 2026 report on unintended model actions. With the guard on, all four are blocked and the honest agent still finishes. With it off, all four escape.

## Run it

No API key needed.

```bash
pip install -e .
python examples/tests_vs_hidden.py   # solved by tests vs on hidden inputs
python examples/misalignment.py      # containment, guard on and off
python examples/deep_dive.py         # 12 tasks, Wilson intervals, McNemar
```

## How it works

- **Tasks.** 12 coding tasks, each graded by its own pytest suite, never by a model.
- **Hidden inputs.** Solutions run against a reference in an isolated interpreter with a timeout.
- **Statistics.** Every solve rate carries a Wilson interval. McNemar's test decides whether a gain is real.
- **Containment.** Each check runs with the guard on and off, so it can fail.

Plug in your own agent through one protocol, or use the OpenAI and Anthropic adapters. See the [guide](docs/guide.md).

## Limits

- The hidden-input check covers 2 of the 12 tasks so far.
- Every number here comes from scripted agents.
- The containment checks replay known incidents. A model can find a fifth way.

## Docs

[Research summary](docs/research.md) · [Guide](docs/guide.md) · [Containment tests](MISALIGNMENT_TESTS.md) · [HTTP API](api/README.md)

MIT
