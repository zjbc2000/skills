#!/usr/bin/env python3
"""L0 结构校验：frontmatter 合法性 + name/目录一致 + 引用可解析。

用法: python3 validate_skill.py <SKILL.md> [<SKILL.md> ...]
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    end = None
    for i, ln in enumerate(lines[1:], start=1):
        if ln.strip() == "---":
            end = i
            break
    if end is None:
        return None
    fm: dict = {}
    for ln in lines[1:end]:
        if ":" in ln:
            k, _, v = ln.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def validate_skill(path: Path) -> list[str]:
    """返回错误列表；空列表 = 通过。path 指向 SKILL.md。"""
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    if fm is None:
        return ["缺少合法 frontmatter（--- 包裹的 YAML）"]
    name = fm.get("name", "")
    if not NAME_RE.match(name):
        errors.append(f"name '{name}' 不合法：需小写 kebab-case")
    if name and name != path.parent.name:
        errors.append(f"name '{name}' 与目录名 '{path.parent.name}' 不一致")
    desc = fm.get("description", "")
    if not desc:
        errors.append("description 为空")
    elif len(desc) > 1024:
        errors.append(f"description 超长：{len(desc)}>1024")
    if "<" in desc or ">" in desc:
        errors.append("description 含尖括号")
    for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        ref = m.group(1)
        if ref.startswith(("http://", "https://", "mailto:")):
            continue
        if not (path.parent / ref).resolve().exists():
            errors.append(f"引用不存在: {ref}")
    return errors


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="校验 SKILL.md 的 L0 结构")
    ap.add_argument("paths", nargs="+", metavar="SKILL.md")
    args = ap.parse_args(argv)
    all_ok = True
    for p in args.paths:
        errs = validate_skill(Path(p))
        if errs:
            all_ok = False
            print(f"{p}: {len(errs)} 个错误")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"{p}: OK")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
