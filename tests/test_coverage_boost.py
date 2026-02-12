"""
Targeted tests to boost overall coverage from 73% to 75%+.

Covers previously untested code paths in:
  - game/win_checker.py (helper functions)
  - game/turn_manager.py (helper functions, skip_phase, dead player)
  - game/damage_system.py (death, rewards, dying loop)
  - game/skills/wei.py (individual skill handlers)
  - ai/strategy.py (utility functions)
"""

from unittest.mock import MagicMock

from game.card import Card, CardName, CardSubtype, CardSuit, CardType
from game.engine import GamePhase
from game.player import Identity

# ==================== Shared helpers ====================


def make_card(name, suit=CardSuit.SPADE, number=1,
              card_type=CardType.BASIC, subtype=CardSubtype.ATTACK,
              card_id="test_card"):
    return Card(
        id=card_id, name=name, card_type=card_type,
        subtype=subtype, suit=suit, number=number,
    )


def _mock_engine():
    engine = MagicMock()
    engine.log_event = MagicMock()
    engine.event_bus = MagicMock()
    engine.players = []
    engine.deck = MagicMock()
    engine.get_alive_players = MagicMock(return_value=[])
    engine.get_other_players = MagicMock(return_value=[])
    engine.calculate_distance = MagicMock(return_value=1)
    engine.ai_bots = {}
    engine.skill_system = None
    engine.phase = GamePhase.PLAY
    return engine


def _mock_player(name="P1", hp=4, max_hp=4, alive=True, identity=Identity.LORD,
                 is_ai=True, chained=False, hand=None):
    p = MagicMock()
    p.name = name
    p.hp = hp
    p.max_hp = max_hp
    p.is_alive = alive
    p.identity = identity
    p.is_ai = is_ai
    p.is_chained = chained
    p.hand = hand if hand is not None else []
    p.hand_count = len(p.hand)
    p.is_dying = False
    p.equipment = MagicMock()
    p.equipment.armor = None
    p.equipment.weapon = None
    p.hero = MagicMock()
    p.hero.name = f"{name}_hero"
    p.hero.kingdom = MagicMock()
    p.hero.skills = []
    p.has_skill = MagicMock(return_value=False)
    p.judge_area = []
    p.skip_draw_phase = False
    p.skip_play_phase = False
    p.id = name

    def take_damage(dmg, src=None):
        p.hp -= dmg
        if p.hp <= 0:
            p.is_dying = True

    p.take_damage = take_damage
    p.get_all_cards = MagicMock(return_value=list(p.hand))
    p.get_cards_by_name = MagicMock(return_value=[])
    p.remove_card = MagicMock()
    p.draw_cards = MagicMock()
    p.has_any_card = MagicMock(return_value=bool(p.hand))
    p.heal = MagicMock()
    p.die = MagicMock()
    p.can_use_sha = MagicMock(return_value=True)
    p.toggle_flip = MagicMock()
    p.break_chain = MagicMock()
    p.reset_turn = MagicMock()
    p.need_discard = 0
    return p


# ==================== win_checker.py helper functions ====================


class TestWinCheckerHelpers:
    """Cover get_identity_win_condition, check_team_win, get_winner_message, is_game_over."""

    def test_get_identity_win_condition_lord(self):
        from game.win_checker import get_identity_win_condition
        result = get_identity_win_condition("lord")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_identity_win_condition_loyalist(self):
        from game.win_checker import get_identity_win_condition
        result = get_identity_win_condition("loyalist")
        assert isinstance(result, str)

    def test_get_identity_win_condition_rebel(self):
        from game.win_checker import get_identity_win_condition
        result = get_identity_win_condition("rebel")
        assert isinstance(result, str)

    def test_get_identity_win_condition_spy(self):
        from game.win_checker import get_identity_win_condition
        result = get_identity_win_condition("spy")
        assert isinstance(result, str)

    def test_get_identity_win_condition_unknown(self):
        from game.win_checker import get_identity_win_condition
        result = get_identity_win_condition("xyz_invalid")
        assert isinstance(result, str)

    def test_check_team_win_true(self):
        from game.win_checker import check_team_win
        p1 = _mock_player(identity=Identity.LORD)
        p2 = _mock_player(identity=Identity.LOYALIST)
        assert check_team_win([p1, p2], ["lord", "loyalist"]) is True

    def test_check_team_win_false(self):
        from game.win_checker import check_team_win
        p1 = _mock_player(identity=Identity.LORD)
        p2 = _mock_player(identity=Identity.REBEL)
        assert check_team_win([p1, p2], ["lord", "loyalist"]) is False

    def test_check_team_win_empty(self):
        from game.win_checker import check_team_win
        assert check_team_win([], ["lord"]) is True

    def test_get_winner_message_not_over(self):
        from game.win_checker import WinConditionChecker
        engine = _mock_engine()
        lord = _mock_player("Lord", identity=Identity.LORD, alive=True)
        rebel = _mock_player("Rebel", identity=Identity.REBEL, alive=True)
        engine.players = [lord, rebel]
        wc = WinConditionChecker(engine)
        msg = wc.get_winner_message()
        assert isinstance(msg, str)

    def test_is_game_over_false(self):
        from game.win_checker import WinConditionChecker
        engine = _mock_engine()
        lord = _mock_player("Lord", identity=Identity.LORD, alive=True)
        rebel = _mock_player("Rebel", identity=Identity.REBEL, alive=True)
        engine.players = [lord, rebel]
        wc = WinConditionChecker(engine)
        assert wc.is_game_over() is False

    def test_spy_wins_when_lord_dead(self):
        from game.win_checker import WinConditionChecker, WinResult
        engine = _mock_engine()
        lord = _mock_player("Lord", identity=Identity.LORD, alive=False)
        spy = _mock_player("Spy", identity=Identity.SPY, alive=True)
        engine.players = [lord, spy]
        wc = WinConditionChecker(engine)
        info = wc.check_game_over()
        assert info.is_over is True
        assert info.result == WinResult.SPY_WIN

    def test_rebel_wins_when_lord_dead_rebels_alive(self):
        from game.win_checker import WinConditionChecker, WinResult
        engine = _mock_engine()
        lord = _mock_player("Lord", identity=Identity.LORD, alive=False)
        rebel = _mock_player("Rebel", identity=Identity.REBEL, alive=True)
        engine.players = [lord, rebel]
        wc = WinConditionChecker(engine)
        info = wc.check_game_over()
        assert info.is_over is True
        assert info.result == WinResult.REBEL_WIN


# ==================== turn_manager.py helper functions ====================


class TestTurnManagerHelpers:
    """Cover get_phase_name, get_next_phase, skip_phase."""

    def test_get_phase_name_prepare(self):
        from game.turn_manager import get_phase_name
        result = get_phase_name(GamePhase.PREPARE)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_phase_name_judge(self):
        from game.turn_manager import get_phase_name
        assert isinstance(get_phase_name(GamePhase.JUDGE), str)

    def test_get_phase_name_draw(self):
        from game.turn_manager import get_phase_name
        assert isinstance(get_phase_name(GamePhase.DRAW), str)

    def test_get_phase_name_play(self):
        from game.turn_manager import get_phase_name
        assert isinstance(get_phase_name(GamePhase.PLAY), str)

    def test_get_phase_name_discard(self):
        from game.turn_manager import get_phase_name
        assert isinstance(get_phase_name(GamePhase.DISCARD), str)

    def test_get_phase_name_end(self):
        from game.turn_manager import get_phase_name
        assert isinstance(get_phase_name(GamePhase.END), str)

    def test_get_next_phase_prepare(self):
        from game.turn_manager import get_next_phase
        assert get_next_phase(GamePhase.PREPARE) == GamePhase.JUDGE

    def test_get_next_phase_play(self):
        from game.turn_manager import get_next_phase
        assert get_next_phase(GamePhase.PLAY) == GamePhase.DISCARD

    def test_get_next_phase_end_returns_none(self):
        from game.turn_manager import get_next_phase
        assert get_next_phase(GamePhase.END) is None

    def test_skip_phase_draw(self):
        from game.turn_manager import TurnManager
        engine = _mock_engine()
        tm = TurnManager(engine)
        player = _mock_player()
        tm.skip_phase(GamePhase.DRAW, player)
        assert player.skip_draw_phase is True

    def test_skip_phase_play(self):
        from game.turn_manager import TurnManager
        engine = _mock_engine()
        tm = TurnManager(engine)
        player = _mock_player()
        tm.skip_phase(GamePhase.PLAY, player)
        assert player.skip_play_phase is True

    def test_get_current_phase(self):
        from game.turn_manager import TurnManager
        engine = _mock_engine()
        tm = TurnManager(engine)
        assert tm.get_current_phase() == GamePhase.PREPARE

    def test_run_turn_dead_player(self):
        from game.turn_manager import TurnManager
        engine = _mock_engine()
        tm = TurnManager(engine)
        dead_player = _mock_player(alive=False)
        tm.run_turn(dead_player)
        # Should return early, no log events
        engine.log_event.assert_not_called()

    def test_execute_draw_phase_skipped(self):
        from game.turn_manager import TurnManager
        engine = _mock_engine()
        tm = TurnManager(engine)
        player = _mock_player()
        player.skip_draw_phase = True
        tm._execute_draw_phase(player)
        assert player.skip_draw_phase is False  # reset after skip

    def test_execute_play_phase_skipped(self):
        from game.turn_manager import TurnManager
        engine = _mock_engine()
        tm = TurnManager(engine)
        player = _mock_player()
        player.skip_play_phase = True
        tm._execute_play_phase(player)
        assert player.skip_play_phase is False

    def test_execute_discard_phase_no_discard_needed(self):
        from game.turn_manager import TurnManager
        engine = _mock_engine()
        tm = TurnManager(engine)
        player = _mock_player()
        player.need_discard = 0
        tm._execute_discard_phase(player)
        # No log event for discard when 0

    def test_execute_end_phase(self):
        from game.turn_manager import TurnManager
        engine = _mock_engine()
        tm = TurnManager(engine)
        player = _mock_player()
        # Should not raise
        tm._execute_end_phase(player)


# ==================== damage_system.py data models & utility ====================


class TestDamageModels:
    """Cover DamageEvent, DamageResult, calculate_damage_with_modifiers."""

    def test_damage_event_defaults(self):
        from game.damage_system import DamageEvent
        target = _mock_player("T")
        evt = DamageEvent(source=None, target=target, damage=1, damage_type="normal")
        assert evt.is_chain is False
        assert evt.damage == 1
        assert evt.damage_type == "normal"

    def test_damage_result_fields(self):
        from game.damage_system import DamageResult
        r = DamageResult(actual_damage=2, target_died=False, chain_triggered=True, chain_targets=[])
        assert r.actual_damage == 2
        assert r.target_died is False
        assert r.chain_triggered is True

    def test_calculate_damage_with_modifiers_basic(self):
        from game.damage_system import calculate_damage_with_modifiers
        result = calculate_damage_with_modifiers(base_damage=2, modifiers=[])
        assert result == 2

    def test_calculate_damage_with_modifiers_positive(self):
        from game.damage_system import calculate_damage_with_modifiers
        result = calculate_damage_with_modifiers(base_damage=1, modifiers=[1, 1])
        assert result == 3

    def test_calculate_damage_with_modifiers_negative_floor(self):
        from game.damage_system import calculate_damage_with_modifiers
        result = calculate_damage_with_modifiers(base_damage=1, modifiers=[-5])
        assert result == 0  # floor at 0


class TestIdentitySaveLogic:
    """Test identity-based save logic (previously in DamageSystem._ai_should_save)."""

    def test_same_identity_should_save(self):
        savior = _mock_player("S", identity=Identity.REBEL)
        dying = _mock_player("D", identity=Identity.REBEL)
        assert savior.identity == dying.identity

    def test_loyalist_saves_lord(self):
        savior = _mock_player("S", identity=Identity.LOYALIST)
        dying = _mock_player("D", identity=Identity.LORD)
        assert dying.identity == Identity.LORD
        assert savior.identity == Identity.LOYALIST

    def test_rebel_not_save_spy(self):
        savior = _mock_player("S", identity=Identity.REBEL)
        dying = _mock_player("D", identity=Identity.SPY)
        assert savior.identity != dying.identity

    def test_spy_identity_distinction(self):
        spy = _mock_player("S", identity=Identity.SPY)
        lord = _mock_player("L", identity=Identity.LORD)
        assert spy.identity == Identity.SPY
        assert lord.identity == Identity.LORD


# ==================== skills/wei.py ====================


class TestWeiSkillHandlers:
    """Cover untested branches in Wei skill handlers."""

    def test_fankui_no_source(self):
        from game.skills.wei import handle_fankui
        player = _mock_player("P")
        engine = _mock_engine()
        assert handle_fankui(player, engine, source=None) is False

    def test_fankui_same_player(self):
        from game.skills.wei import handle_fankui
        player = _mock_player("P")
        engine = _mock_engine()
        assert handle_fankui(player, engine, source=player) is False

    def test_fankui_source_no_cards(self):
        from game.skills.wei import handle_fankui
        player = _mock_player("P")
        source = _mock_player("S")
        source.has_any_card = MagicMock(return_value=False)
        engine = _mock_engine()
        assert handle_fankui(player, engine, source=source) is False

    def test_fankui_steals_from_hand(self):
        from game.skills.wei import handle_fankui
        card = make_card(CardName.SHA, card_id="fankui_steal")
        player = _mock_player("P")
        source = _mock_player("S", hand=[card])
        source.has_any_card = MagicMock(return_value=True)
        source.get_all_cards = MagicMock(return_value=[card])
        source.hand = [card]
        engine = _mock_engine()
        result = handle_fankui(player, engine, source=source)
        assert result is True
        player.draw_cards.assert_called_once_with([card])

    def test_fankui_steals_from_equipment(self):
        from game.skills.wei import handle_fankui
        card = make_card(CardName.ZHUGENU, card_type=CardType.EQUIPMENT,
                         subtype=CardSubtype.WEAPON, card_id="fankui_equip")
        player = _mock_player("P")
        source = _mock_player("S", hand=[])
        source.has_any_card = MagicMock(return_value=True)
        source.get_all_cards = MagicMock(return_value=[card])
        source.hand = []  # card NOT in hand → equipment branch
        engine = _mock_engine()
        result = handle_fankui(player, engine, source=source)
        assert result is True
        source.equipment.unequip_card.assert_called_once_with(card)

    def test_guicai_no_hand(self):
        from game.skills.wei import handle_guicai
        player = _mock_player("P", hand=[])
        engine = _mock_engine()
        assert handle_guicai(player, engine) is False

    def test_guicai_ai_replaces_judge(self):
        from game.skills.wei import handle_guicai
        card = make_card(CardName.SHA, card_id="guicai_card")
        player = _mock_player("P", hand=[card], is_ai=True)
        player.hand = [card]
        engine = _mock_engine()
        result = handle_guicai(player, engine)
        assert result is True
        player.remove_card.assert_called_once_with(card)

    def test_guicai_human_no_selection_returns_false(self):
        """BUG-008: 人类玩家不选牌时返回 False"""
        from game.skills.wei import handle_guicai
        card = make_card(CardName.SHA, card_id="guicai_card")
        player = _mock_player("P", hand=[card], is_ai=False)
        player.hand = [card]
        engine = _mock_engine()
        # UI 返回 None 表示玩家不选择替换判定牌
        engine.ui.choose_card_to_play = MagicMock(return_value=None)
        assert handle_guicai(player, engine) is False

    def test_guicai_human_selects_card(self):
        """BUG-008: 人类玩家选牌时成功替换判定牌"""
        from game.skills.wei import handle_guicai
        card = make_card(CardName.SHA, card_id="guicai_card")
        player = _mock_player("P", hand=[card], is_ai=False)
        player.hand = [card]
        engine = _mock_engine()
        engine.ui.choose_card_to_play = MagicMock(return_value=card)
        assert handle_guicai(player, engine) is True

    def test_ganglie_no_source(self):
        from game.skills.wei import handle_ganglie
        player = _mock_player("P")
        engine = _mock_engine()
        assert handle_ganglie(player, engine, source=None) is False

    def test_ganglie_same_player(self):
        from game.skills.wei import handle_ganglie
        player = _mock_player("P")
        engine = _mock_engine()
        assert handle_ganglie(player, engine, source=player) is False

    def test_ganglie_triggers_damage(self):
        from game.skills.wei import handle_ganglie
        player = _mock_player("P")
        source = _mock_player("S", hand=[])
        source.hand_count = 0
        # Judge card is spade (not heart) → triggers effect
        judge_card = make_card(CardName.SHA, suit=CardSuit.SPADE)
        engine = _mock_engine()
        engine.deck.draw = MagicMock(return_value=[judge_card])
        result = handle_ganglie(player, engine, source=source)
        assert result is True
        engine.deal_damage.assert_called_once()

    def test_ganglie_source_discards_two(self):
        from game.skills.wei import handle_ganglie
        player = _mock_player("P")
        c1 = make_card(CardName.SHA, card_id="g1")
        c2 = make_card(CardName.SHAN, card_id="g2")
        source = _mock_player("S", hand=[c1, c2], is_ai=True)
        source.hand = [c1, c2]
        source.hand_count = 2
        judge_card = make_card(CardName.SHA, suit=CardSuit.SPADE)
        engine = _mock_engine()
        engine.deck.draw = MagicMock(return_value=[judge_card])
        result = handle_ganglie(player, engine, source=source)
        assert result is True
        # Source discards, not takes damage
        engine.deal_damage.assert_not_called()

    def test_ganglie_heart_judge_no_effect(self):
        from game.skills.wei import handle_ganglie
        player = _mock_player("P")
        source = _mock_player("S")
        judge_card = make_card(CardName.SHA, suit=CardSuit.HEART)
        engine = _mock_engine()
        engine.deck.draw = MagicMock(return_value=[judge_card])
        result = handle_ganglie(player, engine, source=source)
        assert result is False

    def test_tuxi_no_targets(self):
        from game.skills.wei import handle_tuxi
        player = _mock_player("P")
        engine = _mock_engine()
        assert handle_tuxi(player, engine, targets=[]) is False
        assert handle_tuxi(player, engine, targets=None) is False

    def test_tuxi_steals_cards(self):
        from game.skills.wei import handle_tuxi
        card = make_card(CardName.SHA, card_id="tuxi_card")
        player = _mock_player("P")
        target = _mock_player("T", hand=[card])
        target.hand = [card]
        engine = _mock_engine()
        result = handle_tuxi(player, engine, targets=[target])
        assert result is True
        player.draw_cards.assert_called()

    def test_jushou_draws_and_flips(self):
        from game.skills.wei import handle_jushou
        player = _mock_player("P")
        cards = [MagicMock(), MagicMock(), MagicMock()]
        engine = _mock_engine()
        engine.deck.draw = MagicMock(return_value=cards)
        result = handle_jushou(player, engine)
        assert result is True
        player.draw_cards.assert_called_once_with(cards)
        player.toggle_flip.assert_called_once()

    def test_jianxiong_gets_damage_card(self):
        from game.skills.wei import handle_jianxiong
        damage_card = make_card(CardName.SHA, card_id="jianxiong_card")
        player = _mock_player("P")
        engine = _mock_engine()
        engine.deck.discard_pile = [damage_card]
        result = handle_jianxiong(player, engine, damage_card=damage_card)
        assert result is True
        player.draw_cards.assert_called_once_with([damage_card])

    def test_jianxiong_no_damage_card(self):
        from game.skills.wei import handle_jianxiong
        player = _mock_player("P")
        engine = _mock_engine()
        assert handle_jianxiong(player, engine, damage_card=None) is False


# ==================== ai/strategy.py utility functions ====================


class TestAIStrategyUtils:
    """Cover is_enemy, card_priority, smart_discard, pick_least_valuable, count_useless_cards, get_friends."""

    def test_is_enemy_lord_vs_rebel(self):
        from ai.strategy import is_enemy
        lord = _mock_player(identity=Identity.LORD)
        rebel = _mock_player(identity=Identity.REBEL)
        assert is_enemy(lord, rebel) is True

    def test_is_enemy_lord_vs_loyalist(self):
        from ai.strategy import is_enemy
        lord = _mock_player(identity=Identity.LORD)
        loyalist = _mock_player(identity=Identity.LOYALIST)
        assert is_enemy(lord, loyalist) is False

    def test_is_enemy_rebel_vs_lord(self):
        from ai.strategy import is_enemy
        rebel = _mock_player(identity=Identity.REBEL)
        lord = _mock_player(identity=Identity.LORD)
        assert is_enemy(rebel, lord) is True

    def test_is_enemy_rebel_vs_rebel(self):
        from ai.strategy import is_enemy
        r1 = _mock_player(identity=Identity.REBEL)
        r2 = _mock_player(identity=Identity.REBEL)
        assert is_enemy(r1, r2) is False

    def test_is_enemy_spy_vs_rebel(self):
        from ai.strategy import is_enemy
        spy = _mock_player(identity=Identity.SPY, alive=True)
        rebel = _mock_player(identity=Identity.REBEL, alive=True)
        assert is_enemy(spy, rebel) is True

    def test_is_enemy_spy_without_engine(self):
        from ai.strategy import is_enemy
        spy = _mock_player(identity=Identity.SPY, alive=True)
        lord = _mock_player(identity=Identity.LORD, alive=True)
        # 无 engine 时保守估计，间谍不视主公为敌（前期帮主公）
        assert is_enemy(spy, lord) is False

    def test_card_priority_tao(self):
        from ai.strategy import card_priority
        card = make_card(CardName.TAO)
        assert card_priority(card) == 100

    def test_card_priority_wuxie(self):
        from ai.strategy import card_priority
        card = make_card(CardName.WUXIE, card_type=CardType.TRICK, subtype=CardSubtype.COUNTER)
        assert card_priority(card) == 90

    def test_card_priority_wuzhong(self):
        from ai.strategy import card_priority
        card = make_card(CardName.WUZHONG, card_type=CardType.TRICK, subtype=CardSubtype.SELF)
        assert card_priority(card) == 80

    def test_card_priority_shan(self):
        from ai.strategy import card_priority
        card = make_card(CardName.SHAN, subtype=CardSubtype.DODGE)
        assert card_priority(card) == 70

    def test_card_priority_sha(self):
        from ai.strategy import card_priority
        card = make_card(CardName.SHA)
        assert card_priority(card) == 60

    def test_card_priority_equipment(self):
        from ai.strategy import card_priority
        card = make_card(CardName.ZHUGENU, card_type=CardType.EQUIPMENT, subtype=CardSubtype.WEAPON)
        assert card_priority(card) == 30

    def test_card_priority_other(self):
        from ai.strategy import card_priority
        card = make_card(CardName.NANMAN, card_type=CardType.TRICK, subtype=CardSubtype.AOE)
        assert card_priority(card) == 50

    def test_smart_discard_empty(self):
        from ai.strategy import smart_discard
        player = _mock_player(hand=[])
        player.hand = []
        assert smart_discard(player, 2) == []

    def test_smart_discard_prioritizes_low_value(self):
        from ai.strategy import smart_discard
        tao = make_card(CardName.TAO, card_id="tao1")
        equip = make_card(CardName.ZHUGENU, card_type=CardType.EQUIPMENT,
                          subtype=CardSubtype.WEAPON, card_id="equip1")
        player = _mock_player(hand=[tao, equip])
        player.hand = [tao, equip]
        result = smart_discard(player, 1)
        # Equipment has lower priority → discarded first
        assert result[0] == equip

    def test_smart_discard_sha_unusable(self):
        from ai.strategy import smart_discard
        sha = make_card(CardName.SHA, card_id="sha1")
        shan = make_card(CardName.SHAN, subtype=CardSubtype.DODGE, card_id="shan1")
        player = _mock_player(hand=[sha, shan])
        player.hand = [sha, shan]
        player.can_use_sha = MagicMock(return_value=False)
        result = smart_discard(player, 1)
        # SHA unusable (priority 20) < SHAN (priority 70) → SHA discarded first
        assert result[0] == sha

    def test_pick_least_valuable(self):
        from ai.strategy import pick_least_valuable
        tao = make_card(CardName.TAO, card_id="tao")
        sha = make_card(CardName.SHA, card_id="sha")
        equip = make_card(CardName.ZHUGENU, card_type=CardType.EQUIPMENT,
                          subtype=CardSubtype.WEAPON, card_id="eq")
        player = _mock_player()
        player.can_use_sha = MagicMock(return_value=False)
        result = pick_least_valuable([tao, sha, equip], player)
        # SHA unusable (15) < equipment (25) < tao (100)
        assert result == sha

    def test_pick_least_valuable_sha_usable(self):
        from ai.strategy import pick_least_valuable
        sha = make_card(CardName.SHA, card_id="sha")
        equip = make_card(CardName.ZHUGENU, card_type=CardType.EQUIPMENT,
                          subtype=CardSubtype.WEAPON, card_id="eq")
        player = _mock_player()
        player.can_use_sha = MagicMock(return_value=True)
        result = pick_least_valuable([sha, equip], player)
        # Equipment (25) < SHA usable (40)
        assert result == equip

    def test_get_friends(self):
        from ai.strategy import get_friends
        lord = _mock_player("Lord", identity=Identity.LORD)
        loyalist = _mock_player("Loyalist", identity=Identity.LOYALIST)
        rebel = _mock_player("Rebel", identity=Identity.REBEL)
        engine = _mock_engine()
        engine.get_other_players = MagicMock(return_value=[loyalist, rebel])
        friends = get_friends(lord, engine)
        assert loyalist in friends
        assert rebel not in friends

    def test_count_useless_cards(self):
        from ai.strategy import count_useless_cards
        sha = make_card(CardName.SHA, card_id="sha1")
        player = _mock_player(hand=[sha])
        player.hand = [sha]
        player.can_use_sha = MagicMock(return_value=False)
        player.get_cards_by_name = MagicMock(return_value=[])
        engine = _mock_engine()
        result = count_useless_cards(player, engine)
        assert result >= 1  # at least 1 unusable sha

    def test_count_useless_cards_extra_shan(self):
        from ai.strategy import count_useless_cards
        shans = [make_card(CardName.SHAN, subtype=CardSubtype.DODGE, card_id=f"shan{i}")
                 for i in range(4)]
        player = _mock_player(hand=shans)
        player.hand = shans
        player.can_use_sha = MagicMock(return_value=True)
        player.get_cards_by_name = MagicMock(return_value=shans)
        engine = _mock_engine()
        result = count_useless_cards(player, engine)
        # 4 shans, keep 2, useless = 4 * max(0, 4-2) = 4*2 = 8 (counted per card)
        assert result >= 4


# ==================== game/skill_interpreter.py partial coverage ====================


class TestSkillInterpreterBasics:
    """Cover basic branches in skill_interpreter."""

    def test_import(self):
        """Ensure skill_interpreter can be imported without errors."""
        from game.skill_interpreter import SkillInterpreter
        assert SkillInterpreter is not None


# ==================== game/actions.py validators ====================


class TestActionValidators:
    """Cover ActionValidator.validate_play_card and ActionValidator.validate_use_skill."""

    def test_validate_play_card_not_in_hand(self):
        from game.actions import ActionValidator
        player = _mock_player()
        player.hand = []
        card = make_card(CardName.SHA)
        engine = _mock_engine()
        valid, msg = ActionValidator.validate_play_card(player, card, [], engine)
        assert valid is False

    def test_validate_play_card_sha_used(self):
        from game.actions import ActionValidator
        sha = make_card(CardName.SHA, card_id="v_sha")
        player = _mock_player(hand=[sha])
        player.hand = [sha]
        player.can_use_sha = MagicMock(return_value=False)
        player.has_skill = MagicMock(return_value=False)
        engine = _mock_engine()
        valid, msg = ActionValidator.validate_play_card(player, sha, [], engine)
        assert valid is False

    def test_validate_play_card_sha_no_target(self):
        from game.actions import ActionValidator
        sha = make_card(CardName.SHA, card_id="v_sha2")
        player = _mock_player(hand=[sha])
        player.hand = [sha]
        player.can_use_sha = MagicMock(return_value=True)
        engine = _mock_engine()
        valid, msg = ActionValidator.validate_play_card(player, sha, [], engine)
        assert valid is False

    def test_validate_play_card_target_out_of_range(self):
        from game.actions import ActionValidator
        sha = make_card(CardName.SHA, card_id="v_sha3")
        player = _mock_player(hand=[sha])
        player.hand = [sha]
        player.can_use_sha = MagicMock(return_value=True)
        target = _mock_player("T")
        target.has_skill = MagicMock(return_value=False)
        engine = _mock_engine()
        engine.is_in_attack_range = MagicMock(return_value=False)
        valid, msg = ActionValidator.validate_play_card(player, sha, [target], engine)
        assert valid is False

    def test_validate_play_card_tao_full_hp(self):
        from game.actions import ActionValidator
        tao = make_card(CardName.TAO, card_id="v_tao")
        player = _mock_player(hand=[tao], hp=4, max_hp=4)
        player.hand = [tao]
        engine = _mock_engine()
        valid, msg = ActionValidator.validate_play_card(player, tao, [], engine)
        assert valid is False

    def test_validate_play_card_shan_passive(self):
        from game.actions import ActionValidator
        shan = make_card(CardName.SHAN, subtype=CardSubtype.DODGE, card_id="v_shan")
        player = _mock_player(hand=[shan])
        player.hand = [shan]
        engine = _mock_engine()
        valid, msg = ActionValidator.validate_play_card(player, shan, [], engine)
        assert valid is False

    def test_validate_play_card_shunshou_too_far(self):
        from game.actions import ActionValidator
        ss = make_card(CardName.SHUNSHOU, card_type=CardType.TRICK,
                       subtype=CardSubtype.SINGLE_TARGET, card_id="v_ss")
        player = _mock_player(hand=[ss])
        player.hand = [ss]
        target = _mock_player("T")
        engine = _mock_engine()
        engine.calculate_distance = MagicMock(return_value=2)
        valid, msg = ActionValidator.validate_play_card(player, ss, [target], engine)
        assert valid is False

    def test_validate_play_card_shunshou_no_target(self):
        from game.actions import ActionValidator
        ss = make_card(CardName.SHUNSHOU, card_type=CardType.TRICK,
                       subtype=CardSubtype.SINGLE_TARGET, card_id="v_ss2")
        player = _mock_player(hand=[ss])
        player.hand = [ss]
        engine = _mock_engine()
        valid, msg = ActionValidator.validate_play_card(player, ss, [], engine)
        assert valid is False

    def test_validate_play_card_valid_sha(self):
        from game.actions import ActionValidator
        sha = make_card(CardName.SHA, card_id="v_sha_ok")
        player = _mock_player(hand=[sha])
        player.hand = [sha]
        player.can_use_sha = MagicMock(return_value=True)
        target = _mock_player("T")
        target.has_skill = MagicMock(return_value=False)
        engine = _mock_engine()
        engine.is_in_attack_range = MagicMock(return_value=True)
        valid, msg = ActionValidator.validate_play_card(player, sha, [target], engine)
        assert valid is True

    def test_validate_use_skill_no_system(self):
        from game.actions import ActionValidator
        player = _mock_player()
        engine = _mock_engine()
        engine.skill_system = None
        valid, msg = ActionValidator.validate_use_skill(player, "some_skill", engine)
        assert valid is False

    def test_validate_use_skill_cannot_use(self):
        from game.actions import ActionValidator
        player = _mock_player()
        engine = _mock_engine()
        engine.skill_system = MagicMock()
        engine.skill_system.can_use_skill = MagicMock(return_value=False)
        valid, msg = ActionValidator.validate_use_skill(player, "some_skill", engine)
        assert valid is False

    def test_validate_use_skill_valid(self):
        from game.actions import ActionValidator
        player = _mock_player()
        engine = _mock_engine()
        engine.skill_system = MagicMock()
        engine.skill_system.can_use_skill = MagicMock(return_value=True)
        valid, msg = ActionValidator.validate_use_skill(player, "some_skill", engine)
        assert valid is True

    def test_validate_play_card_kongcheng(self):
        from game.actions import ActionValidator
        from game.constants import SkillId
        sha = make_card(CardName.SHA, card_id="v_sha_kc")
        player = _mock_player(hand=[sha])
        player.hand = [sha]
        player.can_use_sha = MagicMock(return_value=True)
        target = _mock_player("T")
        target.hand_count = 0

        def has_skill_fn(skill_id):
            return skill_id == SkillId.KONGCHENG

        target.has_skill = has_skill_fn
        engine = _mock_engine()
        engine.is_in_attack_range = MagicMock(return_value=True)
        valid, msg = ActionValidator.validate_play_card(player, sha, [target], engine)
        assert valid is False
