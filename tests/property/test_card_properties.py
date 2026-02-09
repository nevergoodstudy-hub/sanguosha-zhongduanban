"""Card 卡牌系统的性质测试（Property-based）。

核心不变量：
1. 每张牌恰好是红色或黑色之一
2. 花色符号映射完备（4种花色都有符号）
3. 点数字符串映射正确（A/J/Q/K 以及数字）
4. display_name 总是包含 name + suit_symbol + number_str
5. to_dict / from_dict 序列化往返不丢失数据
6. Equipment equip/unequip 装备槽位不变量
7. Equipment equip 替换旧装备并正确返回
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hypothesis import given, settings
from hypothesis import strategies as st

from game.card import (
    Card,
    CardSubtype,
    CardSuit,
    CardType,
)
from game.player import Equipment, EquipmentSlot

# ---------------------------------------------------------------------------
# 辅助策略
# ---------------------------------------------------------------------------

card_suits = st.sampled_from(list(CardSuit))
card_numbers = st.integers(min_value=1, max_value=13)
basic_subtypes = st.sampled_from([CardSubtype.ATTACK, CardSubtype.DODGE, CardSubtype.HEAL])


@st.composite
def card_strategy(draw, card_type=CardType.BASIC, subtype=None):
    """生成一张随机基本牌。"""
    suit = draw(card_suits)
    number = draw(card_numbers)
    sub = subtype or draw(basic_subtypes)
    return Card(
        id=f"prop_{draw(st.integers(min_value=0, max_value=9999))}",
        name="测试牌",
        card_type=card_type,
        subtype=sub,
        suit=suit,
        number=number,
    )


def _make_equip_card(subtype: CardSubtype, idx: int = 0) -> Card:
    """创建一张指定子类型的装备牌。"""
    return Card(
        id=f"equip_{subtype.value}_{idx}",
        name=f"测试{subtype.value}",
        card_type=CardType.EQUIPMENT,
        subtype=subtype,
        suit=CardSuit.SPADE,
        number=1,
        range=3 if subtype == CardSubtype.WEAPON else 1,
        distance_modifier=-1 if subtype == CardSubtype.HORSE_MINUS else (
            1 if subtype == CardSubtype.HORSE_PLUS else 0
        ),
    )


# ---------------------------------------------------------------------------
# 性质 1: 每张牌恰好是红色或黑色之一（互斥且完备）
# ---------------------------------------------------------------------------

@given(suit=card_suits)
@settings(max_examples=20)
def test_suit_color_mutually_exclusive(suit: CardSuit) -> None:
    assert suit.is_red != suit.is_black, (
        f"花色 {suit} 应恰好属于红色或黑色之一"
    )


@given(card=card_strategy())
@settings(max_examples=100)
def test_card_color_matches_suit(card: Card) -> None:
    assert card.is_red == card.suit.is_red
    assert card.is_black == card.suit.is_black


# ---------------------------------------------------------------------------
# 性质 2: 花色符号映射完备
# ---------------------------------------------------------------------------

@given(suit=card_suits)
@settings(max_examples=20)
def test_suit_symbol_is_valid(suit: CardSuit) -> None:
    assert suit.symbol in ("♠", "♥", "♣", "♦"), (
        f"花色 {suit} 的符号 {suit.symbol} 不在合法集合内"
    )


# ---------------------------------------------------------------------------
# 性质 3: 点数字符串映射正确
# ---------------------------------------------------------------------------

@given(number=card_numbers)
@settings(max_examples=20)
def test_number_str_mapping(number: int) -> None:
    card = Card(
        id="t", name="t", card_type=CardType.BASIC,
        subtype=CardSubtype.ATTACK, suit=CardSuit.HEART, number=number,
    )
    expected = {1: "A", 11: "J", 12: "Q", 13: "K"}
    if number in expected:
        assert card.number_str == expected[number]
    else:
        assert card.number_str == str(number)


# ---------------------------------------------------------------------------
# 性质 4: display_name 组成结构
# ---------------------------------------------------------------------------

@given(card=card_strategy())
@settings(max_examples=100)
def test_display_name_structure(card: Card) -> None:
    dn = card.display_name
    assert card.name in dn
    assert card.suit_symbol in dn
    assert card.number_str in dn


# ---------------------------------------------------------------------------
# 性质 5: to_dict / from_dict 往返不丢失数据
# ---------------------------------------------------------------------------

@given(
    suit=card_suits,
    number=card_numbers,
    range_val=st.integers(min_value=1, max_value=10),
    dist_mod=st.integers(min_value=-2, max_value=2),
)
@settings(max_examples=100)
def test_card_serialization_roundtrip(
    suit: CardSuit, number: int, range_val: int, dist_mod: int,
) -> None:
    original = Card(
        id="rt_test",
        name="往返牌",
        card_type=CardType.BASIC,
        subtype=CardSubtype.ATTACK,
        suit=suit,
        number=number,
        description="测试描述",
        range=range_val,
        distance_modifier=dist_mod,
    )
    d = original.to_dict()
    restored = Card.from_dict(d)

    assert restored.id == original.id
    assert restored.name == original.name
    assert restored.card_type == original.card_type
    assert restored.subtype == original.subtype
    assert restored.suit == original.suit
    assert restored.number == original.number
    assert restored.description == original.description
    assert restored.range == original.range
    assert restored.distance_modifier == original.distance_modifier


# ---------------------------------------------------------------------------
# 性质 6: Equipment equip 放入正确的槽位
# ---------------------------------------------------------------------------

@given(subtype=st.sampled_from([
    CardSubtype.WEAPON, CardSubtype.ARMOR,
    CardSubtype.HORSE_MINUS, CardSubtype.HORSE_PLUS,
]))
@settings(max_examples=20)
def test_equip_places_in_correct_slot(subtype: CardSubtype) -> None:
    equip = Equipment()
    card = _make_equip_card(subtype)
    old = equip.equip(card)

    assert old is None  # 空槽应返回 None

    slot_map = {
        CardSubtype.WEAPON: equip.weapon,
        CardSubtype.ARMOR: equip.armor,
        CardSubtype.HORSE_MINUS: equip.horse_minus,
        CardSubtype.HORSE_PLUS: equip.horse_plus,
    }
    assert slot_map[subtype] is card


# ---------------------------------------------------------------------------
# 性质 7: Equipment equip 替换后返回旧装备
# ---------------------------------------------------------------------------

@given(subtype=st.sampled_from([
    CardSubtype.WEAPON, CardSubtype.ARMOR,
    CardSubtype.HORSE_MINUS, CardSubtype.HORSE_PLUS,
]))
@settings(max_examples=20)
def test_equip_replace_returns_old(subtype: CardSubtype) -> None:
    equip = Equipment()
    old_card = _make_equip_card(subtype, idx=0)
    new_card = _make_equip_card(subtype, idx=1)

    equip.equip(old_card)
    replaced = equip.equip(new_card)

    assert replaced is old_card


# ---------------------------------------------------------------------------
# 性质 8: unequip 后槽位为空
# ---------------------------------------------------------------------------

@given(
    subtype=st.sampled_from([
        CardSubtype.WEAPON, CardSubtype.ARMOR,
        CardSubtype.HORSE_MINUS, CardSubtype.HORSE_PLUS,
    ]),
)
@settings(max_examples=20)
def test_unequip_clears_slot(subtype: CardSubtype) -> None:
    equip = Equipment()
    card = _make_equip_card(subtype)
    equip.equip(card)

    slot_enum_map = {
        CardSubtype.WEAPON: EquipmentSlot.WEAPON,
        CardSubtype.ARMOR: EquipmentSlot.ARMOR,
        CardSubtype.HORSE_MINUS: EquipmentSlot.HORSE_MINUS,
        CardSubtype.HORSE_PLUS: EquipmentSlot.HORSE_PLUS,
    }
    removed = equip.unequip(slot_enum_map[subtype])

    assert removed is card
    assert equip.get_card_by_slot(slot_enum_map[subtype]) is None


# ---------------------------------------------------------------------------
# 性质 9: Equipment.count 始终等于非空槽位数
# ---------------------------------------------------------------------------

@given(
    equip_flags=st.tuples(st.booleans(), st.booleans(), st.booleans(), st.booleans()),
)
@settings(max_examples=50)
def test_equipment_count_matches_filled_slots(
    equip_flags: tuple[bool, bool, bool, bool],
) -> None:
    equip = Equipment()
    subtypes = [CardSubtype.WEAPON, CardSubtype.ARMOR,
                CardSubtype.HORSE_MINUS, CardSubtype.HORSE_PLUS]

    expected = 0
    for flag, sub in zip(equip_flags, subtypes):
        if flag:
            equip.equip(_make_equip_card(sub))
            expected += 1

    assert equip.count == expected
    assert len(equip.get_all_cards()) == expected
    assert equip.has_equipment() == (expected > 0)


# ---------------------------------------------------------------------------
# 性质 10: attack_range 默认为 1，装备武器后为武器 range
# ---------------------------------------------------------------------------

@given(weapon_range=st.integers(min_value=1, max_value=10))
@settings(max_examples=50)
def test_attack_range_with_weapon(weapon_range: int) -> None:
    equip = Equipment()
    assert equip.attack_range == 1  # 默认值

    weapon = Card(
        id="w", name="测试武器", card_type=CardType.EQUIPMENT,
        subtype=CardSubtype.WEAPON, suit=CardSuit.SPADE, number=1,
        range=weapon_range,
    )
    equip.equip(weapon)
    assert equip.attack_range == weapon_range


# ---------------------------------------------------------------------------
# 性质 11: distance_to_others 和 distance_from_others 的语义
# ---------------------------------------------------------------------------

def test_distance_modifiers_semantics() -> None:
    equip = Equipment()
    assert equip.distance_to_others == 0
    assert equip.distance_from_others == 0

    equip.equip(_make_equip_card(CardSubtype.HORSE_MINUS))
    assert equip.distance_to_others == -1
    assert equip.distance_from_others == 0

    equip.equip(_make_equip_card(CardSubtype.HORSE_PLUS))
    assert equip.distance_to_others == -1
    assert equip.distance_from_others == 1
