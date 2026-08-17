"""CLI：筛一份简历，写 manifest（tracer bullet，SPEC §0）。

用法：python -m backend.cli.screen <简历.pdf> --jd <岗位key> [--mode ...] [--llm fake|real]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

from ..config import load_config
from ..doc_loader.base import LoaderError, doc_to_text, resolve_loader_names
from ..persistence.jd_map import jd_text, load_jd_map
from ..persistence.manifest import append_record, build_record
from ..registry.fake import fake_call_fn
from ..registry.llm_client import FailedQueue, LLMClient, LLMError
from ..registry.openai_adapter import make_call_fn
from ..scoring.engine import MODES, assess
from ..scoring.prompts import build_prompt
from ..scoring.schema import validate_llm_output
from ..verify.quotation import verify_snapshot

DEFAULT_DATASETS = Path(__file__).resolve().parent.parent.parent / "datasets"


def main(argv=None) -> int:
    load_dotenv(REPO_ROOT / ".env")  # 凭据从项目根 .env 加载
    parser = argparse.ArgumentParser(description="筛一份简历并写入 manifest")
    parser.add_argument("resume", nargs="?", help="简历文件（PDF）")
    parser.add_argument("--jd", help="jd_map 中的岗位 key")
    parser.add_argument("--mode", choices=MODES, default="general_specific")
    parser.add_argument("--datasets", default=str(DEFAULT_DATASETS))
    parser.add_argument("--llm", choices=["real", "fake"], default="real")
    parser.add_argument("--list-failed", action="store_true", help="列出 failed 队列并退出")
    args = parser.parse_args(argv)

    datasets = Path(args.datasets)

    if args.list_failed:
        for rec in FailedQueue(path=datasets / "failed.jsonl").records():
            print(json.dumps(rec, ensure_ascii=False))
        return 0

    if not args.jd or not args.resume:
        parser.error("需要 <简历.pdf> 与 --jd <岗位key>（或用 --list-failed 查看失败队列）")
    try:
        jd_map = load_jd_map(datasets / "jd_map.yml")
    except FileNotFoundError:
        print(f"缺少 jd_map: {datasets / 'jd_map.yml'}", file=sys.stderr)
        return 1
    if args.jd not in jd_map:
        print(f"jd_map 中不存在岗位: {args.jd}", file=sys.stderr)
        return 1

    cfg = load_config()
    try:
        doc = doc_to_text(args.resume, resolve_loader_names(cfg))
    except LoaderError as e:
        print(f"解析失败: {e}", file=sys.stderr)
        return 1

    call = fake_call_fn() if args.llm == "fake" else make_call_fn(cfg)
    client = LLMClient(
        chain=cfg.fallback_chain,
        call_fn=call,
        validator=validate_llm_output,
        failed_queue=FailedQueue(path=datasets / "failed.jsonl"),
    )

    prompt = build_prompt(doc.text, jd_text(jd_map[args.jd]))
    try:
        data = client.complete(prompt)
    except LLMError as e:
        print(f"模型调用失败: {e}", file=sys.stderr)
        return 1

    verdict = assess(data, args.mode, cfg.thresholds)
    snapshot = verify_snapshot(verdict.snapshot, doc.text)
    append_record(
        build_record(args.resume, args.jd, verdict, doc_loader=doc.loader, snapshot=snapshot),
        datasets / "manifest.jsonl",
    )
    print(
        f"verdict={verdict.snapshot['verdict']} "
        f"G={verdict.g} S={verdict.s} T={verdict.t} "
        f"mode={args.mode} loader={doc.loader}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
