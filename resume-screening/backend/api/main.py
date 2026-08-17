"""FastAPI 后端（SPEC §9）：AE 工作台与 skill 的编排入口。

端点：/health /roles /screen /screen/batch /jd/* /eval /label /eval/apply-threshold；
除 /health 外均需 X-API-Key。
"""
from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

import yaml
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ..config import load_config
from ..persistence import usage
from ..doc_loader.base import LoaderError
from ..eval.run_eval import build_eval_data, build_records
from ..persistence.history import add_session, get_session, list_sessions
from ..persistence.jd_map import load_jd_map, save_jd, update_jd
from ..persistence.labels import load_labels, save_label
from ..persistence.manifest import append_record, build_record
from ..registry.fake import fake_jd_call_fn
from ..registry.llm_client import FailedQueue, LLMClient, LLMError
from ..registry.openai_adapter import make_call_fn
from ..scoring.engine import MODES
from ..scoring.prompts import JD_EXTRACT_SYSTEM_PROMPT, build_jd_extract_prompt
from ..scoring.schema import validate_jd_output, validate_llm_output
from ..screening.pipeline import ScreeningError, screen_file
from ..tasks import tasks

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

app = FastAPI(title="resume-screening API", version="0.18")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v0 本地，全放行
    allow_methods=["*"],
    allow_headers=["*"],
)


def _datasets_dir() -> Path:
    return Path(os.environ.get("RESUME_DATASETS", str(REPO_ROOT / "datasets")))


def _config_dir() -> Path:
    return Path(os.environ.get("RESUME_CONFIG", str(REPO_ROOT / "config")))


def _require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get("X_API_KEY", "")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid or missing api key")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/config/thresholds", dependencies=[Depends(_require_api_key)])
def config_thresholds() -> dict:
    """当前生效判定阈值（含 env 覆盖后的值），供前端模式说明等展示。"""
    return {"thresholds": load_config(_config_dir()).thresholds}


@app.get("/config/providers", dependencies=[Depends(_require_api_key)])
def config_providers() -> dict:
    """当前 provider 端点（含本地覆盖），不含密钥。"""
    cfg = load_config(_config_dir())
    return {
        "providers": {
            name: {"base_url": p.get("base_url", ""), "models": list(p.get("models", []))}
            for name, p in cfg.providers.items()
        }
    }


@app.post("/config/providers", dependencies=[Depends(_require_api_key)])
def save_config_providers(body: dict) -> dict:
    """配置一个 OpenAI 兼容 API 端点（provider 名 + base_url + api_key + 模型名）。

    写 `config/providers.local.yml`（运行时覆盖，不污染 models.yml）；key 写入项目根 `.env`。
    """
    provider = (body.get("provider") or "").strip()
    base_url = (body.get("base_url") or "").strip()
    api_key = (body.get("api_key") or "").strip()
    model = (body.get("model") or "").strip()
    for name, v in (("provider", provider), ("base_url", base_url),
                    ("api_key", api_key), ("model", model)):
        if not v:
            raise HTTPException(status_code=400, detail=f"{name} 必填且非空")

    env_key = provider.upper().replace("-", "_") + "_API_KEY"

    # 1) key 写入项目根 .env（已有则替换该行）
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        kept, replaced = [], False
        for ln in lines:
            if ln.startswith(env_key + "="):
                kept.append(f"{env_key}={api_key}")
                replaced = True
            else:
                kept.append(ln)
        if not replaced:
            kept.append(f"{env_key}={api_key}")
        env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    else:
        env_path.write_text(f"{env_key}={api_key}\n", encoding="utf-8")

    # 2) provider 写入 providers.local.yml
    local_path = _config_dir() / "providers.local.yml"
    local = {}
    if local_path.exists():
        try:
            local = yaml.safe_load(local_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            local = {}
    lp = local.setdefault("providers", {})
    lp[provider] = {"base_url": base_url, "api_key_env": env_key, "models": [model]}
    local_path.write_text(
        yaml.safe_dump(local, allow_unicode=True, sort_keys=False), encoding="utf-8")

    return {"provider": provider, "base_url": base_url, "model": model,
            "api_key_env": env_key}


@app.get("/roles", dependencies=[Depends(_require_api_key)])
def roles() -> dict:
    try:
        jd_map = load_jd_map(_datasets_dir() / "jd_map.yml")
    except FileNotFoundError:
        return {"roles": []}
    return {"roles": list(jd_map.keys())}


def _screen_one(path, display_name: str, jd: str, mode: str, llm: str, cfg, log=None) -> dict:
    """筛一份并落 manifest，返回前端结果 dict（失败抛异常，由调用方处理）。"""
    log = log or (lambda _line: None)
    log(f"[{display_name}]")
    result = screen_file(path, jd, mode, cfg, _datasets_dir(), llm=llm, on_log=log)
    snapshot, doc = result["snapshot"], result["doc"]
    append_record(
        build_record(display_name, jd, result["verdict"], doc_loader=doc.loader, snapshot=snapshot),
        _datasets_dir() / "manifest.jsonl",
    )
    return {
        "name": display_name,
        "verdict": snapshot["verdict"],
        "totals": snapshot["totals"],
        "thresholds": snapshot["thresholds"],
        "doc_loader": doc.loader,
        "snapshot": snapshot,
    }


@app.post("/screen", dependencies=[Depends(_require_api_key)])
async def screen(
    file: UploadFile = File(...),
    jd: str = Form(...),
    mode: str = Form("general"),
    llm: str = Form("real"),
) -> dict:
    if mode not in MODES:
        raise HTTPException(status_code=400, detail=f"未知模式: {mode}")
    suffix = Path(file.filename or "resume").suffix or ".pdf"
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(await file.read())
        try:
            return _screen_one(tmp, file.filename or tmp, jd, mode, llm, load_config(_config_dir()))
        except (ScreeningError, LoaderError, LLMError) as e:
            raise HTTPException(status_code=400, detail=str(e))
    finally:
        Path(tmp).unlink(missing_ok=True)


def _docs_from_zip(zip_path: Path, dest: Path) -> List[Path]:
    """解出 zip 内的 PDF/docx（按文件名平铺，忽略目录结构，防路径穿越）。"""
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if name.lower().endswith((".pdf", ".docx")):
                target = dest / name
                with zf.open(info) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                out.append(target)
    return out


def _run_batch(log, docs: List[tuple], jd: str, mode: str, llm: str) -> dict:
    """任务线程内逐份筛选，返回 batch 结果（含逐文件日志）。"""
    cfg = load_config(_config_dir())
    results = []
    log(f"批量筛选 {len(docs)} 份简历，岗位「{jd}」…")
    for path, display_name in docs:
        if path is None:  # 上传阶段解包失败的占位条目
            results.append({"name": display_name, "error": "非法 zip 包或 zip 内无 PDF/docx"})
            continue
        try:
            results.append(_screen_one(path, display_name, jd, mode, llm, cfg, log=log))
        except (ScreeningError, LoaderError, LLMError, ValueError) as e:
            log(f"[{display_name}] 失败：{e}")
            results.append({"name": display_name, "error": str(e)})
    ok = sum(1 for r in results if "verdict" in r)
    log(f"全部完成：成功 {ok}，失败 {len(results) - ok}")
    add_session(_datasets_dir() / "history.db", jd, mode, results)
    return {"results": results, "n_ok": ok, "n_fail": len(results) - ok}


@app.post("/screen/batch", dependencies=[Depends(_require_api_key)])
async def screen_batch(
    files: List[UploadFile] = File(...),
    jd: str = Form(...),
    mode: str = Form("general"),
    llm: str = Form("real"),
) -> dict:
    """批量筛选（异步任务）：立即返回 task_id，进度与结果经 GET /tasks/{id} 获取。"""
    if mode not in MODES:
        raise HTTPException(status_code=400, detail=f"未知模式: {mode}")

    # 先落盘到任务专属临时目录（读取 UploadFile 必须留在请求内）
    task_dir = Path(tempfile.mkdtemp(prefix="screen-task-"))
    docs: List[tuple] = []  # (Path, display_name)
    for i, f in enumerate(files):
        raw = await f.read()
        name = f.filename or f"file{i}"
        staging = task_dir / f"upload{i}{Path(name).suffix}"
        staging.write_bytes(raw)
        if name.lower().endswith(".zip"):
            inner_dir = task_dir / f"zip{i}"
            inner_dir.mkdir()
            try:
                inners = _docs_from_zip(staging, inner_dir)
            except zipfile.BadZipFile:
                docs.append((None, name))  # 无法解包：提交前即记一条失败
            else:
                if not inners:
                    docs.append((None, name))
                else:
                    docs.extend((p, p.name) for p in inners)
        else:
            docs.append((staging, name))

    tid = tasks.submit(_run_batch, docs, jd, mode, llm)
    return {"task_id": tid}


def _run_jd_extract(log, jd_raw: str, llm: str) -> dict:
    """任务线程内调用 LLM 抽取 JD 字段。"""
    log(f"JD 抽取中（{len(jd_raw)} 字符原文）…")
    cfg = load_config(_config_dir())
    call = fake_jd_call_fn() if llm == "fake" else make_call_fn(cfg, system_prompt=JD_EXTRACT_SYSTEM_PROMPT)
    # JD 抽取是轻交互任务：低重试 + 单次 60s 超时，失败快速报错而非长时间重试
    client = LLMClient(
        chain=cfg.fallback_chain,
        call_fn=call,
        validator=validate_jd_output,
        max_retries=1,
        failed_queue=FailedQueue(path=_datasets_dir() / "failed.jsonl"),
    )
    fields = client.complete(build_jd_extract_prompt(jd_raw))
    log(f"抽取完成：position={fields['position']}，skills {len(fields['skills'])} 条，红线 {len(fields['red_lines'])} 条")
    return fields


@app.post("/jd/extract", dependencies=[Depends(_require_api_key)])
def jd_extract(body: dict) -> dict:
    """JD 原文 -> 结构化字段（异步任务，立即返回 task_id）。"""
    jd_raw = body.get("jd_raw")
    if not isinstance(jd_raw, str) or not jd_raw.strip():
        raise HTTPException(status_code=400, detail="jd_raw 必填且非空")
    llm = body.get("llm", "real")
    return {"task_id": tasks.submit(_run_jd_extract, jd_raw, llm)}


@app.get("/history", dependencies=[Depends(_require_api_key)])
def history() -> dict:
    """筛选历史会话列表（sqlite）。"""
    return {"sessions": list_sessions(_datasets_dir() / "history.db")}


@app.get("/history/{session_id}", dependencies=[Depends(_require_api_key)])
def history_detail(session_id: int) -> dict:
    """单个历史会话详情（含逐条记录与 snapshot）。"""
    sess = get_session(_datasets_dir() / "history.db", session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    return sess


@app.get("/tasks/{task_id}", dependencies=[Depends(_require_api_key)])
def task_status(task_id: str) -> dict:
    """任务状态与累计日志。"""
    t = tasks.get(task_id)
    if t is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return {"id": t["id"], "status": t["status"], "logs": t["logs"],
            "error": t.get("error"), "result": t.get("result")}


@app.post("/jd/save", dependencies=[Depends(_require_api_key)])
def jd_save(body: dict) -> dict:
    """保存岗位到 jd_map.yml（key 已存在返回 409）。"""
    key = body.get("key")
    if not isinstance(key, str) or not key.strip():
        raise HTTPException(status_code=400, detail="key 必填且非空")
    skills = body.get("skills")
    red_lines = body.get("red_lines", [])
    if not isinstance(skills, list) or not skills or not all(isinstance(s, str) and s.strip() for s in skills):
        raise HTTPException(status_code=400, detail="skills 应为非空字符串列表")
    if not isinstance(red_lines, list) or not all(isinstance(r, str) for r in red_lines):
        raise HTTPException(status_code=400, detail="red_lines 应为字符串列表")

    path = _datasets_dir() / "jd_map.yml"
    if not path.exists():
        path.write_text("roles: {}\n", encoding="utf-8")
    try:
        save_jd(path, key.strip(), {
            "position": body.get("position", ""),
            "skills": skills,
            "red_lines": red_lines,
        })
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"key": key.strip(), "roles": list(load_jd_map(path).keys())}


@app.get("/jd/list", dependencies=[Depends(_require_api_key)])
def jd_list() -> dict:
    """全部岗位的结构化内容（卡片展示 / 编辑用）。"""
    path = _datasets_dir() / "jd_map.yml"
    if not path.exists():
        return {"jds": []}
    jds = [
        {"key": k, "position": v.get("position", ""), "skills": v.get("skills", []),
         "red_lines": v.get("red_lines", [])}
        for k, v in load_jd_map(path).items()
    ]
    return {"jds": jds}


@app.post("/jd/update", dependencies=[Depends(_require_api_key)])
def jd_update(body: dict) -> dict:
    """更新已有岗位（key 变更则迁移）。"""
    old_key = body.get("old_key")
    key = body.get("key")
    if not isinstance(old_key, str) or not old_key.strip():
        raise HTTPException(status_code=400, detail="old_key 必填且非空")
    if not isinstance(key, str) or not key.strip():
        raise HTTPException(status_code=400, detail="key 必填且非空")
    skills = body.get("skills")
    red_lines = body.get("red_lines", [])
    if not isinstance(skills, list) or not skills or not all(isinstance(s, str) and s.strip() for s in skills):
        raise HTTPException(status_code=400, detail="skills 应为非空字符串列表")
    if not isinstance(red_lines, list) or not all(isinstance(r, str) for r in red_lines):
        raise HTTPException(status_code=400, detail="red_lines 应为字符串列表")

    path = _datasets_dir() / "jd_map.yml"
    try:
        update_jd(path, old_key.strip(), key.strip(), {
            "position": body.get("position", ""),
            "skills": skills,
            "red_lines": red_lines,
        })
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"key": key.strip(), "roles": list(load_jd_map(path).keys())}


@app.get("/models", dependencies=[Depends(_require_api_key)])
def models() -> dict:
    """可用模型（providers × models）与当前默认。"""
    cfg = load_config(_config_dir())
    return {
        "providers": {p: list(c["models"]) for p, c in cfg.providers.items()},
        "default": {"provider": cfg.default["provider"], "model": cfg.default["model"]},
    }


@app.post("/models/default", dependencies=[Depends(_require_api_key)])
def set_default_model(body: dict) -> dict:
    """切换默认模型：写 config/default_model.yml（运行时覆盖，不改 models.yml）。"""
    provider = body.get("provider")
    model = body.get("model")
    cfg = load_config(_config_dir())
    models_list = (cfg.providers.get(provider) or {}).get("models", [])
    if provider not in cfg.providers or model not in models_list:
        raise HTTPException(status_code=400, detail=f"非法模型组合: {provider}/{model}")
    path = _config_dir() / "default_model.yml"
    path.write_text(
        yaml.safe_dump({"provider": provider, "model": model}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return {"default": {"provider": provider, "model": model}}


@app.get("/dashboard", dependencies=[Depends(_require_api_key)])
def dashboard() -> dict:
    """LLM 用量面板：总览 + 按模型 + 最近调用。"""
    return {
        "summary": usage.summary(),
        "by_model": usage.by_model(),
        "recent": usage.recent(),
    }


@app.post("/dashboard/clear", dependencies=[Depends(_require_api_key)])
def dashboard_clear() -> dict:
    usage.clear()
    return {"ok": True}


@app.get("/eval", dependencies=[Depends(_require_api_key)])
def eval_endpoint() -> dict:
    from ..persistence.manifest import load_records

    cfg = load_config(_config_dir())
    records = build_records(
        load_records(_datasets_dir() / "manifest.jsonl"),
        labels=load_labels(_datasets_dir() / "labels.json"),
        thresholds=cfg.thresholds,
    )
    return build_eval_data(records, cfg)


@app.post("/label", dependencies=[Depends(_require_api_key)])
def label(body: dict) -> dict:
    """人工标注一条 manifest 记录（label: pass | fail | null=清除）。"""
    record_key = body.get("record_key")
    label_value = body.get("label", None)
    if not isinstance(record_key, str) or not record_key:
        raise HTTPException(status_code=400, detail="record_key 必填")
    try:
        labels = save_label(_datasets_dir() / "labels.json", record_key, label_value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"n_labels": len(labels)}


@app.post("/eval/apply-threshold", dependencies=[Depends(_require_api_key)])
def apply_threshold(body: dict) -> dict:
    """把扫描出的最优总分阈值回写 thresholds.yml（只动 total）。"""
    threshold = body.get("threshold")
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 0:
        raise HTTPException(status_code=400, detail="threshold 应为非负整数")
    path = _config_dir() / "thresholds.yml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=f"缺少配置文件: {path}") from e
    if not isinstance(data.get("general"), int) or not isinstance(data.get("specific"), int):
        raise HTTPException(status_code=400, detail="thresholds.yml 结构非法")
    data["total"] = threshold
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {"thresholds": data}
