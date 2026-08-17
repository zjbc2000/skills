"""启动飞书 bot（长连接，SPEC §6）。

用法：python -m backend.cli.bot
需先在飞书开放平台：企业自建应用 → 启用机器人 + 配置权限 + 事件订阅切换为长连接。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ..config import load_config
from ..screening.pipeline import screen_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATASETS = REPO_ROOT / "datasets"


def main(argv=None) -> int:
    load_dotenv(REPO_ROOT / ".env")
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        print("缺少 FEISHU_APP_ID / FEISHU_APP_SECRET（.env）", file=sys.stderr)
        return 1
    whitelist = {x.strip() for x in os.environ.get("FEISHU_CHAT_WHITELIST", "").split(",") if x.strip()}
    default_jd = os.environ.get("RESUME_DEFAULT_JD", "")
    datasets = Path(os.environ.get("RESUME_DATASETS", str(DEFAULT_DATASETS)))
    cfg = load_config()

    def screen_fn(path: Path) -> dict:
        return screen_file(path, default_jd, "general_specific", cfg, datasets, llm="real")

    from ..channels.feishu import run_bot

    print(f"bot 启动：白名单群 {len(whitelist)} 个，默认岗位 '{default_jd}'")
    run_bot(app_id, app_secret, whitelist, screen_fn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
