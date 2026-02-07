# -*- coding: utf-8 -*-
"""游戏控制器模块.

管理一局游戏的初始化、主循环、回合流程和出牌交互。
从 main.py 中的 SanguoshaGame 类重构而来。
"""

from __future__ import annotations

import copy
import os
import random
import time
from typing import Dict, List, Optional, TYPE_CHECKING

from .engine import GameEngine, GameState, GamePhase
from .player import Player, Identity
from .card import Card, CardType, CardName
from .constants import SkillId
from .skill import SkillSystem

# AI 回合延迟（秒）。设置环境变量 SANGUOSHA_AI_DELAY=0 可在测试中禁用。
AI_TURN_DELAY: float = float(os.environ.get("SANGUOSHA_AI_DELAY", "0.3"))

if TYPE_CHECKING:
    from .hero import Hero
    from ui.protocol import GameUI
    from ai.bot import AIBot, AIDifficulty


class GameController:
    """游戏控制器.

    负责一局游戏的初始化、主循环和流程控制。
    由 Textual TUI 入口创建并调用 ``run()``。
    """

    def __init__(self, ui: GameUI, ai_difficulty: AIDifficulty | None = None):
        """初始化游戏控制器.

        Args:
            ui: 实现 GameUI 协议的 UI 后端实例。
            ai_difficulty: AI 难度，默认 NORMAL。
        """
        from ai.bot import AIDifficulty

        self.ui = ui
        self.engine: Optional[GameEngine] = None
        self.ai_difficulty: AIDifficulty = ai_difficulty or AIDifficulty.NORMAL
        self.is_running = True

    # ==================== 主循环 ====================

    def run(self) -> None:
        """运行游戏主循环（菜单 → 新游戏 → 回合 → 结算）"""
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
        from ai.bot import AIDifficulty
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

    # ==================== 武将选择 ====================

    def _choose_heroes(self) -> None:
        """武将选择阶段 - 符合真实三国杀规则"""
        if not self.engine:
            return

        # 获取所有武将
        all_heroes = self.engine.hero_repo.get_all_heroes()
        used_heroes: List[str] = []

        # 分离主公专属武将（有主公技的）和普通武将
        lord_heroes = [h for h in all_heroes if any(s.is_lord_skill for s in h.skills)]
        normal_heroes = [h for h in all_heroes if not any(s.is_lord_skill for s in h.skills)]

        # 人类玩家选择武将
        if self.engine.human_player:
            is_lord = self.engine.human_player.identity == Identity.LORD

            if is_lord:
                self.ui.show_log("【主公选将】你是主公，可从5名武将中选择")
                available = lord_heroes.copy()
                remaining = 5 - len(available)
                if remaining > 0:
                    extra = random.sample(normal_heroes, min(remaining, len(normal_heroes)))
                    available.extend(extra)
                random.shuffle(available)
                available = available[:5]
            else:
                self.ui.show_log("【选择武将】请从3名武将中选择")
                available = random.sample(normal_heroes, min(3, len(normal_heroes)))

            selected = self.ui.show_hero_selection(available, 1, is_lord)

            if selected:
                hero = copy.deepcopy(selected[0])
                self.engine.human_player.set_hero(hero)
                used_heroes.append(hero.id)

                if is_lord:
                    self.ui.show_log(f"主公选择了武将：【{hero.name}】")

        # AI玩家自动选择武将（避免重复）
        ai_choices = self._auto_choose_heroes_for_ai(used_heroes)
        self.engine.choose_heroes(ai_choices)

    def _auto_choose_heroes_for_ai(self, used_heroes: List[str]) -> Dict[int, str]:
        """为AI玩家自动选择武将"""
        all_heroes = self.engine.hero_repo.get_all_heroes()
        available = [h for h in all_heroes if h.id not in used_heroes]

        ai_choices: Dict[int, str] = {}
        for player in self.engine.players:
            if player.is_ai and player.hero is None:
                if available:
                    hero = self._select_hero_for_ai(player, available)
                    ai_choices[player.id] = hero.id
                    available.remove(hero)
                    self.ui.show_log(f"{player.name} 选择了武将：【{hero.name}】")

        return ai_choices

    def _select_hero_for_ai(self, player: Player, available: List[Hero]) -> Hero:
        """根据AI身份智能选择武将"""
        from game.hero import SkillType

        identity = player.identity
        preferred: List[Hero] = []

        if identity == Identity.LORD:
            preferred = [h for h in available if any(s.is_lord_skill for s in h.skills)]
        elif identity == Identity.LOYALIST:
            preferred = [h for h in available if h.max_hp >= 4]
        elif identity == Identity.REBEL:
            preferred = [h for h in available if any(s.skill_type == SkillType.ACTIVE for s in h.skills)]
        elif identity == Identity.SPY:
            preferred = [h for h in available if h.max_hp >= 4 or len(h.skills) >= 2]

        if preferred:
            return random.choice(preferred)
        return random.choice(available)

    def _setup_ai_bots(self) -> None:
        """设置AI机器人"""
        if not self.engine:
            return

        from ai.bot import AIBot
        for player in self.engine.players:
            if player.is_ai:
                bot = AIBot(player, self.ai_difficulty)
                self.engine.ai_bots[player.id] = bot

    # ==================== 回合流程 ====================

    def _game_loop(self) -> None:
        """游戏主循环"""
        if not self.engine:
            return

        while not self.engine.is_game_over():
            current_player = self.engine.current_player

            self.ui.show_game_state(self.engine, current_player)

            if current_player.is_ai:
                self._run_ai_turn(current_player)
            else:
                self._run_human_turn(current_player)

            if self.engine.is_game_over():
                break

            self.engine.next_turn()

        self._handle_game_over()

    def _show_turn_header(self, player: Player) -> None:
        """显示回合头部信息"""
        self.ui.show_log("")
        self.ui.show_log("════════════════════════")
        self.ui.show_log(f"【第{self.engine.round_count}回合】 {player.name}({player.hero.name}) 的回合")
        self.ui.show_log("════════════════════════")

    def _execute_prepare_phase(self, player: Player) -> None:
        """执行准备阶段"""
        self.ui.show_log("▶ 准备阶段")
        self.engine.phase_prepare(player)

    def _execute_draw_phase(self, player: Player, show_count: bool = True) -> int:
        """执行摸牌阶段，返回摸牌数量"""
        self.ui.show_log("▶ 摸牌阶段")
        old_count = player.hand_count
        self.engine.phase_draw(player)
        new_cards = player.hand_count - old_count
        if show_count:
            if player.is_ai:
                self.ui.show_log(f"  └─ {player.name} 摸了 {new_cards} 张牌")
            else:
                self.ui.show_log(f"  └─ 摸了 {new_cards} 张牌，当前手牌数: {player.hand_count}")
        return new_cards

    def _execute_discard_phase(self, player: Player) -> None:
        """执行弃牌阶段"""
        if player.need_discard > 0:
            self.ui.show_log("▶ 弃牌阶段")
            if player.is_ai:
                self.ui.show_log(f"  └─ 需弃置 {player.need_discard} 张牌")
            else:
                self.ui.show_log(f"  └─ 需弃置 {player.need_discard} 张牌（手牌上限: {player.hp}）")
                self.engine.phase = GamePhase.DISCARD
                self.ui.show_game_state(self.engine, player)
                self._human_discard_phase(player)
                return
            self.engine.phase_discard(player)

    def _execute_end_phase(self, player: Player) -> None:
        """执行结束阶段"""
        self.ui.show_log("▶ 结束阶段")
        self.engine.phase_end(player)
        turn_end_msg = f"─── {player.name} 回合结束 ───" if player.is_ai else "─── 回合结束 ───"
        self.ui.show_log(turn_end_msg)

    def _run_ai_turn(self, player: Player) -> None:
        """执行AI回合"""
        if not self.engine:
            return

        self._show_turn_header(player)
        self.ui.show_game_state(self.engine, player)

        player.reset_turn()

        self._execute_prepare_phase(player)
        self._execute_draw_phase(player)
        self.ui.show_game_state(self.engine, player)
        if AI_TURN_DELAY > 0:
            time.sleep(AI_TURN_DELAY)

        self.ui.show_log("▶ 出牌阶段")
        self.engine.phase = GamePhase.PLAY
        if player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            bot.play_phase(player, self.engine)
        self.ui.show_game_state(self.engine, player)
        if AI_TURN_DELAY > 0:
            time.sleep(AI_TURN_DELAY)

        self._execute_discard_phase(player)
        self._execute_end_phase(player)
        if AI_TURN_DELAY > 0:
            time.sleep(AI_TURN_DELAY)

    def _run_human_turn(self, player: Player) -> None:
        """执行人类玩家回合"""
        if not self.engine:
            return

        self._show_turn_header(player)
        player.reset_turn()

        self._execute_prepare_phase(player)
        self.ui.show_game_state(self.engine, player)

        self._execute_draw_phase(player)
        self.ui.show_game_state(self.engine, player)

        self.ui.show_log("▶ 出牌阶段")
        self.engine.phase = GamePhase.PLAY
        self._human_play_phase(player)

        self._execute_discard_phase(player)
        self._execute_end_phase(player)

    # ==================== 出牌交互 ====================

    def _human_play_phase(self, player: Player) -> None:
        """人类玩家出牌阶段 - 默认直接进入出牌模式"""
        if not self.engine:
            return

        if not self._can_do_anything(player):
            self._update_playable_mask(player)
            self.ui.show_game_state(self.engine, player)
            print("\n" + "=" * 50)
            print("【自动跳过】当前无可用手牌或技能")
            print("=" * 50)
            self.ui.show_log("  └─ 无可出牌，自动结束出牌阶段")
            if AI_TURN_DELAY > 0:
                time.sleep(AI_TURN_DELAY * 3)  # 稍长一点让玩家看到提示
            return

        while True:
            self._update_playable_mask(player)
            self.ui.show_game_state(self.engine, player)

            action = self.ui.get_player_action()

            if action == 'E':
                self.ui.show_log("  └─ 结束出牌阶段")
                break
            elif action == 'H':
                self.ui.show_help()
            elif action == 'Q':
                if self._confirm_quit():
                    self.engine.state = GameState.FINISHED
                    return
            elif action == 'S':
                self._handle_use_skill(player)
            elif action.isdigit():
                card_idx = int(action) - 1
                if 0 <= card_idx < len(player.hand):
                    card = player.hand[card_idx]
                    self._handle_play_specific_card(player, card)
                else:
                    print("无效的卡牌编号")

            if self.engine.is_game_over():
                return

            if not self._can_do_anything(player):
                print("\n【自动结束】已无可用手牌或技能")
                self.ui.show_log("  └─ 无可出牌，自动结束出牌阶段")
                if AI_TURN_DELAY > 0:
                    time.sleep(AI_TURN_DELAY * 1.5)
                break

    def _check_card_usable(self, player: Player, card: Card) -> bool:
        """检查卡牌是否可以使用"""
        if card.card_type == CardType.EQUIPMENT:
            return True
        if card.name == CardName.SHA:
            if not player.can_use_sha():
                return False
            targets = self.engine.get_targets_in_range(player)
            return len(targets) > 0
        if card.name == CardName.TAO:
            return player.hp < player.max_hp
        if card.name == CardName.SHAN:
            return False
        if card.name == CardName.SHUNSHOU:
            others = self.engine.get_other_players(player)
            valid = [t for t in others
                     if self.engine.calculate_distance(player, t) <= 1 and t.has_any_card()]
            return len(valid) > 0
        if card.name == CardName.GUOHE:
            others = self.engine.get_other_players(player)
            valid = [t for t in others if t.has_any_card()]
            return len(valid) > 0
        if card.name == CardName.JUEDOU:
            return len(self.engine.get_other_players(player)) > 0
        return True

    def get_playable_mask(self, player: Player) -> List[bool]:
        """返回玩家每张手牌是否可出的布尔列表。"""
        return [self._check_card_usable(player, c) for c in player.hand]

    def _update_playable_mask(self, player: Player) -> None:
        """计算可出牌掩码并存入 engine，供 UI 读取。"""
        if self.engine and self.engine.phase == GamePhase.PLAY:
            self.engine._playable_mask = self.get_playable_mask(player)
        else:
            self.engine._playable_mask = []

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

        if card.card_type == CardType.EQUIPMENT:
            self.ui.show_log(f"  └─ 装备了 [{card.name}]")
            self.engine.use_card(player, card)

        elif card.name == CardName.SHA:
            if not player.can_use_sha():
                print("⚠ 本回合已使用过【杀】")
                has_paoxiao = player.has_skill(SkillId.PAOXIAO)
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

        elif card.name == CardName.TAO:
            if player.hp >= player.max_hp:
                print("⚠ 体力已满，无法使用【桃】")
                return
            self.ui.show_log("  └─ 使用【桃】回复1点体力")
            self.engine.use_card(player, card)

        elif card.name == CardName.SHAN:
            print("⚠ 【闪】只能在被【杀】时使用")
            return

        elif card.name == CardName.WUZHONG:
            self.ui.show_log("  └─ 使用【无中生有】摸两张牌")
            self.engine.use_card(player, card)

        elif card.name in [CardName.NANMAN, CardName.WANJIAN]:
            self.ui.show_log(f"  └─ 使用【{card.name}】")
            self.engine.use_card(player, card)

        elif card.name == CardName.TAOYUAN:
            self.ui.show_log("  └─ 使用【桃园结义】所有人回复1点体力")
            self.engine.use_card(player, card)

        elif card.name == CardName.JUEDOU:
            others = self.engine.get_other_players(player)
            if not others:
                print("⚠ 没有可选目标")
                return
            target = self.ui.choose_target(player, others, "选择决斗目标")
            if target:
                self.ui.show_log(f"  └─ 对 {target.name} 使用【决斗】")
                self.engine.use_card(player, card, [target])

        elif card.name == CardName.GUOHE:
            others = self.engine.get_other_players(player)
            valid = [t for t in others if t.has_any_card()]
            if not valid:
                print("⚠ 没有有牌的目标")
                return
            target = self.ui.choose_target(player, valid, "选择拆牌目标")
            if target:
                self.ui.show_log(f"  └─ 对 {target.name} 使用【过河拆桥】")
                self.engine.use_card(player, card, [target])

        elif card.name == CardName.SHUNSHOU:
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

    def _handle_use_skill(self, player: Player) -> None:
        """处理使用技能"""
        if not self.engine or not self.engine.skill_system:
            return

        usable_skills = self.engine.skill_system.get_usable_skills(player)

        skill_id = self.ui.show_skill_menu(player, usable_skills)
        if not skill_id:
            return

        if skill_id == "zhiheng":
            if player.hand:
                self.ui.show_log("选择要换掉的牌")
                cards = self._select_cards_for_skill(player, 1, len(player.hand))
                if cards:
                    self.engine.skill_system.use_skill(skill_id, player, cards=cards)
        elif skill_id == "rende":
            if player.hand:
                cards = self._select_cards_for_skill(player, 1, len(player.hand))
                if cards:
                    others = self.engine.get_other_players(player)
                    target = self.ui.choose_target(player, others, "选择交给谁")
                    if target:
                        self.engine.skill_system.use_skill(skill_id, player,
                                                           targets=[target], cards=cards)
        elif skill_id == "fanjian":
            if player.hand:
                self.ui.show_log("选择要展示的牌")
                card = self.ui.choose_card_to_play(player)
                if card:
                    others = self.engine.get_other_players(player)
                    target = self.ui.choose_target(player, others, "选择反间目标")
                    if target:
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

    # ==================== 弃牌 ====================

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

    # ==================== 游戏结算 ====================

    def _handle_game_over(self) -> None:
        """处理游戏结束"""
        if not self.engine:
            return

        winner_message = self.engine.get_winner_message()

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

    def _confirm_quit(self) -> bool:
        """确认退出"""
        choice = input("确定要退出游戏吗? [Y/N]: ").strip().upper()
        return choice == 'Y'
