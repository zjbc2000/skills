"""真实 LLM 适配（T11）：调用带超时、异常映射、空响应兜底（不联网）。"""
from __future__ import annotations

import pytest

from backend.registry import openai_adapter


def _cfg(provider="p"):
    from types import SimpleNamespace

    return SimpleNamespace(
        providers={provider: {"api_key_env": "TEST_KEY", "base_url": "http://fake"}}
    )


@pytest.fixture(autouse=True)
def _isolate_usage(tmp_path, monkeypatch):
    """usage 记录写入 tmp，不污染真实 datasets。"""
    monkeypatch.setenv("RESUME_DATASETS", str(tmp_path))
    yield


def test_call_fn_sets_request_timeout(monkeypatch):
    """SDK 默认 600s 会导致任务线程长时间阻塞——必须显式传 timeout。"""
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            content = type("M", (), {"content": "{}"})()
            msg = type("Msg", (), {"message": content})()
            return type("Resp", (), {"choices": [msg]})()

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.chat = type(
                "Chat", (), {"completions": FakeCompletions()}
            )()

    monkeypatch.setattr(openai_adapter, "OpenAI", FakeClient)
    monkeypatch.setenv("TEST_KEY", "k")

    fn = openai_adapter.make_call_fn(_cfg())
    assert fn("p", "m", "hello") == "{}"
    assert captured["timeout"] == openai_adapter.REQUEST_TIMEOUT_SECONDS
    assert captured["base_url"] == "http://fake"
    assert captured["api_key"] == "k"


def test_call_fn_uses_custom_system_prompt(monkeypatch):
    """JD 抽取必须用 JD 提示词而非评分提示词，否则模型按评分格式输出、
    校验永远失败、触发全链重试（表现为任务长时间挂起）。"""
    from backend.scoring.prompts import JD_EXTRACT_SYSTEM_PROMPT

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            content = type("M", (), {"content": "{}"})()
            msg = type("Msg", (), {"message": content})()
            return type("Resp", (), {"choices": [msg]})()

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(openai_adapter, "OpenAI", FakeClient)
    monkeypatch.setenv("TEST_KEY", "k")

    fn = openai_adapter.make_call_fn(_cfg(), system_prompt=JD_EXTRACT_SYSTEM_PROMPT)
    fn("p", "m", "jd raw")
    assert captured["messages"][0]["content"] == JD_EXTRACT_SYSTEM_PROMPT


def test_call_fn_missing_api_key_raises_llm_error(monkeypatch):
    from backend.registry.llm_client import LLMError

    monkeypatch.delenv("TEST_KEY", raising=False)
    fn = openai_adapter.make_call_fn(_cfg())
    with pytest.raises(LLMError):
        fn("p", "m", "hi")


def test_call_fn_empty_content_raises_llm_error(monkeypatch):
    from backend.registry.llm_client import LLMError

    class FakeCompletions:
        def create(self, **kwargs):
            return type("Resp", (), {"choices": []})()

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = type(
                "Chat", (), {"completions": FakeCompletions()}
            )()

    monkeypatch.setattr(openai_adapter, "OpenAI", FakeClient)
    monkeypatch.setenv("TEST_KEY", "k")
    fn = openai_adapter.make_call_fn(_cfg())
    with pytest.raises(LLMError):
        fn("p", "m", "hi")
