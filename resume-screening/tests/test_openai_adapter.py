"""OpenAI 兼容适配器：错误映射与成功路径（T04）。"""
from __future__ import annotations

import types

import httpx
import pytest
from openai import APIConnectionError, APIStatusError

import backend.registry.openai_adapter as adapter_mod
from backend.registry.llm_client import LLMError, TransientError


def _cfg():
    return types.SimpleNamespace(providers={"p": {"base_url": "https://x", "api_key_env": "KEY"}})


def _fake_client(behavior):
    class FakeCompletions:
        def create(self, **kw):
            if isinstance(behavior, Exception):
                raise behavior
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=behavior))]
            )

    class FakeChat:
        completions = FakeCompletions()

    client = types.SimpleNamespace()
    client.chat = FakeChat()
    return client


def _patch_openai(monkeypatch, behavior):
    monkeypatch.setenv("KEY", "k")
    monkeypatch.setattr(adapter_mod, "OpenAI", lambda base_url, api_key: _fake_client(behavior))


def test_missing_env_raises(monkeypatch):
    monkeypatch.delenv("KEY", raising=False)
    call = adapter_mod.make_call_fn(_cfg())
    with pytest.raises(LLMError):
        call("p", "m", "hi")


def test_success_returns_content(monkeypatch):
    _patch_openai(monkeypatch, "RESP")
    call = adapter_mod.make_call_fn(_cfg())
    assert call("p", "m", "hi") == "RESP"


def test_429_maps_to_transient(monkeypatch):
    req = httpx.Request("POST", "https://x")
    _patch_openai(monkeypatch, APIStatusError("rl", response=httpx.Response(429, request=req), body=None))
    call = adapter_mod.make_call_fn(_cfg())
    with pytest.raises(TransientError):
        call("p", "m", "hi")


def test_401_maps_to_non_transient(monkeypatch):
    req = httpx.Request("POST", "https://x")
    _patch_openai(monkeypatch, APIStatusError("auth", response=httpx.Response(401, request=req), body=None))
    call = adapter_mod.make_call_fn(_cfg())
    with pytest.raises(LLMError):
        call("p", "m", "hi")


def test_501_maps_to_transient(monkeypatch):
    req = httpx.Request("POST", "https://x")
    _patch_openai(monkeypatch, APIStatusError("impl", response=httpx.Response(501, request=req), body=None))
    call = adapter_mod.make_call_fn(_cfg())
    with pytest.raises(TransientError):
        call("p", "m", "hi")


def test_connection_error_maps_to_transient(monkeypatch):
    _patch_openai(monkeypatch, APIConnectionError(request=httpx.Request("POST", "https://x")))
    call = adapter_mod.make_call_fn(_cfg())
    with pytest.raises(TransientError):
        call("p", "m", "hi")
