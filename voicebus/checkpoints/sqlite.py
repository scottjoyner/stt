from __future__ import annotations

import sqlite3
from pathlib import Path


class SqliteCheckpointStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            create table if not exists checkpoints (
                consumer text primary key,
                cursor text not null,
                updated_at text not null
            )
            """
        )
        self.conn.commit()

    def save(self, consumer: str, cursor: str, updated_at: str) -> None:
        self.conn.execute(
            "insert into checkpoints(consumer, cursor, updated_at) values (?, ?, ?) "
            "on conflict(consumer) do update set cursor=excluded.cursor, updated_at=excluded.updated_at",
            (consumer, cursor, updated_at),
        )
        self.conn.commit()

    def load(self, consumer: str) -> str | None:
        row = self.conn.execute("select cursor from checkpoints where consumer=?", (consumer,)).fetchone()
        return row[0] if row else None
