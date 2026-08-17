"""统一 LLM 客户端：瞬时重试 → provider 降级 → failed 队列。

对上层只暴露 `complete(prompt) -> dict`；call_fn（真正发请求）与
validator（JSON 解析 + schema 校验）均可注入，便于测试与替换实现。
"""
from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from ..persistence.jsonl import append_jsonl, read_jsonl


class LLMError(Exception):
    pass


class TransientError(LLMError):
    """瞬时错误（429 / 5xx / 超时 / 网络），可重试。"""


class SchemaError(LLMError):
    """响应 JSON 解析或 schema 校验失败。"""


class FailedQueue:
    """failed 队列：内存或 JSONL 文件持久化。"""

    def __init__(self, path: Optional[Path] = None):
        self._path = Path(path) if path else None
        self._records: List[dict] = []

    def append(self, record: dict) -> None:
        if self._path is None:
            self._records.append(record)
            return
        append_jsonl(record, self._path)

    def records(self) -> List[dict]:
        if self._path is None:
            return list(self._records)
        return read_jsonl(self._path)


class LLMClient:
    """带重试/降级/failed 队列的 LLM 调用器。"""

    def __init__(
        self,
        chain: List[Tuple[str, str]],
        call_fn: Callable,
        validator: Callable[[str], dict],
        max_retries: int = 3,
        backoff_base: float = 1.0,
        jitter: float = 0.3,
        jitter_fn: Callable[[float, float], float] = random.uniform,
        sleep_fn: Callable[[float], None] = time.sleep,
        failed_queue: Optional[FailedQueue] = None,
    ):
        self._chain = chain
        self._call = call_fn
        self._validate = validator
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._jitter = jitter
        self._jitter_fn = jitter_fn
        self._sleep = sleep_fn
        self._queue = failed_queue or FailedQueue()

    def complete(self, prompt: str) -> dict:
        """按降级链逐个 provider 尝试，全部失败进 failed 队列并抛 LLMError。"""
        attempted: List[str] = []
        for provider, model in self._chain:
            result = self._try_provider(provider, model, prompt, attempted)
            if result is not None:
                return result
        record = {
            "prompt": prompt,
            "providers": attempted,
            "error": "all providers failed",
            "ts": time.time(),
        }
        self._queue.append(record)
        raise LLMError(f"全部模型调用失败: providers={attempted}")

    def _try_provider(
        self, provider: str, model: str, prompt: str, attempted: List[str]
    ) -> Optional[dict]:
        attempted.append(provider)
        for attempt in range(self._max_retries + 1):  # 初始 1 次 + max_retries 次重试
            try:
                raw = self._call(provider, model, prompt)
            except TransientError:
                if attempt < self._max_retries:
                    self._sleep(self._delay(attempt))
                continue
            try:
                return self._validate(raw)
            except SchemaError as err:
                # 一次纠正性重试（带错误信息）
                try:
                    raw2 = self._call(provider, model, prompt, feedback=str(err))
                    return self._validate(raw2)
                except SchemaError:
                    return None  # 校验仍失败 → 降级到下一 provider
                except TransientError:
                    continue  # 纠正性重试遇瞬时失败 → 进入下一轮尝试
        return None

    def _delay(self, attempt: int) -> float:
        return self._backoff_base * (2 ** attempt) + self._jitter_fn(0, self._jitter)
