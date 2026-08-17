"""JSONL 追加/读取（FailedQueue 与 manifest 共享，DRY）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Union


def append_jsonl(record: dict, path: Union[Path, str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Union[Path, str]) -> List[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
