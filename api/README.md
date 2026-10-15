# Eval Harness API

Eval-driven agent engineering, as a service. Built on two ideas from the
frontier labs:

- **Anthropic** ("Demystifying evals for AI agents"): evals are the product.
  Task, trial, grader, transcript, outcome, suite. Grade the *outcome*
  (final environment state), never the *path* (tool-call sequence).
  Capability evals vs regression evals. `pass@k` vs `pass^k`.
- **OpenAI** (Agents SDK, harness engineering): invest in the harness, not
  the prompt. Isolate every run, observe everything, enforce mechanically.

## Quickstart

```bash
cd eval-harness-api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# run the tests
.venv/bin/python -m pytest tests/ -q

# run the end-to-end demo (starts a toy agent, 12 trials, prints results)
.venv/bin/python demo/run_demo.py

# serve the API
.venv/bin/uvicorn app.main:app --port 8000
```

Interactive docs: http://localhost:8000/docs

18/18 tests pass. `python -m pytest tests/ -q` from `api/`.

## The eval vocabulary

| Term | Meaning |
|---|---|
| Task | Input + success criteria (a grader spec) |
| Trial | One attempt at a task. Run several per task. |
| Grader | Scoring logic. Code-based here (`exact`, `contains`, `regex`, `gte`, `lte`, `all_of`, `any_of`); model-based and human graders plug in later. |
| Transcript | Full record of a trial: reset, request, response, outcome, grade. |
| Outcome | The final environment state. **Not** what the agent claimed. |
| Suite | A collection of tasks run against one agent endpoint. |

## Agent contract

Point a suite at any HTTP agent:

```
POST {agent_url}
{"trial_id": "...", "task_id": "...", "input": {...}}

-> {"output": "...", "final_state": {...}, "tool_calls": [...]}
```

`final_state` is the outcome and is the **only** thing graded. `tool_calls`
are recorded in the transcript for observability but never affect the grade.
That is the whole "grade outcomes, not paths" rule, enforced in code.

Optional `reset_url`: `POST {reset_url} {}` fires before every trial so each
trial starts from a clean environment. The trial also carries a unique
`trial_id` the agent can key its own state on.

## API

```
POST /suites                    {name, description, agent_url, reset_url?, default_trials}
POST /suites/{id}/tasks         {name, input, grader, kind: capability|regression, trials?}
POST /trials                    {task_id}            -> one trial
POST /trials                    {suite_id}           -> every task x its trial count
GET  /trials/{id}               transcript + outcome + grade
GET  /suites/{id}/results?k=3   pass rates, pass@k, pass^k, kind split
GET  /health
```

## Metrics

- **pass rate** - fraction of trials passed. Simple, gameable, reported anyway.
- **pass@k** - probability at least one of k attempts succeeds. Unbiased
  estimator `1 - C(n-c,k)/C(n,k)`. Use it when one success is enough.
- **pass^k** - probability all k attempts succeed. Unbiased estimator
  `C(c,k)/C(n,k)`. Use it for customer-facing agents where consistency matters.
- **capability vs regression** - capability evals start low (a hill to climb);
  regression evals should sit near 100% (a backsliding alarm). A capability
  eval that starts passing graduates into the regression suite.

## What the demo proves

`demo/run_demo.py` spins up a toy agent with four tasks and runs 3 trials
each:

- Two capability tasks (math, string ops): 100% across the board.
- One regression task (negative numbers): 100%. The harness holds.
- One flaky regression task (~50% upstream failures): low `pass^3`.
  The suite catches exactly the kind of inconsistency that ships as a
  2 AM page.

Every trial stores a full transcript: reset, request, response with tool
calls, extracted outcome, grade with reasoning.

## Design notes

- SQLite + aiosqlite. Zero ops burden; swap the `db.py` module for Postgres
  when a suite outgrows a file.
- Agent calls bypass proxy env (`trust_env=False`): agent endpoints are
  usually internal.
- Graders are pure functions over the outcome. Adding a model-based grader
  means one new `GraderSpec` type and one branch in `evaluate()`; the
  pipeline does not change.

## Roadmap

- Model-based graders (rubric, pairwise, reference) with human calibration
- `pass@k` curves over k, per-task history, suite diffing across agent versions
- Postgres backend, auth, multi-tenant suites
