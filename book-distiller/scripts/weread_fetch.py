#!/usr/bin/env python3
"""微信读书薄封装：解析 bookId → 调 lbq110/weread-exporter 导出全本 → 返回合并 Markdown。

用法: python3 weread_fetch.py <reader链接或bookId>

依赖（可选）：Playwright + Chromium，首次运行弹出浏览器扫码登录。
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

EXPORT_TIMEOUT_SECONDS = 14400  # 4 小时，整本书导出可能很久
FAILURE_MARKERS = [
    "去 App 阅读",
    "需要有效的微信读书账号",
    "无法导出",
    "登录失败",
    "登录超时",
]


class WereadExportError(Exception):
    """导出失败/超时/找不到产物。"""


def parse_book_id(raw: str) -> str:
    """从 reader URL 或裸 bookId 解析。"""
    s = raw.strip().rstrip("/")
    if "weread.qq.com" in s:
        return s.rsplit("/", 1)[-1]
    return s


def detect_export_failure(output: str) -> str | None:
    """在导出器输出里匹配失败标记。"""
    for marker in FAILURE_MARKERS:
        if marker in output:
            return marker
    return None


def export_book(book_id: str, workdir: Path, exporter_script: Path) -> Path:
    """调导出器，返回 output/ 下合并后的 书名.md；失败抛 WereadExportError。"""
    try:
        proc = subprocess.run(
            [sys.executable, str(exporter_script), book_id],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=EXPORT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise WereadExportError("导出超时（超过 4 小时）")
    output = (proc.stdout or "") + (proc.stderr or "")
    marker = detect_export_failure(output)
    if marker:
        raise WereadExportError(f"导出失败：{marker}")
    merged = sorted((workdir / "output").glob("*.md"))
    if not merged:
        raise WereadExportError("导出完成但未找到合并后的 Markdown 产物")
    return merged[0]


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="微信读书全本导出（薄封装）")
    ap.add_argument("input", help="微信读书 reader 链接或 bookId")
    ap.add_argument("--exporter", default="export_precise.py",
                    help="lbq110/weread-exporter 的 export_precise.py 路径")
    ap.add_argument("--workdir", default=".",
                    help="导出工作目录（export_precise.py 所在目录）")
    args = ap.parse_args(argv)
    book_id = parse_book_id(args.input)
    print(f"Book ID: {book_id}")
    try:
        result = export_book(book_id, Path(args.workdir), Path(args.exporter))
    except WereadExportError as e:
        print(f"✗ {e}", file=sys.stderr)
        print("请提供 PDF/Markdown，或换正版 DRM-free 电子书路径。", file=sys.stderr)
        return 1
    print(f"✅ 导出完成: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
