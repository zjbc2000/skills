"""注册表配置加载（T02）。"""
from __future__ import annotations

import pytest

from backend.config import AppConfig, ConfigError, load_config


def test_loads_real_config():
    cfg = load_config()
    assert isinstance(cfg, AppConfig)
    assert "ark_coding" in cfg.providers
    assert cfg.providers["ark_coding"]["base_url"].startswith("https://")
    assert cfg.default == {"provider": "ark_coding", "model": "deepseek-v4-flash"}
    assert cfg.fallback_chain[0] == ("ark_coding", "deepseek-v4-flash")
    assert cfg.doc_loader["primary"] == "layout_parsing"
    assert isinstance(cfg.thresholds["general"], (int, float))


def test_fallback_chain_covers_all_provider_models():
    cfg = load_config()
    names = {(p, m) for p, m in cfg.fallback_chain}
    assert ("ark_coding", "doubao-seed-2.0-lite") in names
    assert ("deepseek_official", "deepseek-v4-flash") in names
    assert ("deepseek_official", "deepseek-v4-pro") in names
    assert len(cfg.fallback_chain) == len(names)  # 无重复


def test_missing_config_dir_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_invalid_yml_raises(tmp_path):
    (tmp_path / "models.yml").write_text(": bad: :\n", encoding="utf-8")
    (tmp_path / "tools.yml").write_text("doc_loader:\n  primary: x\n", encoding="utf-8")
    (tmp_path / "thresholds.yml").write_text("general: 1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path)
