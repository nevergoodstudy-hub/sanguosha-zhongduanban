"""技能插件系统 (P3-4)

扩展 skill_dsl.json 解释器，支持从外部目录加载自定义技能。
插件文件为 JSON 格式，与 data/skill_dsl.json 同结构。

插件目录:
    plugins/skills/       — 默认插件目录
    plugins/skills/*.json — 每个 JSON 文件可包含一个或多个技能定义

用法:
    loader = SkillPluginLoader()
    loader.discover()                    # 扫描插件目录
    all_skills = loader.get_all_skills() # 合并内置 + 插件技能
    errors = loader.get_errors()         # 获取加载错误
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .skill_dsl import SkillDsl

logger = logging.getLogger(__name__)

# 默认路径
_BASE_DIR = Path(__file__).parent.parent
_BUILTIN_DSL_PATH = _BASE_DIR / "data" / "skill_dsl.json"
_PLUGIN_DIR = _BASE_DIR / "plugins" / "skills"


@dataclass(slots=True)
class PluginInfo:
    """已加载插件的元信息。"""

    name: str
    path: str
    skill_count: int
    skill_ids: list[str] = field(default_factory=list)
    version: str = "1.0"
    author: str = ""


@dataclass(slots=True)
class LoadError:
    """插件加载错误。"""

    path: str
    error: str


class SkillPluginLoader:
    """技能插件加载器。

    负责:
    - 加载内置 data/skill_dsl.json
    - 扫描 plugins/skills/ 目录下的 JSON 插件
    - 验证每个技能定义
    - 合并并提供统一的技能 DSL 字典
    """

    def __init__(
        self,
        builtin_path: str | Path | None = None,
        plugin_dir: str | Path | None = None,
    ) -> None:
        self._builtin_path = Path(builtin_path) if builtin_path else _BUILTIN_DSL_PATH
        self._plugin_dir = Path(plugin_dir) if plugin_dir else _PLUGIN_DIR
        self._builtin_skills: dict[str, dict[str, Any]] = {}
        self._plugin_skills: dict[str, dict[str, Any]] = {}
        self._plugins: list[PluginInfo] = []
        self._errors: list[LoadError] = []

    @property
    def plugins(self) -> list[PluginInfo]:
        """已加载的插件列表。"""
        return list(self._plugins)

    def load_builtin(self) -> int:
        """加载内置技能定义。

        Returns:
            加载的技能数量
        """
        if not self._builtin_path.exists():
            logger.warning("内置技能文件不存在: %s", self._builtin_path)
            return 0
        try:
            with open(self._builtin_path, encoding="utf-8") as f:
                data = json.load(f)
            # 过滤 _comment 等元键
            self._builtin_skills = {
                k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)
            }
            return len(self._builtin_skills)
        except (json.JSONDecodeError, OSError) as e:
            self._errors.append(LoadError(str(self._builtin_path), str(e)))
            return 0

    def discover(self) -> int:
        """扫描插件目录并加载所有 JSON 插件。

        Returns:
            新加载的插件技能总数
        """
        self._plugin_skills.clear()
        self._plugins.clear()
        self._errors.clear()

        # 先加载内置
        self.load_builtin()

        if not self._plugin_dir.exists():
            return 0

        total = 0
        for json_file in sorted(self._plugin_dir.glob("*.json")):
            count = self._load_plugin_file(json_file)
            total += count

        logger.info(
            "插件加载完成: %d 个插件, %d 个技能, %d 个错误",
            len(self._plugins),
            total,
            len(self._errors),
        )
        return total

    def _load_plugin_file(self, path: Path) -> int:
        """加载单个插件文件。"""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self._errors.append(LoadError(str(path), str(e)))
            return 0

        if not isinstance(data, dict):
            self._errors.append(LoadError(str(path), "顶层必须是 JSON 对象"))
            return 0

        # 提取元信息
        meta = data.get("_meta", {})
        plugin_name = meta.get("name", path.stem)
        plugin_version = meta.get("version", "1.0")
        plugin_author = meta.get("author", "")

        # 提取技能
        skill_ids: list[str] = []
        for skill_id, skill_def in data.items():
            if skill_id.startswith("_") or not isinstance(skill_def, dict):
                continue

            # 验证
            errors = self._validate_skill(skill_id, skill_def)
            if errors:
                for err in errors:
                    self._errors.append(LoadError(str(path), f"{skill_id}: {err}"))
                continue

            # 冲突检测
            if skill_id in self._builtin_skills:
                logger.warning(
                    "插件技能 '%s' (%s) 与内置技能冲突，跳过",
                    skill_id,
                    path.name,
                )
                self._errors.append(
                    LoadError(
                        str(path),
                        f"{skill_id}: 与内置技能冲突",
                    )
                )
                continue

            if skill_id in self._plugin_skills:
                logger.warning(
                    "插件技能 '%s' (%s) 与其他插件冲突，覆盖",
                    skill_id,
                    path.name,
                )

            self._plugin_skills[skill_id] = skill_def
            skill_ids.append(skill_id)

        if skill_ids:
            self._plugins.append(
                PluginInfo(
                    name=plugin_name,
                    path=str(path),
                    skill_count=len(skill_ids),
                    skill_ids=skill_ids,
                    version=plugin_version,
                    author=plugin_author,
                )
            )

        return len(skill_ids)

    def _validate_skill(self, skill_id: str, skill_def: dict) -> list[str]:
        """验证技能定义的基本合法性。"""
        errors: list[str] = []
        try:
            dsl = SkillDsl.from_dict(skill_def)
            dsl_errors = dsl.validate()
            errors.extend(dsl_errors)
        except Exception as e:
            errors.append(f"解析失败: {e}")

        if "steps" not in skill_def and "trigger" not in skill_def:
            errors.append("缺少 trigger 或 steps 字段")

        return errors

    def get_all_skills(self) -> dict[str, dict[str, Any]]:
        """获取合并后的所有技能（内置 + 插件）。"""
        merged = dict(self._builtin_skills)
        merged.update(self._plugin_skills)
        return merged

    def get_builtin_skills(self) -> dict[str, dict[str, Any]]:
        """仅内置技能。"""
        return dict(self._builtin_skills)

    def get_plugin_skills(self) -> dict[str, dict[str, Any]]:
        """仅插件技能。"""
        return dict(self._plugin_skills)

    def get_skill_dsl(self, skill_id: str) -> SkillDsl | None:
        """按 ID 获取解析后的 SkillDsl 对象。"""
        all_skills = self.get_all_skills()
        raw = all_skills.get(skill_id)
        if raw is None:
            return None
        return SkillDsl.from_dict(raw)

    def get_errors(self) -> list[LoadError]:
        """获取所有加载错误。"""
        return list(self._errors)

    def is_plugin_skill(self, skill_id: str) -> bool:
        """检查技能是否来自插件。"""
        return skill_id in self._plugin_skills
