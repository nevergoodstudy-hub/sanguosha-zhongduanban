"""技能插件系统测试 (P3-4)"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from game.skill_plugin import LoadError, PluginInfo, SkillPluginLoader


# ─── 固定的有效插件 JSON ───

VALID_PLUGIN = {
    "_meta": {"name": "test_pack", "version": "2.0", "author": "tester"},
    "custom_draw3": {
        "trigger": "phase_end",
        "steps": [{"draw": 3}, {"log": "{player} 发动【{skill}】"}],
    },
    "custom_heal": {
        "trigger": "active",
        "phase": "play",
        "limit": 1,
        "condition": [{"check": "hp_below_max"}],
        "steps": [{"heal": {"target": "self", "amount": 1}}],
    },
}

INVALID_PLUGIN = {
    "bad_skill": {
        "trigger": "nonexistent_trigger",
        "steps": [{"unknown_op": 1}],
    },
}

CONFLICT_PLUGIN = {
    "_meta": {"name": "conflict_pack"},
    "biyue": {  # 与内置 biyue 冲突
        "trigger": "phase_end",
        "steps": [{"draw": 5}],
    },
}


@pytest.fixture
def plugin_env():
    """创建临时的内置文件和插件目录。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        builtin_path = base / "builtin.json"
        plugin_dir = base / "plugins"
        plugin_dir.mkdir()

        # 写入精简的内置技能
        builtin = {
            "_comment": "test builtin",
            "biyue": {
                "trigger": "phase_end",
                "steps": [{"draw": 1}],
            },
            "kurou": {
                "trigger": "active",
                "phase": "play",
                "steps": [{"lose_hp": 1}, {"draw": 2}],
            },
        }
        builtin_path.write_text(json.dumps(builtin, ensure_ascii=False), encoding="utf-8")

        yield base, builtin_path, plugin_dir


class TestPluginLoaderBasic:
    """基础加载测试。"""

    def test_load_builtin(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        count = loader.load_builtin()
        assert count == 2
        assert "biyue" in loader.get_builtin_skills()
        assert "kurou" in loader.get_builtin_skills()

    def test_load_builtin_missing_file(self, plugin_env):
        base, _, plugin_dir = plugin_env
        loader = SkillPluginLoader(base / "nonexistent.json", plugin_dir)
        count = loader.load_builtin()
        assert count == 0

    def test_discover_no_plugins(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        count = loader.discover()
        assert count == 0
        assert len(loader.get_all_skills()) == 2  # only builtin

    def test_discover_nonexistent_dir(self, plugin_env):
        base, builtin_path, _ = plugin_env
        loader = SkillPluginLoader(builtin_path, base / "no_such_dir")
        count = loader.discover()
        assert count == 0


class TestPluginLoading:
    """插件文件加载测试。"""

    def test_load_valid_plugin(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        (plugin_dir / "pack1.json").write_text(
            json.dumps(VALID_PLUGIN, ensure_ascii=False), encoding="utf-8"
        )
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        count = loader.discover()
        assert count == 2
        assert "custom_draw3" in loader.get_plugin_skills()
        assert "custom_heal" in loader.get_plugin_skills()
        assert loader.is_plugin_skill("custom_draw3")
        assert not loader.is_plugin_skill("biyue")

    def test_plugin_metadata(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        (plugin_dir / "pack1.json").write_text(
            json.dumps(VALID_PLUGIN, ensure_ascii=False), encoding="utf-8"
        )
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        loader.discover()
        assert len(loader.plugins) == 1
        info = loader.plugins[0]
        assert info.name == "test_pack"
        assert info.version == "2.0"
        assert info.author == "tester"
        assert info.skill_count == 2

    def test_merge_builtin_and_plugin(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        (plugin_dir / "pack1.json").write_text(
            json.dumps(VALID_PLUGIN, ensure_ascii=False), encoding="utf-8"
        )
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        loader.discover()
        all_skills = loader.get_all_skills()
        assert len(all_skills) == 4  # 2 builtin + 2 plugin
        assert "biyue" in all_skills
        assert "custom_draw3" in all_skills

    def test_get_skill_dsl(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        (plugin_dir / "pack1.json").write_text(
            json.dumps(VALID_PLUGIN, ensure_ascii=False), encoding="utf-8"
        )
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        loader.discover()
        dsl = loader.get_skill_dsl("custom_draw3")
        assert dsl is not None
        assert dsl.trigger == "phase_end"
        assert len(dsl.steps) == 2
        assert loader.get_skill_dsl("nonexistent") is None


class TestPluginValidation:
    """验证和错误处理测试。"""

    def test_invalid_plugin_triggers_error(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        (plugin_dir / "bad.json").write_text(
            json.dumps(INVALID_PLUGIN, ensure_ascii=False), encoding="utf-8"
        )
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        loader.discover()
        assert len(loader.get_errors()) > 0
        assert "bad_skill" not in loader.get_plugin_skills()

    def test_conflict_with_builtin(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        (plugin_dir / "conflict.json").write_text(
            json.dumps(CONFLICT_PLUGIN, ensure_ascii=False), encoding="utf-8"
        )
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        loader.discover()
        errors = loader.get_errors()
        conflict_errors = [e for e in errors if "冲突" in e.error]
        assert len(conflict_errors) == 1
        # 内置 biyue 保持不变
        assert loader.get_all_skills()["biyue"]["steps"][0]["draw"] == 1

    def test_corrupted_json(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        (plugin_dir / "broken.json").write_text("not json{", encoding="utf-8")
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        loader.discover()
        assert len(loader.get_errors()) > 0

    def test_non_dict_json(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        (plugin_dir / "list.json").write_text("[1,2,3]", encoding="utf-8")
        loader = SkillPluginLoader(builtin_path, plugin_dir)
        loader.discover()
        errors = loader.get_errors()
        assert any("JSON 对象" in e.error for e in errors)


class TestMultiplePlugins:
    """多插件交互测试。"""

    def test_multiple_plugin_files(self, plugin_env):
        _, builtin_path, plugin_dir = plugin_env
        pack1 = {"skill_a": {"trigger": "phase_end", "steps": [{"draw": 1}]}}
        pack2 = {"skill_b": {"trigger": "active", "phase": "play", "steps": [{"draw": 2}]}}
        (plugin_dir / "a_pack.json").write_text(json.dumps(pack1), encoding="utf-8")
        (plugin_dir / "b_pack.json").write_text(json.dumps(pack2), encoding="utf-8")

        loader = SkillPluginLoader(builtin_path, plugin_dir)
        count = loader.discover()
        assert count == 2
        assert len(loader.plugins) == 2
        assert "skill_a" in loader.get_all_skills()
        assert "skill_b" in loader.get_all_skills()

    def test_real_builtin_file(self):
        """使用真实的 data/skill_dsl.json 加载。"""
        loader = SkillPluginLoader()
        count = loader.load_builtin()
        assert count >= 15  # 至少 15 个内置技能
        assert "biyue" in loader.get_builtin_skills()
        assert "kurou" in loader.get_builtin_skills()
