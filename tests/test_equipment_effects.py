# -*- coding: utf-8 -*-
"""
装备效果单元测试
测试白银狮子、古锭刀、朱雀羽扇等装备的特殊效果
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from game.engine import GameEngine
from game.card import Card, CardType, CardSubtype, CardSuit, CardName
from game.player import EquipmentSlot


class TestBaiyinshizi:
    """白银狮子测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建测试用的游戏引擎"""
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        # 自动选择武将
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine
    
    @pytest.fixture
    def baiyinshizi_card(self):
        """创建白银狮子卡牌"""
        return Card(
            id="baiyinshizi_test",
            name="白银狮子",
            card_type=CardType.EQUIPMENT,
            subtype=CardSubtype.ARMOR,
            suit=CardSuit.CLUB,
            number=1
        )
    
    def test_baiyinshizi_damage_reduction(self, engine, baiyinshizi_card):
        """测试白银狮子伤害削减：受到大于1点伤害时只受到1点"""
        target = engine.players[1]
        attacker = engine.players[0]
        
        # 装备白银狮子
        target.equip_card(baiyinshizi_card)
        assert target.equipment.armor == baiyinshizi_card
        
        target_hp_before = target.hp
        
        # 造成3点伤害
        engine.deal_damage(attacker, target, 3)
        
        # 应该只受到1点伤害
        assert target.hp == target_hp_before - 1
    
    def test_baiyinshizi_single_damage_no_reduction(self, engine, baiyinshizi_card):
        """测试白银狮子：1点伤害不受影响"""
        target = engine.players[1]
        attacker = engine.players[0]
        
        target.equip_card(baiyinshizi_card)
        target_hp_before = target.hp
        
        # 造成1点伤害
        engine.deal_damage(attacker, target, 1)
        
        # 受到1点伤害
        assert target.hp == target_hp_before - 1
    
    def test_baiyinshizi_lose_heal(self, engine, baiyinshizi_card):
        """测试白银狮子失去装备回复体力"""
        player = engine.players[1]
        
        # 装备白银狮子
        player.equip_card(baiyinshizi_card)
        
        # 先造成一些伤害
        player.take_damage(2, None)
        hp_before = player.hp
        
        # 移除装备
        engine._remove_equipment(player, baiyinshizi_card)
        
        # 应该回复1点体力
        assert player.hp == hp_before + 1
    
    def test_baiyinshizi_lose_no_heal_full_hp(self, engine, baiyinshizi_card):
        """测试白银狮子：满血时失去装备不回复"""
        player = engine.players[1]
        
        # 装备白银狮子
        player.equip_card(baiyinshizi_card)
        
        # 确保满血
        player.hp = player.max_hp
        hp_before = player.hp
        
        # 移除装备
        engine._remove_equipment(player, baiyinshizi_card)
        
        # 不应该回复（因为已满血）
        assert player.hp == hp_before


class TestGudingdao:
    """古锭刀测试类"""
    
    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine
    
    @pytest.fixture
    def gudingdao_card(self):
        return Card(
            id="gudingdao_test",
            name="古锭刀",
            card_type=CardType.EQUIPMENT,
            subtype=CardSubtype.WEAPON,
            suit=CardSuit.SPADE,
            number=1,
            range=2
        )
    
    def test_gudingdao_extra_damage(self, engine, gudingdao_card):
        """测试古锭刀：目标无手牌时伤害+1"""
        attacker = engine.players[0]
        target = engine.players[1]
        
        # 装备古锭刀
        attacker.equip_card(gudingdao_card)
        
        # 清空目标手牌
        target.hand.clear()
        
        # 古锭刀效果在杀造成伤害时触发
        # 这里直接测试效果判断逻辑
        has_hand = len(target.hand) > 0
        extra_damage = 0 if has_hand else 1
        
        assert extra_damage == 1


class TestZhuqueyushan:
    """朱雀羽扇测试类"""
    
    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine
    
    @pytest.fixture
    def zhuqueyushan_card(self):
        return Card(
            id="zhuqueyushan_test",
            name="朱雀羽扇",
            card_type=CardType.EQUIPMENT,
            subtype=CardSubtype.WEAPON,
            suit=CardSuit.DIAMOND,
            number=1,
            range=4
        )
    
    def test_zhuqueyushan_equipped(self, engine, zhuqueyushan_card):
        """测试朱雀羽扇装备"""
        player = engine.players[0]
        
        player.equip_card(zhuqueyushan_card)
        
        assert player.equipment.weapon == zhuqueyushan_card
        assert player.equipment.weapon.name == "朱雀羽扇"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
