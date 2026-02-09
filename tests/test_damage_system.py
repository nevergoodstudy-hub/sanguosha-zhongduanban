"""Tests for game.damage_system module."""

from unittest.mock import MagicMock

from game.card import CardName, DamageType
from game.damage_system import (
    DamageEvent,
    DamageResult,
    DamageSystem,
    calculate_damage_with_modifiers,
)

# ==================== Dataclasses ====================

class TestDamageEvent:
    def test_creation(self):
        target = MagicMock()
        source = MagicMock()
        evt = DamageEvent(
            source=source, target=target, damage=2,
            damage_type=DamageType.FIRE
        )
        assert evt.source is source
        assert evt.target is target
        assert evt.damage == 2
        assert evt.damage_type == DamageType.FIRE
        assert evt.is_chain is False

    def test_chain_flag(self):
        evt = DamageEvent(
            source=None, target=MagicMock(), damage=1,
            damage_type=DamageType.NORMAL, is_chain=True
        )
        assert evt.is_chain is True


class TestDamageResult:
    def test_creation(self):
        r = DamageResult(actual_damage=3, target_died=False,
                         chain_triggered=True, chain_targets=[])
        assert r.actual_damage == 3
        assert r.target_died is False
        assert r.chain_triggered is True
        assert r.chain_targets == []


# ==================== Helper function ====================

class TestCalculateDamageWithModifiers:
    def test_no_modifiers(self):
        assert calculate_damage_with_modifiers(3, []) == 3

    def test_positive_modifiers(self):
        assert calculate_damage_with_modifiers(2, [1, 1]) == 4

    def test_negative_modifiers(self):
        assert calculate_damage_with_modifiers(3, [-2]) == 1

    def test_clamp_to_zero(self):
        assert calculate_damage_with_modifiers(1, [-5]) == 0

    def test_mixed_modifiers(self):
        assert calculate_damage_with_modifiers(5, [2, -3, 1]) == 5


# ==================== DamageSystem ====================

def _make_engine():
    """Create a mock engine for DamageSystem tests."""
    engine = MagicMock()
    engine.log_event = MagicMock()
    engine.event_bus = MagicMock()
    engine.players = []
    engine.deck = MagicMock()
    engine.get_alive_players = MagicMock(return_value=[])
    return engine


def _make_player(name="P1", hp=4, max_hp=4, alive=True, chained=False):
    player = MagicMock()
    player.name = name
    player.hp = hp
    player.max_hp = max_hp
    player.is_alive = alive
    player.is_chained = chained
    player.is_dying = False
    player.equipment = MagicMock()
    player.equipment.armor = None
    player.hand = []
    player.hero = MagicMock()
    player.hero.name = name + "_hero"
    player.has_skill = MagicMock(return_value=False)

    def take_damage(dmg, src=None):
        player.hp -= dmg
        if player.hp <= 0:
            player.is_dying = True

    player.take_damage = take_damage
    return player


class TestDamageSystemDealDamage:
    def test_normal_damage(self):
        engine = _make_engine()
        ds = DamageSystem(engine)
        target = _make_player("T", hp=4)

        result = ds.deal_damage(None, target, 1)
        assert result.actual_damage == 1
        assert result.target_died is False
        assert target.hp == 3

    def test_zero_damage_ignored(self):
        engine = _make_engine()
        ds = DamageSystem(engine)
        target = _make_player("T")

        result = ds.deal_damage(None, target, 0)
        assert result.actual_damage == 0
        assert target.hp == 4  # unchanged

    def test_negative_damage_ignored(self):
        engine = _make_engine()
        ds = DamageSystem(engine)
        target = _make_player("T")

        result = ds.deal_damage(None, target, -1)
        assert result.actual_damage == 0

    def test_dead_target_ignored(self):
        engine = _make_engine()
        ds = DamageSystem(engine)
        target = _make_player("T", alive=False)

        result = ds.deal_damage(None, target, 2)
        assert result.actual_damage == 0

    def test_source_name_in_log(self):
        engine = _make_engine()
        ds = DamageSystem(engine)
        source = _make_player("Attacker")
        target = _make_player("Target")

        ds.deal_damage(source, target, 1)
        engine.log_event.assert_called()

    def test_fire_damage_with_tengjia(self):
        engine = _make_engine()
        ds = DamageSystem(engine)
        target = _make_player("T", hp=4)
        target.equipment.armor = MagicMock()
        target.equipment.armor.name = CardName.TENGJIA

        result = ds.deal_damage(None, target, 1, "fire")
        assert result.actual_damage == 2  # 1 base + 1 tengjia

    def test_baiyinshizi_caps_damage(self):
        engine = _make_engine()
        ds = DamageSystem(engine)
        target = _make_player("T", hp=4)
        target.equipment.armor = MagicMock()
        target.equipment.armor.name = CardName.BAIYINSHIZI

        result = ds.deal_damage(None, target, 3, "normal")
        assert result.actual_damage == 1  # capped to 1

    def test_fire_chain_triggered(self):
        engine = _make_engine()
        target = _make_player("T", hp=4, chained=True)
        # Make break_chain actually set is_chained to False
        target.break_chain = lambda: setattr(target, 'is_chained', False)
        p2 = _make_player("P2", hp=4, chained=True)
        p2.break_chain = lambda: setattr(p2, 'is_chained', False)
        engine.players = [target, p2]

        ds = DamageSystem(engine)
        result = ds.deal_damage(None, target, 1, "fire")
        assert result.chain_triggered is True
        assert target.is_chained is False  # broken by break_chain

    def test_no_chain_for_normal_damage(self):
        engine = _make_engine()
        target = _make_player("T", hp=4, chained=True)
        engine.players = [target]

        ds = DamageSystem(engine)
        result = ds.deal_damage(None, target, 1, "normal")
        assert result.chain_triggered is False


class TestDamageSystemHelpers:
    def test_ai_should_save_same_identity(self):
        from game.player import Identity
        engine = _make_engine()
        ds = DamageSystem(engine)

        savior = MagicMock()
        savior.identity = Identity.REBEL
        dying = MagicMock()
        dying.identity = Identity.REBEL

        assert ds._ai_should_save(savior, dying) is True

    def test_ai_should_save_loyalist_for_lord(self):
        from game.player import Identity
        engine = _make_engine()
        ds = DamageSystem(engine)

        savior = MagicMock()
        savior.identity = Identity.LOYALIST
        dying = MagicMock()
        dying.identity = Identity.LORD

        assert ds._ai_should_save(savior, dying) is True

    def test_ai_spy_not_save_lord_late(self):
        from game.player import Identity
        engine = _make_engine()
        engine.get_alive_players.return_value = [MagicMock(), MagicMock()]
        ds = DamageSystem(engine)

        savior = MagicMock()
        savior.identity = Identity.SPY
        dying = MagicMock()
        dying.identity = Identity.LORD

        assert ds._ai_should_save(savior, dying) is False

    def test_ai_should_not_save_enemy(self):
        from game.player import Identity
        engine = _make_engine()
        ds = DamageSystem(engine)

        savior = MagicMock()
        savior.identity = Identity.REBEL
        dying = MagicMock()
        dying.identity = Identity.LOYALIST

        assert ds._ai_should_save(savior, dying) is False

    def test_handle_rewards_rebel_kill(self):
        from game.player import Identity
        engine = _make_engine()
        killer = _make_player("Killer")
        killer.identity = Identity.LORD
        engine.current_player = killer
        engine.deck.draw.return_value = [MagicMock(), MagicMock(), MagicMock()]

        ds = DamageSystem(engine)

        dead = MagicMock()
        dead.identity = Identity.REBEL
        ds._handle_rewards_and_penalties(dead)

        engine.deck.draw.assert_called_with(3)
        killer.draw_cards.assert_called_once()

    def test_handle_rewards_lord_kills_loyalist(self):
        from game.player import Identity
        engine = _make_engine()
        killer = _make_player("Lord")
        killer.identity = Identity.LORD
        engine.current_player = killer

        ds = DamageSystem(engine)

        dead = MagicMock()
        dead.identity = Identity.LOYALIST
        ds._handle_rewards_and_penalties(dead)

        # Lord should discard all cards
        engine.deck.discard.assert_called()
