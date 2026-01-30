from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    created_at_ms INTEGER,
    config_json TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    created_at_ms INTEGER,
    sample_rate INTEGER,
    channels INTEGER
);

CREATE TABLE IF NOT EXISTS segments (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    start_ms INTEGER,
    end_ms INTEGER,
    audio_path TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    segment_id TEXT,
    event_type TEXT,
    t_ms INTEGER,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    segment_id TEXT,
    pass TEXT,
    text TEXT,
    created_at_ms INTEGER
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    session_id TEXT,
    key TEXT,
    value REAL
);
"""


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def insert_many(conn: sqlite3.Connection, query: str, rows: Iterable[tuple]) -> None:
    conn.executemany(query, rows)
    conn.commit()
