"""API integration tests. The agent is monkeypatched (no network); the
SQLite DB is a temp file per test module."""
import sys
from pathlib import Path

import pytest
import pytest_asyncio
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.main as main_mod
import app.runner as runner_mod
from app import db
from app.main import app

TEST_DB = "/tmp/evalharness_test.db"


@pytest_asyncio.fixture(autouse=True)
async def fresh_db(monkeypatch):
    Path(TEST_DB).unlink(missing_ok=True)
    monkeypatch.setattr(main_mod, "DB_PATH", TEST_DB)
    await db.init_db(TEST_DB)
    yield


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def fake_agent(agent_url: str, payload: dict):
    op = payload["input"].get("op")
    if op == "add":
        return {"output": "ok", "final_state": {"result": payload["input"]["a"] + payload["input"]["b"]},
                "tool_calls": [{"tool": "calc"}]}
    return {"output": "?", "final_state": {"result": None}, "tool_calls": []}


@pytest_asyncio.fixture(autouse=True)
async def fake_agent_patch(monkeypatch):
    async def _fake(url, payload):
        return await fake_agent(url, payload)
    monkeypatch.setattr(runner_mod, "call_agent", _fake)

    async def _noop(url):
        return None
    monkeypatch.setattr(runner_mod, "call_reset", _noop)


async def make_suite(client, **kw):
    body = {"name": "s", "agent_url": "http://agent/run", "default_trials": 2}
    body.update(kw)
    r = await client.post("/suites", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_full_flow(client):
    suite = await make_suite(client)
    sid = suite["id"]

    r = await client.post(f"/suites/{sid}/tasks", json={
        "name": "adds", "input": {"op": "add", "a": 2, "b": 3},
        "grader": {"type": "exact", "field": "result", "expected": 5},
        "kind": "capability",
    })
    assert r.status_code == 201
    task = r.json()

    r = await client.post("/trials", json={"task_id": task["id"]})
    assert r.status_code == 201
    tid = r.json()["trial_ids"][0]

    r = await client.get(f"/trials/{tid}")
    assert r.status_code == 200
    trial = r.json()
    assert trial["status"] == "passed"
    assert trial["passed"] is True
    assert trial["outcome"] == {"result": 5}
    assert any(e["type"] == "graded" for e in trial["transcript"])
    assert any(e["type"] == "agent_request" for e in trial["transcript"])

    r = await client.get(f"/suites/{sid}/results", params={"k": 1})
    res = r.json()
    assert res["overall"]["pass_rate"] == 1.0
    assert res["by_kind"]["capability"]["pass_rate"] == 1.0
    assert res["tasks"][0]["pass_at_k"] == 1.0


async def test_failed_trial_and_metrics(client):
    suite = await make_suite(client, default_trials=3)
    sid = suite["id"]
    r = await client.post(f"/suites/{sid}/tasks", json={
        "name": "wrong", "input": {"op": "add", "a": 1, "b": 1},
        "grader": {"type": "exact", "field": "result", "expected": 999},
        "kind": "regression",
    })
    task = r.json()

    r = await client.post("/trials", json={"suite_id": sid})
    assert r.json()["count"] == 3

    r = await client.get(f"/suites/{sid}/results", params={"k": 3})
    res = r.json()
    t = res["tasks"][0]
    assert t["passes"] == 0 and t["trials"] == 3
    assert t["pass_at_k"] == 0.0
    assert t["pass_caret_k"] == 0.0
    assert res["by_kind"]["regression"]["pass_rate"] == 0.0


async def test_suite_run_uses_task_trial_counts(client):
    suite = await make_suite(client, default_trials=2)
    sid = suite["id"]
    for i in range(2):
        await client.post(f"/suites/{sid}/tasks", json={
            "name": f"t{i}", "input": {"op": "add", "a": i, "b": i},
            "grader": {"type": "exact", "field": "result", "expected": 2 * i},
            "kind": "capability",
        })
    r = await client.post("/trials", json={"suite_id": sid})
    assert r.json()["count"] == 4  # 2 tasks x 2 trials


async def test_404s(client):
    assert (await client.get("/suites/nope")).status_code == 404
    assert (await client.get("/trials/nope")).status_code == 404
    r = await client.post("/trials", json={})
    assert r.status_code == 400


async def test_health(client):
    r = await client.get("/health")
    assert r.json()["ok"] is True
