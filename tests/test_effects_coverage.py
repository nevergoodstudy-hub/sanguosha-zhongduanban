"""Tests for game.effects.basic and game.effects.trick — can_use branches."""

from unittest.mock import MagicMock

from game.effects.basic import JiuEffect, ShaEffect, TaoEffect
from game.effects.trick import (
    BingliangEffect,
    GuoheEffect,
    HuogongEffect,
    JuedouEffect,
    LebusishuEffect,
    NanmanEffect,
    ShandianEffect,
    ShunshouEffect,
    TaoyuanEffect,
    TiesuoEffect,
    WanjianEffect,
    WuzhongEffect,
)

# ==================== Basic effects ====================

class TestShaEffect:
    def test_needs_target(self):
        assert ShaEffect().needs_target is True

    def test_can_use_no_targets(self):
        ok, msg = ShaEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is False
        assert "目标" in msg

    def test_can_use_sha_limit(self):
        player = MagicMock()
        player.can_use_sha.return_value = False
        ok, msg = ShaEffect().can_use(MagicMock(), player, MagicMock(), [MagicMock()])
        assert ok is False
        assert "使用过杀" in msg

    def test_can_use_out_of_range(self):
        player = MagicMock()
        player.can_use_sha.return_value = True
        engine = MagicMock()
        engine.is_in_attack_range.return_value = False
        target = MagicMock()

        ok, msg = ShaEffect().can_use(engine, player, MagicMock(), [target])
        assert ok is False
        assert "范围" in msg

    def test_can_use_ok(self):
        player = MagicMock()
        player.can_use_sha.return_value = True
        engine = MagicMock()
        engine.is_in_attack_range.return_value = True

        ok, msg = ShaEffect().can_use(engine, player, MagicMock(), [MagicMock()])
        assert ok is True

    def test_resolve_delegates(self):
        engine = MagicMock()
        engine._use_sha.return_value = True
        player = MagicMock()
        card = MagicMock()
        targets = [MagicMock()]

        ShaEffect().resolve(engine, player, card, targets)
        engine._use_sha.assert_called_once_with(player, card, targets)


class TestTaoEffect:
    def test_needs_target_default(self):
        assert TaoEffect().needs_target is False

    def test_can_use_hp_full(self):
        player = MagicMock()
        player.hp = 4
        player.max_hp = 4
        ok, msg = TaoEffect().can_use(MagicMock(), player, MagicMock(), [])
        assert ok is False
        assert "已满" in msg

    def test_can_use_ok(self):
        player = MagicMock()
        player.hp = 2
        player.max_hp = 4
        ok, msg = TaoEffect().can_use(MagicMock(), player, MagicMock(), [])
        assert ok is True

    def test_resolve_delegates(self):
        engine = MagicMock()
        player = MagicMock()
        card = MagicMock()
        TaoEffect().resolve(engine, player, card, [])
        engine._use_tao.assert_called_once_with(player, card)


class TestJiuEffect:
    def test_can_use_dying(self):
        player = MagicMock()
        player.is_dying = True
        ok, msg = JiuEffect().can_use(MagicMock(), player, MagicMock(), [])
        assert ok is True

    def test_can_use_already_used(self):
        player = MagicMock()
        player.is_dying = False
        player.alcohol_used = True
        ok, msg = JiuEffect().can_use(MagicMock(), player, MagicMock(), [])
        assert ok is False
        assert "酒" in msg

    def test_can_use_ok(self):
        player = MagicMock()
        player.is_dying = False
        player.alcohol_used = False
        ok, msg = JiuEffect().can_use(MagicMock(), player, MagicMock(), [])
        assert ok is True

    def test_resolve_delegates(self):
        engine = MagicMock()
        player = MagicMock()
        card = MagicMock()
        JiuEffect().resolve(engine, player, card, [])
        engine._use_jiu.assert_called_once_with(player, card)


# ==================== Trick effects ====================

class TestTrickEffectsNeedsTarget:
    def test_juedou_needs_target(self):
        assert JuedouEffect().needs_target is True

    def test_guohe_needs_target(self):
        assert GuoheEffect().needs_target is True

    def test_shunshou_needs_target(self):
        assert ShunshouEffect().needs_target is True

    def test_lebusishu_needs_target(self):
        assert LebusishuEffect().needs_target is True

    def test_bingliang_needs_target(self):
        assert BingliangEffect().needs_target is True

    def test_huogong_needs_target(self):
        assert HuogongEffect().needs_target is True

    def test_nanman_default_target(self):
        assert NanmanEffect().needs_target is False

    def test_wanjian_default_target(self):
        assert WanjianEffect().needs_target is False

    def test_wuzhong_default_target(self):
        assert WuzhongEffect().needs_target is False

    def test_taoyuan_default_target(self):
        assert TaoyuanEffect().needs_target is False

    def test_shandian_default_target(self):
        assert ShandianEffect().needs_target is False

    def test_tiesuo_default_target(self):
        assert TiesuoEffect().needs_target is False


class TestTrickEffectsCanUse:
    """Test can_use for tricks that require targets."""

    def test_juedou_no_target(self):
        ok, msg = JuedouEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is False

    def test_juedou_with_target(self):
        ok, _ = JuedouEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [MagicMock()])
        assert ok is True

    def test_guohe_no_target(self):
        ok, _ = GuoheEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is False

    def test_shunshou_no_target(self):
        ok, _ = ShunshouEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is False

    def test_lebusishu_no_target(self):
        ok, _ = LebusishuEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is False

    def test_bingliang_no_target(self):
        ok, _ = BingliangEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is False

    def test_huogong_no_target(self):
        ok, _ = HuogongEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is False

    def test_nanman_always_ok(self):
        ok, _ = NanmanEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is True

    def test_wanjian_always_ok(self):
        ok, _ = WanjianEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is True

    def test_wuzhong_always_ok(self):
        ok, _ = WuzhongEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is True

    def test_taoyuan_always_ok(self):
        ok, _ = TaoyuanEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is True

    def test_shandian_always_ok(self):
        ok, _ = ShandianEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is True

    def test_tiesuo_always_ok(self):
        ok, _ = TiesuoEffect().can_use(MagicMock(), MagicMock(), MagicMock(), [])
        assert ok is True


class TestTrickEffectsResolve:
    def test_nanman_resolve(self):
        engine = MagicMock()
        NanmanEffect().resolve(engine, MagicMock(), MagicMock(), [])
        engine._use_nanman.assert_called_once()

    def test_wanjian_resolve(self):
        engine = MagicMock()
        WanjianEffect().resolve(engine, MagicMock(), MagicMock(), [])
        engine._use_wanjian.assert_called_once()

    def test_wuzhong_resolve(self):
        engine = MagicMock()
        WuzhongEffect().resolve(engine, MagicMock(), MagicMock(), [])
        engine._use_wuzhong.assert_called_once()

    def test_guohe_resolve(self):
        engine = MagicMock()
        targets = [MagicMock()]
        GuoheEffect().resolve(engine, MagicMock(), MagicMock(), targets)
        engine._use_guohe.assert_called_once()

    def test_shunshou_resolve(self):
        engine = MagicMock()
        targets = [MagicMock()]
        ShunshouEffect().resolve(engine, MagicMock(), MagicMock(), targets)
        engine._use_shunshou.assert_called_once()

    def test_taoyuan_resolve(self):
        engine = MagicMock()
        TaoyuanEffect().resolve(engine, MagicMock(), MagicMock(), [])
        engine._use_taoyuan.assert_called_once()

    def test_juedou_resolve(self):
        engine = MagicMock()
        targets = [MagicMock()]
        JuedouEffect().resolve(engine, MagicMock(), MagicMock(), targets)
        engine._use_juedou.assert_called_once()

    def test_lebusishu_resolve(self):
        engine = MagicMock()
        targets = [MagicMock()]
        LebusishuEffect().resolve(engine, MagicMock(), MagicMock(), targets)
        engine._use_lebusishu.assert_called_once()

    def test_bingliang_resolve(self):
        engine = MagicMock()
        targets = [MagicMock()]
        BingliangEffect().resolve(engine, MagicMock(), MagicMock(), targets)
        engine._use_bingliang.assert_called_once()

    def test_shandian_resolve(self):
        engine = MagicMock()
        targets = [MagicMock()]
        ShandianEffect().resolve(engine, MagicMock(), MagicMock(), targets)
        engine._use_shandian.assert_called_once()

    def test_huogong_resolve(self):
        engine = MagicMock()
        targets = [MagicMock()]
        HuogongEffect().resolve(engine, MagicMock(), MagicMock(), targets)
        engine._use_huogong.assert_called_once()

    def test_tiesuo_resolve(self):
        engine = MagicMock()
        targets = [MagicMock()]
        TiesuoEffect().resolve(engine, MagicMock(), MagicMock(), targets)
        engine._use_tiesuo.assert_called_once()
