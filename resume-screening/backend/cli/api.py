"""启动 FastAPI 后端（端口/主机从 .env 的 API_HOST/API_PORT 读取，默认 127.0.0.1:8000）。

用法：python3 -m backend.cli.api
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main(argv=None) -> int:
    load_dotenv(REPO_ROOT / ".env")
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", "8000"))

    from ..api.main import app
    import uvicorn

    print(f"API 启动：http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
