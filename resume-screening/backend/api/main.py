"""FastAPI 后端（SPEC §9）：AE 工作台与 skill 的编排入口。

端点：/health /roles /screen /eval；除 /health 外均需 X-API-Key。
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ..config import load_config
from ..doc_loader.base import LoaderError
from ..eval.run_eval import build_eval_data
from ..persistence.jd_map import load_jd_map
from ..persistence.manifest import append_record, build_record
from ..registry.llm_client import LLMError
from ..scoring.engine import MODES
from ..screening.pipeline import ScreeningError, screen_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

app = FastAPI(title="resume-screening API", version="0.7")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v0 本地，全放行
    allow_methods=["*"],
    allow_headers=["*"],
)


def _datasets_dir() -> Path:
    return Path(os.environ.get("RESUME_DATASETS", str(REPO_ROOT / "datasets")))


def _require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get("X_API_KEY", "")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid or missing api key")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/roles", dependencies=[Depends(_require_api_key)])
def roles() -> dict:
    try:
        jd_map = load_jd_map(_datasets_dir() / "jd_map.yml")
    except FileNotFoundError:
        return {"roles": []}
    return {"roles": list(jd_map.keys())}


@app.post("/screen", dependencies=[Depends(_require_api_key)])
async def screen(
    file: UploadFile = File(...),
    jd: str = Form(...),
    mode: str = Form("general_specific"),
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
            result = screen_file(tmp, jd, mode, load_config(), _datasets_dir(), llm=llm)
        except (ScreeningError, LoaderError, LLMError) as e:
            raise HTTPException(status_code=400, detail=str(e))
    finally:
        Path(tmp).unlink(missing_ok=True)

    verdict, snapshot, doc = result["verdict"], result["snapshot"], result["doc"]
    append_record(
        build_record(file.filename or tmp, jd, verdict, doc_loader=doc.loader, snapshot=snapshot),
        _datasets_dir() / "manifest.jsonl",
    )
    return {
        "verdict": snapshot["verdict"],
        "totals": snapshot["totals"],
        "thresholds": snapshot["thresholds"],
        "doc_loader": doc.loader,
        "snapshot": snapshot,
    }


@app.get("/eval", dependencies=[Depends(_require_api_key)])
def eval_endpoint() -> dict:
    from ..persistence.manifest import load_records

    from ..eval.run_eval import build_records

    records = build_records(load_records(_datasets_dir() / "manifest.jsonl"))
    return build_eval_data(records, load_config())
