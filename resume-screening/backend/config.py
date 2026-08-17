"""注册表配置加载：models.yml / tools.yml / thresholds.yml。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class ConfigError(Exception):
    """配置缺失或非法。"""


@dataclass(frozen=True)
class AppConfig:
    providers: Dict[str, dict]
    default: Dict[str, str]
    fallback_chain: List[Tuple[str, str]]
    doc_loader: Dict[str, object]
    thresholds: Dict[str, float]


THRESHOLD_KEYS = ("general", "specific", "total")


def _load_yaml(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"缺少配置文件: {path}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"配置文件解析失败: {path}: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件结构非法（应为映射）: {path}")
    return data


def load_config(config_dir: Union[Path, str, None] = None) -> AppConfig:
    """加载注册表配置。config_dir 缺省用仓库 config/ 目录。"""
    base = Path(config_dir) if config_dir else CONFIG_DIR
    models = _load_yaml(base / "models.yml")
    tools = _load_yaml(base / "tools.yml")
    thresholds = _load_yaml(base / "thresholds.yml")
    missing = [k for k in THRESHOLD_KEYS if not isinstance(thresholds.get(k), (int, float))]
    if missing:
        raise ConfigError(f"thresholds.yml: 缺失或非法阈值: {missing}")

    providers = models.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ConfigError("models.yml: providers 缺失或为空")
    default = models.get("default")
    # 运行时默认模型覆盖（dashboard 切换按钮写 default_model.yml，不污染 models.yml）
    override = base / "default_model.yml"
    if override.exists():
        try:
            ov = yaml.safe_load(override.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            ov = {}
        if isinstance(ov, dict) and ov.get("provider") and ov.get("model"):
            default = ov
    if not isinstance(default, dict) or not default.get("provider") or not default.get("model"):
        raise ConfigError("models.yml: default 缺失或非法")

    # 降级链：默认模型在前，其余按 provider 顺序拼接，去重
    chain: List[Tuple[str, str]] = [(default["provider"], default["model"])]
    for pname, pcfg in providers.items():
        for m in pcfg.get("models", []):
            cand = (pname, m)
            if cand != chain[0] and cand not in chain:
                chain.append(cand)

    return AppConfig(
        providers=providers,
        default=default,
        fallback_chain=chain,
        doc_loader=tools.get("doc_loader", {}),
        thresholds=thresholds,
    )
