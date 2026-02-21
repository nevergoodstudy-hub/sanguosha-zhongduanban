"""数据驱动技能参数解析器 (P2-2)

从 data/skill_config.json 加载技能参数配置,
提供对技能属性的查询接口。与 skill_dsl.json (行为步骤) 互补,
本模块聚焦于可调参数查询。

用法:
    resolver = SkillResolver()  # 自动加载默认路径
    if resolver.can_convert("longdan", "sha", "shan"):
        ...
    cfg = resolver.get_config("ganglie")
    dmg = cfg.get("damage_amount", 1)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "data" / "skill_config.json"


class SkillResolver:
    """数据驱动的技能参数解析器。"""

    def __init__(self, config_path: str | Path | None = None) -> None:
        path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._config: dict[str, dict[str, Any]] = {}
        self._load(path)

    # ==================== 加载 ====================

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning("skill_config.json not found at %s", path)
            return
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            for key, value in raw.items():
                if not key.startswith("_") and isinstance(value, dict):
                    self._config[key] = value
            logger.info("Loaded %d skill configs", len(self._config))
        except Exception as e:
            logger.error("Failed to load skill_config.json: %s", e)

    # ==================== 查询 ====================

    def get_config(self, skill_id: str) -> dict[str, Any] | None:
        """获取技能完整配置字典。"""
        return self._config.get(skill_id)

    def get_param(self, skill_id: str, key: str, default: Any = None) -> Any:
        """获取技能的单个参数值。"""
        cfg = self._config.get(skill_id)
        if cfg is None:
            return default
        return cfg.get(key, default)

    def get_type(self, skill_id: str) -> str | None:
        """获取技能类型 (convert / trigger / passive / active)。"""
        return self.get_param(skill_id, "type")

    @property
    def skill_ids(self) -> list[str]:
        """所有已配置的技能 ID。"""
        return list(self._config.keys())

    # ==================== 转换型技能查询 ====================

    def can_convert(self, skill_id: str, from_card: str, to_card: str) -> bool:
        """检查技能是否允许将 from_card 转换为 to_card。

        Args:
            skill_id: 技能 ID
            from_card: 原始卡牌标识 (如 "sha", "red_card")
            to_card: 目标卡牌标识 (如 "shan", "sha")

        Returns:
            是否支持该转换
        """
        cfg = self._config.get(skill_id)
        if cfg is None or cfg.get("type") != "convert":
            return False

        rules = cfg.get("convert_rules", [])
        for rule in rules:
            if rule.get("from") == from_card and rule.get("to") == to_card:
                return True
            # 双向技能反向检查
            if (
                cfg.get("bidirectional")
                and rule.get("from") == to_card
                and rule.get("to") == from_card
            ):
                return True

        return False

    def get_convert_targets(self, skill_id: str, from_card: str) -> list[str]:
        """获取技能能将 from_card 转换成的所有目标。"""
        cfg = self._config.get(skill_id)
        if cfg is None or cfg.get("type") != "convert":
            return []

        targets = []
        for rule in cfg.get("convert_rules", []):
            if rule.get("from") == from_card:
                targets.append(rule["to"])
            elif cfg.get("bidirectional") and rule.get("to") == from_card:
                targets.append(rule["from"])
        return targets

    def get_filter(self, skill_id: str) -> str | None:
        """获取转换型技能的卡牌过滤条件。"""
        return self.get_param(skill_id, "filter")

    # ==================== 被动型技能查询 ====================

    def get_immune_list(self, skill_id: str) -> list[str]:
        """获取免疫的卡牌名列表 (如空城免杀/决斗)。"""
        return self.get_param(skill_id, "immune_to", [])

    def get_distance_modifier(self, skill_id: str) -> int:
        """获取距离修正值 (如马术 -1)。"""
        return self.get_param(skill_id, "distance_modifier", 0)
