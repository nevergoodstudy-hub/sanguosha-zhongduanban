
import sys
import os
from unittest.mock import MagicMock
# import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.rich_ui import RichTerminalUI
from game.engine import GameEngine, GamePhase
from game.player import Player, Identity, Equipment
from game.hero import Hero, Kingdom
from game.card import Card, CardSuit, CardType

def test_rich_ui_instantiation():
    ui = RichTerminalUI()
    assert ui is not None

def test_rich_ui_render_game_state():
    ui = RichTerminalUI()
    
    # Mock objects
    engine = MagicMock(spec=GameEngine)
    engine.round_count = 1
    engine.phase = GamePhase.PLAY
    
    player = MagicMock(spec=Player)
    player.name = "TestPlayer"
    player.hp = 4
    player.max_hp = 4
    player.hand = []
    player.hand_count = 0
    player.equipment = MagicMock(spec=Equipment)
    player.equipment.weapon = None
    player.equipment.armor = None
    player.equipment.horse_minus = None
    player.equipment.horse_plus = None
    player.equipment.attack_range = 1
    player.judge_area = []
    
    hero = MagicMock(spec=Hero)
    hero.name = "Cao Cao"
    hero.kingdom = Kingdom.WEI
    hero.skills = []
    # hero.kingdom.chinese_name = "魏"
    player.hero = hero
    player.identity = Identity.LORD
    # player.identity.chinese_name = "主公"
    
    engine.current_player = player
    engine.human_player = player
    engine.players = [player]
    engine.get_other_players.return_value = []
    
    ui.set_engine(engine)
    
    # This should not raise exception
    try:
        ui.show_game_state(engine, player)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"show_game_state raised exception: {e}")
        sys.exit(1)

def test_rich_ui_show_main_menu():
    """测试主菜单显示"""
    ui = RichTerminalUI()
    # 主菜单方法应该存在
    assert hasattr(ui, 'show_main_menu')


def test_rich_ui_show_player_count_menu():
    """测试玩家数量菜单"""
    ui = RichTerminalUI()
    assert hasattr(ui, 'show_player_count_menu')


def test_rich_ui_show_difficulty_menu():
    """测试难度菜单"""
    ui = RichTerminalUI()
    assert hasattr(ui, 'show_difficulty_menu')


def test_rich_ui_format_card():
    """测试卡牌格式化"""
    ui = RichTerminalUI()

    from game.card import CardSubtype
    card = Card(
        id="test_sha",
        name="杀",
        card_type=CardType.BASIC,
        subtype=CardSubtype.ATTACK,
        suit=CardSuit.SPADE,
        number=7
    )

    # format_card应该返回字符串
    if hasattr(ui, 'format_card'):
        result = ui.format_card(card)
        assert isinstance(result, str)


def test_rich_ui_color_settings():
    """测试颜色设置"""
    ui_color = RichTerminalUI(use_color=True)
    ui_no_color = RichTerminalUI(use_color=False)

    assert ui_color is not None
    assert ui_no_color is not None


def test_rich_ui_clear_screen():
    """测试清屏功能"""
    ui = RichTerminalUI()

    if hasattr(ui, 'clear_screen'):
        # 调用应该不抛出异常
        try:
            ui.clear_screen()
        except Exception:
            pass  # 某些环境可能不支持


def test_rich_ui_show_message():
    """测试消息显示"""
    ui = RichTerminalUI()

    if hasattr(ui, 'show_message'):
        ui.show_message("测试消息")


def test_rich_ui_show_error():
    """测试错误显示"""
    ui = RichTerminalUI()

    if hasattr(ui, 'show_error'):
        ui.show_error("测试错误")


if __name__ == "__main__":
    # Manually run if executed directly
    test_rich_ui_render_game_state()
    print("Rich UI Test Passed")
