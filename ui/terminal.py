# -*- coding: utf-8 -*-
"""
终端UI模块
负责命令行界面的显示和用户输入处理
"""

from __future__ import annotations
import os
import sys
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

# 尝试导入colorama用于彩色输出
try:
    from colorama import init, Fore, Back, Style
    init()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

from .ascii_art import ASCIIArt

# 导入运行时需要的类
from game.card import CardSuit

if TYPE_CHECKING:
    from game.player import Player
    from game.card import Card
    from game.engine import GameEngine
    from game.hero import Hero


class TerminalUI:
    """
    终端UI类
    负责游戏界面的渲染和用户交互
    """
    
    # 界面宽度
    WIDTH = 80
    
    def __init__(self, use_color: bool = True):
        """
        初始化终端UI
        
        Args:
            use_color: 是否使用彩色输出
        """
        self.use_color = use_color and COLORAMA_AVAILABLE
        self.log_messages: List[str] = []
        self.max_log_lines = 8  # 增加日志显示行数
        self.engine: Optional['GameEngine'] = None
    
    def set_engine(self, engine: 'GameEngine') -> None:
        """设置游戏引擎引用"""
        self.engine = engine
    
    def clear_screen(self) -> None:
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_title(self) -> None:
        """显示游戏标题"""
        self.clear_screen()
        print(ASCIIArt.TITLE_SIMPLE)
    
    def show_main_menu(self) -> int:
        """
        显示主菜单
        
        Returns:
            用户选择的选项
        """
        self.show_title()
        print()
        menu_lines = ASCIIArt.get_menu(
            "主菜单",
            [
                "开始新游戏",
                "游戏规则",
                "退出游戏"
            ],
            50
        )
        for line in menu_lines:
            print(line)
        print()
        
        while True:
            choice = input("请选择 [1-3]: ").strip()
            if choice in ['1', '2', '3']:
                return int(choice)
            print("无效选择，请重新输入")
    
    def show_player_count_menu(self) -> int:
        """
        显示玩家数量选择菜单
        
        Returns:
            玩家数量
        """
        self.clear_screen()
        print("\n" + "=" * 60)
        print("                    选择游戏人数")
        print("=" * 60)
        print()
        print("  [2] 2人对战 (主公 vs 反贼)")
        print("  [3] 3人对战 (主公 vs 反贼 + 内奸)")
        print("  [4] 4人对战 (主公 + 忠臣 vs 反贼 + 内奸)")
        print("  [5] 5人对战 (主公 + 忠臣 vs 2反贼 + 内奸)")
        print("  [6] 6人对战 (主公 + 忠臣 vs 3反贼 + 内奸)")
        print("  [7] 7人对战 (主公 + 2忠臣 vs 3反贼 + 内奸)")
        print("  [8] 8人对战 (主公 + 2忠臣 vs 4反贼 + 内奸)")
        print()
        
        while True:
            choice = input("请选择人数 [2-8]: ").strip()
            if choice in ['2', '3', '4', '5', '6', '7', '8']:
                return int(choice)
            print("无效选择，请重新输入")
    
    def show_difficulty_menu(self) -> str:
        """
        显示AI难度选择菜单
        
        Returns:
            难度级别
        """
        self.clear_screen()
        print("\n" + "=" * 50)
        print("           选择AI难度")
        print("=" * 50)
        print()
        print("  [1] 简单 - AI随机出牌")
        print("  [2] 普通 - AI使用基础策略")
        print("  [3] 困难 - AI使用深度策略")
        print()
        
        while True:
            choice = input("请选择难度 [1-3]: ").strip()
            if choice == '1':
                return "easy"
            elif choice == '2':
                return "normal"
            elif choice == '3':
                return "hard"
            print("无效选择，请重新输入")
    
    def show_hero_selection(self, heroes: List['Hero'], 
                           selected_count: int = 1,
                           is_lord: bool = False) -> List['Hero']:
        """
        显示武将选择界面
        
        Args:
            heroes: 可选武将列表
            selected_count: 需要选择的数量
            is_lord: 是否为主公选将
            
        Returns:
            选择的武将列表
        """
        self.clear_screen()
        print("\n" + "═" * 70)
        if is_lord:
            print("              【 主 公 选 将 】 5选1 - 请慎重选择")
        else:
            print("              【 选 择 武 将 】 3选1")
        print("═" * 70)
        print()
        
        for i, hero in enumerate(heroes, 1):
            kingdom = hero.kingdom.chinese_name
            # 势力颜色标识
            kingdom_mark = {"魏": "●", "蜀": "◆", "吴": "▲", "群": "■"}.get(kingdom, "○")
            
            print(f"  ┌─────────────────────────────────────────────────────────────┐")
            print(f"  │ [{i}] {kingdom_mark} {hero.name} [{kingdom}]  体力:{hero.max_hp}  {hero.title:　<12}")
            print(f"  ├─────────────────────────────────────────────────────────────┤")
            
            for skill in hero.skills:
                skill_type = ""
                if skill.is_compulsory:
                    skill_type = "[锁定技]"
                elif skill.is_lord_skill:
                    skill_type = "[主公技]"
                
                print(f"  │  【{skill.name}】{skill_type}")
                # 技能描述分行显示
                desc = skill.description
                max_len = 50
                while len(desc) > 0:
                    line = desc[:max_len]
                    desc = desc[max_len:]
                    print(f"  │    {line}")
            
            print(f"  └─────────────────────────────────────────────────────────────┘")
            print()
        
        selected = []
        while len(selected) < selected_count:
            remaining = selected_count - len(selected)
            prompt = f"请选择武将 [1-{len(heroes)}]"
            if selected_count > 1:
                prompt += f" (还需选择{remaining}个)"
            prompt += ": "
            
            choice = input(prompt).strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(heroes):
                    hero = heroes[idx]
                    if hero not in selected:
                        selected.append(hero)
                        print(f"已选择: {hero.name}")
                    else:
                        print("已经选择过这个武将了")
                else:
                    print("无效选择")
            except ValueError:
                print("请输入数字")
        
        return selected
    
    def show_game_state(self, engine: 'GameEngine', current_player: 'Player') -> None:
        """
        显示游戏状态
        
        Args:
            engine: 游戏引擎
            current_player: 当前回合玩家
        """
        self.clear_screen()
        
        # 标题栏
        print("╔" + "═" * (self.WIDTH - 2) + "╗")
        title = f"【三国杀 - 命令行版】 第{engine.round_count}回合"
        print("║" + self._center_text(title, self.WIDTH - 2) + "║")
        print("╠" + "═" * (self.WIDTH - 2) + "╣")
        
        # 其他玩家信息（含技能、装备、距离）
        for player in engine.players:
            if player != engine.human_player:
                self._print_player_info(player, player == current_player, 
                                       engine.human_player, engine)
        
        print("╠" + "═" * (self.WIDTH - 2) + "╣")
        
        # 当前玩家信息（人类玩家）
        if engine.human_player:
            self._print_current_player_info(engine.human_player, 
                                           engine.human_player == current_player)
        
        print("╠" + "═" * (self.WIDTH - 2) + "╣")
        
        # 战斗日志
        self._print_log()
        
        print("╠" + "═" * (self.WIDTH - 2) + "╣")
        
        # 操作提示
        content_width = self.WIDTH - 4
        if current_player == engine.human_player and engine.phase.value == "play":
            print("║ " + self._pad_to_width("> 请选择操作:", content_width) + " ║")
            print("║ " + self._pad_to_width("  [P]出牌 [S]技能 [E]结束 [H]帮助 [Q]退出", content_width) + " ║")
        else:
            phase_name = self._get_phase_name(engine.phase.value)
            print("║ " + self._pad_to_width(f"当前阶段: {phase_name}", content_width) + " ║")
        
        print("╚" + "═" * (self.WIDTH - 2) + "╝")
    
    def _print_player_info(self, player: 'Player', is_current: bool, 
                            human_player: 'Player' = None, engine: 'GameEngine' = None) -> None:
        """打印玩家信息行(含技能和装备详情)"""
        content_width = self.WIDTH - 4  # 留出边框空间
        
        if not player.is_alive:
            status = "[阵亡]"
            info = f" {status} {player.name} - {player.identity.chinese_name}"
            padded = self._pad_to_width(info, content_width)
            print("║ " + self._color_text(padded, 'dark') + " ║")
            return
        
        current_mark = "→" if is_current else " "
        hero_name = player.hero.name if player.hero else "???"
        kingdom = f"({player.hero.kingdom.chinese_name})" if player.hero else ""
        hp_bar = ASCIIArt.get_hp_bar(player.hp, player.max_hp)
        hand_count = player.hand_count
        
        # 身份显示
        if player.identity.value == "lord":
            identity = "[主公]"
        else:
            identity = "[?]"
        
        # 计算距离
        dist_str = ""
        if human_player and engine and player != human_player:
            dist = engine.calculate_distance(human_player, player)
            attack_range = human_player.equipment.attack_range
            in_range = "✓" if dist <= attack_range else "✗"
            dist_str = f" 距离:{dist}{in_range}"
        
        # 基本信息行
        info = f"{current_mark}[{player.name}] {hero_name}{kingdom} {hp_bar} 牌:{hand_count} {identity}{dist_str}"
        display_info = self._truncate_text(info, content_width)
        padded = self._pad_to_width(display_info, content_width)
        print("║ " + padded + " ║")
        
        # 技能显示
        if player.hero and player.hero.skills:
            skills = [f"【{s.name}】" for s in player.hero.skills]
            skill_line = f"  └技能: {' '.join(skills)}"
            skill_display = self._truncate_text(skill_line, content_width)
            print("║ " + self._pad_to_width(skill_display, content_width) + " ║")
        
        # 装备显示
        equip_str = self._get_equipment_str(player)
        if equip_str:
            equip_line = f"  └装备: {equip_str}"
            equip_display = self._truncate_text(equip_line, content_width)
            print("║ " + self._pad_to_width(equip_display, content_width) + " ║")
    
    def _print_current_player_info(self, player: 'Player', is_turn: bool) -> None:
        """打印当前玩家详细信息"""
        content_width = self.WIDTH - 4
        
        turn_mark = "【当前回合】" if is_turn else ""
        print("║ " + self._pad_to_width(turn_mark, content_width) + " ║")
        
        hero_name = player.hero.name if player.hero else "???"
        kingdom = f"({player.hero.kingdom.chinese_name})" if player.hero else ""
        hp_bar = ASCIIArt.get_hp_bar(player.hp, player.max_hp)
        identity = player.identity.chinese_name
        
        info = f"[{player.name}] {hero_name}{kingdom}(你) {hp_bar} 身份:{identity}"
        print("║ " + self._pad_to_width(info, content_width) + " ║")
        
        # 技能（含描述）
        if player.hero and player.hero.skills:
            for skill in player.hero.skills:
                desc = skill.description[:35] + "..." if len(skill.description) > 35 else skill.description
                skill_line = f"  └【{skill.name}】{desc}"
                skill_display = self._truncate_text(skill_line, content_width)
                print("║ " + self._pad_to_width(skill_display, content_width) + " ║")
        
        # 装备
        equip_str = self._get_equipment_str(player)
        if equip_str:
            equip_line = f"装备: {equip_str}"
            print("║ " + self._pad_to_width(equip_line, content_width) + " ║")
        
        # 手牌
        if player.hand:
            hand_strs = []
            for i, card in enumerate(player.hand, 1):
                card_str = f"[{i}]{card.display_name}"
                hand_strs.append(card_str)
            
            hand_line = "手牌: " + " ".join(hand_strs)
            # 如果太长，分行显示
            if self._get_display_width(hand_line) > content_width:
                print("║ " + self._pad_to_width("手牌:", content_width) + " ║")
                line = ""
                for hs in hand_strs:
                    test_line = line + " " + hs if line else hs
                    if self._get_display_width(test_line) > content_width:
                        if line:
                            print("║ " + self._pad_to_width(line, content_width) + " ║")
                        line = hs
                    else:
                        line = test_line
                if line:
                    print("║ " + self._pad_to_width(line, content_width) + " ║")
            else:
                print("║ " + self._pad_to_width(hand_line, content_width) + " ║")
        else:
            print("║ " + self._pad_to_width("手牌: 无", content_width) + " ║")
    
    def _get_equipment_str(self, player: 'Player') -> str:
        """获取装备字符串"""
        parts = []
        if player.equipment.weapon:
            parts.append(f"[{player.equipment.weapon.name}]")
        if player.equipment.armor:
            parts.append(f"[{player.equipment.armor.name}]")
        if player.equipment.horse_minus:
            parts.append(f"[-1马:{player.equipment.horse_minus.name}]")
        if player.equipment.horse_plus:
            parts.append(f"[+1马:{player.equipment.horse_plus.name}]")
        return "".join(parts) if parts else ""
    
    def _print_log(self) -> None:
        """打印战斗日志"""
        content_width = self.WIDTH - 4
        print("║ " + self._pad_to_width("【战斗日志】", content_width) + " ║")
        
        # 显示最近的日志
        recent_logs = self.log_messages[-self.max_log_lines:]
        for log in recent_logs:
            truncated = self._truncate_text(log, content_width)
            print("║ " + self._pad_to_width(truncated, content_width) + " ║")
        
        # 补充空行
        for _ in range(self.max_log_lines - len(recent_logs)):
            print("║ " + " " * content_width + " ║")
    
    def show_log(self, message: str) -> None:
        """添加日志消息"""
        self.log_messages.append(message)
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
    
    def get_player_action(self) -> str:
        """
        获取玩家操作
        
        Returns:
            操作命令
        """
        while True:
            action = input("\n请输入操作: ").strip().upper()
            if action in ['P', 'S', 'E', 'H', 'Q', 'D']:
                return action
            if action.isdigit():
                return action
            print("无效操作，请重新输入 [P/S/E/H/Q] 或 牌的编号")
    
    def choose_card_to_play(self, player: 'Player') -> Optional['Card']:
        """
        选择要使用的手牌
        
        Args:
            player: 玩家
            
        Returns:
            选择的卡牌，取消返回None
        """
        if not player.hand:
            print("你没有手牌")
            return None
        
        print("\n选择要使用的卡牌 (输入0取消):")
        for i, card in enumerate(player.hand, 1):
            print(f"  [{i}] {card.display_name} - {card.description[:30]}...")
        
        while True:
            choice = input("请选择 [0-{}]: ".format(len(player.hand))).strip()
            try:
                idx = int(choice)
                if idx == 0:
                    return None
                if 1 <= idx <= len(player.hand):
                    return player.hand[idx - 1]
            except ValueError:
                pass
            print("无效选择")
    
    def choose_target(self, player: 'Player', targets: List['Player'], 
                     prompt: str = "选择目标") -> Optional['Player']:
        """
        选择目标玩家
        
        Args:
            player: 当前玩家
            targets: 可选目标列表
            prompt: 提示文字
            
        Returns:
            选择的目标，取消返回None
        """
        if not targets:
            print("没有可选目标")
            return None
        
        print(f"\n{prompt} (输入0取消):")
        for i, target in enumerate(targets, 1):
            hp_bar = ASCIIArt.get_hp_bar(target.hp, target.max_hp)
            hero_name = target.hero.name if target.hero else "???"
            print(f"  [{i}] {target.name} - {hero_name} {hp_bar}")
        
        while True:
            choice = input("请选择 [0-{}]: ".format(len(targets))).strip()
            try:
                idx = int(choice)
                if idx == 0:
                    return None
                if 1 <= idx <= len(targets):
                    return targets[idx - 1]
            except ValueError:
                pass
            print("无效选择")
    
    def choose_cards_to_discard(self, player: 'Player', 
                                count: int) -> List['Card']:
        """
        选择要弃置的手牌
        
        Args:
            player: 玩家
            count: 需要弃置的数量
            
        Returns:
            选择弃置的卡牌列表
        """
        print(f"\n需要弃置 {count} 张牌:")
        for i, card in enumerate(player.hand, 1):
            print(f"  [{i}] {card.display_name}")
        
        selected = []
        while len(selected) < count:
            remaining = count - len(selected)
            prompt = f"选择要弃置的牌 (还需{remaining}张): "
            choice = input(prompt).strip()
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(player.hand):
                    card = player.hand[idx]
                    if card not in selected:
                        selected.append(card)
                        print(f"已选择: {card.display_name}")
                    else:
                        print("已经选择过这张牌了")
                else:
                    print("无效选择")
            except ValueError:
                print("请输入数字")
        
        return selected
    
    def ask_for_shan(self, player: 'Player') -> Optional['Card']:
        """
        询问玩家是否出闪
        
        Args:
            player: 玩家
            
        Returns:
            选择的闪牌，不出返回None
        """
        shan_cards = player.get_cards_by_name("闪")
        if not shan_cards:
            return None
        
        print(f"\n{player.name} 需要出【闪】!")
        print(f"你有 {len(shan_cards)} 张【闪】")
        choice = input("是否出闪? [Y/N]: ").strip().upper()
        
        if choice == 'Y':
            return shan_cards[0]
        return None
    
    def ask_for_sha(self, player: 'Player') -> Optional['Card']:
        """
        询问玩家是否出杀
        
        Args:
            player: 玩家
            
        Returns:
            选择的杀牌，不出返回None
        """
        sha_cards = player.get_cards_by_name("杀")
        if not sha_cards:
            return None
        
        print(f"\n{player.name} 需要出【杀】!")
        print(f"你有 {len(sha_cards)} 张【杀】")
        choice = input("是否出杀? [Y/N]: ").strip().upper()
        
        if choice == 'Y':
            return sha_cards[0]
        return None
    
    def ask_for_tao(self, savior: 'Player', dying: 'Player') -> Optional['Card']:
        """
        询问玩家是否使用桃救援
        
        Args:
            savior: 救援者
            dying: 濒死玩家
            
        Returns:
            选择的桃牌，不救返回None
        """
        tao_cards = savior.get_cards_by_name("桃")
        if not tao_cards:
            return None
        
        print(f"\n{dying.name} 濒死! {savior.name} 是否使用【桃】救援?")
        print(f"你有 {len(tao_cards)} 张【桃】")
        choice = input("是否使用桃? [Y/N]: ").strip().upper()
        
        if choice == 'Y':
            return tao_cards[0]
        return None

    def ask_for_wuxie(self, responder: 'Player', trick_card: 'Card', 
                      source: 'Player', target: Optional['Player'], 
                      currently_cancelled: bool) -> Optional['Card']:
        wuxie_cards = responder.get_cards_by_name("无懈可击")
        if not wuxie_cards:
            return None

        action = "抵消" if not currently_cancelled else "使其生效"
        target_name = target.name if target else "-"
        print(f"\n{responder.name} 是否使用【无懈可击】{action}【{trick_card.name}】?")
        print(f"来源: {source.name}  目标: {target_name}")
        print(f"你有 {len(wuxie_cards)} 张【无懈可击】")
        choice = input("是否使用无懈可击? [Y/N]: ").strip().upper()

        if choice == 'Y':
            return wuxie_cards[0]
        return None
    
    def choose_card_from_player(self, chooser: 'Player', 
                               target: 'Player') -> Optional['Card']:
        """
        从目标玩家区域选择一张牌
        
        Args:
            chooser: 选择者
            target: 目标玩家
            
        Returns:
            选择的卡牌
        """
        all_cards = target.get_all_cards()
        if not all_cards:
            return None
        
        print(f"\n选择 {target.name} 的一张牌:")
        
        # 手牌（不可见）
        hand_count = len(target.hand)
        if hand_count > 0:
            print(f"  [1-{hand_count}] 手牌 ({hand_count}张)")
        
        # 装备（可见）
        equip_cards = target.equipment.get_all_cards()
        offset = hand_count
        for i, card in enumerate(equip_cards, 1):
            print(f"  [{offset + i}] 装备: {card.display_name}")
        
        while True:
            choice = input(f"请选择 [1-{len(all_cards)}]: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(all_cards):
                    return all_cards[idx]
            except ValueError:
                pass
            print("无效选择")
    
    def choose_suit(self, player: 'Player') -> 'CardSuit':
        """
        选择花色
        
        Args:
            player: 玩家
            
        Returns:
            选择的花色
        """
        print("\n选择花色:")
        print("  [1] ♠ 黑桃")
        print("  [2] ♥ 红心")
        print("  [3] ♣ 梅花")
        print("  [4] ♦ 方块")
        
        while True:
            choice = input("请选择 [1-4]: ").strip()
            if choice == '1':
                return CardSuit.SPADE
            elif choice == '2':
                return CardSuit.HEART
            elif choice == '3':
                return CardSuit.CLUB
            elif choice == '4':
                return CardSuit.DIAMOND
            print("无效选择")
    
    def guanxing_selection(self, player: 'Player', 
                          cards: List['Card']) -> Tuple[List['Card'], List['Card']]:
        """
        观星技能的牌序选择
        
        Args:
            player: 玩家
            cards: 观看的卡牌
            
        Returns:
            (放牌堆顶的牌, 放牌堆底的牌)
        """
        print("\n【观星】观看的牌:")
        for i, card in enumerate(cards, 1):
            print(f"  [{i}] {card.display_name}")
        
        print("\n选择放在牌堆顶的牌 (按顺序输入编号，用空格分隔，剩余放底部):")
        print("例如: 1 3 表示将1号和3号牌放顶部")
        
        while True:
            choice = input("请输入: ").strip()
            if not choice:
                # 全部放底部
                return [], cards[:]
            
            try:
                indices = [int(x) - 1 for x in choice.split()]
                if all(0 <= i < len(cards) for i in indices):
                    top_cards = [cards[i] for i in indices]
                    bottom_cards = [c for c in cards if c not in top_cards]
                    return top_cards, bottom_cards
            except ValueError:
                pass
            print("无效输入，请重新输入")
    
    def show_skill_menu(self, player: 'Player', 
                       usable_skills: List[str]) -> Optional[str]:
        """
        显示技能菜单
        
        Args:
            player: 玩家
            usable_skills: 可用技能ID列表
            
        Returns:
            选择的技能ID，取消返回None
        """
        if not usable_skills:
            print("没有可用的技能")
            return None
        
        print("\n可用技能 (输入0取消):")
        skills = []
        for skill_id in usable_skills:
            skill = player.get_skill(skill_id)
            if skill:
                skills.append((skill_id, skill))
        
        for i, (skill_id, skill) in enumerate(skills, 1):
            print(f"  [{i}] {skill.name} - {skill.description[:40]}...")
        
        while True:
            choice = input("请选择 [0-{}]: ".format(len(skills))).strip()
            try:
                idx = int(choice)
                if idx == 0:
                    return None
                if 1 <= idx <= len(skills):
                    return skills[idx - 1][0]
            except ValueError:
                pass
            print("无效选择")
    
    def show_help(self) -> None:
        """显示帮助信息"""
        print(ASCIIArt.get_help_text())
        input("\n按回车键继续...")
    
    def show_game_over(self, winner_message: str, is_victory: bool) -> None:
        """
        显示游戏结束画面
        
        Args:
            winner_message: 胜利消息
            is_victory: 玩家是否获胜
        """
        self.clear_screen()
        if is_victory:
            print(ASCIIArt.VICTORY)
        else:
            print(ASCIIArt.DEFEAT)
        
        print()
        print("=" * 50)
        print(self._center_text(winner_message, 50))
        print("=" * 50)
        print()
        input("按回车键返回主菜单...")
    
    def show_rules(self) -> None:
        """显示游戏规则"""
        self.clear_screen()
        rules = """
╔══════════════════════════════════════════════════════════════╗
║                       三国杀游戏规则                          ║
╠══════════════════════════════════════════════════════════════╣
║  游戏目标:                                                   ║
║    主公: 消灭所有反贼和内奸                                  ║
║    忠臣: 保护主公，帮助主公获胜                              ║
║    反贼: 消灭主公                                            ║
║    内奸: 最后存活（先帮主公清反贼，再与主公单挑）            ║
╠══════════════════════════════════════════════════════════════╣
║  回合流程:                                                   ║
║    1. 准备阶段 - 触发某些技能                                ║
║    2. 判定阶段 - 处理判定牌                                  ║
║    3. 摸牌阶段 - 摸两张牌                                    ║
║    4. 出牌阶段 - 可以使用手牌和技能                          ║
║    5. 弃牌阶段 - 手牌超过体力值需弃牌                        ║
║    6. 结束阶段 - 回合结束                                    ║
╠══════════════════════════════════════════════════════════════╣
║  基本牌:                                                     ║
║    杀 - 对攻击范围内一名角色使用，需出闪否则受1点伤害        ║
║    闪 - 被杀时打出，抵消杀的效果                             ║
║    桃 - 回复1点体力，或濒死时救援                            ║
╠══════════════════════════════════════════════════════════════╣
║  特殊规则:                                                   ║
║    - 每回合只能使用一张杀（某些武将/装备除外）               ║
║    - 手牌上限等于当前体力值                                  ║
║    - 杀死反贼摸三张牌，主公杀忠臣需弃所有牌                  ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(rules)
        input("\n按回车键返回...")
    
    def wait_for_continue(self, message: str = "按回车键继续...") -> None:
        """等待用户确认"""
        input(message)
    
    def _center_text(self, text: str, width: int) -> str:
        """居中文本"""
        display_width = self._get_display_width(text)
        padding = (width - display_width) // 2
        return " " * max(0, padding) + text
    
    def _truncate_text(self, text: str, max_width: int) -> str:
        """截断文本到指定宽度"""
        current_width = 0
        result = []
        for char in text:
            char_width = 2 if ord(char) > 127 else 1
            if current_width + char_width > max_width:
                break
            result.append(char)
            current_width += char_width
        return ''.join(result)
    
    def _get_display_width(self, text: str) -> int:
        """计算显示宽度（中文字2宽度）"""
        width = 0
        for char in text:
            if ord(char) > 127:
                width += 2
            else:
                width += 1
        return width
    
    def _pad_to_width(self, text: str, target_width: int, align: str = 'left') -> str:
        """
        将文本填充到指定宽度（正确处理中文字符）
        
        Args:
            text: 文本
            target_width: 目标宽度
            align: 对齐方式 ('left', 'right', 'center')
        """
        current_width = self._get_display_width(text)
        padding_needed = target_width - current_width
        
        if padding_needed <= 0:
            return text
        
        if align == 'left':
            return text + ' ' * padding_needed
        elif align == 'right':
            return ' ' * padding_needed + text
        else:  # center
            left_pad = padding_needed // 2
            right_pad = padding_needed - left_pad
            return ' ' * left_pad + text + ' ' * right_pad
    
    def _get_phase_name(self, phase: str) -> str:
        """获取阶段名称"""
        phase_names = {
            "prepare": "准备阶段",
            "judge": "判定阶段",
            "draw": "摸牌阶段",
            "play": "出牌阶段",
            "discard": "弃牌阶段",
            "end": "结束阶段"
        }
        return phase_names.get(phase, phase)
    
    def _color_text(self, text: str, color: str) -> str:
        """给文本添加颜色"""
        if not self.use_color:
            return text
        
        color_codes = {
            'red': Fore.RED,
            'green': Fore.GREEN,
            'blue': Fore.BLUE,
            'yellow': Fore.YELLOW,
            'dark': Fore.LIGHTBLACK_EX,
            'reset': Style.RESET_ALL
        }
        
        color_code = color_codes.get(color, '')
        reset = color_codes['reset']
        return f"{color_code}{text}{reset}"
    
    def ask_for_jijiang(self, player: 'Player') -> Optional['Card']:
        """询问是否响应激将"""
        sha_cards = player.get_cards_by_name("杀")
        if not sha_cards:
            return None
        
        print(f"\n主公发动【激将】! {player.name} 是否响应?")
        choice = input("是否打出杀? [Y/N]: ").strip().upper()
        
        if choice == 'Y':
            return sha_cards[0]
        return None
    
    def ask_for_hujia(self, player: 'Player') -> Optional['Card']:
        """询问是否响应护驾"""
        shan_cards = player.get_cards_by_name("闪")
        if not shan_cards:
            return None
        
        print(f"\n主公发动【护驾】! {player.name} 是否响应?")
        choice = input("是否打出闪? [Y/N]: ").strip().upper()
        
        if choice == 'Y':
            return shan_cards[0]
        return None
