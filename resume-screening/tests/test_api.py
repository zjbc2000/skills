"""FastAPI 后端（T10）：/screen /eval /roles + X-API-Key 鉴权。"""
from __future__ import annotations

import json

import pytest

from backend.api.main import app

JD_YML = """roles:
  西安AE:
    position: 高级AE工程师
    skills: [react]
    red_lines: []
"""


def _make_pdf(path, text="Zhang San - Senior Engineer\n3 years react and python.\nLed OCR team."):
    import fitz

    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("X_API_KEY", "test-key")
    monkeypatch.setenv("RESUME_DATASETS", str(tmp_path))
    for k in ("LAYOUT_PARSING_URL", "LAYOUT_PARSING_TOKEN", "ARK_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.setenv(k, "")
    (tmp_path / "jd_map.yml").write_text(JD_YML, encoding="utf-8")
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


def _auth():
    return {"X-API-Key": "test-key"}


def test_health_no_auth(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_roles_requires_api_key(client):
    assert client.get("/roles").status_code == 401
    assert client.get("/roles", headers=_auth()).status_code == 200


def test_roles_lists_jd_keys(client):
    r = client.get("/roles", headers=_auth())
    assert r.json()["roles"] == ["西安AE"]


def test_roles_empty_without_jd_map(tmp_path, monkeypatch):
    monkeypatch.setenv("X_API_KEY", "test-key")
    monkeypatch.setenv("RESUME_DATASETS", str(tmp_path))  # tmp_path 无 jd_map.yml
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        assert c.get("/roles", headers=_auth()).json()["roles"] == []


def test_screen_requires_api_key(client):
    r = client.post("/screen", data={"jd": "西安AE"})
    assert r.status_code == 401


def test_screen_returns_verdict_and_writes_manifest(client, tmp_path):
    pdf = tmp_path / "resume.pdf"
    _make_pdf(pdf)
    with open(pdf, "rb") as f:
        r = client.post(
            "/screen",
            headers=_auth(),
            files={"file": ("resume.pdf", f, "application/pdf")},
            data={"jd": "西安AE", "mode": "general_specific", "llm": "fake"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in ("pass", "fail")
    assert "totals" in body
    assert body["doc_loader"] == "local_pymupdf"
    # manifest 落库
    manifest = tmp_path / "manifest.jsonl"
    assert manifest.exists()
    rec = json.loads(manifest.read_text(encoding="utf-8").splitlines()[0])
    assert rec["jd_ref"] == "西安AE"
    assert "verify" in rec["score_snapshot"]["general"]["projects"][0]


def test_screen_unknown_jd_returns_400(client, tmp_path):
    pdf = tmp_path / "resume.pdf"
    _make_pdf(pdf)
    with open(pdf, "rb") as f:
        r = client.post(
            "/screen", headers=_auth(),
            files={"file": ("resume.pdf", f, "application/pdf")},
            data={"jd": "不存在", "llm": "fake"},
        )
    assert r.status_code == 400


def test_eval_returns_metrics(client, tmp_path):
    # 先筛一份，再跑 eval
    pdf = tmp_path / "resume.pdf"
    _make_pdf(pdf)
    with open(pdf, "rb") as f:
        client.post(
            "/screen", headers=_auth(),
            files={"file": ("resume.pdf", f, "application/pdf")},
            data={"jd": "西安AE", "llm": "fake"},
        )
    r = client.get("/eval", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["n"] == 1
    assert "metrics" in body and "confusion" in body
