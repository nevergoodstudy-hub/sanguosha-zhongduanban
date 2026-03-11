"""游戏主界面 (M3-T02)."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, RichLog, Static

from i18n import t as _t

if TYPE_CHECKING:
    from game.engine import GameEngine
    from game.player import Player


logger = logging.getLogger(__name__)


class GamePlayScreen(Screen):
    """游戏主界面 (M3-T02)."""

    BINDINGS = [
        Binding("e", "end_play", _t("ui.play.end_play")),
        Binding("h", "show_help", _t("ui.play.help")),
        Binding("q", "quit_game", _t("ui.play.quit")),
        Binding("1", "play_card_1", "卡牌1", show=False),
        Binding("2", "play_card_2", "卡牌2", show=False),
        Binding("3", "play_card_3", "卡牌3", show=False),
        Binding("4", "play_card_4", "卡牌4", show=False),
        Binding("5", "play_card_5", "卡牌5", show=False),
        Binding("6", "play_card_6", "卡牌6", show=False),
        Binding("7", "play_card_7", "卡牌7", show=False),
        Binding("8", "play_card_8", "卡牌8", show=False),
        Binding("9", "play_card_9", "卡牌9", show=False),
        Binding("0", "play_card_10", "卡牌10", show=False),
    ]

    CSS = """
    GamePlayScreen {
        layout: grid;
        grid-size: 2 4;
        grid-columns: 3fr 1fr;
        grid-rows: auto auto 1fr auto;
    }
    #phase-bar {
        column-span: 2;
        height: 1;
        dock: top;
        background: $primary-darken-3;
    }
    #opponents {
        row-span: 1;
        column-span: 2;
        height: auto;
        max-height: 14;
        border: round #3498db;
        overflow-y: auto;
        padding: 0 1;
    }
    #play-area {
        column-span: 2;
        height: auto;
        max-height: 5;
    }
    #battle-log {
        height: 100%;
        border: round #2ecc71;
    }
    #info-panel {
        height: 100%;
        border: round #f39c12;
        overflow-y: auto;
    }
    #player-area {
        column-span: 2;
        height: auto;
        max-height: 16;
        border: round #27ae60;
    }
    #equip-section {
        height: auto;
        max-height: 3;
        border: dashed $secondary;
        padding: 0 1;
    }
    #hand-label {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    #hand-cards {
        height: auto;
        min-height: 7;
        layout: horizontal;
        overflow-x: auto;
    }
    .card-btn {
        min-width: 16;
        margin: 0 1;
    }
    #action-bar {
        height: 3;
        layout: horizontal;
        dock: bottom;
    }
    .action-btn {
        margin: 0 1;
    }
    .action-btn:disabled {
        opacity: 50%;
    }
    """

    DEFAULT_PLAY_PHASE_TIMEOUT = 30  # 出牌阶段默认超时秒数

    def __init__(self):
        super().__init__()
        # 线程间通信：使用 asyncio.Queue 与 UI 事件循环桥接
        self._action_queue: asyncio.Queue[str] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._game_thread: threading.Thread | None = None
        self._countdown_remaining: int = 0
        self._countdown_timer = None  # Timer handle
        from game.config import get_config

        self.play_phase_timeout: int = max(
            1, int(get_config().play_phase_timeout or self.DEFAULT_PLAY_PHASE_TIMEOUT)
        )

    def _log_ui_recoverable_error(
        self,
        context: str,
        exc: Exception,
        *,
        level: int = logging.WARNING,
    ) -> None:
        """记录可恢复的 UI 异常，避免无痕吞错."""
        logger.log(
            level,
            "GamePlayScreen %s failed: %s",
            context,
            exc,
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )

    def _run_modal_and_wait(
        self,
        modal_factory: Callable[[], object],
        *,
        timeout: float,
        description: str,
        before_push: Callable[[], None] | None = None,
        after_wait: Callable[[], None] | None = None,
    ):
        """在 worker 线程中统一调度 modal，并同步等待 dismiss 结果."""
        result_holder = [None]
        event = threading.Event()

        def _on_dismiss(result):
            result_holder[0] = result
            event.set()

        def _push():
            try:
                if before_push is not None:
                    before_push()
                modal = modal_factory()
                self.app.push_screen(modal, callback=_on_dismiss)
            except Exception as exc:
                self._log_ui_recoverable_error(f"schedule {description}", exc)
                event.set()

        try:
            self.app.call_from_thread(_push)
        except Exception as exc:
            self._log_ui_recoverable_error(f"dispatch {description}", exc)
            return None

        completed = event.wait(timeout=timeout)

        if after_wait is not None:
            try:
                self.app.call_from_thread(after_wait)
            except Exception as exc:
                self._log_ui_recoverable_error(
                    f"cleanup {description}",
                    exc,
                    level=logging.DEBUG,
                )

        if not completed:
            logger.warning("GamePlayScreen timed out waiting for %s", description)

        return result_holder[0]

    def _select_cards_from_candidates(
        self,
        cards: list,
        need_count: int,
        *,
        title: str,
        confirm_text: str = "✅ 确认选择",
        cancel_text: str | None = None,
        countdown: int = 30,
        timeout: float = 35.0,
        auto_select_on_timeout: bool = False,
        description: str = "card selection",
    ) -> list | None:
        """从候选牌中同步选择若干张，供 screen / bridge 复用."""
        if need_count <= 0:
            return []

        snapshot = list(cards)
        if not snapshot:
            return None

        required_count = min(need_count, len(snapshot))

        from ui.textual_ui.modals.discard_modal import DiscardModal

        indices = self._run_modal_and_wait(
            lambda: DiscardModal(
                cards=snapshot,
                need_count=required_count,
                countdown=countdown,
                title=title,
                confirm_text=confirm_text,
                cancel_text=cancel_text,
                timeout_auto_select=auto_select_on_timeout,
            ),
            timeout=timeout,
            description=description,
        )
        if indices is None or len(indices) != required_count:
            return None

        selected = [snapshot[i] for i in indices if 0 <= i < len(snapshot)]
        if len(selected) != required_count:
            return None
        return selected

    def _select_single_card_from_candidates(
        self,
        cards: list,
        *,
        title: str,
        confirm_text: str = "✅ 确认选择",
        cancel_text: str | None = "❌ 放弃",
        countdown: int = 30,
        timeout: float = 35.0,
        auto_select_on_timeout: bool = False,
        description: str = "single card selection",
    ):
        """从候选牌中同步选择 1 张."""
        selected = self._select_cards_from_candidates(
            cards,
            1,
            title=title,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
            countdown=countdown,
            timeout=timeout,
            auto_select_on_timeout=auto_select_on_timeout,
            description=description,
        )
        return selected[0] if selected else None

    @property
    def engine(self) -> GameEngine:
        return self.app._engine

    def compose(self) -> ComposeResult:
        from ui.textual_ui.widgets.equipment_slots import EquipmentSlots
        from ui.textual_ui.widgets.phase_indicator import PhaseIndicator
        from ui.textual_ui.widgets.play_area import PlayArea

        yield PhaseIndicator(id="phase-bar")
        yield VerticalScroll(id="opponents")
        yield PlayArea(id="play-area")
        yield RichLog(id="battle-log", highlight=True, markup=True, wrap=True)
        yield Static(_t("ui.play.info_panel"), id="info-panel")
        yield Container(
            EquipmentSlots(id="equip-section"),
            Static(_t("ui.play.hand_label"), id="hand-label"),
            Horizontal(id="hand-cards"),
            Horizontal(
                Button(
                    _t("ui.play.btn_play"), id="btn-play", classes="action-btn", variant="primary"
                ),
                Button(
                    _t("ui.play.btn_skill"), id="btn-skill", classes="action-btn", variant="warning"
                ),
                Button(
                    _t("ui.play.btn_end"), id="btn-end", classes="action-btn", variant="default"
                ),
                id="action-bar",
            ),
            id="player-area",
        )
        from textual.widgets import Footer

        yield Footer()

    def on_mount(self) -> None:
        """挂载后设置 UI 桥接，开始游戏循环."""
        engine = self.engine
        # 记录当前 Textual 事件循环并创建动作队列（仅在 UI 线程使用）
        self._loop = asyncio.get_running_loop()
        self._action_queue = asyncio.Queue()

        # 设置 TextualBridge 作为 UI
        from ui.textual_ui.bridge import TextualUIBridge

        bridge = TextualUIBridge(self)
        engine.set_ui(bridge)

        self._refresh_display()
        self._log(_t("ui.play.game_start"))

        # 显示玩家身份信息
        from game.player import Identity

        human = engine.human_player
        identity_name = human.identity.chinese_name
        self._log(
            _t(
                "ui.play.your_identity",
                name=human.name,
                hero=human.hero.name,
                identity=identity_name,
            )
        )

        # 非主公时弹出身份揭示窗口
        if human.identity != Identity.LORD:
            from ui.textual_ui.modals.identity_reveal_modal import IdentityRevealModal

            self.app.push_screen(IdentityRevealModal(human.identity.value, identity_name))

        # 在 worker 线程中运行游戏循环
        self._start_game_loop()

    @work(thread=True)
    def _start_game_loop(self) -> None:
        """在后台线程运行游戏主循环."""
        engine = self.engine
        while not engine.is_game_over():
            current = engine.current_player
            if current.is_ai:
                # Use asyncio.run for async call in thread
                asyncio.run(self._run_ai_turn(current))
            else:
                self._run_human_turn(current)

            if engine.is_game_over():
                break
            engine.next_turn()

        # 游戏结束
        winner = engine.winner_identity
        msg = f"胜利者: {winner.chinese_name}" if winner else "游戏结束"
        # 胜利判定：基于身份阵营匹配
        from game.player import Identity

        human_id = engine.human_player.identity if engine.human_player else None
        if winner and human_id:
            # 主公和忠臣同阵营
            if winner == Identity.LORD:
                is_victory = human_id in (Identity.LORD, Identity.LOYALIST)
            elif winner == Identity.REBEL:
                is_victory = human_id == Identity.REBEL
            elif winner == Identity.SPY:
                is_victory = human_id == Identity.SPY
            else:
                is_victory = False
        else:
            is_victory = False
        from .game_over import GameOverScreen

        self.app.call_from_thread(self.app.push_screen, GameOverScreen(msg, bool(is_victory)))

    async def _run_ai_turn(self, player: Player) -> None:
        """AI 回合."""
        engine = self.engine
        self._post_log(f"\n══ {player.name}({player.hero.name}) 的回合 ══")
        player.reset_turn()
        engine.phase_prepare(player)
        engine.phase_judge(player)
        self._post_refresh()
        engine.phase_draw(player)

        from game.engine import GamePhase

        engine.phase = GamePhase.PLAY
        if player.id in engine.ai_bots:
            engine.ai_bots[player.id].play_phase(player, engine)

        engine.phase_discard(player)
        engine.phase_end(player)
        self._post_refresh()
        from game.config import get_config

        cfg = get_config()
        if cfg.ai_turn_delay > 0:
            await asyncio.sleep(cfg.ai_turn_delay)

    def _run_human_turn(self, player: Player) -> None:
        """人类玩家回合."""
        engine = self.engine
        self._post_log("\n══ 你的回合 ══")
        player.reset_turn()

        engine.phase_prepare(player)
        self._post_refresh()
        engine.phase_judge(player)
        self._post_refresh()
        engine.phase_draw(player)
        self._post_refresh()

        from game.engine import GamePhase

        engine.phase = GamePhase.PLAY
        self._post_log("▶ 出牌阶段 — 点击手牌出牌，或按 E 结束")
        self._post_refresh()

        # 等待玩家操作
        self._human_play_loop(player)

        # 弃牌阶段：检查是否需要弃牌
        engine.phase = GamePhase.DISCARD
        self._post_refresh()
        discard_count = player.need_discard
        if discard_count > 0:
            self._post_log(f"▶ 弃牌阶段 — 需弃置 {discard_count} 张牌")
            self._human_discard(player, discard_count)
        engine.phase_end(player)
        self._post_refresh()

    def _human_play_loop(self, player: Player) -> None:
        """人类出牌阶段循环（在 worker 线程中）."""
        while True:
            self._post_refresh()
            # 等待玩家行动
            action = self._wait_for_response("play_action")
            if action == "end":
                break
            elif action and action.startswith("card:"):
                idx = int(action.split(":")[1])
                if 0 <= idx < len(player.hand):
                    card = player.hand[idx]
                    self._handle_card_play(player, card)
            elif action and action.startswith("skill:"):
                skill_id = action.split(":")[1]
                self._handle_skill_use(player, skill_id)

            if self.engine.is_game_over():
                return

    def _human_discard(self, player: Player, count: int) -> None:
        """人类玩家弃牌交互（worker 线程阻塞，通过 call_from_thread 调度 UI modal）."""
        cards_to_discard = self._select_cards_from_candidates(
            list(player.hand),
            count,
            title=f"🗑 弃牌阶段 — 请选择 {count} 张牌弃掉",
            confirm_text="✅ 确认弃牌",
            countdown=30,
            timeout=35.0,
            auto_select_on_timeout=True,
            description="discard selection",
        )

        if cards_to_discard and len(cards_to_discard) == count:
            self.engine.discard_cards(player, cards_to_discard)
        elif player.need_discard > 0:
            auto_discard = player.hand[-player.need_discard :]
            self.engine.discard_cards(player, list(auto_discard))

    def _handle_card_play(self, player: Player, card) -> None:
        """处理出牌."""
        from game.card import CardName, CardSubtype, CardType

        engine = self.engine

        if card.card_type == CardType.EQUIPMENT:
            engine.use_card(player, card)
        elif card.name == CardName.SHA:
            if not player.can_use_sha():
                from game.constants import SkillId

                if not player.has_skill(SkillId.PAOXIAO):
                    self._post_log("⚠ 本回合已使用过杀")
                    return
            targets = engine.get_targets_in_range(player)
            if not targets:
                self._post_log("⚠ 没有可攻击的目标")
                return
            target = self._wait_for_target(player, targets, "选择杀的目标")
            if target:
                engine.use_card(player, card, [target])
        elif card.name == CardName.TAO:
            if player.hp >= player.max_hp:
                self._post_log("⚠ 体力已满")
                return
            engine.use_card(player, card)
        elif card.name == CardName.SHAN:
            self._post_log("⚠ 闪不能主动使用")
            return
        elif card.name == CardName.WUXIE:
            self._post_log("⚠ 无懈可击不能主动使用")
            return
        elif card.name == CardName.JUEDOU:
            others = engine.get_other_players(player)
            target = self._wait_for_target(player, others, "选择决斗目标")
            if target:
                engine.use_card(player, card, [target])
        elif card.name in [CardName.GUOHE, CardName.SHUNSHOU]:
            others = engine.get_other_players(player)
            valid = [t for t in others if t.has_any_card()]
            if card.name == CardName.SHUNSHOU:
                valid = [t for t in valid if engine.calculate_distance(player, t) <= 1]
            if not valid:
                self._post_log("⚠ 没有有效目标")
                return
            target = self._wait_for_target(player, valid, f"选择{card.name}目标")
            if target:
                engine.use_card(player, card, [target])
        elif card.name == CardName.LEBUSISHU:
            # 乐不思蜀: 选择一个非自己的目标（无距离限制）
            others = engine.get_other_players(player)
            # 排除已有乐不思蜀的目标
            valid = [
                t for t in others if not any(c.name == CardName.LEBUSISHU for c in t.judge_area)
            ]
            if not valid:
                self._post_log("⚠ 没有有效目标")
                return
            target = self._wait_for_target(player, valid, "选择乐不思蜀目标")
            if target:
                engine.use_card(player, card, [target])
        elif card.name == CardName.BINGLIANG:
            # 兵粮寸断: 选择距离≤1的非自己目标
            others = engine.get_other_players(player)
            valid = [
                t
                for t in others
                if engine.calculate_distance(player, t) <= 1
                and not any(c.name == CardName.BINGLIANG for c in t.judge_area)
            ]
            if not valid:
                self._post_log("⚠ 没有有效目标（需距离≤1）")
                return
            target = self._wait_for_target(player, valid, "选择兵粮寸断目标")
            if target:
                engine.use_card(player, card, [target])
        elif card.name == CardName.HUOGONG:
            # 火攻: 选择一个有手牌的目标（可选自己）
            alive = [p for p in engine.players if p.is_alive and p.hand_count > 0]
            if not alive:
                self._post_log("⚠ 没有有手牌的目标")
                return
            target = self._wait_for_target(player, alive, "选择火攻目标")
            if target:
                engine.use_card(player, card, [target])
        elif card.name == CardName.JIEDAO:
            # 借刀杀人: 先选有武器的其他玩家(wielder)，再选 wielder 攻击范围内的目标
            others = engine.get_other_players(player)
            with_weapon = [t for t in others if t.equipment.weapon and t.is_alive]
            if not with_weapon:
                self._post_log("⚠ 没有装备武器的目标")
                return
            wielder = self._wait_for_target(player, with_weapon, "选择持武器者（被借刀的人）")
            if not wielder:
                return
            # 找 wielder 攻击范围内的目标（不含 wielder 自身和 player）
            sha_targets = [
                t
                for t in engine.players
                if t.is_alive
                and t != wielder
                and t != player
                and engine.is_in_attack_range(wielder, t)
            ]
            if not sha_targets:
                self._post_log(f"⚠ {wielder.name} 攻击范围内没有有效目标")
                return
            sha_target = self._wait_for_target(player, sha_targets, f"选择 {wielder.name} 杀的目标")
            if sha_target:
                engine.use_card(player, card, [wielder, sha_target])
        elif card.name == CardName.TIESUO:
            # 铁索连环: 选择0-2个目标（0=重铸）
            others = [p for p in engine.players if p.is_alive]
            targets = self._wait_for_multi_targets(
                player, others, "铁索连环 — 选择0-2个目标（0个=重铸）", min_count=0, max_count=2
            )
            if targets is None:
                return  # 取消
            engine.use_card(player, card, targets)
        elif card.subtype == CardSubtype.ALCOHOL:
            # 酒: 检查本回合是否已使用
            if player.alcohol_used:
                self._post_log("⚠ 本回合已使用过酒")
                return
            engine.use_card(player, card)
        else:
            # 群体锦囊(南蛮/万箭/桃园/闪电)/其他
            engine.use_card(player, card)

    def _handle_skill_use(self, player: Player, skill_id: str) -> None:
        """处理技能使用."""
        engine = self.engine
        if engine.skill_system:
            engine.skill_system.use_skill(skill_id, player)

    # ==================== 线程间通信 ====================

    def _wait_for_response(self, request_type: str) -> str | None:
        """等待 UI 线程的响应（worker 线程阻塞等待 UI 事件循环中的 asyncio.Queue）."""
        assert self._loop is not None and self._action_queue is not None
        # 在 UI 线程启动等待状态（倒计时等）
        self.app.call_from_thread(self._set_waiting, request_type)
        timeout = float(max(1, self.play_phase_timeout))

        async def _await_action(timeout: float) -> str | None:
            try:
                return await asyncio.wait_for(self._action_queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                return "end"  # 超时自动结束出牌

        fut = asyncio.run_coroutine_threadsafe(_await_action(timeout), self._loop)
        try:
            return fut.result(timeout=timeout + 5.0)
        except FutureTimeoutError:
            fut.cancel()
            return "end"

    def _wait_for_target(self, player, targets, prompt: str) -> Player | None:
        """等待目标选择（worker 线程阻塞，通过 call_from_thread 调度 UI modal）."""
        from ui.textual_ui.modals.target_modal import TargetSelectModal
        idx = self._run_modal_and_wait(
            lambda: TargetSelectModal(targets=targets, prompt=prompt),
            timeout=65.0,
            description="target selection",
            before_push=lambda: self._highlight_targets(targets),
            after_wait=self._clear_target_highlights,
        )
        if idx is not None and 0 <= idx < len(targets):
            return targets[idx]
        return None

    def _wait_for_multi_targets(
        self, player, targets, prompt: str, min_count: int = 0, max_count: int = 2
    ) -> list[Player] | None:
        """等待多目标选择（worker 线程阻塞）。返回 Player 列表或 None(取消)."""
        from ui.textual_ui.modals.multi_target_modal import MultiTargetModal
        indices = self._run_modal_and_wait(
            lambda: MultiTargetModal(
                targets=targets, prompt=prompt, min_count=min_count, max_count=max_count
            ),
            timeout=65.0,
            description="multi-target selection",
            before_push=lambda: self._highlight_targets(targets),
            after_wait=self._clear_target_highlights,
        )
        if indices is None:
            return None  # 用户取消
        return [targets[i] for i in indices if 0 <= i < len(targets)]

    def _highlight_targets(self, targets: list) -> None:
        """为合法目标的 PlayerPanel 添加 .targetable 高亮 + 呼吸脉冲 (P1-3)."""
        try:
            from ui.textual_ui.widgets.player_panel import PlayerPanel

            opp_container = self.query_one("#opponents", VerticalScroll)
            target_ids = {id(t) for t in targets}
            for panel in opp_container.query(PlayerPanel):
                if id(panel._player) in target_ids:
                    panel.add_class("targetable")
                    panel.start_pulse()
                else:
                    panel.remove_class("targetable")
                    panel.stop_pulse()
        except Exception as exc:
            self._log_ui_recoverable_error(
                "highlight targets",
                exc,
                level=logging.DEBUG,
            )

    def _clear_target_highlights(self) -> None:
        """移除所有 PlayerPanel 的 .targetable 高亮 + 停止脉冲 (P1-3)."""
        try:
            from ui.textual_ui.widgets.player_panel import PlayerPanel

            opp_container = self.query_one("#opponents", VerticalScroll)
            for panel in opp_container.query(PlayerPanel):
                panel.remove_class("targetable")
                panel.stop_pulse()
        except Exception as exc:
            self._log_ui_recoverable_error(
                "clear target highlights",
                exc,
                level=logging.DEBUG,
            )

    def _set_waiting(self, request_type: str) -> None:
        """标记等待状态，启动倒计时."""
        if request_type == "play_action":
            self._refresh_display()
            # P3-1: 回合开始脉冲特效
            self._turn_start_pulse()
            # 启动倒计时
            self._countdown_remaining = self.play_phase_timeout
            self._update_countdown_display()
            self._start_countdown()

    def _turn_start_pulse(self) -> None:
        """回合开始特效: 对 info-panel 执行快速 opacity 脉冲 (P3-1)."""
        try:
            info_panel = self.query_one("#info-panel", Static)
            info_panel.add_class("active-turn-glow")
            info_panel.styles.animate(
                "opacity",
                value=0.5,
                duration=0.15,
                easing="out_cubic",
                on_complete=lambda: info_panel.styles.animate(
                    "opacity",
                    value=1.0,
                    duration=0.25,
                    easing="in_out_cubic",
                    on_complete=lambda: info_panel.remove_class("active-turn-glow"),
                ),
            )
        except Exception as exc:
            self._log_ui_recoverable_error(
                "animate turn start pulse",
                exc,
                level=logging.DEBUG,
            )

    def _start_countdown(self) -> None:
        """启动每秒倒计时."""
        if self._countdown_remaining <= 0:
            # 超时：自动结束出牌
            self._respond("end")
            return
        self._countdown_timer = self.set_timer(1.0, self._tick_countdown)

    def _tick_countdown(self) -> None:
        """每秒倒计时回调."""
        self._countdown_remaining -= 1
        if self._countdown_remaining <= 0:
            self._respond("end")
            return
        self._update_countdown_display()
        self._countdown_timer = self.set_timer(1.0, self._tick_countdown)

    @staticmethod
    def _countdown_color(secs: int, total: int = 30) -> str:
        """根据剩余秒数计算 RGB 渐变色 (P2-2).

        green(#27ae60) → yellow(#f39c12) → red(#e74c3c)
        ratio > 0.5 时 green→yellow，ratio <= 0.5 时 yellow→red
        """
        ratio = max(0.0, min(1.0, secs / total))
        if ratio > 0.5:
            # green → yellow (ratio 1.0→0.5 maps to factor 0→1)
            f = (1.0 - ratio) * 2  # 0→1
            r = int(0x27 + (0xF3 - 0x27) * f)
            g = int(0xAE + (0x9C - 0xAE) * f)
            b = int(0x60 + (0x12 - 0x60) * f)
        else:
            # yellow → red (ratio 0.5→0 maps to factor 0→1)
            f = (0.5 - ratio) * 2  # 0→1
            r = int(0xF3 + (0xE7 - 0xF3) * f)
            g = int(0x9C + (0x4C - 0x9C) * f)
            b = int(0x12 + (0x3C - 0x12) * f)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _update_countdown_display(self) -> None:
        """更新信息面板的倒计时显示 — P2-2: RGB 渐变色."""
        try:
            info = self.query_one("#info-panel", Static)
            current = info.renderable
            secs = self._countdown_remaining
            color = self._countdown_color(secs, self.play_phase_timeout)
            info.update(
                f"{current}\n\n[bold green]▶ 你的回合[/bold green]\n"
                f"点击手牌出牌 / 按 E 结束\n"
                f"[bold {color}]⏱ 剩余 {secs} 秒[/bold {color}]"
            )
        except Exception as exc:
            self._log_ui_recoverable_error(
                "update countdown display",
                exc,
                level=logging.DEBUG,
            )

    def _cancel_countdown(self) -> None:
        """取消倒计时."""
        self._countdown_remaining = 0
        if self._countdown_timer is not None:
            self._countdown_timer.stop()
            self._countdown_timer = None

    def _respond(self, response: str) -> None:
        """发送响应给 worker 线程，并取消倒计时（通过 asyncio.Queue）."""
        self._cancel_countdown()
        if self._action_queue is not None:
            # UI 线程直接 put_nowait 是安全的
            self._action_queue.put_nowait(response)

    # ==================== UI 更新 ====================

    def _post_log(self, msg: str) -> None:
        """线程安全的日志写入."""
        self.app.call_from_thread(self._log, msg)

    def _post_refresh(self) -> None:
        """线程安全的界面刷新."""
        self.app.call_from_thread(self._refresh_display)

    def _log(self, msg: str) -> None:
        """写入战斗日志，根据内容添加视觉效果 + PlayArea 中央展示."""
        try:
            log_widget = self.query_one("#battle-log", RichLog)
            if "伤害" in msg or "受到" in msg or "损失" in msg:
                msg = f"[bold red]⚡ {msg}[/bold red]"
                self._flash_by_name(msg, "flash-damage", 0.6)
                self._update_play_area_damage(msg)
            elif "回复" in msg or "治疗" in msg or "桃】" in msg:
                msg = f"[bold green]❤ {msg}[/bold green]"
                self._flash_by_name(msg, "flash-heal", 0.5)
            elif "发动【" in msg:
                msg = f"[bold yellow]✨ {msg}[/bold yellow]"
                self._flash_by_name(msg, "flash-skill", 0.4)
                self._skill_toast(msg)
                self._update_play_area_skill(msg)
            elif "使用了【" in msg or "使用【" in msg:
                self._update_play_area_card(msg)
            elif "死亡" in msg or "阵亡" in msg or "杀死" in msg:
                msg = f"[bold red on black]💀 {msg}[/bold red on black]"
                self._flash_by_name(msg, "flash-damage", 1.0)
                self._trigger_death_shake(msg)
            elif "你的回合" in msg:
                msg = f"[bold cyan]🎮 {msg}[/bold cyan]"
            log_widget.write(msg)
            log_widget.scroll_end(animate=True)
        except Exception as exc:
            self._log_ui_recoverable_error("write battle log", exc)

    def _update_play_area_card(self, msg: str) -> None:
        """更新中央出牌区显示."""
        try:
            import re

            from ui.textual_ui.widgets.play_area import PlayArea

            play_area = self.query_one("#play-area", PlayArea)
            # 解析 "玩家 对 目标 使用了【卡牌】" 或 "玩家 使用了【卡牌】"
            m = re.search(r"(.+?)\s+(?:对\s+(.+?)\s+)?使用[了]*【(.+?)】", msg)
            if m:
                player_name = m.group(1).strip()
                target_name = m.group(2).strip() if m.group(2) else ""
                card_name = m.group(3).strip()
                play_area.show_card_play(player_name, card_name, target_name)
        except Exception as exc:
            self._log_ui_recoverable_error(
                "update play area for card",
                exc,
                level=logging.DEBUG,
            )

    def _update_play_area_skill(self, msg: str) -> None:
        """更新中央出牌区显示技能."""
        try:
            import re

            from ui.textual_ui.widgets.play_area import PlayArea

            play_area = self.query_one("#play-area", PlayArea)
            m = re.search(r"(.+?)\s+发动【(.+?)】", msg)
            if m:
                player_name = m.group(1).strip()
                skill_name = m.group(2).strip()
                play_area.show_skill_use(player_name, skill_name)
        except Exception as exc:
            self._log_ui_recoverable_error(
                "update play area for skill",
                exc,
                level=logging.DEBUG,
            )

    def _update_play_area_damage(self, msg: str) -> None:
        """更新中央出牌区显示伤害."""
        try:
            import re

            from ui.textual_ui.widgets.play_area import PlayArea

            play_area = self.query_one("#play-area", PlayArea)
            m = re.search(r"(.+?)\s+受到[了]*\s*(\d+)\s*点", msg)
            if m:
                target_name = m.group(1).strip()
                amount = int(m.group(2))
                dtype = ""
                if "火焰" in msg:
                    dtype = "fire"
                elif "雷电" in msg:
                    dtype = "thunder"
                play_area.show_damage(target_name, amount, dtype)
        except Exception as exc:
            self._log_ui_recoverable_error(
                "update play area for damage",
                exc,
                level=logging.DEBUG,
            )

    def _flash_by_name(self, msg: str, css_class: str, duration: float) -> None:
        """从 log 消息中解析角色名，精准闪烁对应 PlayerPanel (P0-4)."""
        target_widget_id = "#battle-log"
        try:
            from ui.textual_ui.widgets.player_panel import PlayerPanel

            opp_container = self.query_one("#opponents", VerticalScroll)
            for panel in opp_container.query(PlayerPanel):
                if panel._player and panel._player.name in msg:
                    self.flash_effect(
                        css_class, f"#{panel.id}" if panel.id else "#battle-log", duration
                    )
                    return
        except Exception as exc:
            self._log_ui_recoverable_error(
                "resolve flash target",
                exc,
                level=logging.DEBUG,
            )
        self.flash_effect(css_class, target_widget_id, duration)

    def _refresh_display(self) -> None:
        """刷新界面显示."""
        engine = self.engine
        if not engine or not engine.human_player:
            return

        human = engine.human_player

        # 更新阶段指示器 + 额外信息
        try:
            from ui.textual_ui.widgets.phase_indicator import PhaseIndicator

            phase_bar = self.query_one("#phase-bar", PhaseIndicator)
            phase_bar.set_phase(engine.phase.value)
            current_name = engine.current_player.name if engine.current_player else ""
            deck_remaining = engine.deck.remaining
            discard_pile = engine.deck.discarded
            phase_bar.set_info(
                round_count=engine.round_count,
                deck_count=deck_remaining,
                discard_count=discard_pile,
                player_name=current_name,
            )
        except Exception as exc:
            self._log_ui_recoverable_error(
                "refresh phase bar",
                exc,
                level=logging.DEBUG,
            )

        # 更新对手面板——显示所有其他玩家（含已死亡）
        try:
            from ui.textual_ui.widgets.player_panel import PlayerPanel

            opp_container = self.query_one("#opponents", VerticalScroll)
            all_others = engine.get_all_other_players(human)
            existing = list(opp_container.query(PlayerPanel))
            if len(existing) != len(all_others):
                with self.app.batch_update():
                    opp_container.remove_children()
                    for i, p in enumerate(all_others):
                        panel = PlayerPanel(p, index=i, id=f"opp-{i}")
                        if not p.is_alive:
                            panel.add_class("dead")
                        if p == engine.current_player:
                            panel.add_class("active-turn")
                        opp_container.mount(panel)
            else:
                for panel, p in zip(existing, all_others, strict=False):
                    dist = engine.calculate_distance(human, p) if p.is_alive else -1
                    in_rng = engine.is_in_attack_range(human, p) if p.is_alive else False
                    panel.update_player(p, distance=dist, in_range=in_rng)
                    if p == engine.current_player:
                        panel.add_class("active-turn")
                    else:
                        panel.remove_class("active-turn")
        except Exception as exc:
            self._log_ui_recoverable_error(
                "refresh opponent panels",
                exc,
                level=logging.DEBUG,
            )

        # 更新手牌区——CardWidget + batch_update 防闪烁 + P0-3: .playable 提示
        try:
            from ui.textual_ui.widgets.card_widget import CardWidget

            hand_container = self.query_one("#hand-cards", Horizontal)
            is_player_turn = engine.current_player == human
            can_sha = human.can_use_sha() if hasattr(human, "can_use_sha") else True
            has_targets = bool(engine.get_targets_in_range(human)) if is_player_turn else False
            with self.app.batch_update():
                hand_container.remove_children()
                for i, card in enumerate(human.hand):
                    widget = CardWidget(card, index=i)
                    if is_player_turn and self._is_card_playable(card, human, can_sha, has_targets):
                        widget.add_class("playable")
                    hand_container.mount(widget)
        except Exception as exc:
            self._log_ui_recoverable_error(
                "refresh hand cards",
                exc,
                level=logging.DEBUG,
            )

        # 更新装备槽
        try:
            from ui.textual_ui.widgets.equipment_slots import EquipmentSlots

            equip_widget = self.query_one("#equip-section", EquipmentSlots)
            equip_widget.update_player(human)
        except Exception as exc:
            self._log_ui_recoverable_error(
                "refresh equipment slots",
                exc,
                level=logging.DEBUG,
            )

        # 更新信息面板
        try:
            hp_bar = "●" * human.hp + "○" * (human.max_hp - human.hp)
            hp_full = "●" * human.hp
            hp_empty = "[dim]○[/dim]" * (human.max_hp - human.hp)
            if human.hp <= 1:
                hp_bar = f"[red]{hp_full}[/red]" + hp_empty
            elif human.hp <= human.max_hp // 2:
                hp_bar = f"[yellow]{hp_full}[/yellow]" + hp_empty
            else:
                hp_bar = f"[green]{hp_full}[/green]" + hp_empty
            skills_lines = ""
            if human.hero:
                for s in human.hero.skills:
                    tag = ""
                    if s.is_compulsory:
                        tag = "[dim]锁定技[/dim] "
                    elif s.is_lord_skill:
                        tag = "[dim]主公技[/dim] "
                    skills_lines += f"  [bold yellow]【{s.name}】[/bold yellow]{tag}\n"
                    skills_lines += f"    [dim]{s.description}[/dim]\n"
            # 显示身份和对应胜利条件
            identity_color = human.identity.color
            identity_name = human.identity.chinese_name
            from game.win_checker import get_identity_win_condition

            win_cond = get_identity_win_condition(human.identity.value)
            info_text = (
                f"[bold]{human.name}[/bold] {human.hero.name if human.hero else ''}\n"
                f"体力: {hp_bar} {human.hp}/{human.max_hp}\n"
                f"身份: [{identity_color}]{identity_name}[/{identity_color}]\n"
                f"目标: {win_cond}\n"
                f"─── 技能 ───\n"
                f"{skills_lines.rstrip()}"
            )
            self.query_one("#info-panel", Static).update(info_text)
        except Exception as exc:
            self._log_ui_recoverable_error(
                "refresh info panel",
                exc,
                level=logging.DEBUG,
            )

    def _is_card_playable(self, card, player, can_sha: bool, has_targets: bool) -> bool:
        """判断卡牌是否可在出牌阶段主动使用 (P0-3b)."""
        try:
            from game.card import CardName

            name = card.name if hasattr(card, "name") else None
            if name == CardName.SHAN:
                return False
            if name == CardName.WUXIE:
                return False
            if name == CardName.SHA:
                return can_sha and has_targets
            if name == CardName.TAO:
                return player.hp < player.max_hp
            if name == CardName.JIU:
                return not getattr(player, "drunk", False)
            return True
        except Exception as exc:
            self._log_ui_recoverable_error(
                "compute playable card hint",
                exc,
                level=logging.DEBUG,
            )
            return True

    # ==================== M3-T04: 视觉反馈 (animate API) ====================

    def flash_effect(
        self, css_class: str, widget_id: str = "#battle-log", duration: float = 0.5
    ) -> None:
        """对指定 widget 施加两段式 opacity 脉冲闪烁 (P0-1).

        使用 Textual 原生 animate() API:
        阶段1: opacity 1.0→0.3 (快速变暗, out_cubic)
        阶段2: opacity 0.3→1.0 (缓慢恢复, in_out_cubic)
        CSS class 在整个过程中保持，动画结束后移除。
        """
        try:
            widget = self.query_one(widget_id)
            widget.add_class(css_class)
            widget.styles.animate(
                "opacity",
                value=0.3,
                duration=duration * 0.4,
                easing="out_cubic",
                on_complete=lambda: self._flash_restore(widget, css_class, duration * 0.6),
            )
        except Exception as exc:
            self._log_ui_recoverable_error(
                "apply flash effect",
                exc,
                level=logging.DEBUG,
            )

    def _flash_restore(self, widget, css_class: str, duration: float) -> None:
        """闪烁第二阶段: 恢复 opacity 并移除 CSS class."""
        try:
            widget.styles.animate(
                "opacity",
                value=1.0,
                duration=duration,
                easing="in_out_cubic",
                on_complete=lambda: widget.remove_class(css_class),
            )
        except Exception as exc:
            self._log_ui_recoverable_error(
                "restore flash effect",
                exc,
                level=logging.DEBUG,
            )
            widget.remove_class(css_class)

    def _post_flash(
        self, css_class: str, widget_id: str = "#battle-log", duration: float = 0.5
    ) -> None:
        """线程安全的闪烁效果 — 确保在 UI 线程执行 animate() (P0-5)."""
        self.app.call_from_thread(self.flash_effect, css_class, widget_id, duration)

    def _skill_toast(self, msg: str) -> None:
        """P3-2: 技能发动时显示 toast 浮动通知."""
        try:
            import re

            m = re.search(r"发动【(.+?)】", msg)
            if m:
                skill_name = m.group(1)
                self.notify(
                    f"✨ 【{skill_name}】发动！",
                    title="技能",
                    severity="information",
                    timeout=2,
                )
        except Exception as exc:
            self._log_ui_recoverable_error(
                "show skill toast",
                exc,
                level=logging.DEBUG,
            )

    def _trigger_death_shake(self, msg: str) -> None:
        """P2-4: 检测死亡消息并触发对应面板震动."""
        try:
            from ui.textual_ui.widgets.player_panel import PlayerPanel

            opp_container = self.query_one("#opponents", VerticalScroll)
            for panel in opp_container.query(PlayerPanel):
                if panel._player and panel._player.name in msg:
                    panel.death_shake()
                    return
        except Exception as exc:
            self._log_ui_recoverable_error(
                "trigger death shake",
                exc,
                level=logging.DEBUG,
            )

    # ==================== 事件处理 ====================

    def on_card_widget_card_clicked(self, event) -> None:
        """处理 CardWidget 点击事件 — P2-3: 卡牌打出渐隐动画."""
        try:
            from ui.textual_ui.widgets.card_widget import CardWidget

            hand_container = self.query_one("#hand-cards", Horizontal)
            widgets = list(hand_container.query(CardWidget))
            if 0 <= event.index < len(widgets):
                clicked = widgets[event.index]
                clicked.add_class("card-played")
                clicked.styles.animate(
                    "opacity",
                    value=0.0,
                    duration=0.15,
                    easing="out_cubic",
                    on_complete=lambda: self._respond(f"card:{event.index}"),
                )
                return
        except Exception as exc:
            self._log_ui_recoverable_error(
                "animate clicked card",
                exc,
                level=logging.DEBUG,
            )
        self._respond(f"card:{event.index}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("hcard-"):
            idx = int(btn_id.split("-")[1])
            self._respond(f"card:{idx}")
        elif btn_id == "btn-end":
            self._respond("end")
        elif btn_id == "btn-play":
            pass  # 手牌直接点击
        elif btn_id == "btn-skill":
            self._handle_skill_button()
        elif btn_id.startswith("target-"):
            idx = int(btn_id.split("-")[1])
            self._respond(f"target:{idx}")

    def _handle_skill_button(self) -> None:
        """技能按钮."""
        engine = self.engine
        human = engine.human_player
        if engine.skill_system and human:
            usable = engine.skill_system.get_usable_skills(human)
            if usable:
                self._respond(f"skill:{usable[0]}")
            else:
                self._log("⚠ 当前无可用技能")

    def action_end_play(self) -> None:
        self._respond("end")

    def _action_play_card_by_index(self, idx: int) -> None:
        """通过数字键快速出牌."""
        self._respond(f"card:{idx}")

    def action_play_card_1(self) -> None:
        self._action_play_card_by_index(0)

    def action_play_card_2(self) -> None:
        self._action_play_card_by_index(1)

    def action_play_card_3(self) -> None:
        self._action_play_card_by_index(2)

    def action_play_card_4(self) -> None:
        self._action_play_card_by_index(3)

    def action_play_card_5(self) -> None:
        self._action_play_card_by_index(4)

    def action_play_card_6(self) -> None:
        self._action_play_card_by_index(5)

    def action_play_card_7(self) -> None:
        self._action_play_card_by_index(6)

    def action_play_card_8(self) -> None:
        self._action_play_card_by_index(7)

    def action_play_card_9(self) -> None:
        self._action_play_card_by_index(8)

    def action_play_card_10(self) -> None:
        self._action_play_card_by_index(9)

    def action_show_help(self) -> None:
        from .rules import RulesScreen

        self.app.push_screen(RulesScreen())

    def action_quit_game(self) -> None:
        self._respond("end")
        self.app.exit()
