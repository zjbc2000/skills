#!/usr/bin/env python3
"""plugin 结构校验：plugin.json / marketplace.json 合法性。

用法: python3 validate_plugin.py <plugin_dir>
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

PLUGIN_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+")


def validate_plugin_json(data: dict) -> list[str]:
    errors: list[str] = []
    name = data.get("name", "")
    if not PLUGIN_NAME_RE.match(name):
        errors.append(f"plugin name '{name}' 不合法：需小写 kebab-case")
    version = data.get("version", "")
    if version and not SEMVER_RE.match(version):
        errors.append(f"version '{version}' 非 SemVer")
    if not data.get("description"):
        errors.append("description 为空")
    author = data.get("author")
    if not isinstance(author, dict) or not author.get("name"):
        errors.append("author.name 缺失")
    return errors


def validate_marketplace_json(data: dict) -> list[str]:
    errors: list[str] = []
    for field in ("name", "owner", "plugins"):
        if not data.get(field):
            errors.append(f"marketplace 缺字段: {field}")
    return errors


def validate_plugin(plugin_dir: Path) -> list[str]:
    """读 .claude-plugin/plugin.json（必需）+ marketplace.json（可选）并校验。"""
    errors: list[str] = []
    plugin_file = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_file.exists():
        return [".claude-plugin/plugin.json 缺失"]
    try:
        data = json.loads(plugin_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"plugin.json 不是合法 JSON: {e}"]
    errors += validate_plugin_json(data)
    marketplace_file = plugin_dir / ".claude-plugin" / "marketplace.json"
    if marketplace_file.exists():
        try:
            mdata = json.loads(marketplace_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"marketplace.json 不是合法 JSON: {e}")
        else:
            errors += validate_marketplace_json(mdata)
    return errors


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="校验 plugin 结构")
    ap.add_argument("dirs", nargs="+", metavar="plugin_dir")
    args = ap.parse_args(argv)
    all_ok = True
    for d in args.dirs:
        errs = validate_plugin(Path(d))
        if errs:
            all_ok = False
            print(f"{d}: {len(errs)} 个错误")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"{d}: OK")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
