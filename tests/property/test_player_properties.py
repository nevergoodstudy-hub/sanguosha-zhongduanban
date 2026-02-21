"""Player 玩家系统的性质测试（Property-based）。

核心不变量：
1. heal 后 hp ≤ max_hp（上限不变量）
2. take_damage 后 hp ≤ 0 → is_dying
3. heal 实际回复量 = hp_after - hp_before
4. hand_limit == max(0, hp)
5. need_discard == max(0, hand_count - hand_limit)
6. draw_cards 增加 hand_count 恰好 len(cards)
7. remove_card 成功时减少 hand_count 恰好 1
8. die() 后 is_alive=False, is_dying=False
9. reset_turn 将回合状态清零
10. toggle_chain 是自反对合（调用两次恢复原状）
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from game.card import Card, CardSubtype, CardSuit, CardType
from game.player import Player

# ---------------------------------------------------------------------------
# 辅助策略
# ---------------------------------------------------------------------------


def _make_player(hp: int = 4, max_hp: int = 4) -> Player:
    """创建一个测试玩家。"""
    return Player(id=0, name="测试", is_ai=True, seat=0, hp=hp, max_hp=max_hp)


def _make_card(idx: int) -> Card:
    """创建一张测试手牌。"""
    return Card(
        id=f"h_{idx}",
        name="测试杀",
        card_type=CardType.BASIC,
        subtype=CardSubtype.ATTACK,
        suit=CardSuit.HEART,
        number=(idx % 13) + 1,
    )


# ---------------------------------------------------------------------------
# 性质 1: heal 后 hp ≤ max_hp
# ---------------------------------------------------------------------------


@given(
    max_hp=st.integers(min_value=1, max_value=10),
    current_hp=st.integers(min_value=-5, max_value=10),
    heal_amount=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=200)
def test_heal_respects_max_hp(max_hp: int, current_hp: int, heal_amount: int) -> None:
    assume(current_hp <= max_hp)
    p = _make_player(hp=current_hp, max_hp=max_hp)
    p.heal(heal_amount)
    assert p.hp <= p.max_hp, f"hp {p.hp} > max_hp {p.max_hp}"


# ---------------------------------------------------------------------------
# 性质 2: take_damage 使 hp 减少，hp ≤ 0 时进入濒死
# ---------------------------------------------------------------------------


@given(
    hp=st.integers(min_value=1, max_value=10),
    damage=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=200)
def test_take_damage_dying_threshold(hp: int, damage: int) -> None:
    p = _make_player(hp=hp, max_hp=hp)
    p.take_damage(damage)
    assert p.hp == hp - damage
    if p.hp <= 0:
        assert p.is_dying, f"hp={p.hp} ≤ 0 but is_dying=False"
    else:
        assert not p.is_dying


# ---------------------------------------------------------------------------
# 性质 3: heal 返回实际回复量
# ---------------------------------------------------------------------------


@given(
    max_hp=st.integers(min_value=1, max_value=10),
    current_hp=st.integers(min_value=-3, max_value=10),
    heal_amount=st.integers(min_value=0, max_value=15),
)
@settings(max_examples=200)
def test_heal_returns_actual_amount(max_hp: int, current_hp: int, heal_amount: int) -> None:
    assume(current_hp <= max_hp)
    p = _make_player(hp=current_hp, max_hp=max_hp)
    hp_before = p.hp
    actual = p.heal(heal_amount)
    assert actual == p.hp - hp_before
    assert actual >= 0


# ---------------------------------------------------------------------------
# 性质 4: hand_limit == max(0, hp)
# ---------------------------------------------------------------------------


@given(hp=st.integers(min_value=-5, max_value=10))
@settings(max_examples=100)
def test_hand_limit_equals_max_zero_hp(hp: int) -> None:
    p = _make_player(hp=hp, max_hp=10)
    assert p.hand_limit == max(0, hp)


# ---------------------------------------------------------------------------
# 性质 5: need_discard 不变量
# ---------------------------------------------------------------------------


@given(
    hp=st.integers(min_value=0, max_value=10),
    n_cards=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=200)
def test_need_discard_invariant(hp: int, n_cards: int) -> None:
    p = _make_player(hp=hp, max_hp=10)
    p.hand = [_make_card(i) for i in range(n_cards)]
    expected = max(0, n_cards - max(0, hp))
    assert p.need_discard == expected


# ---------------------------------------------------------------------------
# 性质 6: draw_cards 增加 hand_count 恰好 len(cards)
# ---------------------------------------------------------------------------


@given(
    initial=st.integers(min_value=0, max_value=10),
    add_count=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=100)
def test_draw_cards_increases_hand_count(initial: int, add_count: int) -> None:
    p = _make_player()
    p.hand = [_make_card(i) for i in range(initial)]
    new_cards = [_make_card(100 + i) for i in range(add_count)]
    p.draw_cards(new_cards)
    assert p.hand_count == initial + add_count


# ---------------------------------------------------------------------------
# 性质 7: remove_card 成功时 hand_count 减 1
# ---------------------------------------------------------------------------


@given(
    n_cards=st.integers(min_value=1, max_value=20),
    remove_idx=st.data(),
)
@settings(max_examples=100)
def test_remove_card_decreases_count(n_cards: int, remove_idx: st.DataObject) -> None:
    p = _make_player()
    cards = [_make_card(i) for i in range(n_cards)]
    p.hand = list(cards)

    idx = remove_idx.draw(st.integers(min_value=0, max_value=n_cards - 1))
    before = p.hand_count
    result = p.remove_card(cards[idx])

    assert result is True
    assert p.hand_count == before - 1


# ---------------------------------------------------------------------------
# 性质 8: remove_card 对不存在的牌返回 False，hand_count 不变
# ---------------------------------------------------------------------------


@given(n_cards=st.integers(min_value=0, max_value=10))
@settings(max_examples=50)
def test_remove_nonexistent_card_noop(n_cards: int) -> None:
    p = _make_player()
    p.hand = [_make_card(i) for i in range(n_cards)]
    fake = _make_card(999)
    before = p.hand_count
    result = p.remove_card(fake)
    assert result is False
    assert p.hand_count == before


# ---------------------------------------------------------------------------
# 性质 9: die() 后状态
# ---------------------------------------------------------------------------


def test_die_sets_flags() -> None:
    p = _make_player()
    p.is_dying = True
    p.die()
    assert not p.is_alive
    assert not p.is_dying


# ---------------------------------------------------------------------------
# 性质 10: reset_turn 清零回合状态
# ---------------------------------------------------------------------------


@given(
    sha_count=st.integers(min_value=0, max_value=10),
    is_drunk=st.booleans(),
    alcohol_used=st.booleans(),
    skip_play=st.booleans(),
    skip_draw=st.booleans(),
)
@settings(max_examples=100)
def test_reset_turn_clears_all(
    sha_count: int,
    is_drunk: bool,
    alcohol_used: bool,
    skip_play: bool,
    skip_draw: bool,
) -> None:
    p = _make_player()
    p.sha_count = sha_count
    p.is_drunk = is_drunk
    p.alcohol_used = alcohol_used
    p.skip_play_phase = skip_play
    p.skip_draw_phase = skip_draw
    p.skill_used = {"test": 3}

    p.reset_turn()

    assert p.sha_count == 0
    assert not p.is_drunk
    assert not p.alcohol_used
    assert not p.skip_play_phase
    assert not p.skip_draw_phase
    assert p.skill_used == {}


# ---------------------------------------------------------------------------
# 性质 11: toggle_chain 是对合映射（两次恢复原状）
# ---------------------------------------------------------------------------


@given(initial_chained=st.booleans())
@settings(max_examples=10)
def test_toggle_chain_involution(initial_chained: bool) -> None:
    p = _make_player()
    p.is_chained = initial_chained

    p.toggle_chain()
    assert p.is_chained != initial_chained

    p.toggle_chain()
    assert p.is_chained == initial_chained


# ---------------------------------------------------------------------------
# 性质 12: toggle_flip 也是对合映射
# ---------------------------------------------------------------------------


@given(initial_flipped=st.booleans())
@settings(max_examples=10)
def test_toggle_flip_involution(initial_flipped: bool) -> None:
    p = _make_player()
    p.flipped = initial_flipped

    p.toggle_flip()
    assert p.flipped != initial_flipped

    p.toggle_flip()
    assert p.flipped == initial_flipped


# ---------------------------------------------------------------------------
# 性质 13: get_all_cards = 手牌 + 装备牌
# ---------------------------------------------------------------------------


@given(
    n_hand=st.integers(min_value=0, max_value=10),
    has_weapon=st.booleans(),
    has_armor=st.booleans(),
)
@settings(max_examples=50)
def test_get_all_cards_is_hand_plus_equipment(
    n_hand: int,
    has_weapon: bool,
    has_armor: bool,
) -> None:
    p = _make_player()
    p.hand = [_make_card(i) for i in range(n_hand)]
    n_equip = 0
    if has_weapon:
        p.equipment.equip(
            Card(
                id="w",
                name="武器",
                card_type=CardType.EQUIPMENT,
                subtype=CardSubtype.WEAPON,
                suit=CardSuit.SPADE,
                number=1,
            )
        )
        n_equip += 1
    if has_armor:
        p.equipment.equip(
            Card(
                id="a",
                name="防具",
                card_type=CardType.EQUIPMENT,
                subtype=CardSubtype.ARMOR,
                suit=CardSuit.HEART,
                number=1,
            )
        )
        n_equip += 1

    all_cards = p.get_all_cards()
    assert len(all_cards) == n_hand + n_equip


# ---------------------------------------------------------------------------
# 性质 14: has_any_card 当且仅当 手牌>0 或 有装备
# ---------------------------------------------------------------------------


@given(
    n_hand=st.integers(min_value=0, max_value=5),
    has_equip=st.booleans(),
)
@settings(max_examples=50)
def test_has_any_card_iff(n_hand: int, has_equip: bool) -> None:
    p = _make_player()
    p.hand = [_make_card(i) for i in range(n_hand)]
    if has_equip:
        p.equipment.equip(
            Card(
                id="w",
                name="武器",
                card_type=CardType.EQUIPMENT,
                subtype=CardSubtype.WEAPON,
                suit=CardSuit.SPADE,
                number=1,
            )
        )

    assert p.has_any_card() == (n_hand > 0 or has_equip)
