from __future__ import annotations

import sqlite3


class DeadLetterQueue:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.execute(
            "create table if not exists dlq (task_id text, run_id text, reason text, ts text)"
        )
        self.conn.commit()

    def push(self, task_id: str, run_id: str, reason: str, ts: str) -> None:
        self.conn.execute("insert into dlq(task_id, run_id, reason, ts) values (?, ?, ?, ?)", (task_id, run_id, reason, ts))
        self.conn.commit()
