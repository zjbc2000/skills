"""layout-parsing 远程解析（T05）。"""
from __future__ import annotations

import base64
import json

import pytest
import requests

import backend.doc_loader.layout_parsing as mod
from backend.doc_loader.base import LoaderError


def _file(tmp_path, name="x.pdf", content=b"dummy"):
    p = tmp_path / name
    p.write_bytes(content)
    return p


def _set_env(monkeypatch):
    monkeypatch.setenv("LAYOUT_PARSING_URL", "https://x/layout-parsing")
    monkeypatch.setenv("LAYOUT_PARSING_TOKEN", "tok")


def _ok_body(text="# Markdown\n内容"):
    return {"errorCode": 0, "errorMsg": "Success",
            "result": {"layoutParsingResults": [{"markdown": {"text": text}}]}}


def test_success_sends_base64_and_returns_markdown(monkeypatch, tmp_path, fake_response):
    _set_env(monkeypatch)
    seen = {}
    pdf = _file(tmp_path, content=b"pdf-bytes")

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update({"url": url, "auth": headers["Authorization"], "file": json["file"]})
        return fake_response(200, json_body=_ok_body())

    monkeypatch.setattr(mod.requests, "post", fake_post)
    assert "# Markdown" in mod.extract_text(pdf)
    assert seen["url"] == "https://x/layout-parsing"
    assert seen["auth"] == "Bearer tok"
    assert seen["file"] == base64.b64encode(b"pdf-bytes").decode()


def test_multipage_markdown_concatenated(monkeypatch, tmp_path, fake_response):
    _set_env(monkeypatch)
    body = {"errorCode": 0, "result": {"layoutParsingResults": [
        {"markdown": {"text": "第一页"}}, {"markdown": {"text": "第二页"}},
    ]}}
    monkeypatch.setattr(mod.requests, "post", lambda *a, **k: fake_response(200, json_body=body))
    assert mod.extract_text(_file(tmp_path)) == "第一页\n第二页"


def test_missing_env_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("LAYOUT_PARSING_URL", raising=False)
    monkeypatch.delenv("LAYOUT_PARSING_TOKEN", raising=False)
    with pytest.raises(LoaderError):
        mod.extract_text(_file(tmp_path))


def test_missing_file_raises(monkeypatch, tmp_path):
    _set_env(monkeypatch)
    with pytest.raises(LoaderError):
        mod.extract_text(tmp_path / "nope.pdf")


def test_non_200_raises(monkeypatch, tmp_path, fake_response):
    _set_env(monkeypatch)
    monkeypatch.setattr(mod.requests, "post", lambda *a, **k: fake_response(500, "boom"))
    with pytest.raises(LoaderError):
        mod.extract_text(_file(tmp_path))


def test_nonzero_error_code_raises(monkeypatch, tmp_path, fake_response):
    _set_env(monkeypatch)
    body = {"errorCode": 5001, "errorMsg": "内部错误"}
    monkeypatch.setattr(mod.requests, "post", lambda *a, **k: fake_response(200, json_body=body))
    with pytest.raises(LoaderError):
        mod.extract_text(_file(tmp_path))


def test_empty_text_raises(monkeypatch, tmp_path, fake_response):
    _set_env(monkeypatch)
    monkeypatch.setattr(mod.requests, "post", lambda *a, **k: fake_response(200, json_body=_ok_body("   ")))
    with pytest.raises(LoaderError):
        mod.extract_text(_file(tmp_path))


def test_invalid_json_response_raises(monkeypatch, tmp_path, fake_response):
    _set_env(monkeypatch)
    monkeypatch.setattr(mod.requests, "post", lambda *a, **k: fake_response(200, text="not json"))
    with pytest.raises(LoaderError):
        mod.extract_text(_file(tmp_path))


def test_request_error_raises(monkeypatch, tmp_path):
    _set_env(monkeypatch)

    def fake_post(*a, **k):
        raise requests.RequestException("network down")

    monkeypatch.setattr(mod.requests, "post", fake_post)
    with pytest.raises(LoaderError):
        mod.extract_text(_file(tmp_path))
