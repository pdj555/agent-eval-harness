# Eval Harness API

A FastAPI service that evaluates agents over HTTP. Point a suite at an agent endpoint; the service runs trials, grades each one, and stores the record in SQLite.

The vocabulary follows Anthropic's "Demystifying evals for AI agents." One rule: grade the outcome, the final environment state, never the path the agent took to get there.

## Quickstart

```bash
cd api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python demo/run_demo.py

.venv/bin/uvicorn app.main:app --port 8000
```

Interactive docs: http://localhost:8000/docs

## Vocabulary

| Term | Meaning |
|---|---|
| Task | Input plus success criteria (a grader spec) |
| Trial | One attempt at a task |
| Grader | Written in code (`exact`, `contains`, `regex`, `gte`, `lte`, `all_of`, `any_of`) |
| Transcript | Record of a trial: reset, request, response, outcome, grade. |
| Suite | A collection of tasks run against an agent endpoint. |

## Agent contract

```
POST {agent_url}
{"trial_id": "...", "task_id": "...", "input": {...}}

-> {"output": "...", "final_state": {...}, "tool_calls": [...]}
```

`final_state` is the outcome, and it is the only thing graded. If `final_state` is absent, the outcome is the response with `tool_calls` removed. `tool_calls` are recorded in the transcript, but they never affect the grade.

Optional `reset_url`: `POST {reset_url} {}` fires before every trial. The trial carries a unique `trial_id` the agent can key its own state on.

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

- pass rate: the fraction of trials passed.
- `pass@k`: the probability at least one of k attempts succeeds. Unbiased estimator `1 - C(n-c,k)/C(n,k)`, where n is the trial count and c the passes.
- `pass^k`: the probability all k attempts succeed. Unbiased estimator `C(c,k)/C(n,k)`.
- capability vs regression: capability tasks start low and should rise; regression tasks should stay near 100%, and a drop means something that worked has broken.

## What the demo shows

`demo/run_demo.py` starts an agent with four tasks and runs 3 trials each, 12 trials:

- Two capability tasks (math, string ops): 100%.
- One regression task (negative numbers): 100%.
- One flaky regression task (about 50% upstream failures): low `pass^3`.

## Design notes

- SQLite with aiosqlite.
- Agent calls bypass proxy env (`trust_env=False`).
- Graders are pure functions over the outcome. Adding a model grader means one new `GraderSpec` type and one branch in `evaluate()`.
