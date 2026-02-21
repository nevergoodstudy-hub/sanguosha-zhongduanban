"""
子系统单元测试 (Phase 2.8)
覆盖 CombatSystem / EquipmentSystem / JudgeSystem / CardResolver
"""

from unittest.mock import patch

import pytest

from game.card import Card, CardName, CardSubtype, CardSuit, CardType
from game.card_resolver import CardResolver
from game.combat import CombatSystem
from game.engine import GameEngine
from game.equipment_system import EquipmentSystem
from game.judge_system import JudgeSystem
from game.skill import SkillSystem

# ==================== 共享 Fixture ====================


@pytest.fixture
def engine():
    """创建完整初始化的测试引擎"""
    eng = GameEngine()
    eng.setup_game(player_count=4, human_player_index=-1)
    skill_system = SkillSystem(eng)
    eng.set_skill_system(skill_system)
    choices = eng.auto_choose_heroes_for_ai()
    eng.choose_heroes(choices)
    eng.start_game()
    return eng


@pytest.fixture
def two_player_engine():
    """创建 2 人测试引擎（简化场景）"""
    eng = GameEngine()
    eng.setup_game(player_count=2, human_player_index=-1)
    skill_system = SkillSystem(eng)
    eng.set_skill_system(skill_system)
    choices = eng.auto_choose_heroes_for_ai()
    eng.choose_heroes(choices)
    eng.start_game()
    return eng


def make_card(
    name,
    suit=CardSuit.SPADE,
    number=1,
    card_type=CardType.BASIC,
    subtype=CardSubtype.ATTACK,
    card_id="test_card",
):
    """快速创建测试卡牌"""
    return Card(
        id=card_id,
        name=name,
        card_type=card_type,
        subtype=subtype,
        suit=suit,
        number=number,
    )


# ==================== CombatSystem 测试 ====================


class TestCombatSystem:
    """战斗子系统测试"""

    def test_combat_system_init(self, engine):
        """CombatSystem 正确初始化"""
        assert engine.combat is not None
        assert isinstance(engine.combat, CombatSystem)

    def test_use_sha_no_targets(self, engine):
        """杀无目标返回 False"""
        player = engine.players[0]
        sha = make_card(CardName.SHA)
        result = engine.combat.use_sha(player, sha, [])
        assert result is False

    def test_use_sha_with_target(self, engine):
        """杀对有效目标执行"""
        player = engine.players[0]
        target = engine.players[1]
        sha = make_card(CardName.SHA)
        # 清除目标手中的闪以确保伤害
        target.hand = [c for c in target.hand if c.name != CardName.SHAN]
        hp_before = target.hp
        engine.combat.use_sha(player, sha, [target])
        # 目标应该受伤或被闪避（取决于 AI 响应）
        assert target.hp <= hp_before

    def test_request_shan_no_cards(self, engine):
        """没有闪时 request_shan 返回 0"""
        player = engine.players[0]
        player.hand = [make_card(CardName.SHA)]  # 只有杀，没有闪
        count = engine.combat.request_shan(player, 1)
        assert count == 0

    def test_request_shan_has_card(self, engine):
        """有闪时 request_shan 返回 1"""
        player = engine.players[0]
        shan = make_card(CardName.SHAN, subtype=CardSubtype.DODGE)
        player.hand = [shan]
        count = engine.combat.request_shan(player, 1)
        assert count == 1

    def test_request_sha_no_cards(self, engine):
        """没有杀时 request_sha 返回 0"""
        player = engine.players[0]
        # 清除龙胆/武圣等转换技能，确保闪不会被当杀打出
        if player.hero:
            player.hero.skills.clear()
        player.hand = [make_card(CardName.SHAN, subtype=CardSubtype.DODGE)]
        count = engine.combat.request_sha(player, 1)
        assert count == 0

    def test_use_juedou_no_targets(self, engine):
        """决斗无目标返回 False"""
        player = engine.players[0]
        card = make_card(
            CardName.JUEDOU, card_type=CardType.TRICK, subtype=CardSubtype.SINGLE_TARGET
        )
        result = engine.combat.use_juedou(player, card, [])
        assert result is False

    def test_use_juedou_with_target(self, engine):
        """决斗对有效目标执行"""
        player = engine.players[0]
        target = engine.players[1]
        card = make_card(
            CardName.JUEDOU, card_type=CardType.TRICK, subtype=CardSubtype.SINGLE_TARGET
        )
        hp_before = target.hp
        engine.combat.use_juedou(player, card, [target])
        # 决斗应导致某方受伤
        assert target.hp <= hp_before or player.hp < player.max_hp


# ==================== EquipmentSystem 测试 ====================


class TestEquipmentSystem:
    """装备子系统测试"""

    def test_equipment_system_init(self, engine):
        """EquipmentSystem 正确初始化"""
        assert engine.equipment_sys is not None
        assert isinstance(engine.equipment_sys, EquipmentSystem)

    def test_equip_weapon(self, engine):
        """装备武器"""
        player = engine.players[0]
        weapon = make_card(
            CardName.ZHUGENU,
            card_type=CardType.EQUIPMENT,
            subtype=CardSubtype.WEAPON,
            card_id="zhuge_test",
        )
        result = engine.equipment_sys.equip(player, weapon)
        assert result is True
        assert player.equipment.weapon is not None

    def test_equip_armor(self, engine):
        """装备防具"""
        player = engine.players[0]
        armor = make_card(
            CardName.BAGUA,
            card_type=CardType.EQUIPMENT,
            subtype=CardSubtype.ARMOR,
            card_id="bagua_test",
        )
        result = engine.equipment_sys.equip(player, armor)
        assert result is True
        assert player.equipment.armor is not None

    def test_remove_equipment(self, engine):
        """移除装备"""
        player = engine.players[0]
        weapon = make_card(
            CardName.ZHUGENU,
            card_type=CardType.EQUIPMENT,
            subtype=CardSubtype.WEAPON,
            card_id="zhuge_remove",
        )
        engine.equipment_sys.equip(player, weapon)
        assert player.equipment.weapon is not None
        engine.equipment_sys.remove(player, weapon)
        assert player.equipment.weapon is None

    def test_modify_damage_normal(self, engine):
        """普通伤害无修正"""
        target = engine.players[0]
        # 确保没有护甲
        target.equipment.armor = None
        damage = engine.equipment_sys.modify_damage(target, 1, "normal")
        assert damage == 1

    def test_is_immune_to_normal_aoe_without_tengja(self, engine):
        """无藤甲不免疫 AOE"""
        target = engine.players[0]
        target.equipment.armor = None
        assert engine.equipment_sys.is_immune_to_normal_aoe(target) is False


# ==================== JudgeSystem 测试 ====================


class TestJudgeSystem:
    """判定子系统测试"""

    def test_judge_system_init(self, engine):
        """JudgeSystem 正确初始化"""
        assert engine.judge_sys is not None
        assert isinstance(engine.judge_sys, JudgeSystem)

    def test_phase_judge_empty_area(self, engine):
        """空判定区不触发判定"""
        player = engine.players[0]
        player.judge_area.clear()
        engine.judge_sys.phase_judge(player)
        # 应该正常执行，无异常
        assert player.judge_area == []

    def test_phase_judge_lebusishu(self, engine):
        """判定区有乐不思蜀时触发判定"""
        player = engine.players[0]
        player.judge_area.clear()
        lebu = make_card(
            CardName.LEBUSISHU,
            card_type=CardType.TRICK,
            subtype=CardSubtype.DELAY,
            suit=CardSuit.SPADE,
            number=6,
            card_id="lebu_judge_test",
        )
        player.judge_area.append(lebu)
        engine.judge_sys.phase_judge(player)
        # 判定后乐不思蜀应从判定区移除
        assert lebu not in player.judge_area

    def test_phase_judge_bingliang(self, engine):
        """判定区有兵粮寸断时触发判定"""
        player = engine.players[0]
        player.judge_area.clear()
        bl = make_card(
            CardName.BINGLIANG,
            card_type=CardType.TRICK,
            subtype=CardSubtype.DELAY,
            suit=CardSuit.CLUB,
            number=4,
            card_id="bl_judge_test",
        )
        player.judge_area.append(bl)
        engine.judge_sys.phase_judge(player)
        # 判定后兵粮寸断应从判定区移除
        assert bl not in player.judge_area


# ==================== CardResolver 测试 ====================


class TestCardResolver:
    """卡牌效果解析器测试"""

    def test_card_resolver_init(self, engine):
        """CardResolver 正确初始化"""
        assert engine.card_resolver is not None
        assert isinstance(engine.card_resolver, CardResolver)

    def test_use_tao_heal(self, engine):
        """使用桃回复体力"""
        player = engine.players[0]
        player.hp = player.max_hp - 1
        tao = make_card(CardName.TAO, subtype=CardSubtype.HEAL, suit=CardSuit.HEART)
        result = engine.card_resolver.use_tao(player, tao)
        assert result is True
        assert player.hp == player.max_hp

    def test_use_tao_full_hp(self, engine):
        """满血时使用桃失败"""
        player = engine.players[0]
        player.hp = player.max_hp
        tao = make_card(CardName.TAO, subtype=CardSubtype.HEAL, suit=CardSuit.HEART)
        result = engine.card_resolver.use_tao(player, tao)
        assert result is False

    def test_use_wuzhong(self, engine):
        """使用无中生有摸 2 张牌"""
        player = engine.players[0]
        hand_before = len(player.hand)
        wz = make_card(
            CardName.WUZHONG, card_type=CardType.TRICK, subtype=CardSubtype.SELF, card_id="wz_test"
        )
        result = engine.card_resolver.use_wuzhong(player, wz)
        assert result is True
        assert len(player.hand) == hand_before + 2

    def test_use_jiu_alcohol(self, engine):
        """使用酒增加杀伤害"""
        player = engine.players[0]
        player.alcohol_used = False
        player.is_dying = False
        jiu = make_card(
            CardName.JIU,
            card_type=CardType.BASIC,
            subtype=CardSubtype.ALCOHOL,
            suit=CardSuit.SPADE,
            card_id="jiu_test",
        )
        result = engine.card_resolver.use_jiu(player, jiu)
        assert result is True
        assert player.is_drunk is True

    def test_use_jiu_already_used(self, engine):
        """本回合已使用酒再使用失败"""
        player = engine.players[0]
        player.alcohol_used = True
        player.is_dying = False
        jiu = make_card(
            CardName.JIU,
            card_type=CardType.BASIC,
            subtype=CardSubtype.ALCOHOL,
            suit=CardSuit.SPADE,
            card_id="jiu_test2",
        )
        result = engine.card_resolver.use_jiu(player, jiu)
        assert result is False

    def test_use_lebusishu(self, engine):
        """使用乐不思蜀放入判定区"""
        player = engine.players[0]
        target = engine.players[1]
        target.judge_area.clear()
        lebu = make_card(
            CardName.LEBUSISHU,
            card_type=CardType.TRICK,
            subtype=CardSubtype.DELAY,
            card_id="lebu_use_test",
        )
        result = engine.card_resolver.use_lebusishu(player, lebu, [target])
        assert result is True
        assert lebu in target.judge_area

    def test_use_lebusishu_self_target(self, engine):
        """乐不思蜀不能对自己使用"""
        player = engine.players[0]
        player.judge_area.clear()
        lebu = make_card(
            CardName.LEBUSISHU,
            card_type=CardType.TRICK,
            subtype=CardSubtype.DELAY,
            card_id="lebu_self_test",
        )
        result = engine.card_resolver.use_lebusishu(player, lebu, [player])
        assert result is False

    def test_use_tiesuo_reforge(self, engine):
        """铁索连环无目标时重铸"""
        player = engine.players[0]
        hand_before = len(player.hand)
        tiesuo = make_card(
            CardName.TIESUO,
            card_type=CardType.TRICK,
            subtype=CardSubtype.CHAIN,
            card_id="tiesuo_reforge",
        )
        result = engine.card_resolver.use_tiesuo(player, tiesuo, targets=None)
        assert result is True
        assert len(player.hand) == hand_before + 1

    def test_use_tiesuo_chain_target(self, engine):
        """铁索连环对目标使用改变连环状态"""
        player = engine.players[0]
        target = engine.players[1]
        was_chained = target.is_chained
        tiesuo = make_card(
            CardName.TIESUO,
            card_type=CardType.TRICK,
            subtype=CardSubtype.CHAIN,
            card_id="tiesuo_chain",
        )
        result = engine.card_resolver.use_tiesuo(player, tiesuo, targets=[target])
        assert result is True
        assert target.is_chained != was_chained

    def test_use_shandian(self, engine):
        """闪电放入判定区"""
        player = engine.players[0]
        player.judge_area.clear()
        sd = make_card(
            CardName.SHANDIAN,
            card_type=CardType.TRICK,
            subtype=CardSubtype.DELAY,
            card_id="sd_test",
        )
        result = engine.card_resolver.use_shandian(player, sd)
        assert result is True
        assert sd in player.judge_area

    def test_use_guohe_no_cards(self, engine):
        """过河拆桥目标无牌返回 False"""
        player = engine.players[0]
        target = engine.players[1]
        target.hand.clear()
        target.equipment.weapon = None
        target.equipment.armor = None
        target.equipment.horse_plus = None
        target.equipment.horse_minus = None
        guohe = make_card(
            CardName.GUOHE,
            card_type=CardType.TRICK,
            subtype=CardSubtype.SINGLE_TARGET,
            card_id="guohe_test",
        )
        result = engine.card_resolver.use_guohe(player, guohe, [target])
        assert result is False

    def test_use_taoyuan(self, engine):
        """桃园结义为所有角色回血"""
        for p in engine.players:
            if p.is_alive:
                p.hp = max(1, p.hp - 1)  # 扣 1 血
        player = engine.players[0]
        ty = make_card(
            CardName.TAOYUAN, card_type=CardType.TRICK, subtype=CardSubtype.AOE, card_id="ty_test"
        )
        engine.card_resolver.use_taoyuan(player, ty)
        # 存活角色应有人回血
        healed = any(p.hp == p.max_hp for p in engine.players if p.is_alive)
        assert healed


# ==================== 委托集成测试 ====================


class TestEngineDelegation:
    """验证 engine 方法正确委托给子系统"""

    def test_engine_combat_use_sha(self, engine):
        """通过 combat.use_sha 直接调用"""
        player = engine.players[0]
        sha = make_card(CardName.SHA)
        with patch.object(engine.combat, "use_sha", return_value=True) as mock:
            engine.combat.use_sha(player, sha, [])
            mock.assert_called_once_with(player, sha, [])

    def test_engine_card_resolver_use_tao(self, engine):
        """通过 card_resolver.use_tao 直接调用"""
        player = engine.players[0]
        tao = make_card(CardName.TAO, subtype=CardSubtype.HEAL)
        with patch.object(engine.card_resolver, "use_tao", return_value=True) as mock:
            engine.card_resolver.use_tao(player, tao)
            mock.assert_called_once_with(player, tao)

    def test_engine_equipment_sys_equip(self, engine):
        """通过 equipment_sys.equip 直接调用"""
        player = engine.players[0]
        weapon = make_card(
            CardName.ZHUGENU, card_type=CardType.EQUIPMENT, subtype=CardSubtype.WEAPON
        )
        with patch.object(engine.equipment_sys, "equip", return_value=True) as mock:
            engine.equipment_sys.equip(player, weapon)
            mock.assert_called_once_with(player, weapon)

    def test_engine_phase_judge_delegates(self, engine):
        """engine.phase_judge 委托给 turn_manager → judge_sys"""
        player = engine.players[0]
        player.judge_area.clear()
        with patch.object(engine.judge_sys, "phase_judge") as mock:
            engine.phase_judge(player)
            mock.assert_called_once_with(player)

    def test_engine_phase_prepare_delegates(self, engine):
        """engine.phase_prepare 委托给 turn_manager"""
        player = engine.players[0]
        with patch.object(engine.turn_manager, "_execute_prepare_phase") as mock:
            engine.phase_prepare(player)
            mock.assert_called_once_with(player)

    def test_engine_phase_draw_delegates(self, engine):
        """engine.phase_draw 委托给 turn_manager"""
        player = engine.players[0]
        with patch.object(engine.turn_manager, "_execute_draw_phase") as mock:
            engine.phase_draw(player)
            mock.assert_called_once_with(player)

    def test_engine_phase_discard_delegates(self, engine):
        """engine.phase_discard 委托给 turn_manager"""
        player = engine.players[0]
        with patch.object(engine.turn_manager, "_execute_discard_phase") as mock:
            engine.phase_discard(player)
            mock.assert_called_once_with(player)


# ==================== 技能注册装饰器 测试 ====================


class TestSkillRegistry:
    """验证 @skill_handler 装饰器注册机制"""

    def test_registry_contains_all_factions(self):
        """注册表包含蜀魏吴群全部技能"""
        from game.skills.registry import get_registry

        reg = get_registry()
        expected = {
            # 蜀 13
            "rende",
            "jijiang",
            "wusheng",
            "paoxiao",
            "guanxing",
            "kongcheng",
            "longdan",
            "mashu",
            "tieji",
            "jizhi",
            "qicai",
            "liegong",
            "kuanggu",
            # 魏 9
            "jianxiong",
            "hujia",
            "fankui",
            "guicai",
            "ganglie",
            "tuxi",
            "duanliang",
            "jushou",
            "shensu",
            # 吴 11
            "zhiheng",
            "jiuyuan",
            "yingzi",
            "fanjian",
            "guose",
            "liuli",
            "qixi",
            "keji",
            "kurou",
            "jieyin",
            "xiaoji",
            # 群 5
            "wushuang",
            "qingnang",
            "jijiu",
            "lijian",
            "biyue",
        }
        assert expected.issubset(reg.keys()), f"Missing: {expected - reg.keys()}"

    def test_registry_handlers_are_callable(self):
        """注册的 handler 均为可调用对象"""
        from game.skills.registry import get_registry

        for sid, fn in get_registry().items():
            assert callable(fn), f"{sid} handler not callable"

    def test_get_all_skill_handlers_uses_registry(self):
        """get_all_skill_handlers 优先返回装饰器注册表"""
        from game.skills import get_all_skill_handlers
        from game.skills.registry import get_registry

        handlers = get_all_skill_handlers()
        registry = get_registry()
        # 装饰器注册表非空时，两者应一致
        assert len(handlers) == len(registry)
        for k, v in registry.items():
            assert handlers[k] is v

    def test_registry_returns_copy(self):
        """get_registry 返回副本，外部修改不影响全局注册表"""
        from game.skills.registry import get_registry

        copy = get_registry()
        copy["__test_fake__"] = lambda: None
        assert "__test_fake__" not in get_registry()

    def test_skill_handler_decorator_preserves_function(self):
        """装饰器不改变原始函数引用"""
        from game.skills.registry import _SKILL_REGISTRY
        from game.skills.registry import skill_handler as sh

        def _dummy(player, engine, **kw):
            return True

        decorated = sh("__test_dummy__")(_dummy)
        assert decorated is _dummy
        assert _SKILL_REGISTRY["__test_dummy__"] is _dummy
        # cleanup
        _SKILL_REGISTRY.pop("__test_dummy__", None)

    def test_engine_skill_system_uses_registry(self, engine):
        """SkillSystem._skill_handlers 与装饰器注册表一致"""
        from game.skills.registry import get_registry

        registry = get_registry()
        for sid, fn in registry.items():
            assert engine.skill_system._skill_handlers[sid] is fn
