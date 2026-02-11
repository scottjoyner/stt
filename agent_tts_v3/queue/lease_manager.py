from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone


class LeaseManager:
    def __init__(self, conn: sqlite3.Connection, lease_seconds: int = 30) -> None:
        self.conn = conn
        self.lease_seconds = lease_seconds

    def acquire(self, run_id: str) -> str:
        exp = datetime.now(timezone.utc) + timedelta(seconds=self.lease_seconds)
        expiry = exp.isoformat()
        self.conn.execute("update task_runs set lease_expires_at=?, heartbeat_ts=? where run_id=?", (expiry, expiry, run_id))
        self.conn.commit()
        return expiry

    def heartbeat(self, run_id: str) -> str:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("update task_runs set heartbeat_ts=? where run_id=?", (now, run_id))
        self.conn.commit()
        return now
