"""Tests for game.effects.data_driven.DataDrivenCardEffect."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from game.effects.data_driven import DataDrivenCardEffect, load_card_effects_config


def _make_engine():
    engine = MagicMock()
    engine.players = []
    engine.deck = MagicMock()
    return engine


def _make_player(name="Player1", hp=3, max_hp=4, is_alive=True):
    player = MagicMock()
    player.name = name
    player.hp = hp
    player.max_hp = max_hp
    player.is_alive = is_alive
    return player


def _make_card():
    card = MagicMock()
    card.name = "test_card"
    return card


# ==================== DataDrivenCardEffect ====================

class TestDataDrivenCardEffect:
    def test_init(self):
        config = {"display_name": "桃", "needs_target": False}
        effect = DataDrivenCardEffect("tao", config)
        assert effect._card_name == "tao"
        assert effect._display_name == "桃"

    def test_needs_target_default(self):
        effect = DataDrivenCardEffect("tao", {})
        assert effect.needs_target is False

    def test_needs_target_true(self):
        effect = DataDrivenCardEffect("guohe", {"needs_target": True})
        assert effect.needs_target is True


class TestCanUse:
    def test_no_condition(self):
        effect = DataDrivenCardEffect("tao", {})
        ok, msg = effect.can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is True
        assert msg == ""

    def test_condition_pass(self):
        config = {"condition": {"check": "hp_below_max"}}
        effect = DataDrivenCardEffect("tao", config)
        player = _make_player(hp=2, max_hp=4)
        ok, msg = effect.can_use(MagicMock(), player, MagicMock(), [])
        assert ok is True

    def test_condition_fail(self):
        config = {
            "condition": {"check": "hp_below_max"},
            "condition_fail_msg": "满血了"
        }
        effect = DataDrivenCardEffect("tao", config)
        player = _make_player(hp=4, max_hp=4)
        ok, msg = effect.can_use(MagicMock(), player, MagicMock(), [])
        assert ok is False

    def test_condition_has_target_cards(self):
        config = {"condition": {"check": "has_target_cards"}}
        effect = DataDrivenCardEffect("guohe", config)
        target = _make_player()
        target.has_any_card.return_value = True
        ok, _ = effect.can_use(MagicMock(), MagicMock(), MagicMock(), [target])
        assert ok is True

    def test_condition_has_target_cards_empty(self):
        config = {"condition": {"check": "has_target_cards"}}
        effect = DataDrivenCardEffect("guohe", config)
        ok, _ = effect.can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is False

    def test_unknown_check_passes(self):
        config = {"condition": {"check": "unknown_check"}}
        effect = DataDrivenCardEffect("x", config)
        ok, _ = effect.can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is True


class TestResolve:
    def test_condition_fail_return_card(self):
        config = {
            "condition": {"check": "hp_below_max"},
            "condition_fail_action": "return_card",
            "condition_fail_msg": "满血"
        }
        effect = DataDrivenCardEffect("tao", config)
        engine = _make_engine()
        player = _make_player(hp=4, max_hp=4)
        card = _make_card()
        result = effect.resolve(engine, player, card, [])
        assert result is False
        player.draw_cards.assert_called_once_with([card])

    def test_condition_fail_no_return(self):
        config = {"condition": {"check": "hp_below_max"}}
        effect = DataDrivenCardEffect("tao", config)
        player = _make_player(hp=4, max_hp=4)
        result = effect.resolve(_make_engine(), player, _make_card(), [])
        assert result is False

    def test_simple_self_effect(self):
        config = {
            "steps": [{"draw": 2}],
            "discard_after": True,
        }
        effect = DataDrivenCardEffect("wuzhong", config)
        engine = _make_engine()
        engine.deck.draw.return_value = [MagicMock(), MagicMock()]
        player = _make_player()
        card = _make_card()
        result = effect.resolve(engine, player, card, [])
        assert result is True
        engine.deck.discard.assert_called_once_with([card])

    def test_wuxie_cancelled(self):
        config = {
            "wuxie": True,
            "steps": [{"draw": 2}],
        }
        effect = DataDrivenCardEffect("wuzhong", config)
        engine = _make_engine()
        engine._request_wuxie.return_value = True
        player = _make_player()
        card = _make_card()
        result = effect.resolve(engine, player, card, [])
        assert result is True
        engine.deck.discard.assert_called_once_with([card])

    def test_wuxie_not_cancelled(self):
        config = {
            "wuxie": True,
            "steps": [{"draw": 2}],
            "discard_after": True,
        }
        effect = DataDrivenCardEffect("wuzhong", config)
        engine = _make_engine()
        engine._request_wuxie.return_value = False
        engine.deck.draw.return_value = [MagicMock()]
        player = _make_player()
        card = _make_card()
        result = effect.resolve(engine, player, card, [])
        assert result is True

    def test_wuxie_target(self):
        config = {
            "wuxie": True,
            "wuxie_target": "target",
            "steps": [],
        }
        effect = DataDrivenCardEffect("x", config)
        engine = _make_engine()
        engine._request_wuxie.return_value = True
        target = _make_player()
        card = _make_card()
        result = effect.resolve(engine, _make_player(), card, [target])
        assert result is True

    def test_all_alive_scope(self):
        config = {
            "scope": "all_alive_from_player",
            "steps": [{"heal": {"amount": 1, "target": "current", "if_wounded": True}}],
            "discard_after": True,
        }
        effect = DataDrivenCardEffect("taoyuan", config)
        engine = _make_engine()
        p1 = _make_player("P1", hp=2, max_hp=4)
        p2 = _make_player("P2", hp=4, max_hp=4)
        p3 = _make_player("P3", hp=3, max_hp=4, is_alive=False)
        engine.players = [p1, p2, p3]
        card = _make_card()
        result = effect.resolve(engine, p1, card, [])
        assert result is True

    def test_all_alive_wuxie_per_target(self):
        config = {
            "scope": "all_alive_from_player",
            "wuxie_per_target": True,
            "steps": [{"heal": 1}],
        }
        effect = DataDrivenCardEffect("taoyuan", config)
        engine = _make_engine()
        p1 = _make_player("P1")
        p2 = _make_player("P2")
        engine.players = [p1, p2]
        engine._request_wuxie.side_effect = [True, False]
        card = _make_card()
        effect.resolve(engine, p1, card, [])

    def test_no_discard_after(self):
        config = {
            "steps": [],
            "discard_after": False,
        }
        effect = DataDrivenCardEffect("x", config)
        engine = _make_engine()
        card = _make_card()
        effect.resolve(engine, _make_player(), card, [])
        engine.deck.discard.assert_not_called()


class TestExecStep:
    def test_draw_int(self):
        config = {"steps": [{"draw": 3}]}
        effect = DataDrivenCardEffect("wuzhong", config)
        engine = _make_engine()
        cards = [MagicMock(), MagicMock(), MagicMock()]
        engine.deck.draw.return_value = cards
        player = _make_player()
        effect._execute_steps(engine, player, player)
        engine.deck.draw.assert_called_once_with(3)
        player.draw_cards.assert_called_once_with(cards)

    def test_draw_dict(self):
        config = {"steps": [{"draw": {"count": 2, "target": "target"}}]}
        effect = DataDrivenCardEffect("x", config)
        engine = _make_engine()
        cards = [MagicMock()]
        engine.deck.draw.return_value = cards
        player = _make_player("P1")
        target = _make_player("P2")
        effect._execute_steps(engine, player, target)
        target.draw_cards.assert_called_once_with(cards)

    def test_draw_empty(self):
        config = {"steps": [{"draw": 2}]}
        effect = DataDrivenCardEffect("x", config)
        engine = _make_engine()
        engine.deck.draw.return_value = []
        player = _make_player()
        effect._execute_steps(engine, player, player)
        player.draw_cards.assert_not_called()

    def test_heal_int(self):
        config = {"steps": [{"heal": 1}]}
        effect = DataDrivenCardEffect("tao", config)
        engine = _make_engine()
        player = _make_player(hp=2, max_hp=4)
        effect._execute_steps(engine, player, player)
        player.heal.assert_called_once_with(1)

    def test_heal_dict_if_wounded_skip(self):
        config = {"steps": [{"heal": {"amount": 1, "target": "self", "if_wounded": True}}]}
        effect = DataDrivenCardEffect("taoyuan", config)
        engine = _make_engine()
        player = _make_player(hp=4, max_hp=4)
        effect._execute_steps(engine, player, player)
        player.heal.assert_not_called()

    def test_heal_dict_if_wounded_ok(self):
        config = {"steps": [{"heal": {"amount": 1, "target": "current", "if_wounded": True}}]}
        effect = DataDrivenCardEffect("taoyuan", config)
        engine = _make_engine()
        player = _make_player(hp=2, max_hp=4)
        effect._execute_steps(engine, player, player)
        player.heal.assert_called_once_with(1)

    def test_log_step(self):
        config = {"steps": [{"log": "{player} used on {target}"}]}
        effect = DataDrivenCardEffect("x", config)
        engine = _make_engine()
        player = _make_player("A")
        target = _make_player("B")
        effect._execute_steps(engine, player, target)
        engine.log_event.assert_called_once()

    def test_log_step_no_target(self):
        config = {"steps": [{"log": "{player} self"}]}
        effect = DataDrivenCardEffect("x", config)
        engine = _make_engine()
        player = _make_player("A")
        effect._execute_steps(engine, player, None)
        engine.log_event.assert_called_once()

    def test_log_if_healed(self):
        config = {"steps": [{"log_if_healed": "{target} healed by {player}"}]}
        effect = DataDrivenCardEffect("x", config)
        engine = _make_engine()
        player = _make_player("A")
        target = _make_player("B", hp=2, max_hp=4)
        effect._execute_steps(engine, player, target)
        engine.log_event.assert_called_once()

    def test_log_if_healed_skip(self):
        config = {"steps": [{"log_if_healed": "{target} healed"}]}
        effect = DataDrivenCardEffect("x", config)
        engine = _make_engine()
        player = _make_player("A")
        target = _make_player("B", hp=4, max_hp=4)
        effect._execute_steps(engine, player, target)
        engine.log_event.assert_not_called()


class TestResolvePlayer:
    def test_self(self):
        effect = DataDrivenCardEffect("x", {})
        p = _make_player("A")
        t = _make_player("B")
        assert effect._resolve_player("self", p, t) is p

    def test_target(self):
        effect = DataDrivenCardEffect("x", {})
        p = _make_player("A")
        t = _make_player("B")
        assert effect._resolve_player("target", p, t) is t

    def test_target_none(self):
        effect = DataDrivenCardEffect("x", {})
        p = _make_player("A")
        assert effect._resolve_player("target", p, None) is p

    def test_current(self):
        effect = DataDrivenCardEffect("x", {})
        p = _make_player("A")
        t = _make_player("B")
        assert effect._resolve_player("current", p, t) is t

    def test_unknown(self):
        effect = DataDrivenCardEffect("x", {})
        p = _make_player("A")
        assert effect._resolve_player("xyz", p, None) is p


# ==================== load_card_effects_config ====================

class TestLoadCardEffectsConfig:
    def test_load_existing(self):
        result = load_card_effects_config()
        # Should return dict even if file doesn't exist
        assert isinstance(result, dict)

    def test_no_file(self):
        with patch.object(Path, "exists", return_value=False):
            result = load_card_effects_config()
            assert result == {}

    def test_json_error(self):
        with patch.object(Path, "exists", return_value=True), \
             patch("builtins.open", side_effect=Exception("bad")):
            result = load_card_effects_config()
            assert result == {}
