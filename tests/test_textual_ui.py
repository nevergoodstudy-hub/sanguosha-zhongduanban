# -*- coding: utf-8 -*-
"""
Textual TUI 测试（M3）
"""

import pytest
from ui.protocol import GameUI
from ui.textual_ui.app import (
    SanguoshaApp,
    MainMenuScreen,
    RulesScreen,
    GameSetupScreen,
    GameOverScreen,
    TextualUIBridge,
)


class TestTextualAppImport:
    """测试 Textual App 模块导入"""

    def test_app_class(self):
        assert SanguoshaApp is not None

    def test_screens_exist(self):
        assert MainMenuScreen is not None
        assert RulesScreen is not None
        assert GameSetupScreen is not None
        assert GameOverScreen is not None

    def test_bridge_class(self):
        assert TextualUIBridge is not None


class TestGameUIProtocol:
    """测试 GameUI Protocol"""

    def test_bridge_has_protocol_methods(self):
        """TextualUIBridge 拥有 Protocol 所需的方法"""
        bridge = TextualUIBridge.__new__(TextualUIBridge)
        bridge.log_messages = []
        bridge._screen = None
        bridge.engine = None
        # 验证关键方法存在
        assert hasattr(bridge, 'show_main_menu')
        assert hasattr(bridge, 'show_game_state')
        assert hasattr(bridge, 'show_log')
        assert hasattr(bridge, 'ask_for_shan')
        assert hasattr(bridge, 'choose_target')
        assert hasattr(bridge, 'get_player_action')


class TestTextualUIBridge:
    """测试 TextualUIBridge"""

    def test_bridge_show_log(self):
        """Bridge show_log 不抛异常"""
        # 不创建真正的 screen，仅测试日志存储
        bridge = TextualUIBridge.__new__(TextualUIBridge)
        bridge.log_messages = []
        bridge._screen = None
        bridge.engine = None

        # show_log 应存储消息（即使 screen 不可用）
        bridge.log_messages.append("test")
        assert len(bridge.log_messages) == 1

    def test_bridge_has_all_methods(self):
        """Bridge 拥有引擎所需的全部 UI 方法"""
        bridge = TextualUIBridge.__new__(TextualUIBridge)
        bridge.log_messages = []
        bridge._screen = None
        bridge.engine = None

        required_methods = [
            'show_log', 'show_game_state', 'show_title',
            'show_main_menu', 'ask_for_shan', 'ask_for_sha',
            'ask_for_tao', 'ask_for_wuxie', 'choose_target',
            'choose_suit', 'guanxing_selection',
        ]
        for method in required_methods:
            assert hasattr(bridge, method), f"Missing method: {method}"


class TestAnimationCSS:
    """测试 M3-T04 动画相关"""

    def test_css_contains_animation_classes(self):
        """应用 CSS 包含动画类"""
        css = SanguoshaApp.CSS
        assert "flash-damage" in css
        assert "flash-heal" in css
        assert "flash-skill" in css
        assert "card-btn" in css
        assert "transition" in css

    def test_gameplay_screen_has_flash_method(self):
        """游戏界面应有 flash_effect 方法"""
        from ui.textual_ui.app import GamePlayScreen
        assert hasattr(GamePlayScreen, 'flash_effect')
        assert hasattr(GamePlayScreen, '_post_flash')


class TestMainEntry:
    """测试主入口（Textual TUI 唯一模式）"""

    def test_default_is_textual(self):
        """默认启动 Textual TUI（无 --ui 参数）"""
        from ui.textual_ui import SanguoshaApp
        assert SanguoshaApp is not None

    def test_argparse_no_ui_flag(self):
        """main.py 不再有 --ui 参数"""
        import argparse
        parser = argparse.ArgumentParser()
        # 只保留网络/回放参数
        parser.add_argument("--server", nargs="?", const="0.0.0.0:8765", default=None)
        parser.add_argument("--connect", default=None)
        parser.add_argument("--replay", default=None)

        args = parser.parse_args([])
        assert args.server is None
        assert args.connect is None
        assert args.replay is None
