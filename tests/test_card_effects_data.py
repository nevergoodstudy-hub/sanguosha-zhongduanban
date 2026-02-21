"""
数据驱动卡牌效果测试（M2-T04）
"""

from game.effects.data_driven import DataDrivenCardEffect, load_card_effects_config
from game.effects.registry import create_default_registry


class TestCardEffectsConfigLoading:
    """测试配置加载"""

    def test_config_loaded(self):
        """data/card_effects.json 可正常加载"""
        configs = load_card_effects_config()
        assert len(configs) >= 3

    def test_tao_config(self):
        configs = load_card_effects_config()
        assert "桃" in configs
        assert configs["桃"]["display_name"] == "桃"

    def test_wuzhong_config(self):
        configs = load_card_effects_config()
        assert "无中生有" in configs
        assert configs["无中生有"]["wuxie"] is True

    def test_taoyuan_config(self):
        configs = load_card_effects_config()
        assert "桃园结义" in configs
        assert configs["桃园结义"]["scope"] == "all_alive_from_player"


class TestDataDrivenCardEffect:
    """测试 DataDrivenCardEffect 类"""

    def test_needs_target(self):
        effect = DataDrivenCardEffect("test", {"needs_target": True})
        assert effect.needs_target is True

    def test_no_target(self):
        effect = DataDrivenCardEffect("test", {"needs_target": False})
        assert effect.needs_target is False

    def test_tao_can_use_hp_full(self):
        """桃：体力满时不可用"""
        config = load_card_effects_config()["桃"]
        effect = DataDrivenCardEffect("桃", config)

        class FakePlayer:
            hp = 4
            max_hp = 4

        ok, msg = effect.can_use(None, FakePlayer(), None, [])
        assert ok is False
        assert "体力已满" in msg

    def test_tao_can_use_hp_not_full(self):
        """桃：体力未满时可用"""
        config = load_card_effects_config()["桃"]
        effect = DataDrivenCardEffect("桃", config)

        class FakePlayer:
            hp = 2
            max_hp = 4

        ok, msg = effect.can_use(None, FakePlayer(), None, [])
        assert ok is True


class TestRegistryDataDriven:
    """测试注册表的数据驱动加载"""

    def test_registry_loads_data_driven(self):
        registry = create_default_registry()
        # JSON key 现在是中文（"桃"/"无中生有"/"桃园结义"），与手写 key 一致，
        # 所以 load_data_driven 跳过所有已注册的卡牌，数据驱动数量为 0
        assert registry._data_driven_count == 0

    def test_hand_written_not_overridden(self):
        """手写效果不被数据驱动覆盖"""
        from game.card import CardName
        from game.effects.basic import TaoEffect

        registry = create_default_registry()
        # 手写注册用 CardName.TAO="桃"，JSON 也用 "桃"
        # load_data_driven 检测到已注册，跳过，手写效果仍然完好
        tao = registry.get(CardName.TAO)
        assert isinstance(tao, TaoEffect)

    def test_data_driven_effect_accessible(self):
        """JSON 键名与手写一致时，手写效果优先"""
        from game.effects.basic import TaoEffect

        registry = create_default_registry()
        # "桃" 已有手写 TaoEffect，数据驱动不覆盖
        effect = registry.get("桃")
        assert isinstance(effect, TaoEffect)

    def test_new_card_via_data_only(self):
        """全新卡牌可仅通过数据配置添加"""
        registry = create_default_registry()

        # 动态添加一个全新的卡牌效果
        custom = DataDrivenCardEffect(
            "custom_heal_card",
            {
                "display_name": "测试回血卡",
                "needs_target": False,
                "steps": [{"heal": {"target": "self", "amount": 2}}],
                "discard_after": True,
            },
        )
        registry.register("custom_heal_card", custom)

        assert registry.has("custom_heal_card")
        assert registry.get("custom_heal_card").needs_target is False
