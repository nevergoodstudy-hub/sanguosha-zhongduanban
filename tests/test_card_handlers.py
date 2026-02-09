"""Tests for game.card_handlers module — registry pattern and handler management."""

from unittest.mock import MagicMock

from game.card_handlers import (
    CardHandlerInfo,
    CardHandlerRegistry,
    CardHandlerType,
    get_global_registry,
    init_default_handlers,
)


class TestCardHandlerType:
    def test_enum_values(self):
        assert CardHandlerType.BASIC is not None
        assert CardHandlerType.TRICK is not None
        assert CardHandlerType.DELAY_TRICK is not None
        assert CardHandlerType.EQUIPMENT is not None

    def test_all_four_types(self):
        assert len(CardHandlerType) == 4


class TestCardHandlerInfo:
    def test_creation(self):
        handler = lambda: None
        info = CardHandlerInfo(
            card_name="sha",
            handler_type=CardHandlerType.BASIC,
            handler=handler,
            requires_target=True,
            target_count=1,
        )
        assert info.card_name == "sha"
        assert info.handler_type == CardHandlerType.BASIC
        assert info.handler is handler
        assert info.requires_target is True
        assert info.target_count == 1

    def test_defaults(self):
        info = CardHandlerInfo(
            card_name="test",
            handler_type=CardHandlerType.TRICK,
            handler=lambda: None,
        )
        assert info.requires_target is False
        assert info.target_count == 1


class TestCardHandlerRegistry:
    def test_register_and_get(self):
        reg = CardHandlerRegistry()
        handler = MagicMock()
        reg.register("sha", handler, CardHandlerType.BASIC, requires_target=True)

        result = reg.get_handler("sha")
        assert result is handler

    def test_get_handler_not_found(self):
        reg = CardHandlerRegistry()
        assert reg.get_handler("nonexistent") is None

    def test_get_handler_info(self):
        reg = CardHandlerRegistry()
        handler = MagicMock()
        reg.register("tao", handler, CardHandlerType.BASIC)

        info = reg.get_handler_info("tao")
        assert isinstance(info, CardHandlerInfo)
        assert info.card_name == "tao"
        assert info.handler_type == CardHandlerType.BASIC

    def test_get_handler_info_not_found(self):
        reg = CardHandlerRegistry()
        assert reg.get_handler_info("missing") is None

    def test_has_handler(self):
        reg = CardHandlerRegistry()
        reg.register("sha", lambda: None, CardHandlerType.BASIC)
        assert reg.has_handler("sha") is True
        assert reg.has_handler("shan") is False

    def test_list_handlers_all(self):
        reg = CardHandlerRegistry()
        reg.register("sha", lambda: None, CardHandlerType.BASIC)
        reg.register("nanman", lambda: None, CardHandlerType.TRICK)
        reg.register("lebusishu", lambda: None, CardHandlerType.DELAY_TRICK)

        all_names = reg.list_handlers()
        assert "sha" in all_names
        assert "nanman" in all_names
        assert "lebusishu" in all_names

    def test_list_handlers_by_type(self):
        reg = CardHandlerRegistry()
        reg.register("sha", lambda: None, CardHandlerType.BASIC)
        reg.register("tao", lambda: None, CardHandlerType.BASIC)
        reg.register("nanman", lambda: None, CardHandlerType.TRICK)

        basics = reg.list_handlers(CardHandlerType.BASIC)
        assert set(basics) == {"sha", "tao"}

        tricks = reg.list_handlers(CardHandlerType.TRICK)
        assert tricks == ["nanman"]

    def test_list_handlers_empty_type(self):
        reg = CardHandlerRegistry()
        reg.register("sha", lambda: None, CardHandlerType.BASIC)
        assert reg.list_handlers(CardHandlerType.EQUIPMENT) == []

    def test_register_overwrites(self):
        reg = CardHandlerRegistry()
        handler1 = MagicMock(name="h1")
        handler2 = MagicMock(name="h2")
        reg.register("sha", handler1)
        reg.register("sha", handler2)
        assert reg.get_handler("sha") is handler2


class TestGetGlobalRegistry:
    def test_returns_registry(self):
        reg = get_global_registry()
        assert isinstance(reg, CardHandlerRegistry)

    def test_is_singleton(self):
        r1 = get_global_registry()
        r2 = get_global_registry()
        assert r1 is r2


class TestInitDefaultHandlers:
    def test_registers_expected_cards(self):
        reg = CardHandlerRegistry()
        engine = MagicMock()
        init_default_handlers(reg, engine)

        # Should have at least sha, tao, juedou, nanman, wanjian, wuzhong, guohe, shunshou, taoyuan,
        # lebusishu, bingliang, shandian, huogong
        assert reg.has_handler("杀")
        assert reg.has_handler("桃")
        assert reg.has_handler("决斗")
        assert reg.has_handler("南蛮入侵")
        assert reg.has_handler("万箭齐发")
        assert reg.has_handler("无中生有")
        assert reg.has_handler("过河拆桥")
        assert reg.has_handler("顺手牵羊")
        assert reg.has_handler("桃园结义")
        assert reg.has_handler("乐不思蜀")
        assert reg.has_handler("兵粮寸断")
        assert reg.has_handler("闪电")
        assert reg.has_handler("火攻")

    def test_handler_types_correct(self):
        reg = CardHandlerRegistry()
        engine = MagicMock()
        init_default_handlers(reg, engine)

        sha_info = reg.get_handler_info("杀")
        assert sha_info.handler_type == CardHandlerType.BASIC

        nanman_info = reg.get_handler_info("南蛮入侵")
        assert nanman_info.handler_type == CardHandlerType.TRICK

        lebu_info = reg.get_handler_info("乐不思蜀")
        assert lebu_info.handler_type == CardHandlerType.DELAY_TRICK
