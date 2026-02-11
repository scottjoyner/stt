from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter


def build_router(conn: sqlite3.Connection) -> APIRouter:
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.post("/enqueue")
    async def enqueue(payload: dict) -> dict:
        task_id = payload.get("task_id") or f"task_{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "insert into tasks(task_id, turn_id, task_signature, priority, status, created_at) values (?, ?, ?, ?, 'queued', ?)",
            (task_id, payload["turn_id"], payload["task_signature"], payload.get("priority", "interactive"), now),
        )
        conn.commit()
        return {"task_id": task_id, "status": "queued"}

    @router.post("/{task_id}/cancel")
    async def cancel(task_id: str) -> dict:
        conn.execute("update tasks set status='cancelled' where task_id=?", (task_id,))
        conn.commit()
        return {"task_id": task_id, "status": "cancelled"}

    @router.get("")
    async def list_tasks(status: str | None = None) -> dict:
        if status:
            rows = conn.execute("select task_id, status from tasks where status=?", (status,)).fetchall()
        else:
            rows = conn.execute("select task_id, status from tasks").fetchall()
        return {"tasks": [{"task_id": r[0], "status": r[1]} for r in rows]}

    @router.get("/runs/{run_id}/trace")
    async def run_trace(run_id: str) -> dict:
        rows = conn.execute(
            "select step_id, agent_name, status, summary from agent_steps where run_id=? order by rowid", (run_id,)
        ).fetchall()
        return {"run_id": run_id, "steps": [dict(step_id=s[0], agent_name=s[1], status=s[2], summary=s[3]) for s in rows]}

    return router
