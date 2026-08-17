"""FastAPI 后端（T10）：/screen /eval /roles + X-API-Key 鉴权。"""
from __future__ import annotations

import json

import pytest
import yaml

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


def _wait_task(client, tid, timeout=10):
    """轮询任务直至 done/failed，返回 task 响应体。"""
    import time

    for _ in range(timeout * 10):
        r = client.get(f"/tasks/{tid}", headers=_auth())
        assert r.status_code == 200
        t = r.json()
        if t["status"] in ("done", "failed"):
            return t
        time.sleep(0.1)
    raise AssertionError(f"任务超时: {tid}")


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
            data={"jd": "西安AE", "mode": "general", "llm": "fake"},
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
    assert body["labeled"] == 0  # 未人工标注 -> 指标为空
    assert body["records"][0]["record_key"]


def test_jd_extract_fake_llm(client):
    r = client.post(
        "/jd/extract",
        headers=_auth(),
        json={"jd_raw": "岗位职责：\n1.负责RAG交付\n岗位要求：\n1.本科以上", "llm": "fake"},
    )
    assert r.status_code == 200
    tid = r.json()["task_id"]
    t = _wait_task(client, tid)
    assert t["status"] == "done"
    assert any("抽取完成" in line for line in t["logs"])
    body = t["result"]
    assert body["position"] == "测试岗位"
    assert "1.负责RAG交付" in body["skills"]


def test_jd_extract_requires_raw(client):
    assert client.post("/jd/extract", headers=_auth(), json={"jd_raw": " "}).status_code == 400


def test_task_status_unknown_404(client):
    assert client.get("/tasks/nonexistent", headers=_auth()).status_code == 404
    assert client.get("/tasks/nonexistent").status_code == 401


def test_jd_save_registers_role_and_rejects_duplicate(client, tmp_path):
    r = client.post(
        "/jd/save",
        headers=_auth(),
        json={"key": "北京AE", "position": "AE", "skills": ["熟悉RAG"], "red_lines": []},
    )
    assert r.status_code == 200
    assert "北京AE" in r.json()["roles"]
    saved = yaml.safe_load((tmp_path / "jd_map.yml").read_text(encoding="utf-8"))
    assert saved["roles"]["北京AE"]["skills"] == ["熟悉RAG"]
    assert client.get("/roles", headers=_auth()).json()["roles"] == ["西安AE", "北京AE"]

    dup = client.post(
        "/jd/save",
        headers=_auth(),
        json={"key": "北京AE", "position": "AE", "skills": ["x"], "red_lines": []},
    )
    assert dup.status_code == 409


def test_jd_save_validates_payload(client):
    r = client.post(
        "/jd/save",
        headers=_auth(),
        json={"key": "K", "position": "P", "skills": [], "red_lines": []},
    )
    assert r.status_code == 400


def test_screen_batch_with_zip_and_docx(client, tmp_path):
    import docx as docx_lib
    import io
    import zipfile

    pdf1, pdf2 = tmp_path / "a.pdf", tmp_path / "b.pdf"
    _make_pdf(pdf1, "Zhang San - Senior Engineer with react and python. Led OCR team.")
    _make_pdf(pdf2, "Li Si - Senior Engineer with react and python. Led RAG team.")

    d = docx_lib.Document()
    d.add_paragraph("Wang Wu - docx engineer, familiar with react.")
    buf = io.BytesIO()
    d.save(buf)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.write(pdf1, "resumes/a.pdf")
        zf.write(pdf2, "resumes/b.pdf")
        zf.writestr("ignore.txt", "not a resume")

    r = client.post(
        "/screen/batch",
        headers=_auth(),
        files=[
            ("files", ("pack.zip", zip_buf.getvalue(), "application/zip")),
            ("files", ("c.docx", buf.getvalue(),
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ],
        data={"jd": "西安AE", "mode": "general", "llm": "fake"},
    )
    assert r.status_code == 200
    t = _wait_task(client, r.json()["task_id"])
    assert t["status"] == "done"
    assert any("批量筛选 3 份简历" in line for line in t["logs"])
    body = t["result"]
    assert body["n_ok"] == 3 and body["n_fail"] == 0
    names = {x["name"]: x for x in body["results"]}
    assert names["a.pdf"]["verdict"] in ("pass", "fail")
    assert names["c.docx"]["doc_loader"] == "local_docx"
    # manifest 追加 3 条
    manifest_lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 3


def test_screen_batch_bad_file_reports_error(client):
    r = client.post(
        "/screen/batch",
        headers=_auth(),
        files=[("files", ("junk.pdf", b"garbage", "application/pdf"))],
        data={"jd": "西安AE", "llm": "fake"},
    )
    assert r.status_code == 200
    t = _wait_task(client, r.json()["task_id"])
    body = t["result"]
    assert body["n_fail"] == 1
    assert "error" in body["results"][0]


def test_label_and_eval_metrics(client, tmp_path):
    pdf = tmp_path / "resume.pdf"
    _make_pdf(pdf)
    with open(pdf, "rb") as f:
        client.post(
            "/screen",
            headers=_auth(),
            files={"file": ("resume.pdf", f, "application/pdf")},
            data={"jd": "西安AE", "mode": "general", "llm": "fake"},
        )
    rec = client.get("/eval", headers=_auth()).json()["records"][0]

    r = client.post("/label", headers=_auth(), json={"record_key": rec["record_key"], "label": "pass"})
    assert r.status_code == 200
    assert r.json()["n_labels"] == 1

    body = client.get("/eval", headers=_auth()).json()
    assert body["labeled"] == 1 and body["unlabeled"] == 0
    # fake LLM 得 G=3、T=6，真实配置阈值 G>=30 -> 重算 predicted=fail，标注 pass -> 准确率 0
    assert body["records"][0]["predicted"] == "fail"
    assert body["records"][0]["label"] == "pass"
    assert body["metrics"]["accuracy"] == 0.0


def test_label_validates_payload(client):
    assert client.post("/label", headers=_auth(), json={"record_key": "k", "label": "maybe"}).status_code == 400
    assert client.post("/label", headers=_auth(), json={"label": "pass"}).status_code == 400


def test_apply_threshold_writes_config(client, tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "thresholds.yml").write_text(
        "general: 30\nspecific: 20\ntotal: 45\n", encoding="utf-8")
    monkeypatch.setenv("RESUME_CONFIG", str(cfg_dir))

    r = client.post("/eval/apply-threshold", headers=_auth(), json={"threshold": 18})
    assert r.status_code == 200
    assert r.json()["thresholds"]["total"] == 18
    data = yaml.safe_load((cfg_dir / "thresholds.yml").read_text(encoding="utf-8"))
    assert data == {"general": 30, "specific": 20, "total": 18}

    assert client.post("/eval/apply-threshold", headers=_auth(), json={"threshold": -1}).status_code == 400


def test_history_api_flow(client, tmp_path):
    """batch 筛选后写 sqlite，/history 可列出并取详情。"""
    pdf = tmp_path / "resume.pdf"
    _make_pdf(pdf, "Zhang San - Senior Engineer, react and python, OCR team.")
    with open(pdf, "rb") as f:
        r = client.post(
            "/screen/batch",
            headers=_auth(),
            files={"files": ("resume.pdf", f, "application/pdf")},
            data={"jd": "西安AE", "llm": "fake"},
        )
    t = _wait_task(client, r.json()["task_id"])
    assert t["status"] == "done"

    hist = client.get("/history", headers=_auth()).json()
    assert len(hist["sessions"]) == 1
    sid = hist["sessions"][0]["id"]
    assert hist["sessions"][0]["jd"] == "西安AE"

    detail = client.get(f"/history/{sid}", headers=_auth()).json()
    assert detail["records"][0]["name"] == "resume.pdf"
    assert detail["records"][0]["snapshot"] is not None

    assert client.get("/history/99999", headers=_auth()).status_code == 404
    assert client.get("/history").status_code == 401


def test_jd_list_returns_full_structures(client, tmp_path):
    r = client.post(
        "/jd/save",
        headers=_auth(),
        json={"key": "北京AE", "position": "高级AE", "skills": ["熟悉RAG", "熟悉LangGraph"], "red_lines": ["失信记录"]},
    )
    assert r.status_code == 200
    jds = client.get("/jd/list", headers=_auth()).json()["jds"]
    by_key = {j["key"]: j for j in jds}
    assert by_key["北京AE"]["position"] == "高级AE"
    assert by_key["北京AE"]["skills"] == ["熟悉RAG", "熟悉LangGraph"]
    assert by_key["北京AE"]["red_lines"] == ["失信记录"]


def test_jd_update_edits_and_migrates_key(client, tmp_path):
    client.post("/jd/save", headers=_auth(),
                json={"key": "北京AE", "position": "P", "skills": ["x"], "red_lines": []})

    # 直接改字段
    r = client.post("/jd/update", headers=_auth(),
                    json={"old_key": "北京AE", "key": "北京AE", "position": "高级AE",
                          "skills": ["x", "y"], "red_lines": []})
    assert r.status_code == 200
    jds = client.get("/jd/list", headers=_auth()).json()["jds"]
    ae = next(j for j in jds if j["key"] == "北京AE")
    assert ae["position"] == "高级AE" and ae["skills"] == ["x", "y"]

    # 改 key（迁移）
    r = client.post("/jd/update", headers=_auth(),
                    json={"old_key": "北京AE", "key": "上海AE", "position": "P",
                          "skills": ["z"], "red_lines": []})
    assert r.status_code == 200
    keys = client.get("/roles", headers=_auth()).json()["roles"]
    assert "上海AE" in keys and "北京AE" not in keys

    # 目标 key 被占 -> 409
    client.post("/jd/save", headers=_auth(),
                json={"key": "广州AE", "position": "P", "skills": ["z"], "red_lines": []})
    dup = client.post("/jd/update", headers=_auth(),
                      json={"old_key": "上海AE", "key": "广州AE", "position": "P",
                            "skills": ["z"], "red_lines": []})
    assert dup.status_code == 409

    # 不存在的 old_key -> 409
    miss = client.post("/jd/update", headers=_auth(),
                       json={"old_key": "不存在", "key": "K", "position": "P",
                             "skills": ["z"], "red_lines": []})
    assert miss.status_code == 409


def test_dashboard_models_and_switch_api(client, tmp_path, monkeypatch):
    """dashboard 聚合 / models 列表 / 切换默认模型（写 tmp 配置）/ 清空用量。"""
    from backend.persistence import usage

    usage.record("ark_coding", "deepseek-v4-flash", 100, 50, 100.0, True)
    usage.record("ark_coding", "deepseek-v4-flash", 10, 5, 500.0, False)

    dash = client.get("/dashboard", headers=_auth()).json()
    assert dash["summary"]["n"] == 2 and dash["summary"]["success_rate"] == 0.5
    assert dash["by_model"][0]["model"] == "deepseek-v4-flash"
    assert len(dash["recent"]) == 2

    m = client.get("/models", headers=_auth()).json()
    assert "ark_coding" in m["providers"]
    assert m["default"]["provider"] == "ark_coding"

    # 切换默认模型：RESUME_CONFIG 指向 tmp 配置目录，避免写仓库 config/
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "models.yml").write_text(
        "providers:\n  ark_coding:\n    base_url: http://x\n    api_key_env: K\n"
        "    models: [deepseek-v4-flash, doubao-seed-2.0-lite]\n"
        "default:\n  provider: ark_coding\n  model: deepseek-v4-flash\n", encoding="utf-8")
    (cfg_dir / "tools.yml").write_text("doc_loader:\n  primary: local_pymupdf\n", encoding="utf-8")
    (cfg_dir / "thresholds.yml").write_text("general: 30\nspecific: 20\ntotal: 45\n", encoding="utf-8")
    monkeypatch.setenv("RESUME_CONFIG", str(cfg_dir))

    r = client.post("/models/default", headers=_auth(),
                    json={"provider": "ark_coding", "model": "doubao-seed-2.0-lite"})
    assert r.status_code == 200
    assert (cfg_dir / "default_model.yml").exists()
    m2 = client.get("/models", headers=_auth()).json()
    assert m2["default"] == {"provider": "ark_coding", "model": "doubao-seed-2.0-lite"}

    bad = client.post("/models/default", headers=_auth(),
                      json={"provider": "ark_coding", "model": "不存在"})
    assert bad.status_code == 400

    c = client.post("/dashboard/clear", headers=_auth())
    assert c.status_code == 200
    assert client.get("/dashboard", headers=_auth()).json()["summary"]["n"] == 0


def test_eval_returns_current_thresholds(client):
    """/eval 响应带当前生效阈值（G/S/T），供评测页展示。"""
    body = client.get("/eval", headers=_auth()).json()
    assert set(body["thresholds"]) == {"general", "specific", "total"}
    assert isinstance(body["thresholds"]["general"], int)


def test_config_thresholds_endpoint(client):
    """/config/thresholds 返回当前生效阈值（含 env 覆盖）。"""
    body = client.get("/config/thresholds", headers=_auth()).json()
    assert set(body["thresholds"]) == {"general", "specific", "total"}
    assert isinstance(body["thresholds"]["general"], int)
