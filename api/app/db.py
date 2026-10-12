"""Async SQLite storage. One connection per call, WAL mode, JSON columns
for the semi-structured bits (inputs, graders, transcripts, outcomes)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent / "evalharness.db"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _j(v: Any) -> str:
    return json.dumps(v, default=str)


def _u(s: str | None) -> Any:
    return json.loads(s) if s else None


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS suites (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    agent_url TEXT NOT NULL,
    reset_url TEXT,
    default_trials INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL REFERENCES suites(id),
    name TEXT NOT NULL,
    input_json TEXT NOT NULL DEFAULT '{}',
    grader_json TEXT NOT NULL DEFAULT '{}',
    kind TEXT NOT NULL DEFAULT 'capability',
    trials INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trials (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    suite_id TEXT NOT NULL REFERENCES suites(id),
    status TEXT NOT NULL DEFAULT 'pending',
    transcript_json TEXT NOT NULL DEFAULT '[]',
    outcome_json TEXT,
    passed INTEGER,
    grade_detail TEXT NOT NULL DEFAULT '',
    started_at TEXT,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_trials_task ON trials(task_id);
CREATE INDEX IF NOT EXISTS idx_trials_suite ON trials(suite_id);
CREATE INDEX IF NOT EXISTS idx_tasks_suite ON tasks(suite_id);
"""


async def init_db(path: str | Path = DB_PATH) -> None:
    async with aiosqlite.connect(path) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def insert_suite(path: str | Path, s: dict) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "INSERT INTO suites (id, name, description, agent_url, reset_url, default_trials, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (s["id"], s["name"], s["description"], s["agent_url"], s["reset_url"],
             s["default_trials"], s["created_at"]),
        )
        await db.commit()


async def get_suite(path: str | Path, suite_id: str) -> dict | None:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM suites WHERE id = ?", (suite_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def insert_task(path: str | Path, t: dict) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "INSERT INTO tasks (id, suite_id, name, input_json, grader_json, kind, trials, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (t["id"], t["suite_id"], t["name"], _j(t["input"]), _j(t["grader"]),
             t["kind"], t["trials"], t["created_at"]),
        )
        await db.commit()


async def get_task(path: str | Path, task_id: str) -> dict | None:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["input"] = _u(d.pop("input_json"))
            d["grader"] = _u(d.pop("grader_json"))
            return d


async def list_tasks(path: str | Path, suite_id: str) -> list[dict]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks WHERE suite_id = ? ORDER BY created_at", (suite_id,)
        ) as cur:
            rows = await cur.fetchall()
    out = []
    for row in rows:
        d = dict(row)
        d["input"] = _u(d.pop("input_json"))
        d["grader"] = _u(d.pop("grader_json"))
        out.append(d)
    return out


async def insert_trial(path: str | Path, t: dict) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "INSERT INTO trials (id, task_id, suite_id, status, transcript_json, outcome_json,"
            " passed, grade_detail, started_at, finished_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (t["id"], t["task_id"], t["suite_id"], t["status"], _j(t.get("transcript", [])),
             _j(t["outcome"]) if t.get("outcome") is not None else None,
             None if t.get("passed") is None else int(t["passed"]),
             t.get("grade_detail", ""), t.get("started_at"), t.get("finished_at")),
        )
        await db.commit()


async def update_trial(path: str | Path, trial_id: str, **fields: Any) -> None:
    cols = []
    vals: list[Any] = []
    for k, v in fields.items():
        if k in ("transcript", "outcome"):
            cols.append(f"{k}_json = ?")
            vals.append(_j(v) if v is not None else None)
        elif k == "passed":
            cols.append("passed = ?")
            vals.append(None if v is None else int(v))
        else:
            cols.append(f"{k} = ?")
            vals.append(v)
    vals.append(trial_id)
    async with aiosqlite.connect(path) as db:
        await db.execute(f"UPDATE trials SET {', '.join(cols)} WHERE id = ?", vals)
        await db.commit()


async def get_trial(path: str | Path, trial_id: str) -> dict | None:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM trials WHERE id = ?", (trial_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["transcript"] = _u(d.pop("transcript_json")) or []
            d["outcome"] = _u(d.pop("outcome_json"))
            d["passed"] = None if d["passed"] is None else bool(d["passed"])
            return d


async def list_trials_for_task(path: str | Path, task_id: str) -> list[dict]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, passed, status FROM trials WHERE task_id = ? ORDER BY started_at",
            (task_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
