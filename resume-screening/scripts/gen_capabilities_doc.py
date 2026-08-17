#!/usr/bin/env python3
"""从注册表生成 docs/capabilities.md（防漂移）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import load_config
from backend.registry.capabilities import render_capabilities

DOC = Path(__file__).resolve().parent.parent / "docs" / "capabilities.md"

if __name__ == "__main__":
    DOC.write_text(render_capabilities(load_config()), encoding="utf-8")
    print(f"written: {DOC}")
