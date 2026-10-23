# Eval Harness API

A FastAPI service that evaluates agents over HTTP. Point a suite at an agent endpoint; the service runs trials, grades each one, and stores the full record in SQLite.

The vocabulary (task, trial, grader, transcript, outcome, capability and regression suites, `pass@k` and `pass^k`) follows Anthropic's "Demystifying evals for AI agents." One rule runs through the service, also from that post: grade the outcome, the final environment state, never the path the agent took to get there.

## Quickstart

From the repo root:

```bash
cd api
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

## The vocabulary

| Term | Meaning |
|---|---|
| Task | Input plus success criteria (a grader spec) |
| Trial | One attempt at a task. Run several per task. |
| Grader | Scoring logic. Written in code here (`exact`, `contains`, `regex`, `gte`, `lte`, `all_of`, `any_of`); model and human graders plug in later. |
| Transcript | Full record of a trial: reset, request, response, outcome, grade. |
| Outcome | The final environment state. Not what the agent claimed. |
| Suite | A collection of tasks run against one agent endpoint. |

## Agent contract

Point a suite at any HTTP agent:

```
POST {agent_url}
{"trial_id": "...", "task_id": "...", "input": {...}}

-> {"output": "...", "final_state": {...}, "tool_calls": [...]}
```

`final_state` is the outcome, and it is the only thing graded. If `final_state` is absent, the outcome is the response with `tool_calls` removed. `tool_calls` are recorded in the transcript so the run can be inspected later, but they never affect the grade.

Optional `reset_url`: `POST {reset_url} {}` fires before every trial so each trial starts from a clean environment. The trial also carries a unique `trial_id` the agent can key its own state on.

## API

```
POST /suites                    {name, description, agent_url, reset_url?, default_trials}
GET  /suites/{id}               Read a suite
POST /suites/{id}/tasks         {name, input, grader, kind: capability|regression, trials?}
GET  /suites/{id}/tasks         List a suite's tasks
POST /trials                    {task_id}            -> one trial
POST /trials                    {suite_id}           -> every task x its trial count
GET  /trials/{id}               transcript + outcome + grade
GET  /suites/{id}/results?k=3   pass rates, pass@k, pass^k, kind split
GET  /health                    service health and version
```

## Metrics

- pass rate: the fraction of trials passed. Easy to game on its own, so it is reported with the two scores below.
- `pass@k`: the probability at least one of k attempts succeeds. Unbiased estimator `1 - C(n-c,k)/C(n,k)`, where n is the trial count and c the passes. Use it when one success is enough.
- `pass^k`: the probability all k attempts succeed. Unbiased estimator `C(c,k)/C(n,k)`. Use it for agents that face users, where consistency matters.
- capability vs regression: capability tasks start low and should rise as the agent improves; regression tasks should stay near 100%, and a drop means something that worked has broken.

## What the demo shows

`demo/run_demo.py` starts a toy agent with four tasks and runs 3 trials each, 12 trials in total:

- Two capability tasks (math, string ops): 100% across the board.
- One regression task (negative numbers): 100%.
- One flaky regression task (about 50% upstream failures): low `pass^3`.

Every trial stores a full transcript: reset, request, response with tool calls, extracted outcome, grade with reasoning.

## Design notes

- SQLite with aiosqlite. Swap the `db.py` module for Postgres when a suite outgrows a file.
- Agent calls bypass proxy env (`trust_env=False`): agent endpoints are usually internal.
- Graders are pure functions over the outcome. Adding a model grader means one new `GraderSpec` type and one branch in `evaluate()`; the pipeline does not change.

## Roadmap

- Model graders (rubric, pairwise, reference) with human calibration
- `pass@k` curves over k, history per task, suite diffing across agent versions
- Postgres backend, auth, suites for more than one tenant
