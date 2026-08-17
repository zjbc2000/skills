"""筛简历管线（CLI 与飞书 bot 共用，DRY，SPEC §5.4）。"""
from __future__ import annotations

from pathlib import Path

from ..config import AppConfig
from ..doc_loader.base import doc_to_text, resolve_loader_names
from ..persistence.jd_map import jd_text, load_jd_map
from ..registry.fake import fake_call_fn
from ..registry.llm_client import FailedQueue, LLMClient
from ..registry.openai_adapter import make_call_fn
from ..scoring.engine import assess
from ..scoring.prompts import build_prompt
from ..scoring.schema import validate_llm_output
from ..verify.quotation import verify_snapshot


class ScreeningError(Exception):
    pass


def screen_file(resume_path, jd_ref: str, mode: str, cfg: AppConfig, datasets_dir, llm: str = "real") -> dict:
    """解析 → LLM → 评分 → quotation 校验。返回 {verdict, snapshot, doc}。

    失败抛 ScreeningError / LoaderError / LLMError（由调用方处理）。
    """
    datasets = Path(datasets_dir)
    try:
        jd_map = load_jd_map(datasets / "jd_map.yml")
    except FileNotFoundError as e:
        raise ScreeningError(f"缺少 jd_map: {datasets / 'jd_map.yml'}") from e
    if jd_ref not in jd_map:
        raise ScreeningError(f"jd_map 中不存在岗位: {jd_ref}")

    doc = doc_to_text(resume_path, resolve_loader_names(cfg))
    call = fake_call_fn() if llm == "fake" else make_call_fn(cfg)
    client = LLMClient(
        chain=cfg.fallback_chain,
        call_fn=call,
        validator=validate_llm_output,
        failed_queue=FailedQueue(path=datasets / "failed.jsonl"),
    )
    prompt = build_prompt(doc.text, jd_text(jd_map[jd_ref]))
    data = client.complete(prompt)
    verdict = assess(data, mode, cfg.thresholds)
    snapshot = verify_snapshot(verdict.snapshot, doc.text)
    return {"verdict": verdict, "snapshot": snapshot, "doc": doc}
