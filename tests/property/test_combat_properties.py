"""Combat 战斗系统的性质测试（Property-based）。

核心不变量：
1. 伤害 + 满血回复 后，hp == max_hp（若未死亡）
2. use_alcohol 只能成功一次/回合
3. consume_drunk 消耗酒状态后恢复
4. use_sha 单调递增 sha_count
5. can_use_sha 默认每回合限一次（无特殊装备/技能）
6. 多回合场景：reset_turn 后恢复初始战斗状态
7. 连续伤害序列 HP 严格递减
8. 过度治疗 = 0（已满血时 heal 不会超额）
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from game.player import Player

# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------


def _make_player(hp: int = 4, max_hp: int = 4) -> Player:
    return Player(id=0, name="战斗测试", is_ai=True, seat=0, hp=hp, max_hp=max_hp)


# ---------------------------------------------------------------------------
# 性质 1: 非致死伤害 + 满额回复 → hp == max_hp
# ---------------------------------------------------------------------------


@given(
    max_hp=st.integers(min_value=1, max_value=10),
    damage=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=200)
def test_damage_then_full_heal_restores_hp(max_hp: int, damage: int) -> None:
    assume(damage < max_hp)  # 非致死
    p = _make_player(hp=max_hp, max_hp=max_hp)
    p.take_damage(damage)
    p.heal(max_hp)  # 足够大的回复量
    assert p.hp == max_hp


# ---------------------------------------------------------------------------
# 性质 2: use_alcohol 每回合只能成功一次
# ---------------------------------------------------------------------------


@given(attempts=st.integers(min_value=1, max_value=10))
@settings(max_examples=50)
def test_alcohol_once_per_turn(attempts: int) -> None:
    p = _make_player()
    results = [p.use_alcohol() for _ in range(attempts)]

    # 第一次成功，之后都失败
    assert results[0] is True
    assert all(r is False for r in results[1:])
    assert p.alcohol_used is True


# ---------------------------------------------------------------------------
# 性质 3: consume_drunk 只返回 True 一次
# ---------------------------------------------------------------------------


def test_consume_drunk_once() -> None:
    p = _make_player()
    assert p.consume_drunk() is False  # 未饮酒

    p.use_alcohol()
    assert p.is_drunk is True

    assert p.consume_drunk() is True
    assert p.is_drunk is False
    assert p.consume_drunk() is False  # 已消耗


# ---------------------------------------------------------------------------
# 性质 4: use_sha 单调递增
# ---------------------------------------------------------------------------


@given(n_uses=st.integers(min_value=1, max_value=20))
@settings(max_examples=50)
def test_sha_count_monotonic(n_uses: int) -> None:
    p = _make_player()
    prev = 0
    for _ in range(n_uses):
        p.use_sha()
        assert p.sha_count == prev + 1
        prev = p.sha_count


# ---------------------------------------------------------------------------
# 性质 5: can_use_sha 默认每回合限一次
# ---------------------------------------------------------------------------


@given(n_shas=st.integers(min_value=0, max_value=5))
@settings(max_examples=20)
def test_can_use_sha_default_limit(n_shas: int) -> None:
    p = _make_player()  # 无诸葛连弩，无咸哮
    for i in range(n_shas):
        p.use_sha()

    if n_shas < 1:
        assert p.can_use_sha() is True
    else:
        assert p.can_use_sha() is False


# ---------------------------------------------------------------------------
# 性质 6: reset_turn 后可再使用杀和酒
# ---------------------------------------------------------------------------


@given(n_turns=st.integers(min_value=1, max_value=5))
@settings(max_examples=20)
def test_reset_turn_restores_combat_state(n_turns: int) -> None:
    p = _make_player()
    for _ in range(n_turns):
        p.use_sha()
        p.use_alcohol()
        assert not p.can_use_sha()
        assert p.alcohol_used

        p.reset_turn()
        assert p.can_use_sha()
        assert not p.alcohol_used
        assert not p.is_drunk


# ---------------------------------------------------------------------------
# 性质 7: 连续伤害序列使 HP 严格递减
# ---------------------------------------------------------------------------


@given(
    damages=st.lists(
        st.integers(min_value=1, max_value=5),
        min_size=1,
        max_size=10,
    ),
)
@settings(max_examples=100)
def test_consecutive_damage_decreases_hp(damages: list[int]) -> None:
    p = _make_player(hp=100, max_hp=100)
    prev_hp = p.hp
    for dmg in damages:
        p.take_damage(dmg)
        assert p.hp < prev_hp, f"hp should decrease: {prev_hp} -> {p.hp}"
        prev_hp = p.hp


# ---------------------------------------------------------------------------
# 性质 8: 满血回复 = 0（不会超额回复）
# ---------------------------------------------------------------------------


@given(
    max_hp=st.integers(min_value=1, max_value=10),
    heal_amount=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=100)
def test_heal_at_full_hp_is_zero(max_hp: int, heal_amount: int) -> None:
    p = _make_player(hp=max_hp, max_hp=max_hp)
    actual = p.heal(heal_amount)
    assert actual == 0
    assert p.hp == max_hp


# ---------------------------------------------------------------------------
# 性质 9: 伤害-回复 交替序列的 HP 边界
# ---------------------------------------------------------------------------


@given(
    max_hp=st.integers(min_value=3, max_value=10),
    ops=st.lists(
        st.tuples(
            st.sampled_from(["damage", "heal"]),
            st.integers(min_value=1, max_value=5),
        ),
        min_size=1,
        max_size=20,
    ),
)
@settings(max_examples=200)
def test_damage_heal_sequence_hp_bounded(max_hp: int, ops: list) -> None:
    """HP 始终 ≤ max_hp（下限不受约束因可以为负数进入濒死）。"""
    p = _make_player(hp=max_hp, max_hp=max_hp)

    for op, val in ops:
        if op == "damage":
            p.take_damage(val)
        else:
            p.heal(val)
        # 上限不变量
        assert p.hp <= p.max_hp, f"hp {p.hp} exceeds max_hp {p.max_hp}"


# ---------------------------------------------------------------------------
# 性质 10: 濒死→回复→脱离濒死
# ---------------------------------------------------------------------------


@given(
    max_hp=st.integers(min_value=2, max_value=10),
    overkill=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100)
def test_dying_healed_back(max_hp: int, overkill: int) -> None:
    p = _make_player(hp=max_hp, max_hp=max_hp)
    p.take_damage(max_hp + overkill)  # 致死伤害

    assert p.is_dying
    assert p.hp <= 0

    p.heal(max_hp + overkill + 1)  # 足够的回复
    assert not p.is_dying
    assert p.hp > 0
    assert p.hp <= max_hp


# ---------------------------------------------------------------------------
# 性质 11: 酒后杀 → consume_drunk 恰好触发一次
# ---------------------------------------------------------------------------


@given(n_sha=st.integers(min_value=1, max_value=5))
@settings(max_examples=30)
def test_drunk_consumed_on_first_sha_only(n_sha: int) -> None:
    p = _make_player()
    p.use_alcohol()

    consumed = []
    for _ in range(n_sha):
        consumed.append(p.consume_drunk())

    assert consumed[0] is True, "第一次杀应消耗酒状态"
    assert all(c is False for c in consumed[1:]), "后续杀不应再有酒加成"


# ---------------------------------------------------------------------------
# 性质 12: break_chain 总是将 is_chained 设为 False
# ---------------------------------------------------------------------------


@given(initial=st.booleans())
@settings(max_examples=10)
def test_break_chain_always_false(initial: bool) -> None:
    p = _make_player()
    p.is_chained = initial
    p.break_chain()
    assert not p.is_chained
