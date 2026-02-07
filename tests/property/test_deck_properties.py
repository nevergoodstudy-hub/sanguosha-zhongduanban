# -*- coding: utf-8 -*-
"""Deck 牌堆操作的性质测试（Property-based）。

核心不变量：
1. draw(n) 返回的牌数 ≤ n，且 ≤ 牌堆总量
2. draw + discard 循环不会丢失也不会凭空产生牌
3. 牌堆 + 弃牌堆 + 已取出牌 = 初始总量
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from game.card import (
    Card,
    CardType,
    CardSubtype,
    CardSuit,
    Deck,
)


# ---------------------------------------------------------------------------
# 辅助：构造一个最小的 Deck（不依赖外部 JSON 文件）
# ---------------------------------------------------------------------------

def _make_card(idx: int) -> Card:
    """生成一张确定性测试卡牌。"""
    suits = list(CardSuit)
    return Card(
        id=f"test_{idx}",
        name="测试杀",
        card_type=CardType.BASIC,
        subtype=CardSubtype.ATTACK,
        suit=suits[idx % len(suits)],
        number=(idx % 13) + 1,
    )


def _make_deck(n_cards: int) -> Deck:
    """创建一个含有 n_cards 张牌的 Deck（不洗牌，便于确定性测试）。"""
    deck = Deck()  # 不加载 JSON
    deck._all_cards = [_make_card(i) for i in range(n_cards)]
    deck.draw_pile = list(deck._all_cards)
    deck.discard_pile = []
    return deck


# ---------------------------------------------------------------------------
# 性质 1: draw(n) 返回牌数 ≤ n，且 ≤ 牌堆总量
# ---------------------------------------------------------------------------

@given(
    total=st.integers(min_value=0, max_value=200),
    draw_n=st.integers(min_value=0, max_value=300),
)
@settings(max_examples=200)
def test_draw_returns_at_most_n_cards(total: int, draw_n: int) -> None:
    deck = _make_deck(total)
    drawn = deck.draw(draw_n)

    assert len(drawn) <= draw_n
    assert len(drawn) <= total


# ---------------------------------------------------------------------------
# 性质 2: draw + discard 循环后，总牌数不变
# ---------------------------------------------------------------------------

@given(
    total=st.integers(min_value=1, max_value=200),
    ops=st.lists(
        st.tuples(
            st.sampled_from(["draw", "discard"]),
            st.integers(min_value=1, max_value=50),
        ),
        min_size=1,
        max_size=30,
    ),
)
@settings(max_examples=200)
def test_total_cards_conserved(total: int, ops: list) -> None:
    """抽牌 + 弃牌操作序列后，draw_pile + discard_pile + hand 总数恒等于 total。"""
    deck = _make_deck(total)
    hand: list[Card] = []

    for op, n in ops:
        if op == "draw":
            drawn = deck.draw(n)
            hand.extend(drawn)
        else:  # discard
            to_discard = hand[:n]
            hand = hand[n:]
            deck.discard(to_discard)

    total_now = len(deck.draw_pile) + len(deck.discard_pile) + len(hand)
    assert total_now == total, (
        f"Card conservation violated: {total_now} != {total}"
    )


# ---------------------------------------------------------------------------
# 性质 3: draw 不返回重复对象引用（在同一次 draw 调用中）
# ---------------------------------------------------------------------------

@given(
    total=st.integers(min_value=2, max_value=200),
    draw_n=st.integers(min_value=2, max_value=100),
)
@settings(max_examples=200)
def test_draw_no_duplicate_references(total: int, draw_n: int) -> None:
    deck = _make_deck(total)
    drawn = deck.draw(draw_n)

    # 用 id() 检查对象引用唯一性
    ids = [id(c) for c in drawn]
    assert len(ids) == len(set(ids)), "draw() returned duplicate object references"


# ---------------------------------------------------------------------------
# 性质 4: reset 后，牌堆恢复到初始状态的数量
# ---------------------------------------------------------------------------

@given(total=st.integers(min_value=0, max_value=200))
@settings(max_examples=100)
def test_reset_restores_count(total: int) -> None:
    deck = _make_deck(total)

    # 随意抽一些牌
    deck.draw(total // 2)

    # reset
    deck.reset()

    assert len(deck.draw_pile) == total
    assert len(deck.discard_pile) == 0
