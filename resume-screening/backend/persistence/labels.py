"""labels.json 人工真值（评测 SPEC）：record_key -> "pass"|"fail"。

manifest 保持 append-only；人工标注独立存放，评测时按 key 关联。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Union

VALID_LABELS = ("pass", "fail")


def load_labels(path: Union[Path, str]) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_label(path: Union[Path, str], record_key: str, label: Union[str, None]) -> dict:
    """upsert 一条标注；label 为 None 时删除该条。返回最新全量。"""
    p = Path(path)
    labels = load_labels(p)
    if label is None:
        labels.pop(record_key, None)
    else:
        if label not in VALID_LABELS:
            raise ValueError(f"非法标注: {label}")
        labels[record_key] = label
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    return labels
