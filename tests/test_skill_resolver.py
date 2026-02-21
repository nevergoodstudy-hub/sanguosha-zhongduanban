"""Skill resolver tests (P2-2)."""

import pytest

from game.skill_resolver import SkillResolver


class TestSkillResolver:
    """Test SkillResolver data-driven skill config."""

    def setup_method(self):
        self.resolver = SkillResolver()

    def test_loads_skills(self):
        assert len(self.resolver.skill_ids) > 0

    def test_get_config_existing(self):
        cfg = self.resolver.get_config("longdan")
        assert cfg is not None
        assert cfg["type"] == "convert"

    def test_get_config_missing(self):
        assert self.resolver.get_config("nonexistent") is None

    def test_get_param(self):
        assert self.resolver.get_param("ganglie", "damage_amount") == 1
        assert self.resolver.get_param("ganglie", "nonexistent", 42) == 42

    def test_get_type(self):
        assert self.resolver.get_type("longdan") == "convert"
        assert self.resolver.get_type("paoxiao") == "passive"
        assert self.resolver.get_type("rende") == "active"
        assert self.resolver.get_type("jianxiong") == "trigger"

    # ========== Convert skills ==========

    def test_can_convert_longdan_sha_to_shan(self):
        assert self.resolver.can_convert("longdan", "sha", "shan") is True

    def test_can_convert_longdan_shan_to_sha(self):
        """Longdan is bidirectional."""
        assert self.resolver.can_convert("longdan", "shan", "sha") is True

    def test_can_convert_wusheng(self):
        assert self.resolver.can_convert("wusheng", "red_card", "sha") is True
        assert self.resolver.can_convert("wusheng", "sha", "red_card") is False

    def test_can_convert_qixi(self):
        assert self.resolver.can_convert("qixi", "black_card", "guohe") is True

    def test_can_convert_invalid_skill(self):
        assert self.resolver.can_convert("paoxiao", "sha", "shan") is False

    def test_get_convert_targets(self):
        targets = self.resolver.get_convert_targets("longdan", "sha")
        assert "shan" in targets

    def test_get_convert_targets_bidirectional(self):
        targets = self.resolver.get_convert_targets("longdan", "shan")
        assert "sha" in targets

    def test_get_convert_targets_empty(self):
        assert self.resolver.get_convert_targets("paoxiao", "sha") == []

    def test_get_filter(self):
        assert self.resolver.get_filter("wusheng") == "color_red"
        assert self.resolver.get_filter("qixi") == "color_black"
        assert self.resolver.get_filter("longdan") is None

    # ========== Passive skills ==========

    def test_get_immune_list(self):
        immune = self.resolver.get_immune_list("kongcheng")
        assert "sha" in immune
        assert "juedou" in immune

    def test_get_immune_list_empty(self):
        assert self.resolver.get_immune_list("paoxiao") == []

    def test_get_distance_modifier(self):
        assert self.resolver.get_distance_modifier("mashu") == -1
        assert self.resolver.get_distance_modifier("longdan") == 0

    # ========== Active/trigger skills ==========

    def test_trigger_skill_params(self):
        assert self.resolver.get_param("yingzi", "extra_draw_count") == 1
        assert self.resolver.get_param("fanjian", "limit_per_turn") == 1

    def test_kurou_params(self):
        assert self.resolver.get_param("kurou", "hp_cost") == 1
        assert self.resolver.get_param("kurou", "draw_count") == 2

    def test_wushuang_params(self):
        assert self.resolver.get_param("wushuang", "sha_shan_required") == 2
        assert self.resolver.get_param("wushuang", "juedou_sha_required") == 2

    # ========== Edge cases ==========

    def test_comments_excluded(self):
        """_comment keys should not appear as skill ids."""
        assert "_comment" not in self.resolver.skill_ids

    def test_missing_file(self):
        """Missing file should not crash."""
        resolver = SkillResolver("/nonexistent/path.json")
        assert len(resolver.skill_ids) == 0
