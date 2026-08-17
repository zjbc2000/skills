"""筛简历管线（CLI 与飞书 bot 共用，DRY，SPEC §5.4）。"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

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


def screen_file(
    resume_path,
    jd_ref: str,
    mode: str,
    cfg: AppConfig,
    datasets_dir,
    llm: str = "real",
    on_log: Callable[[str], None] = None,
) -> dict:
    """解析 → LLM → 评分 → quotation 校验。返回 {verdict, snapshot, doc}。

    失败抛 ScreeningError / LoaderError / LLMError（由调用方处理）。
    on_log 可选：逐步上报进度日志（异步任务用）。
    """
    log = on_log or (lambda _line: None)
    datasets = Path(datasets_dir)
    try:
        jd_map = load_jd_map(datasets / "jd_map.yml")
    except FileNotFoundError as e:
        raise ScreeningError(f"缺少 jd_map: {datasets / 'jd_map.yml'}") from e
    if jd_ref not in jd_map:
        raise ScreeningError(f"jd_map 中不存在岗位: {jd_ref}")

    name = Path(resume_path).name
    log(f"解析 {name} …")
    doc = doc_to_text(resume_path, resolve_loader_names(cfg))
    log(f"解析完成（{doc.loader}，{len(doc.text)} 字符）")

    call = fake_call_fn() if llm == "fake" else make_call_fn(cfg)
    client = LLMClient(
        chain=cfg.fallback_chain,
        call_fn=call,
        validator=validate_llm_output,
        failed_queue=FailedQueue(path=datasets / "failed.jsonl"),
    )
    prompt = build_prompt(doc.text, jd_text(jd_map[jd_ref]))
    log(f"LLM 评分中（{len(doc.text)} 字符简历）…")
    data = client.complete(prompt)
    verdict = assess(data, mode, cfg.thresholds)
    snapshot = verify_snapshot(verdict.snapshot, doc.text)
    log(f"判定完成：{'通过' if verdict.passed else '不通过'}（G={verdict.g} S={verdict.s} T={verdict.t}）")
    return {"verdict": verdict, "snapshot": snapshot, "doc": doc}


def build_summary(result: dict) -> str:
    """把筛简历结果渲染成纯文本摘要（CLI / 飞书 bot 共用）。"""
    v = result["verdict"]
    snap = result["snapshot"]
    lines = [
        f"判定：{snap['verdict'].upper()}",
        f"G={v.g} S={v.s} T={v.t}（阈值 G≥{snap['thresholds']['general']} 且 T≥{snap['thresholds']['total']}）",
    ]
    if v.red_lines_hit:
        lines.append("红线命中：" + "、".join(v.red_lines_hit))
    lines.append(f"解析器：{result['doc'].loader}")
    return "\n".join(lines)
