"""End-to-end demo: harness + toy agent.

Starts the demo agent on 127.0.0.1:8001, drives the harness app in-process,
creates a suite with 4 tasks (2 capability, 2 regression, one flaky),
runs 3 trials per task, and prints the results table.

Usage:  .venv/bin/python demo/run_demo.py
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import uvicorn

from app.main import app as harness_app
from demo.demo_agent import app as agent_app

AGENT_BASE = "http://127.0.0.1:8001"


async def _init() -> None:
    from app import db
    from app.main import DB_PATH
    await db.init_db(DB_PATH)


def start_agent() -> None:
    t = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": agent_app, "host": "127.0.0.1", "port": 8001, "log_level": "warning"},
        daemon=True,
    )
    t.start()
    for _ in range(50):
        try:
            httpx.post(f"{AGENT_BASE}/reset", timeout=2, trust_env=False)
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("demo agent did not start")


TASKS = [
    ("add two numbers", "capability",
     {"op": "add", "a": 21, "b": 21},
     {"type": "exact", "field": "result", "expected": 42}),
    ("reverse a string", "capability",
     {"op": "reverse", "s": "stressed"},
     {"type": "exact", "field": "result", "expected": "desserts"}),
    ("add negatives (regression)", "regression",
     {"op": "add", "a": -3, "b": -4},
     {"type": "exact", "field": "result", "expected": -7}),
    ("flaky upstream (regression)", "regression",
     {"op": "flaky"},
     {"type": "exact", "field": "result", "expected": "ok"}),
]


def main() -> None:
    import asyncio

    start_agent()
    from pathlib import Path as _P
    _P("evalharness.db").unlink(missing_ok=True)
    asyncio.run(_init())
    transport = httpx.ASGITransport(app=harness_app)

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport, base_url="http://harness") as c:
            r = await c.post("/suites", json={
                "name": "demo-suite",
                "description": "Toy agent eval: math, strings, one flaky op",
                "agent_url": f"{AGENT_BASE}/run",
                "reset_url": f"{AGENT_BASE}/reset",
                "default_trials": 3,
            })
            r.raise_for_status()
            suite = r.json()
            print(f"suite: {suite['id']}  {suite['name']}")

            for name, kind, inp, grader in TASKS:
                r = await c.post(f"/suites/{suite['id']}/tasks", json={
                    "name": name, "input": inp, "grader": grader, "kind": kind,
                })
                r.raise_for_status()
                print(f"task:  {r.json()['name']} [{kind}]")

            r = await c.post("/trials", json={"suite_id": suite["id"]})
            r.raise_for_status()
            print(f"\nran {r.json()['count']} trials\n")

            r = await c.get(f"/suites/{suite['id']}/results", params={"k": 3})
            r.raise_for_status()
            res = r.json()

            print(f"{'task':38} {'kind':10} {'n':>3} {'pass%':>6} {'pass@3':>7} {'pass^3':>7}")
            print("-" * 78)
            for t in res["tasks"]:
                print(f"{t['name']:38} {t['kind']:10} {t['trials']:>3} "
                      f"{t['pass_rate']*100:>5.0f}% "
                      f"{(t['pass_at_k']*100 if t['pass_at_k'] is not None else float('nan')):>6.0f}% "
                      f"{(t['pass_caret_k']*100 if t['pass_caret_k'] is not None else float('nan')):>6.0f}%")
            print("-" * 78)
            o = res["overall"]
            print(f"{'OVERALL':38} {'':10} {o['trials']:>3} "
                  f"{o['pass_rate']*100:>5.0f}% {o['pass_at_k']*100:>6.0f}% {o['pass_caret_k']*100:>6.0f}%")
            for kind, m in res["by_kind"].items():
                print(f"  {kind:36} {m['trials']:>3} "
                      f"{m['pass_rate']*100:>5.0f}% {m['pass_at_k']*100:>6.0f}% {m['pass_caret_k']*100:>6.0f}%")

            # Show one transcript so the demo proves full observability.
            r = await c.post("/trials", json={"task_id": res["tasks"][0]["task_id"]})
            trial_id = r.json()["trial_ids"][0]
            r = await c.get(f"/trials/{trial_id}")
            tr = r.json()
            print(f"\nsample transcript ({trial_id}, {tr['status']}):")
            for ev in tr["transcript"]:
                print(f"  [{ev['type']}] {str(ev['payload'])[:110]}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
