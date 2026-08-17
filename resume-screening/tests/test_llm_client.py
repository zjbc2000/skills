"""统一 LLM 客户端：重试 / 降级 / JSON 校验 / failed 队列（T02）。"""
from __future__ import annotations

import pytest

from backend.registry.llm_client import (
    FailedQueue,
    LLMClient,
    LLMError,
    TransientError,
)


def make_client(chain, call, validator, **kw):
    return LLMClient(
        chain=chain,
        call_fn=call,
        validator=validator,
        max_retries=kw.get("max_retries", 3),
        backoff_base=kw.get("backoff_base", 1.0),
        jitter=0.0,
        jitter_fn=lambda a, b: 0.0,
        sleep_fn=kw.get("sleep_fn", lambda s: None),
        failed_queue=kw.get("failed_queue", FailedQueue()),
    )


def test_success_first_call(json_validator):
    calls = []

    def call(provider, model, prompt, feedback=None):
        calls.append(provider)
        return '{"ok": true}'

    client = make_client([("p1", "m1")], call, json_validator)
    assert client.complete("hi") == {"ok": True}
    assert calls == ["p1"]


def test_transient_retried_then_degrade(json_validator):
    calls = []

    def call(provider, model, prompt, feedback=None):
        calls.append(provider)
        if provider == "p1":
            raise TransientError("overload")
        return '{"ok": 1}'

    client = make_client([("p1", "m1"), ("p2", "m2")], call, json_validator, max_retries=3)
    assert client.complete("hi") == {"ok": 1}
    assert calls.count("p1") == 4  # 初始 1 次 + 3 次重试后降级
    assert calls.count("p2") == 1


def test_all_failed_goes_to_failed_queue(json_validator):
    def call(provider, model, prompt, feedback=None):
        raise TransientError("down")

    q = FailedQueue()
    client = make_client(
        [("p1", "m1"), ("p2", "m2")], call, json_validator, max_retries=2, failed_queue=q
    )
    with pytest.raises(LLMError):
        client.complete("hi")
    recs = q.records()
    assert len(recs) == 1
    assert recs[0]["prompt"] == "hi"
    assert recs[0]["providers"] == ["p1", "p2"]


def test_json_invalid_triggers_corrective_retry(json_validator):
    attempts = []

    def call(provider, model, prompt, feedback=None):
        attempts.append(feedback)
        if len(attempts) == 1:
            return "not-json"
        return '{"ok": true}'

    client = make_client([("p1", "m1")], call, json_validator)
    assert client.complete("hi") == {"ok": True}
    assert attempts[0] is None
    assert attempts[1] is not None  # 纠正性重试携带了错误信息


def test_json_invalid_twice_degrades(json_validator):
    def call(provider, model, prompt, feedback=None):
        return "not-json"

    client = make_client([("p1", "m1"), ("p2", "m2")], call, json_validator)
    with pytest.raises(LLMError):
        client.complete("hi")


def test_backoff_increasing(json_validator):
    delays = []

    def call(provider, model, prompt, feedback=None):
        raise TransientError("slow")

    client = make_client(
        [("p1", "m1")], call, json_validator, max_retries=3, sleep_fn=delays.append
    )
    with pytest.raises(LLMError):
        client.complete("hi")
    assert delays == [1.0, 2.0, 4.0]  # base * 2**attempt，jitter=0


def test_failed_queue_file_backed(tmp_path, json_validator):
    def call(provider, model, prompt, feedback=None):
        raise TransientError("down")

    path = tmp_path / "failed.jsonl"
    q = FailedQueue(path=path)
    client = make_client([("p1", "m1")], call, json_validator, max_retries=1, failed_queue=q)
    with pytest.raises(LLMError):
        client.complete("hi")
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 1
    q2 = FailedQueue(path=path)  # 重新打开仍能读到持久化记录
    assert q2.records()[0]["prompt"] == "hi"
