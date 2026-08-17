"""manifest.jsonl 事件流（事实表，append-only，SPEC §2.2）。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from .jsonl import append_jsonl, read_jsonl


def append_record(record: dict, path: Union[Path, str]) -> None:
    append_jsonl(record, path)


def load_records(path: Union[Path, str]) -> List[dict]:
    return read_jsonl(path)


def build_record(
    resume, jd_ref: str, verdict, doc_loader: str, ts: Optional[str] = None
) -> dict:
    """由 Verdict 组装一条 manifest 记录（score_snapshot 即 verdict.snapshot）。"""
    return {
        "resume": str(resume),
        "decision": "pass" if verdict.passed else "fail",
        "jd_ref": jd_ref,
        "score_snapshot": verdict.snapshot,
        "doc_loader": doc_loader,
        "time": ts or datetime.now(timezone.utc).isoformat(),
    }
