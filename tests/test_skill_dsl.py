"""
技能 DSL 解释器测试

验证:
1. DSL 定义加载
2. 解释器执行正确性
3. 纯数据驱动武将可工作
"""

import pytest

from game.engine import GameEngine
from game.skill import SkillSystem
from game.skill_dsl import SkillDsl
from game.skill_interpreter import SkillInterpreter


class TestSkillDslLoading:
    """测试 DSL 定义加载"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_dsl_registry_loaded(self, engine):
        """测试 DSL 注册表已加载"""
        ss = engine.skill_system
        assert len(ss._dsl_registry) >= 15, f"Expected >=15 DSL defs, got {len(ss._dsl_registry)}"

    def test_dsl_biyue_loaded(self, engine):
        """测试闭月 DSL 加载正确"""
        dsl = engine.skill_system.get_dsl("biyue")
        assert dsl is not None
        assert dsl.trigger == "phase_end"
        assert len(dsl.steps) == 2

    def test_dsl_jianxiong_loaded(self, engine):
        """测试奸雄 DSL 加载正确"""
        dsl = engine.skill_system.get_dsl("jianxiong")
        assert dsl is not None
        assert dsl.trigger == "after_damaged"


class TestSkillDslValidation:
    """测试 DSL 验证"""

    def test_valid_dsl(self):
        dsl = SkillDsl.from_dict({"trigger": "active", "steps": [{"draw": 1}]})
        errors = dsl.validate()
        assert errors == []

    def test_invalid_trigger(self):
        dsl = SkillDsl.from_dict({"trigger": "bogus", "steps": []})
        errors = dsl.validate()
        assert len(errors) > 0
        assert "unknown trigger" in errors[0]


class TestSkillInterpreter:
    """测试 DSL 解释器执行"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_draw_step(self, engine):
        """测试 draw 步骤"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]
        initial = len(player.hand)

        dsl = SkillDsl.from_dict({"trigger": "active", "steps": [{"draw": 2}]})
        result = interp.execute(dsl, player, "测试技能")
        assert result is True
        assert len(player.hand) == initial + 2

    def test_heal_step(self, engine):
        """测试 heal 步骤"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]
        player.hp = 1

        dsl = SkillDsl.from_dict({"trigger": "active", "steps": [{"heal": 1}]})
        result = interp.execute(dsl, player, "测试技能")
        assert result is True
        assert player.hp == 2

    def test_lose_hp_step(self, engine):
        """测试 lose_hp 步骤"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]
        old_hp = player.hp

        dsl = SkillDsl.from_dict({"trigger": "active", "steps": [{"lose_hp": 1}]})
        result = interp.execute(dsl, player, "测试技能")
        assert result is True
        assert player.hp == old_hp - 1

    def test_condition_check_hp(self, engine):
        """测试条件检查 — 体力未满"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]

        dsl = SkillDsl.from_dict(
            {"trigger": "active", "condition": [{"check": "hp_below_max"}], "steps": [{"heal": 1}]}
        )

        player.hp = player.max_hp
        result = interp.execute(dsl, player, "测试")
        assert result is False  # hp 已满，条件不满足

        player.hp = player.max_hp - 1
        result = interp.execute(dsl, player, "测试")
        assert result is True

    def test_judge_step(self, engine):
        """测试判定步骤"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]

        dsl = SkillDsl.from_dict(
            {
                "trigger": "active",
                "steps": [
                    {
                        "judge": {
                            "success_if": {"color": "red"},
                            "success": [{"draw": 1}],
                            "fail": [],
                        }
                    }
                ],
            }
        )
        initial = len(player.hand)
        result = interp.execute(dsl, player, "测试判定")
        assert result is True
        # 无论判定结果如何，技能执行成功

    def test_biyue_via_dsl(self, engine):
        """测试通过 DSL 执行闭月"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]
        initial = len(player.hand)

        dsl = engine.skill_system.get_dsl("biyue")
        assert dsl is not None
        result = interp.execute(dsl, player, "闭月")
        assert result is True
        assert len(player.hand) == initial + 1

    def test_jushou_via_dsl(self, engine):
        """测试通过 DSL 执行据守"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]
        initial = len(player.hand)
        initial_flip = getattr(player, "flipped", False)

        dsl = engine.skill_system.get_dsl("jushou")
        assert dsl is not None
        result = interp.execute(dsl, player, "据守")
        assert result is True
        assert len(player.hand) == initial + 3

    def test_kurou_via_dsl(self, engine):
        """测试通过 DSL 执行苦肉"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]
        player.hp = 3
        initial_hand = len(player.hand)

        dsl = engine.skill_system.get_dsl("kurou")
        assert dsl is not None
        result = interp.execute(dsl, player, "苦肉")
        assert result is True
        assert player.hp == 2
        assert len(player.hand) == initial_hand + 2

    def test_kurou_blocked_by_condition(self, engine):
        """测试苦肉在体力=1时被条件阻止"""
        interp = SkillInterpreter(engine)
        player = engine.players[0]
        player.hp = 1

        dsl = engine.skill_system.get_dsl("kurou")
        assert dsl is not None
        result = interp.execute(dsl, player, "苦肉")
        assert result is False  # hp_above(2) 不满足


class TestDataDrivenHero:
    """测试纯数据驱动武将"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_custom_dsl_skill(self, engine):
        """测试自定义 DSL 技能可以直接添加并执行"""
        ss = engine.skill_system

        # 动态添加一个 DSL 技能
        custom_dsl = SkillDsl.from_dict(
            {
                "trigger": "active",
                "phase": "play",
                "steps": [{"draw": 3}, {"log": "{player} 发动了自定义技能"}],
            }
        )
        ss._dsl_registry["custom_test_skill"] = custom_dsl

        player = engine.players[0]
        initial = len(player.hand)

        # 通过解释器直接执行
        result = ss._interpreter.execute(custom_dsl, player, "自定义技能")
        assert result is True
        assert len(player.hand) == initial + 3

    def test_xushu_dsl_loaded(self, engine):
        """徐庶的 DSL 技能已加载"""
        ss = engine.skill_system
        assert ss.get_dsl("tuixin") is not None
        assert ss.get_dsl("zhufu") is not None

    def test_xushu_tuixin_via_dsl(self, engine):
        """徐庶「推心」：结束阶段摸两张牌（纯 DSL）"""
        ss = engine.skill_system
        dsl = ss.get_dsl("tuixin")
        player = engine.players[0]
        initial = len(player.hand)

        result = ss._interpreter.execute(dsl, player, "推心")
        assert result is True
        assert len(player.hand) == initial + 2

    def test_xushu_zhufu_via_dsl(self, engine):
        """徐庶「祤福」：主动失去1点体力，摸三张牌（纯 DSL）"""
        ss = engine.skill_system
        dsl = ss.get_dsl("zhufu")
        player = engine.players[0]
        player.hp = 3
        initial = len(player.hand)

        result = ss._interpreter.execute(dsl, player, "祤福")
        assert result is True
        assert player.hp == 2
        assert len(player.hand) == initial + 3

    def test_xushu_zhufu_blocked_low_hp(self, engine):
        """徐庶「祤福」：体力=1时条件不满足"""
        ss = engine.skill_system
        dsl = ss.get_dsl("zhufu")
        player = engine.players[0]
        player.hp = 1

        result = ss._interpreter.execute(dsl, player, "祤福")
        assert result is False

    def test_xushu_trigger_skill_uses_dsl(self, engine):
        """徐庶技能通过 trigger_skill 路由时走 DSL 路径"""
        ss = engine.skill_system
        player = engine.players[0]
        player.hp = 3
        initial = len(player.hand)

        # trigger_skill 应当走 DSL-first 路径
        result = ss.trigger_skill("zhufu", player, engine)
        assert result is True
        assert player.hp == 2
        assert len(player.hand) == initial + 3
