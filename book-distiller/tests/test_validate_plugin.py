from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from validate_plugin import validate_plugin, validate_plugin_json, validate_marketplace_json

VALID_PLUGIN = {
    "name": "my-plugin",
    "version": "0.1.0",
    "description": "测试插件",
    "author": {"name": "edy"},
}


def _make_plugin_dir(tmp_path, plugin: dict | None = VALID_PLUGIN,
                     marketplace: dict | None = None) -> Path:
    d = tmp_path / "p"
    (d / ".claude-plugin").mkdir(parents=True)
    if plugin is not None:
        (d / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(plugin, ensure_ascii=False), encoding="utf-8")
    if marketplace is not None:
        (d / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps(marketplace, ensure_ascii=False), encoding="utf-8")
    return d


def test_valid_plugin_passes(tmp_path):
    assert validate_plugin(_make_plugin_dir(tmp_path)) == []


def test_missing_plugin_json(tmp_path):
    assert validate_plugin(_make_plugin_dir(tmp_path, plugin=None)) != []


def test_bad_plugin_name(tmp_path):
    d = _make_plugin_dir(tmp_path, {**VALID_PLUGIN, "name": "My_Plugin"})
    assert validate_plugin_json({"name": "My_Plugin"}) != []
    assert validate_plugin(d) != []


def test_missing_author(tmp_path):
    d = _make_plugin_dir(tmp_path, {"name": "my-plugin", "version": "0.1.0"})
    assert validate_plugin(d) != []


def test_bad_version(tmp_path):
    assert validate_plugin_json({**VALID_PLUGIN, "version": "0.1"}) != []


def test_marketplace_missing_fields(tmp_path):
    assert validate_marketplace_json({"name": "x"}) != []


def test_valid_marketplace_passes(tmp_path):
    mp = {"name": "mk", "owner": "edy", "plugins": [{"name": "my-plugin"}]}
    assert validate_marketplace_json(mp) == []
    assert validate_plugin(_make_plugin_dir(tmp_path, marketplace=mp)) == []


def test_invalid_json(tmp_path):
    d = tmp_path / "p"
    (d / ".claude-plugin").mkdir(parents=True)
    (d / ".claude-plugin" / "plugin.json").write_text("{not json", encoding="utf-8")
    assert validate_plugin(d) != []
