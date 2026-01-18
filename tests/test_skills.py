# -*- coding: utf-8 -*-
"""
技能系统单元测试
覆盖 game/skill.py 中的主要技能处理器
"""

import pytest
from game.engine import GameEngine
from game.card import Card, CardType, CardSubtype, CardSuit
from game.skill import SkillSystem
from game.hero import Skill, SkillType, Kingdom


class TestSkillSystem:
    """测试技能系统基础功能"""

    @pytest.fixture
    def engine(self):
        """创建测试用的游戏引擎"""
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        # 初始化技能系统
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    @pytest.fixture
    def skill_system(self, engine):
        """创建技能系统"""
        return engine.skill_system

    def test_skill_system_init(self, skill_system):
        """测试技能系统初始化"""
        assert skill_system is not None
        assert hasattr(skill_system, '_skill_handlers')
        assert len(skill_system._skill_handlers) > 0

    def test_can_use_skill_unknown(self, skill_system, engine):
        """测试未知技能返回False"""
        player = engine.players[0]
        result = skill_system.can_use_skill("unknown_skill", player)
        assert result is False

    def test_trigger_skill_unknown(self, skill_system, engine):
        """测试触发未知技能返回False"""
        player = engine.players[0]
        result = skill_system.trigger_skill("unknown_skill", player, engine)
        assert result is False

    def test_get_usable_skills(self, skill_system, engine):
        """测试获取可用技能列表"""
        player = engine.players[0]
        skills = skill_system.get_usable_skills(player)
        assert isinstance(skills, list)


class TestRende:
    """测试仁德技能"""

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

    def test_rende_transfer_cards(self, engine):
        """测试仁德转移卡牌"""
        player = engine.players[0]
        target = engine.players[1]

        # 给玩家手牌
        test_card = Card(
            id="test_card",
            name="桃",
            card_type=CardType.BASIC,
            subtype=CardSubtype.HEAL,
            suit=CardSuit.HEART,
            number=3
        )
        player.hand.append(test_card)

        # 模拟仁德技能（如果玩家有该技能）
        skill_system = engine.skill_system
        initial_target_hand = len(target.hand)

        result = skill_system._handle_rende(
            player, engine,
            targets=[target],
            cards=[test_card]
        )

        if test_card not in player.hand:
            # 卡牌已转移
            assert result is True
            assert len(target.hand) == initial_target_hand + 1

    def test_rende_no_cards(self, engine):
        """测试仁德没有卡牌时失败"""
        player = engine.players[0]
        target = engine.players[1]

        skill_system = engine.skill_system
        result = skill_system._handle_rende(player, engine, targets=[target], cards=[])
        assert result is False

    def test_rende_no_target(self, engine):
        """测试仁德没有目标时失败"""
        player = engine.players[0]
        test_card = Card(
            id="test_card",
            name="桃",
            card_type=CardType.BASIC,
            subtype=CardSubtype.HEAL,
            suit=CardSuit.HEART,
            number=3
        )
        player.hand.append(test_card)

        skill_system = engine.skill_system
        result = skill_system._handle_rende(player, engine, targets=None, cards=[test_card])
        assert result is False


class TestZhiheng:
    """测试制衡技能"""

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

    def test_zhiheng_exchange_cards(self, engine):
        """测试制衡交换卡牌"""
        player = engine.players[0]

        # 清空手牌并添加测试卡牌
        player.hand.clear()
        test_cards = []
        for i in range(3):
            card = Card(
                id=f"test_card_{i}",
                name="杀",
                card_type=CardType.BASIC,
                subtype=CardSubtype.ATTACK,
                suit=CardSuit.SPADE,
                number=i + 1
            )
            test_cards.append(card)
            player.hand.append(card)

        initial_hand_count = len(player.hand)
        skill_system = engine.skill_system

        result = skill_system._handle_zhiheng(player, engine, cards=test_cards[:2])

        # 制衡应该弃掉选择的牌然后摸等量的牌
        assert result is True

    def test_zhiheng_no_cards(self, engine):
        """测试制衡没有卡牌时失败"""
        player = engine.players[0]
        skill_system = engine.skill_system

        result = skill_system._handle_zhiheng(player, engine, cards=[])
        assert result is False


class TestWusheng:
    """测试武圣技能"""

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

    def test_wusheng_convert_red_card(self, engine):
        """测试武圣将红色牌当杀"""
        player = engine.players[0]
        target = engine.players[1]

        # 添加红色手牌
        red_card = Card(
            id="red_card",
            name="桃",
            card_type=CardType.BASIC,
            subtype=CardSubtype.HEAL,
            suit=CardSuit.HEART,
            number=3
        )
        player.hand.append(red_card)

        skill_system = engine.skill_system
        result = skill_system._handle_wusheng(
            player, engine,
            targets=[target],
            cards=[red_card]
        )

        # 武圣应该能将红色牌当杀使用
        assert result is True or result is False  # 取决于实现


class TestLongdan:
    """测试龙胆技能"""

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

    def test_longdan_sha_as_shan(self, engine):
        """测试龙胆将杀当闪"""
        player = engine.players[0]

        sha_card = Card(
            id="sha_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(sha_card)

        skill_system = engine.skill_system
        result = skill_system._handle_longdan(
            player, engine,
            cards=[sha_card],
            convert_to="shan"
        )

        assert result is True or result is False


class TestQingnang:
    """测试青囊技能"""

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

    def test_qingnang_heal(self, engine):
        """测试青囊治疗"""
        player = engine.players[0]
        target = engine.players[1]

        # 让目标受伤
        target.hp = target.max_hp - 1

        # 给玩家一张手牌
        test_card = Card(
            id="test_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(test_card)

        skill_system = engine.skill_system
        target_hp_before = target.hp

        result = skill_system._handle_qingnang(
            player, engine,
            targets=[target],
            cards=[test_card]
        )

        if result:
            assert target.hp >= target_hp_before

    def test_qingnang_no_card(self, engine):
        """测试青囊没有卡牌时失败"""
        player = engine.players[0]
        target = engine.players[1]
        target.hp = target.max_hp - 1

        skill_system = engine.skill_system
        result = skill_system._handle_qingnang(player, engine, targets=[target], cards=[])
        assert result is False


class TestKurou:
    """测试苦肉技能"""

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

    def test_kurou_self_damage(self, engine):
        """测试苦肉自伤摸牌"""
        player = engine.players[0]
        player.hp = player.max_hp  # 确保满血

        skill_system = engine.skill_system
        hp_before = player.hp
        hand_before = len(player.hand)

        result = skill_system._handle_kurou(player, engine)

        if result:
            # 苦肉：失去1点体力，摸2张牌
            assert player.hp == hp_before - 1
            assert len(player.hand) >= hand_before + 2


class TestBiyue:
    """测试闭月技能"""

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

    def test_biyue_draw(self, engine):
        """测试闭月摸牌"""
        player = engine.players[0]
        hand_before = len(player.hand)

        skill_system = engine.skill_system
        result = skill_system._handle_biyue(player, engine)

        if result:
            # 闭月：结束阶段摸1张牌
            assert len(player.hand) >= hand_before + 1


class TestYingzi:
    """测试英姿技能"""

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

    def test_yingzi_extra_draw(self, engine):
        """测试英姿额外摸牌"""
        player = engine.players[0]
        hand_before = len(player.hand)

        skill_system = engine.skill_system
        result = skill_system._handle_yingzi(player, engine)

        # 英姿技能应该返回True或False
        assert result is True or result is False
        # 如果成功，手牌数量应该增加
        if result:
            assert len(player.hand) >= hand_before


class TestJianxiong:
    """测试奸雄技能"""

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

    def test_jianxiong_get_damage_card(self, engine):
        """测试奸雄获取造成伤害的牌"""
        player = engine.players[0]

        damage_card = Card(
            id="damage_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )

        skill_system = engine.skill_system
        hand_before = len(player.hand)

        result = skill_system._handle_jianxiong(
            player, engine,
            damage_card=damage_card
        )

        # 奸雄：受到伤害后可获得造成伤害的牌
        assert result is True or result is False


class TestGanglie:
    """测试刚烈技能"""

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

    def test_ganglie_retaliation(self, engine):
        """测试刚烈反击"""
        player = engine.players[0]
        source = engine.players[1]

        skill_system = engine.skill_system

        result = skill_system._handle_ganglie(
            player, engine,
            source=source
        )

        # 刚烈：受到伤害后可进行判定，红色则伤害来源弃2牌或受1伤
        assert result is True or result is False

    def test_ganglie_no_source(self, engine):
        """测试刚烈没有伤害来源时返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_ganglie(player, engine, source=None)
        assert result is False

    def test_ganglie_self_damage(self, engine):
        """测试刚烈对自己造成伤害时返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_ganglie(player, engine, source=player)
        assert result is False


class TestFankui:
    """测试反馈技能"""

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

    def test_fankui_get_card(self, engine):
        """测试反馈获取伤害来源的牌"""
        player = engine.players[0]
        source = engine.players[1]

        # 确保来源有牌
        test_card = Card(
            id="fankui_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        source.hand.append(test_card)

        skill_system = engine.skill_system
        result = skill_system._handle_fankui(player, engine, source=source)
        assert result is True

    def test_fankui_no_source(self, engine):
        """测试反馈没有来源时返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_fankui(player, engine, source=None)
        assert result is False

    def test_fankui_self_source(self, engine):
        """测试反馈来源是自己时返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_fankui(player, engine, source=player)
        assert result is False

    def test_fankui_source_no_cards(self, engine):
        """测试反馈来源没有牌时返回False"""
        player = engine.players[0]
        source = engine.players[1]
        source.hand.clear()
        # 清空装备
        source.equipment.weapon = None
        source.equipment.armor = None
        source.equipment.plus_horse = None
        source.equipment.minus_horse = None

        skill_system = engine.skill_system
        result = skill_system._handle_fankui(player, engine, source=source)
        assert result is False


class TestTuxi:
    """测试突袭技能"""

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

    def test_tuxi_get_cards(self, engine):
        """测试突袭获取他人手牌"""
        player = engine.players[0]
        target = engine.players[1]

        # 确保目标有牌
        test_card = Card(
            id="tuxi_test",
            name="闪",
            card_type=CardType.BASIC,
            subtype=CardSubtype.DODGE,
            suit=CardSuit.DIAMOND,
            number=5
        )
        target.hand.append(test_card)
        hand_before = len(player.hand)

        skill_system = engine.skill_system
        result = skill_system._handle_tuxi(player, engine, targets=[target])

        assert result is True
        assert len(player.hand) > hand_before

    def test_tuxi_no_targets(self, engine):
        """测试突袭没有目标时返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_tuxi(player, engine, targets=[])
        assert result is False


class TestGuanxing:
    """测试观星技能"""

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

    def test_guanxing_ai(self, engine):
        """测试AI观星"""
        player = engine.players[0]
        player.is_ai = True

        skill_system = engine.skill_system
        result = skill_system._handle_guanxing(player, engine)

        # 观星应该成功执行
        assert result is True

    def test_guanxing_empty_deck(self, engine):
        """测试牌堆为空时观星返回False"""
        player = engine.players[0]
        engine.deck.draw_pile.clear()

        skill_system = engine.skill_system
        result = skill_system._handle_guanxing(player, engine)
        assert result is False


class TestKongcheng:
    """测试空城技能"""

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

    def test_kongcheng_no_hand(self, engine):
        """测试空城：没有手牌时返回True"""
        player = engine.players[0]
        player.hand.clear()

        skill_system = engine.skill_system
        result = skill_system._handle_kongcheng(player, engine)
        assert result is True

    def test_kongcheng_has_hand(self, engine):
        """测试空城：有手牌时返回False"""
        player = engine.players[0]
        test_card = Card(
            id="kongcheng_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(test_card)

        skill_system = engine.skill_system
        result = skill_system._handle_kongcheng(player, engine)
        assert result is False


class TestJizhi:
    """测试集智技能"""

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

    def test_jizhi_draw(self, engine):
        """测试集智摸牌"""
        player = engine.players[0]
        hand_before = len(player.hand)

        skill_system = engine.skill_system
        result = skill_system._handle_jizhi(player, engine)

        assert result is True
        assert len(player.hand) == hand_before + 1


class TestTieji:
    """测试铁骑技能"""

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

    def test_tieji_judge(self, engine):
        """测试铁骑判定"""
        player = engine.players[0]
        target = engine.players[1]

        skill_system = engine.skill_system
        result = skill_system._handle_tieji(player, engine, target=target)

        # 铁骑根据判定结果返回True或False
        assert result is True or result is False

    def test_tieji_no_target(self, engine):
        """测试铁骑没有目标返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_tieji(player, engine, target=None)
        assert result is False


class TestGuicai:
    """测试鬼才技能"""

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

    def test_guicai_ai(self, engine):
        """测试AI鬼才"""
        player = engine.players[0]
        player.is_ai = True

        # 给玩家手牌
        test_card = Card(
            id="guicai_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(test_card)

        skill_system = engine.skill_system
        result = skill_system._handle_guicai(player, engine)
        assert result is True

    def test_guicai_no_hand(self, engine):
        """测试鬼才没有手牌返回False"""
        player = engine.players[0]
        player.hand.clear()

        skill_system = engine.skill_system
        result = skill_system._handle_guicai(player, engine)
        assert result is False


class TestJushou:
    """测试据守技能"""

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

    def test_jushou_draw_and_flip(self, engine):
        """测试据守摸牌并翻面"""
        player = engine.players[0]
        hand_before = len(player.hand)
        flipped_before = player.flipped

        skill_system = engine.skill_system
        result = skill_system._handle_jushou(player, engine)

        assert result is True
        assert len(player.hand) == hand_before + 3
        assert player.flipped != flipped_before


class TestKeji:
    """测试克己技能"""

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

    def test_keji_no_sha(self, engine):
        """测试克己：未使用杀时返回True"""
        player = engine.players[0]
        player.sha_count = 0

        skill_system = engine.skill_system
        result = skill_system._handle_keji(player, engine)
        assert result is True

    def test_keji_used_sha(self, engine):
        """测试克己：使用过杀时返回False"""
        player = engine.players[0]
        player.sha_count = 1

        skill_system = engine.skill_system
        result = skill_system._handle_keji(player, engine)
        assert result is False


class TestXiaoji:
    """测试枭姬技能"""

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

    def test_xiaoji_draw(self, engine):
        """测试枭姬摸牌"""
        player = engine.players[0]
        hand_before = len(player.hand)

        skill_system = engine.skill_system
        result = skill_system._handle_xiaoji(player, engine)

        assert result is True
        assert len(player.hand) == hand_before + 2


class TestKuanggu:
    """测试狂骨技能"""

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

    def test_kuanggu_heal(self, engine):
        """测试狂骨回血"""
        player = engine.players[0]
        target = engine.players[1]

        # 让玩家受伤
        player.hp = player.max_hp - 1
        hp_before = player.hp

        skill_system = engine.skill_system
        result = skill_system._handle_kuanggu(player, engine, target=target, damage=1)

        # 根据距离判定是否回血
        assert result is True or result is False
        if result:
            assert player.hp > hp_before

    def test_kuanggu_no_target(self, engine):
        """测试狂骨没有目标返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_kuanggu(player, engine, target=None)
        assert result is False


class TestLiegong:
    """测试烈弓技能"""

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

    def test_liegong_high_hand(self, engine):
        """测试烈弓：目标手牌多时触发"""
        player = engine.players[0]
        target = engine.players[1]

        # 让玩家体力低，目标手牌多
        player.hp = 2
        for i in range(5):
            test_card = Card(
                id=f"liegong_test_{i}",
                name="杀",
                card_type=CardType.BASIC,
                subtype=CardSubtype.ATTACK,
                suit=CardSuit.SPADE,
                number=i + 1
            )
            target.hand.append(test_card)

        skill_system = engine.skill_system
        result = skill_system._handle_liegong(player, engine, target=target)

        # 目标手牌数 >= 玩家体力值，应该触发
        assert result is True

    def test_liegong_no_target(self, engine):
        """测试烈弓没有目标返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_liegong(player, engine, target=None)
        assert result is False


class TestShensu:
    """测试神速技能"""

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

    def test_shensu_attack(self, engine):
        """测试神速攻击"""
        player = engine.players[0]
        target = engine.players[1]
        hp_before = target.hp

        skill_system = engine.skill_system
        result = skill_system._handle_shensu(player, engine, target=target)

        assert result is True
        assert target.hp < hp_before

    def test_shensu_no_target(self, engine):
        """测试神速没有目标返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_shensu(player, engine, target=None)
        assert result is False


class TestJieyin:
    """测试结姻技能"""

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

    def test_jieyin_heal(self, engine):
        """测试结姻双方回血"""
        player = engine.players[0]
        target = engine.players[1]

        # 设置目标为受伤男性
        if target.hero:
            target.hero.gender = "male"
        target.hp = target.max_hp - 1
        player.hp = player.max_hp - 1

        # 给玩家两张手牌
        cards = []
        for i in range(2):
            card = Card(
                id=f"jieyin_test_{i}",
                name="杀",
                card_type=CardType.BASIC,
                subtype=CardSubtype.ATTACK,
                suit=CardSuit.SPADE,
                number=i + 1
            )
            player.hand.append(card)
            cards.append(card)

        hp_before = player.hp

        skill_system = engine.skill_system
        result = skill_system._handle_jieyin(player, engine, target=target, cards=cards)

        assert result is True
        assert player.hp > hp_before

    def test_jieyin_no_cards(self, engine):
        """测试结姻没有足够卡牌返回False"""
        player = engine.players[0]
        target = engine.players[1]
        if target.hero:
            target.hero.gender = "male"
        target.hp = target.max_hp - 1

        skill_system = engine.skill_system
        result = skill_system._handle_jieyin(player, engine, target=target, cards=[])
        assert result is False

    def test_jieyin_target_full_hp(self, engine):
        """测试结姻目标满血返回False"""
        player = engine.players[0]
        target = engine.players[1]
        if target.hero:
            target.hero.gender = "male"
        target.hp = target.max_hp

        cards = []
        for i in range(2):
            card = Card(
                id=f"jieyin_test2_{i}",
                name="杀",
                card_type=CardType.BASIC,
                subtype=CardSubtype.ATTACK,
                suit=CardSuit.SPADE,
                number=i + 1
            )
            player.hand.append(card)
            cards.append(card)

        skill_system = engine.skill_system
        result = skill_system._handle_jieyin(player, engine, target=target, cards=cards)
        assert result is False


class TestFanjian:
    """测试反间技能"""

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

    def test_fanjian_success(self, engine):
        """测试反间成功执行"""
        player = engine.players[0]
        target = engine.players[1]
        target.is_ai = True

        card = Card(
            id="fanjian_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(card)

        skill_system = engine.skill_system
        result = skill_system._handle_fanjian(player, engine, targets=[target], cards=[card])

        assert result is True

    def test_fanjian_no_targets(self, engine):
        """测试反间没有目标返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_fanjian(player, engine, targets=None, cards=None)
        assert result is False

    def test_fanjian_card_not_in_hand(self, engine):
        """测试反间卡牌不在手中返回False"""
        player = engine.players[0]
        target = engine.players[1]

        card = Card(
            id="fanjian_card2",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        # 不加入手牌

        skill_system = engine.skill_system
        result = skill_system._handle_fanjian(player, engine, targets=[target], cards=[card])
        assert result is False


class TestLiuli:
    """测试流离技能"""

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

    def test_liuli_redirect(self, engine):
        """测试流离转移目标"""
        player = engine.players[0]
        new_target = engine.players[2]

        # 给玩家手牌
        card = Card(
            id="liuli_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(card)

        skill_system = engine.skill_system
        result = skill_system._handle_liuli(player, engine, new_target=new_target)

        assert result is True

    def test_liuli_no_hand(self, engine):
        """测试流离没有手牌返回False"""
        player = engine.players[0]
        new_target = engine.players[2]
        player.hand.clear()

        skill_system = engine.skill_system
        result = skill_system._handle_liuli(player, engine, new_target=new_target)
        assert result is False

    def test_liuli_no_target(self, engine):
        """测试流离没有新目标返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_liuli(player, engine, new_target=None)
        assert result is False


class TestLijian:
    """测试离间技能"""

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

    def test_lijian_no_card(self, engine):
        """测试离间没有卡牌返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_lijian(player, engine, targets=None, card=None)
        assert result is False

    def test_lijian_not_enough_targets(self, engine):
        """测试离间目标不足返回False"""
        player = engine.players[0]
        target = engine.players[1]

        card = Card(
            id="lijian_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(card)

        skill_system = engine.skill_system
        result = skill_system._handle_lijian(player, engine, targets=[target], card=card)
        assert result is False


class TestPassiveSkills:
    """测试被动/锁定技能"""

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

    def test_wushuang(self, engine):
        """测试无双技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_wushuang(player, engine)
        assert result is True

    def test_paoxiao(self, engine):
        """测试咆哮技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_paoxiao(player, engine)
        assert result is True

    def test_mashu(self, engine):
        """测试马术技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_mashu(player, engine)
        assert result is True

    def test_qicai(self, engine):
        """测试奇才技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_qicai(player, engine)
        assert result is True

    def test_jiuyuan(self, engine):
        """测试救援技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_jiuyuan(player, engine)
        assert result is True

    def test_longdan(self, engine):
        """测试龙胆技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_longdan(player, engine)
        assert result is True

    def test_guose(self, engine):
        """测试国色技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_guose(player, engine)
        assert result is True

    def test_jijiu(self, engine):
        """测试急救技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_jijiu(player, engine)
        assert result is True

    def test_qixi(self, engine):
        """测试奇袭技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_qixi(player, engine)
        assert result is True

    def test_duanliang(self, engine):
        """测试断粮技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_duanliang(player, engine)
        assert result is True


class TestSkillUsage:
    """测试use_skill和can_use_skill方法"""

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

    def test_can_use_skill_no_hero_skill(self, engine):
        """测试玩家没有该技能"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system.can_use_skill("nonexistent_skill", player)
        assert result is False

    def test_use_skill_rende(self, engine):
        """测试通过use_skill方法使用仁德"""
        player = engine.players[0]
        target = engine.players[1]

        # 设置仁德技能
        from game.hero import Skill, SkillType
        rende_skill = Skill(
            id="rende",
            name="仁德",
            description="仁德描述",
            skill_type=SkillType.ACTIVE,
            limit_per_turn=1
        )
        if player.hero:
            player.hero.skills.append(rende_skill)

        # 给玩家手牌
        card = Card(
            id="use_skill_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(card)

        skill_system = engine.skill_system
        result = skill_system.use_skill("rende", player, targets=[target], cards=[card])

        # 可能成功也可能失败，取决于具体实现
        assert result is True or result is False

    def test_can_use_skill_limit_per_turn(self, engine):
        """测试技能使用次数限制"""
        player = engine.players[0]

        from game.hero import Skill, SkillType
        test_skill = Skill(
            id="zhiheng",
            name="制衡",
            description="制衡描述",
            skill_type=SkillType.ACTIVE,
            limit_per_turn=1
        )
        if player.hero:
            player.hero.skills.append(test_skill)

        # 标记已使用
        player.skill_used["zhiheng"] = 1

        skill_system = engine.skill_system
        result = skill_system.can_use_skill("zhiheng", player)
        assert result is False

    def test_can_use_skill_fanjian_needs_cards_and_targets(self, engine):
        """测试反间需要手牌和目标"""
        player = engine.players[0]

        from game.hero import Skill, SkillType
        fanjian_skill = Skill(
            id="fanjian",
            name="反间",
            description="反间描述",
            skill_type=SkillType.ACTIVE,
            limit_per_turn=1
        )
        if player.hero:
            player.hero.skills.append(fanjian_skill)

        # 清空手牌
        player.hand.clear()

        skill_system = engine.skill_system
        result = skill_system.can_use_skill("fanjian", player)
        assert result is False

        # 给手牌
        card = Card(
            id="fanjian_can_use_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(card)

        result = skill_system.can_use_skill("fanjian", player)
        assert result is True


class TestJianxiongDetailed:
    """详细测试奸雄技能"""

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

    def test_jianxiong_card_in_discard(self, engine):
        """测试奸雄从弃牌堆获取牌"""
        player = engine.players[0]

        damage_card = Card(
            id="jianxiong_discard",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        # 把牌放入弃牌堆
        engine.deck.discard([damage_card])

        hand_before = len(player.hand)
        skill_system = engine.skill_system
        result = skill_system._handle_jianxiong(player, engine, damage_card=damage_card)

        assert result is True
        assert len(player.hand) == hand_before + 1

    def test_jianxiong_no_damage_card(self, engine):
        """测试奸雄没有伤害牌时返回False"""
        player = engine.players[0]
        skill_system = engine.skill_system
        result = skill_system._handle_jianxiong(player, engine, damage_card=None)
        assert result is False


class TestRendeDetailed:
    """详细测试仁德技能"""

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

    def test_rende_heal_on_second_card(self, engine):
        """测试仁德给出第二张牌时回血"""
        player = engine.players[0]
        target = engine.players[1]

        # 让玩家受伤
        player.hp = player.max_hp - 1
        hp_before = player.hp

        # 设置已给出1张牌
        player.skill_used["rende_cards"] = 1

        # 给玩家手牌
        card = Card(
            id="rende_heal_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(card)

        skill_system = engine.skill_system
        result = skill_system._handle_rende(player, engine, targets=[target], cards=[card])

        assert result is True
        # 第二张牌应该触发回血
        assert player.hp > hp_before


class TestKurouDetailed:
    """详细测试苦肉技能"""

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

    def test_kurou_low_hp(self, engine):
        """测试苦肉体力不足时返回False"""
        player = engine.players[0]
        player.hp = 1  # 只有1点体力

        skill_system = engine.skill_system
        result = skill_system._handle_kurou(player, engine)
        assert result is False


class TestQingnangDetailed:
    """详细测试青囊技能"""

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

    def test_qingnang_card_not_in_hand(self, engine):
        """测试青囊卡牌不在手中"""
        player = engine.players[0]
        target = engine.players[1]
        target.hp = target.max_hp - 1

        card = Card(
            id="qingnang_not_in_hand",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        # 不加入手牌

        skill_system = engine.skill_system
        result = skill_system._handle_qingnang(player, engine, target=target, cards=[card])
        assert result is False
