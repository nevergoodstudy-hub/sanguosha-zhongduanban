# -*- coding: utf-8 -*-
"""距离与座位环的性质测试（Property-based）。

核心不变量：
1. 自己到自己的距离为 0
2. 相邻座位的基础距离为 1（无装备修正时）
3. 距离的对称性：无装备时 dist(A,B) == dist(B,A)
4. 距离 ≥ 1（对不同玩家）
5. +1马 只增大别人到自己的距离，-1马 只减小自己到别人的距离
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from game.card import Card, CardType, CardSubtype, CardSuit
from game.player import Player, Equipment


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _make_players(n: int) -> list[Player]:
    """创建 n 个存活玩家，无装备。"""
    return [
        Player(id=i, name=f"P{i}", is_ai=True, seat=i, hp=4, max_hp=4)
        for i in range(n)
    ]


def _make_horse(subtype: CardSubtype) -> Card:
    """创建一匹坐骑牌。"""
    return Card(
        id="horse_test",
        name="测试马",
        card_type=CardType.EQUIPMENT,
        subtype=subtype,
        suit=CardSuit.HEART,
        number=5,
        distance_modifier=-1 if subtype == CardSubtype.HORSE_MINUS else 1,
    )


class _FakeEngine:
    """仅实现距离计算所需的最小引擎替身。"""

    def __init__(self, players: list[Player]):
        self.players = players

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players if p.is_alive]

    def calculate_distance(self, from_p: Player, to_p: Player) -> int:
        """与 GameEngine.calculate_distance 完全一致的逻辑复制。"""
        if from_p == to_p:
            return 0

        alive = self.get_alive_players()
        if len(alive) <= 1:
            return 0

        try:
            fi = alive.index(from_p)
            ti = alive.index(to_p)
        except ValueError:
            return 999

        n = len(alive)
        cw = (ti - fi) % n
        ccw = (fi - ti) % n
        base = min(cw, ccw)

        mod = from_p.equipment.distance_to_others
        mod += to_p.equipment.distance_from_others

        return max(1, base + mod)


# ---------------------------------------------------------------------------
# 性质 1: 自己到自己距离为 0
# ---------------------------------------------------------------------------

@given(n=st.integers(min_value=2, max_value=10))
@settings(max_examples=50)
def test_distance_to_self_is_zero(n: int) -> None:
    players = _make_players(n)
    eng = _FakeEngine(players)
    for p in players:
        assert eng.calculate_distance(p, p) == 0


# ---------------------------------------------------------------------------
# 性质 2: 无装备时距离对称
# ---------------------------------------------------------------------------

@given(
    n=st.integers(min_value=2, max_value=10),
    data=st.data(),
)
@settings(max_examples=100)
def test_distance_symmetry_no_equipment(n: int, data: st.DataObject) -> None:
    players = _make_players(n)
    eng = _FakeEngine(players)

    i = data.draw(st.integers(min_value=0, max_value=n - 1))
    j = data.draw(st.integers(min_value=0, max_value=n - 1))
    assume(i != j)

    assert eng.calculate_distance(players[i], players[j]) == \
           eng.calculate_distance(players[j], players[i])


# ---------------------------------------------------------------------------
# 性质 3: 不同玩家之间距离 ≥ 1
# ---------------------------------------------------------------------------

@given(
    n=st.integers(min_value=2, max_value=10),
    data=st.data(),
)
@settings(max_examples=100)
def test_distance_minimum_is_one(n: int, data: st.DataObject) -> None:
    players = _make_players(n)
    eng = _FakeEngine(players)

    i = data.draw(st.integers(min_value=0, max_value=n - 1))
    j = data.draw(st.integers(min_value=0, max_value=n - 1))
    assume(i != j)

    assert eng.calculate_distance(players[i], players[j]) >= 1


# ---------------------------------------------------------------------------
# 性质 4: +1马 增大别人到自己的距离（单调性）
# ---------------------------------------------------------------------------

@given(
    n=st.integers(min_value=3, max_value=10),
    data=st.data(),
)
@settings(max_examples=100)
def test_plus_horse_increases_distance_from_others(n: int, data: st.DataObject) -> None:
    players = _make_players(n)
    eng = _FakeEngine(players)

    target_idx = data.draw(st.integers(min_value=0, max_value=n - 1))
    attacker_idx = data.draw(st.integers(min_value=0, max_value=n - 1))
    assume(target_idx != attacker_idx)

    target = players[target_idx]
    attacker = players[attacker_idx]

    dist_before = eng.calculate_distance(attacker, target)

    # 给 target 装上 +1马
    target.equipment = Equipment(horse_plus=_make_horse(CardSubtype.HORSE_PLUS))

    dist_after = eng.calculate_distance(attacker, target)

    assert dist_after >= dist_before, (
        f"+1马 应使距离不减少：{dist_before} -> {dist_after}"
    )


# ---------------------------------------------------------------------------
# 性质 5: -1马 减小自己到别人的距离（单调性）
# ---------------------------------------------------------------------------

@given(
    n=st.integers(min_value=3, max_value=10),
    data=st.data(),
)
@settings(max_examples=100)
def test_minus_horse_decreases_distance_to_others(n: int, data: st.DataObject) -> None:
    players = _make_players(n)
    eng = _FakeEngine(players)

    attacker_idx = data.draw(st.integers(min_value=0, max_value=n - 1))
    target_idx = data.draw(st.integers(min_value=0, max_value=n - 1))
    assume(attacker_idx != target_idx)

    attacker = players[attacker_idx]
    target = players[target_idx]

    dist_before = eng.calculate_distance(attacker, target)

    # 给 attacker 装上 -1马
    attacker.equipment = Equipment(horse_minus=_make_horse(CardSubtype.HORSE_MINUS))

    dist_after = eng.calculate_distance(attacker, target)

    assert dist_after <= dist_before, (
        f"-1马 应使距离不增加：{dist_before} -> {dist_after}"
    )
