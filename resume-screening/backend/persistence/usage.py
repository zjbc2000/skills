"""LLM 用量监控（v0.23）：sqlite 记录每次真实调用的 token / 耗时 / 成败。

路径懒读 `RESUME_DATASETS/usage.db`（测试用 monkeypatch env 隔离，datasets/* 已被 gitignore）。
openai_adapter 每次真实 HTTP 调用写一条；聚合供 dashboard 面板。
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def db_path() -> Path:
    repo = Path(__file__).resolve().parent.parent.parent.parent  # …/backend/persistence → repo
    return Path(os.environ.get("RESUME_DATASETS", str(repo / "datasets"))) / "usage.db"


def _connect() -> sqlite3.Connection:
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                duration_ms REAL NOT NULL,
                ok INTEGER NOT NULL
            )"""
        )


def record(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
    ok: bool,
) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO usage (ts, provider, model, prompt_tokens, completion_tokens, duration_ms, ok)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                provider,
                model,
                int(prompt_tokens),
                int(completion_tokens),
                duration_ms,
                1 if ok else 0,
            ),
        )


def summary() -> dict:
    """总览：次数 / 成功失败 / 成功率 / token / 平均耗时。"""
    if not db_path().exists():
        return {"n": 0, "n_ok": 0, "n_fail": 0, "success_rate": 0.0,
                "prompt_tokens": 0, "completion_tokens": 0, "avg_duration_ms": 0.0}
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(ok),0) n_ok, "
            "COALESCE(SUM(prompt_tokens),0) pt, COALESCE(SUM(completion_tokens),0) ct, "
            "COALESCE(AVG(duration_ms),0) avg_ms FROM usage"
        ).fetchone()
    n = row["n"]
    return {
        "n": n,
        "n_ok": row["n_ok"],
        "n_fail": n - row["n_ok"],
        "success_rate": row["n_ok"] / n if n else 0.0,
        "prompt_tokens": row["pt"],
        "completion_tokens": row["ct"],
        "avg_duration_ms": round(row["avg_ms"], 1),
    }


def by_model() -> list:
    """按 provider.model 分组明细。"""
    if not db_path().exists():
        return []
    with _connect() as conn:
        rows = conn.execute(
            "SELECT provider, model, COUNT(*) n, SUM(ok) n_ok, "
            "SUM(prompt_tokens) pt, SUM(completion_tokens) ct, AVG(duration_ms) avg_ms "
            "FROM usage GROUP BY provider, model ORDER BY n DESC"
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "provider": r["provider"],
            "model": r["model"],
            "n": r["n"],
            "n_ok": r["n_ok"],
            "n_fail": r["n"] - r["n_ok"],
            "success_rate": r["n_ok"] / r["n"] if r["n"] else 0.0,
            "prompt_tokens": r["pt"],
            "completion_tokens": r["ct"],
            "avg_duration_ms": round(r["avg_ms"], 1),
        })
    return out


def recent(limit: int = 15) -> list:
    if not db_path().exists():
        return []
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ts, provider, model, prompt_tokens, completion_tokens, duration_ms, ok "
            "FROM usage ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def clear() -> None:
    """清空用量（dashboard 提供重置按钮）。"""
    if not db_path().exists():
        return
    with _connect() as conn:
        conn.execute("DELETE FROM usage")
