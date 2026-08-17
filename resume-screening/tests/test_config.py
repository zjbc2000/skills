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


def test_threshold_env_override(monkeypatch, tmp_path):
    """THRESH_GENERAL/SPECIFIC/TOTAL 环境变量覆盖 thresholds.yml。"""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "models.yml").write_text(
        "providers:\n  p:\n    base_url: http://x\n    api_key_env: K\n    models: [m]\n"
        "default:\n  provider: p\n  model: m\n", encoding="utf-8")
    (cfg_dir / "tools.yml").write_text("doc_loader:\n  primary: local_pymupdf\n", encoding="utf-8")
    (cfg_dir / "thresholds.yml").write_text("general: 40\nspecific: 20\ntotal: 45\n", encoding="utf-8")

    monkeypatch.setenv("THRESH_GENERAL", "55")
    monkeypatch.setenv("THRESH_TOTAL", "70")
    cfg = load_config(cfg_dir)
    assert cfg.thresholds == {"general": 55, "specific": 20, "total": 70}

    monkeypatch.setenv("THRESH_GENERAL", "abc")
    with pytest.raises(ConfigError):
        load_config(cfg_dir)
