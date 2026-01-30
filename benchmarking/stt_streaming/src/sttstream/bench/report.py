from __future__ import annotations

import sqlite3
from pathlib import Path


def export_markdown_report(sqlite_path: Path, output_path: Path) -> None:
    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.execute(
        "SELECT key, AVG(value) FROM metrics GROUP BY key ORDER BY key"
    )
    rows = cur.fetchall()
    lines = ["# STT Benchmark Report", "", "| Metric | Value |", "| --- | --- |"]
    for key, value in rows:
        lines.append(f"| {key} | {value:.4f} |")
    output_path.write_text("\n".join(lines))
