"""筛选历史（v0.21）：sqlite 记录每次 batch 会话与逐条结果。

manifest.jsonl 仍是评测事实流；sqlite 只服务「历史记录」展示。
表：
  sessions(id, created_at, jd, mode, n_ok, n_fail)
  records(id, session_id, name, verdict, g, s, t, error, snapshot_json)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union


def _connect(db_path: Union[Path, str]) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Union[Path, str]) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                jd TEXT NOT NULL,
                mode TEXT NOT NULL,
                n_ok INTEGER NOT NULL,
                n_fail INTEGER NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                name TEXT NOT NULL,
                verdict TEXT,
                g INTEGER,
                s INTEGER,
                t INTEGER,
                error TEXT,
                snapshot_json TEXT
            )"""
        )


def add_session(
    db_path: Union[Path, str],
    jd: str,
    mode: str,
    results: List[dict],
    ts: Optional[str] = None,
) -> int:
    """写入一次 batch 会话与全部结果，返回 session_id。"""
    init_db(db_path)
    n_ok = sum(1 for r in results if "verdict" in r)
    ts = ts or datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO sessions (created_at, jd, mode, n_ok, n_fail) VALUES (?, ?, ?, ?, ?)",
            (ts, jd, mode, n_ok, len(results) - n_ok),
        )
        sid = cur.lastrowid
        for r in results:
            conn.execute(
                """INSERT INTO records (session_id, name, verdict, g, s, t, error, snapshot_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sid,
                    r.get("name", ""),
                    r.get("verdict"),
                    (r.get("totals") or {}).get("G"),
                    (r.get("totals") or {}).get("S"),
                    (r.get("totals") or {}).get("T"),
                    r.get("error"),
                    json.dumps(r.get("snapshot"), ensure_ascii=False) if "snapshot" in r else None,
                ),
            )
    return sid


def list_sessions(db_path: Union[Path, str], limit: int = 50) -> List[dict]:
    if not Path(db_path).exists():
        return []
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, created_at, jd, mode, n_ok, n_fail FROM sessions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_session(db_path: Union[Path, str], session_id: int) -> Optional[dict]:
    if not Path(db_path).exists():
        return None
    with _connect(db_path) as conn:
        sess = conn.execute(
            "SELECT id, created_at, jd, mode, n_ok, n_fail FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if sess is None:
            return None
        rows = conn.execute(
            "SELECT name, verdict, g, s, t, error, snapshot_json FROM records "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    records = []
    for r in rows:
        d = dict(r)
        d["snapshot"] = json.loads(d.pop("snapshot_json")) if d.get("snapshot_json") else None
        records.append(d)
    out = dict(sess)
    out["records"] = records
    return out
