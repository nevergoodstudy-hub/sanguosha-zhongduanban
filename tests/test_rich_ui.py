
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

if __name__ == "__main__":
    # Manually run if executed directly
    test_rich_ui_render_game_state()
    print("Rich UI Test Passed")
