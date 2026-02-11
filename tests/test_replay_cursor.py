from __future__ import annotations

from stt_service.events.replay import EventReplayStore


def test_replay_from_cursor(tmp_path):
    store = EventReplayStore(tmp_path)
    p = tmp_path / "a.jsonl"
    p.write_text('{"event_id":"e1"}\n{"event_id":"e2"}\n', encoding="utf-8")
    store.add_index("e1", p, 1, "now")
    store.add_index("e2", p, 2, "now")

    items = store.from_cursor(from_line=2)
    assert items[0]["event_id"] == "e2"
