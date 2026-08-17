"""CLI：筛一份简历，写 manifest（tracer bullet，SPEC §0）。

用法：python -m backend.cli.screen <简历.pdf> --jd <岗位key> [--mode ...] [--llm fake|real]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from ..config import load_config
from ..doc_loader.base import LoaderError
from ..persistence.manifest import append_record, build_record
from ..registry.llm_client import FailedQueue, LLMError
from ..scoring.engine import MODES
from ..screening.pipeline import ScreeningError, screen_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATASETS = REPO_ROOT / "datasets"


def main(argv=None) -> int:
    load_dotenv(REPO_ROOT / ".env")  # 凭据从项目根 .env 加载
    parser = argparse.ArgumentParser(description="筛一份简历并写入 manifest")
    parser.add_argument("resume", nargs="?", help="简历文件（PDF）")
    parser.add_argument("--jd", help="jd_map 中的岗位 key")
    parser.add_argument("--mode", choices=MODES, default="general")
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

    cfg = load_config()
    try:
        result = screen_file(args.resume, args.jd, args.mode, cfg, datasets, llm=args.llm)
    except ScreeningError as e:
        print(f"失败: {e}", file=sys.stderr)
        return 1
    except LoaderError as e:
        print(f"解析失败: {e}", file=sys.stderr)
        return 1
    except LLMError as e:
        print(f"模型调用失败: {e}", file=sys.stderr)
        return 1

    verdict, snapshot, doc = result["verdict"], result["snapshot"], result["doc"]
    append_record(
        build_record(args.resume, args.jd, verdict, doc_loader=doc.loader, snapshot=snapshot),
        datasets / "manifest.jsonl",
    )
    print(
        f"verdict={snapshot['verdict']} G={verdict.g} S={verdict.s} T={verdict.t} "
        f"mode={args.mode} loader={doc.loader}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
