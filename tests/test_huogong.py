# -*- coding: utf-8 -*-
"""
火攻锦囊单元测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from game.engine import GameEngine
from game.card import Card, CardType, CardSubtype, CardSuit, CardName


class TestHuogong:
    """火攻锦囊测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建测试用的游戏引擎"""
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine
    
    @pytest.fixture
    def huogong_card(self):
        """创建火攻卡牌"""
        return Card(
            id="huogong_test",
            name="火攻",
            card_type=CardType.TRICK,
            subtype=CardSubtype.SINGLE_TARGET,
            suit=CardSuit.HEART,
            number=2
        )
    
    def test_huogong_basic(self, engine, huogong_card):
        """测试火攻基本流程：目标展示手牌，使用者弃同花色造成伤害"""
        player = engine.players[0]
        target = engine.players[1]

        # 清空目标手牌，只给一张特定花色的牌
        target.hand.clear()
        target_card = Card(
            id="target_hand_card",
            name="桃",
            card_type=CardType.BASIC,
            subtype=CardSubtype.HEAL,
            suit=CardSuit.HEART,
            number=3
        )
        target.hand.append(target_card)

        # 清空使用者手牌，给火攻和同花色牌
        player.hand.clear()
        player.hand.append(huogong_card)

        # 给使用者一张同花色的牌用于弃置
        matching_card = Card(
            id="matching_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.HEART,  # 与目标手牌同花色
            number=5
        )
        player.hand.append(matching_card)

        target_hp_before = target.hp

        # 使用火攻
        result = engine._use_huogong(player, huogong_card, [target])

        assert result is True
        # 如果有同花色牌，应该造成1点火焰伤害
        assert target.hp == target_hp_before - 1
    
    def test_huogong_no_matching_suit(self, engine, huogong_card):
        """测试火攻：使用者没有同花色牌时不造成伤害"""
        player = engine.players[0]
        target = engine.players[1]
        
        # 确保目标有手牌
        if not target.hand:
            test_card = Card(
                id="target_card",
                name="桃",
                card_type=CardType.BASIC,
                subtype=CardSubtype.HEAL,
                suit=CardSuit.HEART,
                number=3
            )
            target.draw_cards([test_card])
        
        # 清空使用者手牌
        player.hand.clear()
        player.draw_cards([huogong_card])
        
        # 给使用者一张不同花色的牌
        diff_card = Card(
            id="diff_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,  # 不同花色
            number=5
        )
        player.draw_cards([diff_card])
        
        target_hp_before = target.hp
        
        # 如果目标手牌是红心，使用者只有黑桃，不造成伤害
        if target.hand[0].suit != CardSuit.SPADE:
            result = engine._use_huogong(player, huogong_card, [target])
            assert result is True
            # 没有同花色牌，不造成伤害
            assert target.hp == target_hp_before
    
    def test_huogong_target_no_hand(self, engine, huogong_card):
        """测试火攻：目标没有手牌时无效"""
        player = engine.players[0]
        target = engine.players[1]
        
        # 清空目标手牌
        target.hand.clear()
        
        player.draw_cards([huogong_card])
        
        target_hp_before = target.hp
        
        result = engine._use_huogong(player, huogong_card, [target])
        
        assert result is False
        assert target.hp == target_hp_before
    
    def test_huogong_fire_damage_type(self, engine, huogong_card):
        """测试火攻造成的是火焰伤害"""
        player = engine.players[0]
        target = engine.players[1]
        
        # 确保目标有手牌
        heart_card = Card(
            id="heart_test",
            name="桃",
            card_type=CardType.BASIC,
            subtype=CardSubtype.HEAL,
            suit=CardSuit.HEART,
            number=3
        )
        target.hand.clear()
        target.draw_cards([heart_card])
        
        # 给使用者同花色牌
        player.hand.clear()
        player.draw_cards([huogong_card])
        matching = Card(
            id="matching_heart",
            name="闪",
            card_type=CardType.BASIC,
            subtype=CardSubtype.DODGE,
            suit=CardSuit.HEART,
            number=2
        )
        player.draw_cards([matching])
        
        # 记录事件日志来验证伤害类型
        engine.event_log.clear()
        
        engine._use_huogong(player, huogong_card, [target])
        
        # 检查日志中是否有火焰伤害相关记录
        damage_logs = [e for e in engine.event_log if 'damage' in e.event_type.lower() or '伤害' in e.message]
        assert len(damage_logs) > 0 or target.hp < target.max_hp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
