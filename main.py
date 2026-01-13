# -*- coding: utf-8 -*-
"""
三国杀 - 命令行终端版
主程序入口

版本: 1.0.0
作者: Sanguosha Dev Team

使用方法:
    python main.py

依赖:
    - Python 3.8+
    - colorama (可选，用于彩色输出)
"""

import sys
import os
import copy
import logging
from pathlib import Path
from typing import Optional, List, Dict

from logging_config import setup_logging

logger = logging.getLogger(__name__)

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent))

from game.engine import GameEngine, GameState, GamePhase
from game.player import Player, Identity
from game.card import Card, CardType
from game.hero import Hero, HeroRepository
from game.skill import SkillSystem
from ai.bot import AIBot, AIDifficulty
from ui.terminal import TerminalUI
from ui.rich_ui import RichTerminalUI


class SanguoshaGame:
    """
    三国杀游戏主类
    负责游戏的初始化、主循环和流程控制
    """
    
    def __init__(self):
        """初始化游戏"""
        # self.ui = TerminalUI(use_color=True)
        self.ui = RichTerminalUI(use_color=True)
        self.engine: Optional[GameEngine] = None
        self.ai_difficulty: AIDifficulty = AIDifficulty.NORMAL
        self.is_running = True
    
    def run(self) -> None:
        """运行游戏主循环"""
        while self.is_running:
            choice = self.ui.show_main_menu()
            
            if choice == 1:
                self.start_new_game()
            elif choice == 2:
                self.ui.show_rules()
            elif choice == 3:
                self.is_running = False
                print("\n感谢游玩三国杀！再见！")
    
    def start_new_game(self) -> None:
        """开始新游戏"""
        # 选择玩家数量
        player_count = self.ui.show_player_count_menu()
        
        # 选择AI难度
        difficulty_str = self.ui.show_difficulty_menu()
        self.ai_difficulty = AIDifficulty(difficulty_str)
        
        # 初始化游戏引擎
        self.engine = GameEngine()
        self.engine.setup_game(player_count, human_player_index=0)
        
        # 设置UI
        self.engine.set_ui(self.ui)
        self.ui.set_engine(self.engine)
        
        # 初始化技能系统
        skill_system = SkillSystem(self.engine)
        self.engine.set_skill_system(skill_system)
        
        # 选择武将
        self._choose_heroes()
        
        # 初始化AI
        self._setup_ai_bots()
        
        # 开始游戏
        self.engine.start_game()
        
        # 进入游戏主循环
        self._game_loop()
    
    def _choose_heroes(self) -> None:
        """武将选择阶段 - 符合真实三国杀规则"""
        if not self.engine:
            return
        
        import random
        
        # 获取所有武将
        all_heroes = self.engine.hero_repo.get_all_heroes()
        used_heroes = []  # 已被选择的武将
        
        # 分离主公专属武将（有主公技的）和普通武将
        lord_heroes = [h for h in all_heroes if any(s.is_lord_skill for s in h.skills)]
        normal_heroes = [h for h in all_heroes if not any(s.is_lord_skill for s in h.skills)]
        
        # 人类玩家选择武将
        if self.engine.human_player:
            is_lord = self.engine.human_player.identity == Identity.LORD
            
            if is_lord:
                # 主公5选1：优先提供主公专属武将 + 部分普通武将
                self.ui.show_log("【主公选将】你是主公，可从5名武将中选择")
                available = lord_heroes.copy()
                remaining = 5 - len(available)
                if remaining > 0:
                    extra = random.sample(normal_heroes, min(remaining, len(normal_heroes)))
                    available.extend(extra)
                random.shuffle(available)
                available = available[:5]  # 最多5个
            else:
                # 其他身份3选1
                self.ui.show_log("【选择武将】请从3名武将中选择")
                available = random.sample(normal_heroes, min(3, len(normal_heroes)))
            
            selected = self.ui.show_hero_selection(available, 1, is_lord)
            
            if selected:
                hero = copy.deepcopy(selected[0])
                self.engine.human_player.set_hero(hero)
                used_heroes.append(hero.id)
                
                # 主公选将后公布
                if is_lord:
                    self.ui.show_log(f"主公选择了武将：【{hero.name}】")
        
        # AI玩家自动选择武将（避免重复）
        ai_choices = self._auto_choose_heroes_for_ai(used_heroes)
        self.engine.choose_heroes(ai_choices)
    
    def _auto_choose_heroes_for_ai(self, used_heroes: List[str]) -> Dict[int, str]:
        """为AI玩家自动选择武将"""
        import random
        
        all_heroes = self.engine.hero_repo.get_all_heroes()
        # 过滤掉已使用的武将
        available = [h for h in all_heroes if h.id not in used_heroes]
        
        ai_choices = {}
        for player in self.engine.players:
            if player.is_ai and player.hero is None:
                if available:
                    # 根据身份选择合适的武将
                    hero = self._select_hero_for_ai(player, available)
                    ai_choices[player.id] = hero.id  # 返回hero.id而不是Hero对象
                    available.remove(hero)
                    self.ui.show_log(f"{player.name} 选择了武将：【{hero.name}】")
        
        return ai_choices
    
    def _select_hero_for_ai(self, player: 'Player', available: List['Hero']) -> 'Hero':
        """根据AI身份智能选择武将"""
        import random
        from game.hero import SkillType
        
        identity = player.identity
        
        # 根据身份偏好选择
        preferred = []
        
        if identity == Identity.LORD:
            # 主公优先选有主公技的
            preferred = [h for h in available if any(s.is_lord_skill for s in h.skills)]
        elif identity == Identity.LOYALIST:
            # 忠臣选辅助型或防御型
            preferred = [h for h in available if h.max_hp >= 4]
        elif identity == Identity.REBEL:
            # 反贼选攻击型
            preferred = [h for h in available if any(s.skill_type == SkillType.ACTIVE for s in h.skills)]
        elif identity == Identity.SPY:
            # 内奸选生存能力强的
            preferred = [h for h in available if h.max_hp >= 4 or len(h.skills) >= 2]
        
        if preferred:
            return random.choice(preferred)
        return random.choice(available)
    
    def _setup_ai_bots(self) -> None:
        """设置AI机器人"""
        if not self.engine:
            return
        
        for player in self.engine.players:
            if player.is_ai:
                bot = AIBot(player, self.ai_difficulty)
                self.engine.ai_bots[player.id] = bot
    
    def _game_loop(self) -> None:
        """游戏主循环"""
        if not self.engine:
            return
        
        while not self.engine.is_game_over():
            current_player = self.engine.current_player
            
            # 显示游戏状态
            self.ui.show_game_state(self.engine, current_player)
            
            if current_player.is_ai:
                # AI回合
                self._run_ai_turn(current_player)
            else:
                # 人类玩家回合
                self._run_human_turn(current_player)
            
            # 检查游戏是否结束
            if self.engine.is_game_over():
                break
            
            # 进入下一个回合
            self.engine.next_turn()
        
        # 游戏结束
        self._handle_game_over()
    
    def _run_ai_turn(self, player: Player) -> None:
        """执行AI回合"""
        if not self.engine:
            return
        
        import time
        
        self.ui.show_log(f"")
        self.ui.show_log(f"════════════════════════")
        self.ui.show_log(f"【第{self.engine.round_count}回合】 {player.name}({player.hero.name}) 的回合")
        self.ui.show_log(f"════════════════════════")
        self.ui.show_game_state(self.engine, player)
        
        # 重置回合状态
        player.reset_turn()
        
        # 准备阶段
        self.ui.show_log(f"▶ 准备阶段")
        self.engine.phase_prepare(player)
        
        # 摸牌阶段
        self.ui.show_log(f"▶ 摸牌阶段")
        old_count = player.hand_count
        self.engine.phase_draw(player)
        new_cards = player.hand_count - old_count
        self.ui.show_log(f"  └─ {player.name} 摸了 {new_cards} 张牌")
        self.ui.show_game_state(self.engine, player)
        time.sleep(0.3)
        
        # 出牌阶段
        self.ui.show_log(f"▶ 出牌阶段")
        self.engine.phase = GamePhase.PLAY
        if player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            bot.play_phase(player, self.engine)
        
        self.ui.show_game_state(self.engine, player)
        time.sleep(0.3)
        
        # 弃牌阶段
        if player.need_discard > 0:
            self.ui.show_log(f"▶ 弃牌阶段")
            self.ui.show_log(f"  └─ 需弃置 {player.need_discard} 张牌")
            self.engine.phase_discard(player)
        
        # 结束阶段
        self.ui.show_log(f"▶ 结束阶段")
        self.engine.phase_end(player)
        self.ui.show_log(f"─── {player.name} 回合结束 ───")
        time.sleep(0.3)
    
    def _run_human_turn(self, player: Player) -> None:
        """执行人类玩家回合"""
        if not self.engine:
            return
        
        self.ui.show_log(f"")
        self.ui.show_log(f"════════════════════════")
        self.ui.show_log(f"【第{self.engine.round_count}回合】 {player.name}({player.hero.name}) 的回合")
        self.ui.show_log(f"════════════════════════")
        
        # 重置回合状态
        player.reset_turn()
        
        # 准备阶段
        self.ui.show_log(f"▶ 准备阶段")
        self.engine.phase_prepare(player)
        self.ui.show_game_state(self.engine, player)
        
        # 摸牌阶段
        self.ui.show_log(f"▶ 摸牌阶段")
        old_hand_count = player.hand_count
        self.engine.phase_draw(player)
        new_cards = player.hand_count - old_hand_count
        self.ui.show_log(f"  └─ 摸了 {new_cards} 张牌，当前手牌数: {player.hand_count}")
        self.ui.show_game_state(self.engine, player)
        
        # 出牌阶段
        self.ui.show_log(f"▶ 出牌阶段")
        self.engine.phase = GamePhase.PLAY
        self._human_play_phase(player)
        
        # 弃牌阶段
        if player.need_discard > 0:
            self.ui.show_log(f"▶ 弃牌阶段")
            self.ui.show_log(f"  └─ 需弃置 {player.need_discard} 张牌（手牌上限: {player.hp}）")
            self.engine.phase = GamePhase.DISCARD
            self.ui.show_game_state(self.engine, player)
            self._human_discard_phase(player)
        
        # 结束阶段
        self.ui.show_log(f"▶ 结束阶段")
        self.engine.phase_end(player)
        self.ui.show_log(f"─── 回合结束 ───")
    
    def _human_play_phase(self, player: Player) -> None:
        """人类玩家出牌阶段 - 默认直接进入出牌模式"""
        if not self.engine:
            return
        
        # 首次检查是否有可操作的牌或技能
        if not self._can_do_anything(player):
            self.ui.show_game_state(self.engine, player)
            print("\n" + "=" * 50)
            print("【自动跳过】当前无可用手牌或技能")
            print("=" * 50)
            self.ui.show_log(f"  └─ 无可出牌，自动结束出牌阶段")
            import time
            time.sleep(1)
            return
        
        while True:
            self.ui.show_game_state(self.engine, player)
            
            # 获取玩家操作
            action = self.ui.get_player_action()
            
            if action == 'E':  # 结束出牌
                self.ui.show_log(f"  └─ 结束出牌阶段")
                break
            elif action == 'H':  # 帮助
                self.ui.show_help()
            elif action == 'Q':  # 退出
                if self._confirm_quit():
                    self.engine.state = GameState.FINISHED
                    return
            elif action == 'S':  # 使用技能
                self._handle_use_skill(player)
            elif action.isdigit():  # 直接选择手牌
                card_idx = int(action) - 1
                if 0 <= card_idx < len(player.hand):
                    card = player.hand[card_idx]
                    self._handle_play_specific_card(player, card)
                else:
                    print("无效的卡牌编号")
            
            # 检查游戏是否结束
            if self.engine.is_game_over():
                return
            
            # 再次检查是否还有可操作的牌或技能
            if not self._can_do_anything(player):
                print("\n【自动结束】已无可用手牌或技能")
                self.ui.show_log(f"  └─ 无可出牌，自动结束出牌阶段")
                import time
                time.sleep(0.5)
                break
    
    def _check_card_usable(self, player: Player, card: Card) -> bool:
        """检查卡牌是否可以使用"""
        if card.card_type == CardType.EQUIPMENT:
            return True
        if card.name == "杀":
            if not player.can_use_sha():
                return False
            targets = self.engine.get_targets_in_range(player)
            return len(targets) > 0
        if card.name == "桃":
            return player.hp < player.max_hp
        if card.name == "闪":
            return False  # 闪不能主动使用
        if card.name == "顺手牵羊":
            others = self.engine.get_other_players(player)
            valid = [t for t in others 
                    if self.engine.calculate_distance(player, t) <= 1 and t.has_any_card()]
            return len(valid) > 0
        if card.name == "过河拆桥":
            others = self.engine.get_other_players(player)
            valid = [t for t in others if t.has_any_card()]
            return len(valid) > 0
        if card.name == "决斗":
            return len(self.engine.get_other_players(player)) > 0
        return True
    
    def _has_usable_cards(self, player: Player) -> bool:
        """检查玩家是否有可出的牌"""
        if not player.hand:
            return False
        for card in player.hand:
            if self._check_card_usable(player, card):
                return True
        return False
    
    def _has_usable_skills(self, player: Player) -> bool:
        """检查玩家是否有可用的技能"""
        if not self.engine or not self.engine.skill_system:
            return False
        usable_skills = self.engine.skill_system.get_usable_skills(player)
        return len(usable_skills) > 0
    
    def _can_do_anything(self, player: Player) -> bool:
        """检查玩家是否可以进行任何操作"""
        return self._has_usable_cards(player) or self._has_usable_skills(player)
    
    def _handle_play_specific_card(self, player: Player, card: Card) -> None:
        """处理使用指定卡牌"""
        if not self.engine:
            return
        
        # 根据卡牌类型处理
        if card.card_type == CardType.EQUIPMENT:
            self.ui.show_log(f"  └─ 装备了 [{card.name}]")
            self.engine.use_card(player, card)
            
        elif card.name == "杀":
            if not player.can_use_sha():
                print("⚠ 本回合已使用过【杀】")
                has_paoxiao = player.has_skill("paoxiao")
                if has_paoxiao:
                    print("✔ 但你有【咆哮】技能，可无限出杀")
                else:
                    return
            
            targets = self.engine.get_targets_in_range(player)
            if not targets:
                print("⚠ 没有可攻击的目标（距离不足）")
                return
            
            target = self.ui.choose_target(player, targets, "选择攻击目标")
            if target:
                self.ui.show_log(f"  └─ 对 {target.name} 使用【杀】")
                self.engine.use_card(player, card, [target])
                
        elif card.name == "桃":
            if player.hp >= player.max_hp:
                print("⚠ 体力已满，无法使用【桃】")
                return
            self.ui.show_log(f"  └─ 使用【桃】回复1点体力")
            self.engine.use_card(player, card)
            
        elif card.name == "闪":
            print("⚠ 【闪】只能在被【杀】时使用")
            return
            
        elif card.name == "无中生有":
            self.ui.show_log(f"  └─ 使用【无中生有】摸两张牌")
            self.engine.use_card(player, card)
            
        elif card.name in ["南蛮入侵", "万箭齐发"]:
            self.ui.show_log(f"  └─ 使用【{card.name}】")
            self.engine.use_card(player, card)
            
        elif card.name == "桃园结义":
            self.ui.show_log(f"  └─ 使用【桃园结义】所有人回复1点体力")
            self.engine.use_card(player, card)
            
        elif card.name == "决斗":
            others = self.engine.get_other_players(player)
            if not others:
                print("⚠ 没有可选目标")
                return
            target = self.ui.choose_target(player, others, "选择决斗目标")
            if target:
                self.ui.show_log(f"  └─ 对 {target.name} 使用【决斗】")
                self.engine.use_card(player, card, [target])
                
        elif card.name == "过河拆桥":
            others = self.engine.get_other_players(player)
            valid = [t for t in others if t.has_any_card()]
            if not valid:
                print("⚠ 没有有牌的目标")
                return
            target = self.ui.choose_target(player, valid, "选择拆牌目标")
            if target:
                self.ui.show_log(f"  └─ 对 {target.name} 使用【过河拆桥】")
                self.engine.use_card(player, card, [target])
                
        elif card.name == "顺手牵羊":
            others = self.engine.get_other_players(player)
            valid = [t for t in others 
                    if self.engine.calculate_distance(player, t) <= 1 and t.has_any_card()]
            if not valid:
                print("⚠ 没有距离为1且有牌的目标")
                return
            target = self.ui.choose_target(player, valid, "选择牵羊目标")
            if target:
                self.ui.show_log(f"  └─ 对 {target.name} 使用【顺手牵羊】")
                self.engine.use_card(player, card, [target])
        else:
            self.engine.use_card(player, card)
    
    def _handle_play_card(self, player: Player) -> None:
        """处理出牌操作 - 已废弃，使用_handle_play_specific_card"""
        pass
    
    def _handle_use_skill(self, player: Player) -> None:
        """处理使用技能"""
        if not self.engine or not self.engine.skill_system:
            return
        
        # 获取可用技能
        usable_skills = self.engine.skill_system.get_usable_skills(player)
        
        skill_id = self.ui.show_skill_menu(player, usable_skills)
        if not skill_id:
            return
        
        # 根据技能类型处理
        if skill_id == "zhiheng":
            # 制衡：选择要弃置的牌
            if player.hand:
                self.ui.show_log("选择要换掉的牌")
                cards = self._select_cards_for_skill(player, 1, len(player.hand))
                if cards:
                    self.engine.skill_system.use_skill(skill_id, player, cards=cards)
        elif skill_id == "rende":
            # 仁德：选择牌和目标
            if player.hand:
                cards = self._select_cards_for_skill(player, 1, len(player.hand))
                if cards:
                    others = self.engine.get_other_players(player)
                    target = self.ui.choose_target(player, others, "选择交给谁")
                    if target:
                        self.engine.skill_system.use_skill(skill_id, player, 
                                                          targets=[target], cards=cards)
        elif skill_id == "fanjian":
            # 反间：选择牌和目标
            if player.hand:
                self.ui.show_log("选择要展示的牌")
                card = self.ui.choose_card_to_play(player)
                if card:
                    others = self.engine.get_other_players(player)
                    target = self.ui.choose_target(player, others, "选择反间目标")
                    if target:
                        # 临时将牌加回手牌（因为choose_card会移除）
                        self.engine.skill_system.use_skill(skill_id, player,
                                                          targets=[target], cards=[card])
    
    def _select_cards_for_skill(self, player: Player, 
                               min_count: int, max_count: int) -> List[Card]:
        """为技能选择卡牌"""
        print(f"\n选择 {min_count}-{max_count} 张牌 (输入编号，用空格分隔):")
        for i, card in enumerate(player.hand, 1):
            print(f"  [{i}] {card.display_name}")
        
        while True:
            choice = input("请选择: ").strip()
            if not choice:
                return []
            
            try:
                indices = [int(x) - 1 for x in choice.split()]
                if min_count <= len(indices) <= max_count:
                    if all(0 <= i < len(player.hand) for i in indices):
                        return [player.hand[i] for i in indices]
            except ValueError:
                pass
            print(f"请选择 {min_count}-{max_count} 张有效的牌")
    
    def _show_battle_info(self, player: Player) -> None:
        """显示简要对战信息"""
        if not self.engine:
            return
        
        # 显示可出牌数量
        usable_cards = sum(1 for c in player.hand if self._check_card_usable(player, c))
        print(f"\n📊 可出牌: {usable_cards}/{len(player.hand)}  ", end="")
        
        # 显示攻击范围内的目标数
        targets = self.engine.get_targets_in_range(player)
        print(f"攻击范围内目标: {len(targets)}人")
    
    def _show_detailed_battle_info(self, player: Player) -> None:
        """显示详细对战信息"""
        if not self.engine:
            return
        
        print("\n" + "=" * 60)
        print("【 对 战 信 息 】")
        print("=" * 60)
        
        # 显示玩家自己的信息
        print(f"\n🎭 【你的角色】 {player.hero.name} ({player.hero.kingdom.chinese_name})")
        print(f"   体力: {player.hp}/{player.max_hp}  手牌: {player.hand_count}张")
        
        # 显示技能
        if player.hero and player.hero.skills:
            print("\n   📜 技能:")
            for skill in player.hero.skills:
                skill_type_name = {
                    'passive': '被动',
                    'active': '主动',
                    'trigger': '触发',
                    'lord': '主公技'
                }.get(skill.skill_type.value, skill.skill_type.value)
                print(f"      【{skill.name}】({skill_type_name}) - {skill.description}")
        
        # 显示装备
        print("\n   ⚔️ 装备区:")
        if player.equipment.weapon:
            w = player.equipment.weapon
            print(f"      武器: [{w.name}] 攻击范围+{w.range - 1}")
        else:
            print(f"      武器: 无 (攻击范围1)")
        
        if player.equipment.armor:
            print(f"      防具: [{player.equipment.armor.name}]")
        else:
            print(f"      防具: 无")
        
        if player.equipment.horse_minus:
            print(f"      -1马: [{player.equipment.horse_minus.name}] (进攻距离-1)")
        if player.equipment.horse_plus:
            print(f"      +1马: [{player.equipment.horse_plus.name}] (防御距离+1)")
        
        # 显示对手信息
        print("\n" + "-" * 60)
        print("【 对 手 信 息 】")
        
        for other in self.engine.players:
            if other == player:
                continue
            if not other.is_alive:
                print(f"\n💀 [{other.name}] 已阵亡")
                continue
            
            # 计算距离
            dist = self.engine.calculate_distance(player, other)
            in_range = "✓在范围内" if dist <= player.equipment.attack_range else "✗超出范围"
            
            # 身份显示
            if other.identity.value == "lord":
                identity = "[主公]"
            else:
                identity = "[?身份未知]"
            
            print(f"\n🎭 [{other.name}] {other.hero.name} ({other.hero.kingdom.chinese_name}) {identity}")
            print(f"   体力: {other.hp}/{other.max_hp}  手牌: {other.hand_count}张  距离: {dist} {in_range}")
            
            # 对手技能介绍
            if other.hero and other.hero.skills:
                print("   技能:")
                for skill in other.hero.skills:
                    # 简短显示技能
                    desc = skill.description[:40] + "..." if len(skill.description) > 40 else skill.description
                    print(f"      【{skill.name}】- {desc}")
            
            # 对手装备
            equips = []
            if other.equipment.weapon:
                equips.append(f"武器:{other.equipment.weapon.name}")
            if other.equipment.armor:
                equips.append(f"防具:{other.equipment.armor.name}")
            if other.equipment.horse_minus:
                equips.append(f"-1马:{other.equipment.horse_minus.name}")
            if other.equipment.horse_plus:
                equips.append(f"+1马:{other.equipment.horse_plus.name}")
            
            if equips:
                print(f"   装备: {', '.join(equips)}")
        
        print("\n" + "=" * 60)
    
    def _handle_voluntary_discard(self, player: Player) -> None:
        """处理主动弃牌"""
        if not player.hand:
            self.ui.show_log("你没有手牌")
            return
        
        card = self.ui.choose_card_to_play(player)
        if card:
            player.remove_card(card)
            self.engine.deck.discard([card])
            self.ui.show_log(f"你弃置了 {card.display_name}")
    
    def _human_discard_phase(self, player: Player) -> None:
        """人类玩家弃牌阶段"""
        if not self.engine:
            return
        
        discard_count = player.need_discard
        if discard_count <= 0:
            return
        
        self.ui.show_log(f"需要弃置 {discard_count} 张牌")
        cards = self.ui.choose_cards_to_discard(player, discard_count)
        
        if cards:
            self.engine.discard_cards(player, cards)
    
    def _confirm_quit(self) -> bool:
        """确认退出"""
        choice = input("确定要退出游戏吗? [Y/N]: ").strip().upper()
        return choice == 'Y'
    
    def _handle_game_over(self) -> None:
        """处理游戏结束"""
        if not self.engine:
            return
        
        winner_message = self.engine.get_winner_message()
        
        # 判断人类玩家是否获胜
        is_victory = False
        if self.engine.human_player:
            human_identity = self.engine.human_player.identity
            if self.engine.winner_identity == Identity.LORD:
                is_victory = human_identity in [Identity.LORD, Identity.LOYALIST]
            elif self.engine.winner_identity == Identity.REBEL:
                is_victory = human_identity == Identity.REBEL
            elif self.engine.winner_identity == Identity.SPY:
                is_victory = human_identity == Identity.SPY
        
        self.ui.show_game_over(winner_message, is_victory)


def main():
    """程序入口"""
    setup_logging(enable_console=False)

    try:
        game = SanguoshaGame()
        game.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt - exiting")
        print("\n\n游戏被中断，再见！")
        sys.exit(0)
    except Exception as e:
        logger.exception("Unhandled exception")
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
