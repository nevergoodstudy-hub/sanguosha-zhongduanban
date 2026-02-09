"""游戏控制器模块.

管理一局游戏的初始化、主循环、回合流程和出牌交互。
从 main.py 中的 SanguoshaGame 类重构而来。
"""

from __future__ import annotations

import copy
import logging
import random
import time
from typing import TYPE_CHECKING

from i18n import t as _t

from .card import Card, CardName, CardType
from .config import get_config
from .constants import SkillId
from .engine import GameEngine, GamePhase, GameState
from .player import Identity, Player
from .skill import SkillSystem

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ai.bot import AIDifficulty
    from ui.protocol import GameUI

    from .hero import Hero


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
        self.engine: GameEngine | None = None
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
                self.ui.show_log(_t("controller.thanks"))
                logger.info("User exited game via main menu")

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
        assert self.engine is not None  # mypy type narrowing

        # 获取所有武将
        all_heroes = self.engine.hero_repo.get_all_heroes()
        used_heroes: list[str] = []

        # 分离主公专属武将（有主公技的）和普通武将
        lord_heroes = [h for h in all_heroes if any(s.is_lord_skill for s in h.skills)]
        normal_heroes = [h for h in all_heroes if not any(s.is_lord_skill for s in h.skills)]

        # 人类玩家选择武将
        if self.engine.human_player:
            is_lord = self.engine.human_player.identity == Identity.LORD

            if is_lord:
                self.ui.show_log(_t("controller.lord_choose_hero"))
                available = lord_heroes.copy()
                remaining = 5 - len(available)
                if remaining > 0:
                    extra = random.sample(normal_heroes, min(remaining, len(normal_heroes)))
                    available.extend(extra)
                random.shuffle(available)
                available = available[:5]
            else:
                self.ui.show_log(_t("controller.choose_hero"))
                available = random.sample(normal_heroes, min(3, len(normal_heroes)))

            selected = self.ui.show_hero_selection(available, 1, is_lord)

            if selected:
                hero = copy.deepcopy(selected[0])
                self.engine.human_player.set_hero(hero)
                used_heroes.append(hero.id)

                if is_lord:
                    self.ui.show_log(_t("controller.hero_chosen", player=self.engine.human_player.name, hero=hero.name))

        # AI玩家自动选择武将（避免重复）
        ai_choices = self._auto_choose_heroes_for_ai(used_heroes)
        self.engine.choose_heroes(ai_choices)

    def _auto_choose_heroes_for_ai(self, used_heroes: list[str]) -> dict[int, str]:
        """为AI玩家自动选择武将"""
        all_heroes = self.engine.hero_repo.get_all_heroes()
        available = [h for h in all_heroes if h.id not in used_heroes]

        ai_choices: dict[int, str] = {}
        for player in self.engine.players:
            if player.is_ai and player.hero is None:
                if available:
                    hero = self._select_hero_for_ai(player, available)
                    ai_choices[player.id] = hero.id
                    available.remove(hero)
                    self.ui.show_log(_t("controller.hero_chosen", player=player.name, hero=hero.name))

        return ai_choices

    def _select_hero_for_ai(self, player: Player, available: list[Hero]) -> Hero:
        """根据AI身份智能选择武将"""
        from game.hero import SkillType

        identity = player.identity
        preferred: list[Hero] = []

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
        assert self.engine is not None  # mypy type narrowing
        self.ui.show_log("")
        self.ui.show_log("════════════════════════")
        self.ui.show_log(_t("controller.round_header", round=self.engine.round_count, player=player.name, hero=player.hero.name))
        self.ui.show_log("════════════════════════")

    def _execute_prepare_phase(self, player: Player) -> None:
        """执行准备阶段"""
        assert self.engine is not None  # mypy type narrowing
        self.ui.show_log(_t("controller.phase_prepare"))
        self.engine.phase_prepare(player)

    def _execute_draw_phase(self, player: Player, show_count: bool = True) -> int:
        """执行摸牌阶段，返回摸牌数量"""
        assert self.engine is not None  # mypy type narrowing
        self.ui.show_log(_t("controller.phase_draw"))
        old_count = player.hand_count
        self.engine.phase_draw(player)
        new_cards = player.hand_count - old_count
        if show_count:
            if player.is_ai:
                self.ui.show_log(_t("controller.drew_cards_ai", player=player.name, count=new_cards))
            else:
                self.ui.show_log(_t("controller.drew_cards_human", count=new_cards, hand_count=player.hand_count))
        return new_cards

    def _execute_discard_phase(self, player: Player) -> None:
        """执行弃牌阶段"""
        assert self.engine is not None  # mypy type narrowing
        if player.need_discard > 0:
            self.ui.show_log(_t("controller.phase_discard"))
            if player.is_ai:
                self.ui.show_log(_t("controller.need_discard", count=player.need_discard))
            else:
                self.ui.show_log(_t("controller.need_discard_limit", count=player.need_discard, limit=player.hp))
                self.engine.phase = GamePhase.DISCARD
                self.ui.show_game_state(self.engine, player)
                self._human_discard_phase(player)
                return
            self.engine.phase_discard(player)

    def _execute_end_phase(self, player: Player) -> None:
        """执行结束阶段"""
        assert self.engine is not None  # mypy type narrowing
        self.ui.show_log(_t("controller.phase_end"))
        self.engine.phase_end(player)
        turn_end_msg = _t("controller.turn_end_ai", player=player.name) if player.is_ai else _t("controller.turn_end_human")
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
        cfg = get_config()
        if cfg.ai_turn_delay > 0:
            time.sleep(cfg.ai_turn_delay)

        self.ui.show_log(_t("controller.phase_play"))
        self.engine.phase = GamePhase.PLAY
        if player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            bot.play_phase(player, self.engine)
        self.ui.show_game_state(self.engine, player)
        if cfg.ai_turn_delay > 0:
            time.sleep(cfg.ai_turn_delay)

        self._execute_discard_phase(player)
        self._execute_end_phase(player)
        if cfg.ai_turn_delay > 0:
            time.sleep(cfg.ai_turn_delay)

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

        self.ui.show_log(_t("controller.phase_play"))
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
            self.ui.show_log(_t("controller.auto_skip"))
            self.ui.show_log(_t("controller.auto_skip_detail"))
            cfg = get_config()
            if cfg.ai_turn_delay > 0:
                time.sleep(cfg.ai_turn_delay * 3)  # 稍长一点让玩家看到提示
            return

        while True:
            self._update_playable_mask(player)
            self.ui.show_game_state(self.engine, player)

            action = self.ui.get_player_action()

            if action == 'E':
                self.ui.show_log(_t("controller.end_play"))
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
                    self.ui.show_log(_t("controller.invalid_card_num"))

            if self.engine.is_game_over():
                return

            if not self._can_do_anything(player):
                self.ui.show_log(_t("controller.auto_end"))
                self.ui.show_log(_t("controller.auto_skip_detail"))
                cfg = get_config()
                if cfg.ai_turn_delay > 0:
                    time.sleep(cfg.ai_turn_delay * 1.5)
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

    def get_playable_mask(self, player: Player) -> list[bool]:
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
            self.ui.show_log(_t("controller.equipped", card=card.name))
            self.engine.use_card(player, card)

        elif card.name == CardName.SHA:
            if not player.can_use_sha():
                self.ui.show_log(_t("controller.sha_used"))
                has_paoxiao = player.has_skill(SkillId.PAOXIAO)
                if has_paoxiao:
                    self.ui.show_log(_t("controller.sha_paoxiao"))
                else:
                    return

            targets = self.engine.get_targets_in_range(player)
            if not targets:
                self.ui.show_log(_t("controller.no_targets"))
                return

            target = self.ui.choose_target(player, targets, _t("controller.choose_attack"))
            if target:
                self.ui.show_log(_t("controller.use_sha", target=target.name))
                self.engine.use_card(player, card, [target])

        elif card.name == CardName.TAO:
            if player.hp >= player.max_hp:
                self.ui.show_log(_t("controller.hp_full"))
                return
            self.ui.show_log(_t("controller.use_tao"))
            self.engine.use_card(player, card)

        elif card.name == CardName.SHAN:
            self.ui.show_log(_t("controller.shan_passive"))
            return

        elif card.name == CardName.WUZHONG:
            self.ui.show_log(_t("controller.use_wuzhong"))
            self.engine.use_card(player, card)

        elif card.name in [CardName.NANMAN, CardName.WANJIAN]:
            self.ui.show_log(_t("controller.use_card", card=card.name))
            self.engine.use_card(player, card)

        elif card.name == CardName.TAOYUAN:
            self.ui.show_log(_t("controller.use_taoyuan"))
            self.engine.use_card(player, card)

        elif card.name == CardName.JUEDOU:
            others = self.engine.get_other_players(player)
            if not others:
                self.ui.show_log(_t("controller.no_other_targets"))
                return
            target = self.ui.choose_target(player, others, _t("controller.choose_duel_target"))
            if target:
                self.ui.show_log(_t("controller.use_juedou", target=target.name))
                self.engine.use_card(player, card, [target])

        elif card.name == CardName.GUOHE:
            others = self.engine.get_other_players(player)
            valid = [t for t in others if t.has_any_card()]
            if not valid:
                self.ui.show_log(_t("controller.no_card_targets"))
                return
            target = self.ui.choose_target(player, valid, _t("controller.choose_guohe_target"))
            if target:
                self.ui.show_log(_t("controller.use_guohe", target=target.name))
                self.engine.use_card(player, card, [target])

        elif card.name == CardName.SHUNSHOU:
            others = self.engine.get_other_players(player)
            valid = [t for t in others
                     if self.engine.calculate_distance(player, t) <= 1 and t.has_any_card()]
            if not valid:
                self.ui.show_log(_t("controller.no_shunshou_targets"))
                return
            target = self.ui.choose_target(player, valid, _t("controller.choose_shunshou_target"))
            if target:
                self.ui.show_log(_t("controller.use_shunshou", target=target.name))
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
                self.ui.show_log(_t("controller.choose_discard_cards"))
                cards = self._select_cards_for_skill(player, 1, len(player.hand))
                if cards:
                    self.engine.skill_system.use_skill(skill_id, player, cards=cards)
        elif skill_id == "rende":
            if player.hand:
                cards = self._select_cards_for_skill(player, 1, len(player.hand))
                if cards:
                    others = self.engine.get_other_players(player)
                    target = self.ui.choose_target(player, others, _t("controller.choose_give_target"))
                    if target:
                        self.engine.skill_system.use_skill(skill_id, player,
                                                           targets=[target], cards=cards)
        elif skill_id == "fanjian":
            if player.hand:
                self.ui.show_log(_t("controller.choose_show_card"))
                card = self.ui.choose_card_to_play(player)
                if card:
                    others = self.engine.get_other_players(player)
                    target = self.ui.choose_target(player, others, _t("controller.choose_fanjian_target"))
                    if target:
                        self.engine.skill_system.use_skill(skill_id, player,
                                                           targets=[target], cards=[card])

    def _select_cards_for_skill(self, player: Player,
                                min_count: int, max_count: int) -> list[Card]:
        """为技能选择卡牌"""
        self.ui.show_log(_t("controller.select_cards", min=min_count, max=max_count))
        for i, card in enumerate(player.hand, 1):
            self.ui.show_log(f"  [{i}] {card.display_name}")

        while True:
            choice = input(_t("controller.input_prompt")).strip()
            if not choice:
                return []

            try:
                indices = [int(x) - 1 for x in choice.split()]
                if min_count <= len(indices) <= max_count:
                    if all(0 <= i < len(player.hand) for i in indices):
                        return [player.hand[i] for i in indices]
            except ValueError:
                pass
            self.ui.show_log(_t("controller.select_cards_range", min=min_count, max=max_count))

    # ==================== 弃牌 ====================

    def _human_discard_phase(self, player: Player) -> None:
        """人类玩家弃牌阶段"""
        if not self.engine:
            return

        discard_count = player.need_discard
        if discard_count <= 0:
            return

        self.ui.show_log(_t("controller.need_discard_cards", count=discard_count))
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
        choice = input(_t("controller.confirm_quit")).strip().upper()
        return choice == 'Y'
