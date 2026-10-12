"""Toy agent for the eval harness demo.

Contract:
  POST /run   {trial_id, task_id, input} -> {output, final_state, tool_calls}
  POST /reset {} -> clears per-trial state (isolation hook)

Ops:
  add      -> final_state {result: a + b}
  reverse  -> final_state {result: reversed string}
  flaky    -> final_state {result} but fails ~50% of trials (seeded by trial_id,
              so it is deterministic per trial yet mixed across trials)
"""
from __future__ import annotations

import hashlib
import random

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any

app = FastAPI(title="Demo agent")

_state: dict[str, Any] = {}


class RunRequest(BaseModel):
    trial_id: str
    task_id: str
    input: dict[str, Any]


@app.post("/reset")
async def reset():
    _state.clear()
    return {"ok": True}


@app.post("/run")
async def run(req: RunRequest):
    op = req.input.get("op")
    tool_calls: list[dict] = []
    final_state: dict[str, Any] = {}

    if op == "add":
        a, b = req.input["a"], req.input["b"]
        tool_calls.append({"tool": "calculator", "args": {"a": a, "b": b}})
        final_state = {"result": a + b}
        output = f"{a} + {b} = {a + b}"

    elif op == "reverse":
        s = req.input["s"]
        tool_calls.append({"tool": "string_op", "args": {"s": s}})
        final_state = {"result": s[::-1]}
        output = s[::-1]

    elif op == "flaky":
        # Deterministic per trial_id: ~half the trials "fail" at the tool layer.
        seed = int(hashlib.sha256(req.trial_id.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        tool_calls.append({"tool": "unreliable_api", "args": {}})
        if rng.random() < 0.5:
            final_state = {"result": None, "error": "upstream timeout"}
            output = "failed: upstream timeout"
        else:
            final_state = {"result": "ok"}
            output = "ok"

    else:
        final_state = {"error": f"unknown op: {op}"}
        output = f"unknown op: {op}"

    _state[req.trial_id] = final_state
    return {"output": output, "final_state": final_state, "tool_calls": tool_calls}
