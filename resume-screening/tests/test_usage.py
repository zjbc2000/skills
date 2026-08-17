"""LLM 用量监控（v0.23）：记录 / 聚合 / adapter 埋点。API 测试在 test_api.py。"""
from __future__ import annotations

import pytest

from backend.persistence import usage


@pytest.fixture(autouse=True)
def _tmp_usage(tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DATASETS", str(tmp_path))
    yield
    usage._connect().close()


def test_record_and_summary(tmp_path):
    usage.record("p", "m1", 100, 50, 120.0, True)
    usage.record("p", "m1", 200, 80, 300.0, False)
    usage.record("p", "m2", 10, 5, 40.0, True)

    s = usage.summary()
    assert s["n"] == 3 and s["n_ok"] == 2 and s["n_fail"] == 1
    assert s["success_rate"] == pytest.approx(2 / 3)
    assert s["prompt_tokens"] == 310 and s["completion_tokens"] == 135
    assert s["avg_duration_ms"] > 0

    rows = {f"{r['provider']}/{r['model']}": r for r in usage.by_model()}
    assert rows["p/m1"]["n"] == 2 and rows["p/m2"]["n"] == 1

    recent = usage.recent()
    assert len(recent) == 3
    assert recent[0]["ok"] == 1  # 最新一条（m2）在前


def test_clear_and_empty():
    assert usage.summary()["n"] == 0
    usage.record("p", "m", 1, 1, 1.0, True)
    assert usage.summary()["n"] == 1
    usage.clear()
    assert usage.summary()["n"] == 0


def test_openai_adapter_records_usage(monkeypatch):
    """成功调用写入 usage（含 token）；空响应记录失败。"""
    from backend.registry import openai_adapter

    usage_resp = type("U", (), {"prompt_tokens": 10, "completion_tokens": 20})()

    class FakeCompletions:
        def __init__(self, content, use_usage):
            self._c = content
            self._u = use_usage

        def create(self, **kwargs):
            content = type("M", (), {"content": self._c})()
            msg = type("Msg", (), {"message": content})()
            if self._u:
                return type("Resp", (), {"choices": [msg], "usage": usage_resp})()
            return type("Resp", (), {"choices": [msg]})()

    class FakeClient:
        def __init__(self, **kwargs):
            self._c = FakeCompletions("{}", True)
            self.chat = type("Chat", (), {"completions": self._c})()

    monkeypatch.setattr(openai_adapter, "OpenAI", FakeClient)
    monkeypatch.setenv("TEST_KEY", "k")
    from types import SimpleNamespace

    cfg = SimpleNamespace(providers={"p": {"api_key_env": "TEST_KEY", "base_url": "http://fake"}})
    fn = openai_adapter.make_call_fn(cfg)
    assert fn("p", "m", "hello") == "{}"

    s = usage.summary()
    assert s["n"] == 1 and s["n_ok"] == 1
    assert s["prompt_tokens"] == 10 and s["completion_tokens"] == 20

    # 空响应 -> 记录一次失败
    class EmptyClient:
        def __init__(self, **kwargs):
            self._c = FakeCompletions("", False)
            self.chat = type("Chat", (), {"completions": self._c})()

    monkeypatch.setattr(openai_adapter, "OpenAI", EmptyClient)
    from backend.registry.llm_client import LLMError

    with pytest.raises(LLMError):
        fn("p", "m", "hi")
    s2 = usage.summary()
    assert s2["n"] == 2 and s2["n_ok"] == 1 and s2["n_fail"] == 1
