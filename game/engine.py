"""游戏引擎模块 — Facade / 组合协调器.

GameEngine 作为统一入口，组合并协调以下子系统：
  - TurnManager      : 回合阶段流转 (准备/判定/摸牌/出牌/弃牌/结束)
  - CombatSystem      : 杀/闪/决斗/无懈可击
  - EquipmentSystem   : 装备穿戴/移除/护甲效果
  - JudgeSystem        : 延时锦囊判定
  - CardResolver       : 卡牌效果解析 (锦囊/基本牌)
  - CardEffectRegistry : 卡牌效果注册表
  - RequestHandler     : 统一 AI/UI 输入路由
  - SkillSystem        : 技能触发 (外部注入)
  - EventBus           : 事件发布订阅

Engine 本身保留的职责：
  - 游戏状态管理 (玩家、轮次、胜负)
  - 伤害/濒死/死亡系统 (跨子系统协调)
  - 卡牌使用路由 (use_card)
  - AI 决策协调
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

from .card import Card, CardName, CardSubtype, CardType, Deck  # noqa: E402
from .constants import IdentityConfig, SkillId  # noqa: E402
from .events import EventBus, EventType, GameEvent  # noqa: E402
from .hero import HeroRepository, Kingdom  # noqa: E402
from .player import Identity, Player  # noqa: E402

if TYPE_CHECKING:
    from ai.bot import AIBot
    from ui.protocol import GameUI

    from .actions import GameAction
    from .skill import SkillSystem


# M1-T04: 日志分类 → 语义化事件类型映射
_LOG_CATEGORY_MAP: dict[str, EventType] = {
    "game_setup": EventType.GAME_START,
    "game_start": EventType.GAME_START,
    "game_over": EventType.GAME_END,
    "hero_chosen": EventType.STATE_CHANGED,
    "phase": EventType.STATE_CHANGED,
    "turn_start": EventType.TURN_START,
    "turn_end": EventType.TURN_END,
    "draw_cards": EventType.CARD_DRAWN,
    "play": EventType.CARD_USED,
    "discard": EventType.CARD_DISCARDED,
    "judge": EventType.JUDGE_START,
    "effect": EventType.CARD_EFFECT,
    "damage": EventType.DAMAGE_INFLICTED,
    "dying": EventType.DYING,
    "death": EventType.DEATH,
    "save": EventType.HP_RECOVERED,
    "heal": EventType.HP_RECOVERED,
    "skill": EventType.SKILL_TRIGGERED,
    "equipment": EventType.EQUIPMENT_EQUIPPED,
    "equip": EventType.EQUIPMENT_EQUIPPED,
    "chain": EventType.DAMAGE_INFLICTED,
    "reward": EventType.STATE_CHANGED,
    "penalty": EventType.STATE_CHANGED,
}


# 枚举已提取到 enums.py，此处 re-export 保持向后兼容
# P2-4: 距离缓存
from .distance_cache import DistanceCache  # noqa: E402
from .enums import GamePhase, GameState  # noqa: E402,F401  — 公共 API re-export

# P0-4: 玩家管理器 (引擎分解 Step 1)
from .player_manager import PlayerManager  # noqa: E402

# M1-T01: 导入 TurnManager（GamePhase 已在上方定义，不会循环导入）
from .turn_manager import TurnManager  # noqa: E402
from .engine_event_logging import (
    log_event as _engine_log_event,
    notify_cards_lost as _engine_notify_cards_lost,
    notify_cards_obtained as _engine_notify_cards_obtained,
)
from .engine_setup_helpers import (
    assign_identities as _engine_assign_identities,
    ensure_can_start_game as _engine_ensure_can_start_game,
    setup_game as _engine_setup_game,
)


@dataclass(slots=True)
class GameLogEntry:
    """游戏日志条目类
    用于记录游戏日志（避免与 events.py 中的 GameEvent 冲突）.
    """

    event_type: str
    message: str
    source: Player | None = None
    target: Player | None = None
    card: Card | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class GameEngine:
    """游戏引擎 — Facade / 组合协调器.

    作为所有子系统的统一入口，通过委托模式将具体逻辑分发到各子系统。
    外部调用方（game_controller / game_play / tests）只需通过
    GameEngine 的公共 API 与游戏交互。
    """

    def __init__(self, data_dir: str = "data"):
        """初始化游戏引擎.

        Args:
            data_dir: 数据文件目录路径
        """
        # 获取正确的数据目录路径
        base_path = Path(__file__).parent.parent / data_dir

        # 事件总线（核心解耦组件）
        self.event_bus: EventBus = EventBus()
        # 日志事件语义映射（供外部辅助模块复用）
        self._log_category_map = _LOG_CATEGORY_MAP

        # 核心组件
        self.deck: Deck = Deck(str(base_path / "cards.json"))
        self.hero_repo: HeroRepository = HeroRepository(str(base_path / "heroes.json"))

        # P0-4: 玩家管理 — 委托给 PlayerManager
        self._player_mgr: PlayerManager = PlayerManager()
        # 向后兼容: 直接属性访问委托到 PlayerManager
        self.players = self._player_mgr.players  # type: ignore[assignment]
        self.human_player: Player | None = None

        # 游戏状态
        self.state: GameState = GameState.NOT_STARTED
        self.phase: GamePhase = GamePhase.PREPARE
        self.round_count: int = 0
        self.winner_identity: Identity | None = None

        # 事件日志（保留兼容）
        self.event_log: list[GameLogEntry] = []
        self.max_log_size: int = 100

        # UI和AI回调
        self.ui: GameUI | None = None
        self.ai_bots: dict[int, AIBot] = {}

        # 技能系统引用
        self.skill_system: SkillSystem | None = None

        # P2-4: 距离缓存 (事件驱动失效)
        self._distance_cache = DistanceCache()
        self._distance_cache.register_events(self.event_bus)

        # 回合管理器（M1-T01: 回合逻辑委托）
        self.turn_manager: TurnManager = TurnManager(self)

        # M1-T02: 卡牌效果注册表（新架构）
        from .effects.registry import create_default_registry

        self.effect_registry = create_default_registry()

        # M1-T03: 请求处理器（统一 AI/UI 输入路由）
        from .request_handler import DefaultRequestHandler

        self.request_handler = DefaultRequestHandler(self)

        # Phase 2.2: 战斗子系统（杀/闪/决斗/无懈可击）
        from .combat import CombatSystem

        self.combat = CombatSystem(self)

        # Phase 2.3: 装备子系统（装备穿戴/移除/护甲效果）
        from .equipment_system import EquipmentSystem

        self.equipment_sys = EquipmentSystem(self)

        # Phase 2.4: 判定子系统（延时锯囊判定）
        from .judge_system import JudgeSystem

        self.judge_sys = JudgeSystem(self)

        # Phase 2.5: 卡牌效果解析器（锯囊/基本牌效果）
        from .card_resolver import CardResolver

        self.card_resolver = CardResolver(self)

    def set_ui(self, ui: GameUI) -> None:
        """设置UI组件并通过EventBus订阅日志消息."""
        self.ui = ui
        # M1-T04: UI 通过 EventBus 订阅，不再由引擎直接 push
        self.event_bus.subscribe(EventType.LOG_MESSAGE, self._on_log_for_ui)

    def _on_log_for_ui(self, event: GameEvent) -> None:
        """EventBus handler: 转发日志消息到 UI."""
        if self.ui:
            msg = event.data.get("message", "")
            if msg:
                self.ui.show_log(msg)

    def set_skill_system(self, skill_system: SkillSystem) -> None:
        """设置技能系统并注册被动技能事件处理器."""
        self.skill_system = skill_system
        # M1-T04: 被动技能通过 EventBus 监听事件自动触发
        skill_system.register_event_handlers(self.event_bus)

    def _ensure_skill_system(self) -> None:
        """确保当前引擎已挂载技能系统."""
        if self.skill_system is None:
            from .skill import SkillSystem

            self.set_skill_system(SkillSystem(self))

    def _deal_initial_hand_cards(self) -> None:
        """为所有玩家发放初始手牌并发布对应事件."""
        from i18n import t as _t

        for player in self.players:
            cards = self.deck.draw(4)
            player.draw_cards(cards)
            self.notify_cards_obtained(player, cards, reason="initial_draw")
            self.log_event("draw_cards", _t("game.draw_cards", player=player.name, count=len(cards)))

    def _begin_started_game(self) -> None:
        """进入已开始状态并发布统一的开局生命周期事件."""
        from i18n import t as _t

        self.state = GameState.IN_PROGRESS
        self.current_player_index = self.lord_player_index
        self.round_count = 1
        for player in self.players:
            player.reset_round()

        self.log_event("game_start", _t("game.start"))
        self.event_bus.emit(
            EventType.ROUND_START,
            round=self.round_count,
            player=self.current_player,
        )

    def execute_action(self, action: GameAction) -> bool:
        """统一动作执行入口（M2-T01）.

        所有玩家行为（出牌/技能/弃牌）都应通过此方法执行，
        以确保统一的校验和日志记录。

        Args:
            action: 要执行的动作

        Returns:
            动作是否执行成功
        """
        from .actions import ActionExecutor

        # 惰性创建执行器
        if not hasattr(self, "_action_executor") or self._action_executor is None:
            self._action_executor = ActionExecutor(self)

        # 记录动作到日志（用于回放）
        if not hasattr(self, "action_log"):
            self.action_log = []

        result = self._action_executor.execute(action)

        if result:
            # 成功执行的动作记录到日志
            self.action_log.append(
                {
                    "log_schema_version": "1.1",
                    "action_id": action.action_id,
                    "correlation_id": action.correlation_id,
                    "source_channel": action.source_channel,
                    "action_type": action.action_type.name,
                    "player_id": action.player_id,
                    "timestamp": action.timestamp,
                    "data": self._serialize_action(action),
                }
            )

        return result

    def _serialize_action(self, action: GameAction) -> dict:
        """序列化动作数据（用于回放）."""
        from .actions import DiscardAction, PlayCardAction, UseSkillAction

        data = {
            "type": action.action_type.name,
            "action_id": action.action_id,
            "source_channel": action.source_channel,
            "correlation_id": action.correlation_id,
        }

        if isinstance(action, PlayCardAction):
            data["card_id"] = action.card_id
            data["target_ids"] = action.target_ids
        elif isinstance(action, UseSkillAction):
            data["skill_id"] = action.skill_id
            data["target_ids"] = action.target_ids
            data["card_ids"] = action.card_ids
            data["extra_payload"] = action.extra_payload
        elif isinstance(action, DiscardAction):
            data["card_ids"] = action.card_ids

        return data

    def log_event(
        self,
        event_type: str,
        message: str,
        source: Player | None = None,
        target: Player | None = None,
        card: Card | None = None,
        **extra_data,
    ) -> None:
        """记录游戏事件并通过事件总线发布."""
        _engine_log_event(
            self,
            event_type,
            message,
            source=source,
            target=target,
            card=card,
            **extra_data,
        )

    def notify_cards_obtained(
        self,
        player: Player,
        cards: list[Card],
        *,
        source: Player | None = None,
        from_player: Player | None = None,
        reason: str = "",
    ) -> None:
        """发布获得牌语义事件."""
        _engine_notify_cards_obtained(
            self,
            player,
            cards,
            source=source,
            from_player=from_player,
            reason=reason,
        )

    def notify_cards_lost(
        self,
        player: Player,
        cards: list[Card],
        *,
        source: Player | None = None,
        to_player: Player | None = None,
        reason: str = "",
    ) -> None:
        """发布失去牌语义事件."""
        _engine_notify_cards_lost(
            self,
            player,
            cards,
            source=source,
            to_player=to_player,
            reason=reason,
        )

    def setup_game(
        self, player_count: int, human_player_index: int = 0, role_preference: str = "lord"
    ) -> None:
        """设置游戏."""
        _engine_setup_game(
            self,
            player_count,
            human_player_index=human_player_index,
            role_preference=role_preference,
        )

    def _assign_identities(self) -> None:
        """分配身份（支持2-8人）- 使用 IdentityConfig (SSOT)."""
        _engine_assign_identities(self)

    @property
    def lord_player(self) -> Player | None:
        """获取主公玩家."""
        for p in self.players:
            if p.identity == Identity.LORD:
                return p
        return None

    @property
    def lord_player_index(self) -> int:
        """获取主公玩家的座位索引."""
        for i, p in enumerate(self.players):
            if p.identity == Identity.LORD:
                return i
        return 0

    def choose_heroes(self, choices: dict[int, str]) -> None:
        """为所有玩家选择武将.

        Args:
            choices: 玩家ID到武将ID的映射
        """
        for player_id, hero_id in choices.items():
            player = self.get_player_by_id(player_id)
            hero = self.hero_repo.get_hero(hero_id)
            if player and hero:
                # 复制武将对象，避免共享状态
                import copy

                player_hero = copy.deepcopy(hero)
                player.set_hero(player_hero)
                from i18n import t as _t

                self.log_event(
                    "hero_chosen", _t("game.hero_chosen", player=player.name, hero=hero.name)
                )

    def auto_choose_heroes_for_ai(self) -> dict[int, str]:
        """为AI玩家自动选择武将.

        Returns:
            AI玩家的武将选择
        """
        available_heroes = self.hero_repo.get_all_heroes()
        random.shuffle(available_heroes)

        choices = {}
        used_heroes = set()

        for player in self.players:
            if player.is_ai and player.hero is None:
                for hero in available_heroes:
                    if hero.id not in used_heroes:
                        choices[player.id] = hero.id
                        used_heroes.add(hero.id)
                        break

        return choices

    def start_game(self) -> None:
        """开始游戏."""
        _engine_ensure_can_start_game(self)
        self._deal_initial_hand_cards()
        self._begin_started_game()

    @property
    def current_player(self) -> Player:
        """获取当前回合玩家."""
        return self.players[self.current_player_index]

    def get_player_by_id(self, player_id: int) -> Player | None:
        """根据ID获取玩家."""
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def get_alive_players(self) -> list[Player]:
        """获取所有存活玩家."""
        return [p for p in self.players if p.is_alive]

    def get_other_players(self, player: Player) -> list[Player]:
        """获取除指定玩家外的其他存活玩家."""
        return [p for p in self.players if p.is_alive and p != player]

    def count_alive_kingdoms(self) -> int:
        """获取当前存活角色的势力数."""
        return len({player.hero.kingdom.value for player in self.get_alive_players() if player.hero})

    def record_card_usage(
        self, player: Player, card: Card, targets: list[Player] | None = None, *, is_virtual: bool = False
    ) -> None:
        """记录回合内的用牌统计，供复杂技能条件判定使用."""
        used_types = set(player.get_turn_flag("used_card_types", set()))
        used_types.add(card.card_type.value)
        player.set_turn_flag("used_card_types", used_types)
        if targets and any(target != player for target in targets):
            player.set_turn_flag("used_card_targeting_others", True)
        if is_virtual:
            player.set_turn_flag("used_virtual_card", True)

    def get_all_other_players(self, player: Player) -> list[Player]:
        """获取除指定玩家外的所有其他玩家（含已死亡），用于 UI 显示."""
        return [p for p in self.players if p != player]

    def get_next_player(self, player: Player | None = None) -> Player:
        """获取下一个存活玩家."""
        if player is None:
            player = self.current_player

        start_index = self.players.index(player)
        for i in range(1, len(self.players) + 1):
            next_index = (start_index + i) % len(self.players)
            if self.players[next_index].is_alive:
                return self.players[next_index]

        return player  # 如果只剩一个玩家

    def calculate_distance(self, from_player: Player, to_player: Player) -> int:
        """计算两个玩家之间的距离 (P2-4: 带缓存).

        Args:
            from_player: 起始玩家
            to_player: 目标玩家

        Returns:
            距离值
        """
        if from_player == to_player:
            return 0

        # P2-4: 查询缓存
        cached = self._distance_cache.get(from_player.id, to_player.id)
        if cached is not None:
            return cached

        dist = self._calculate_distance_raw(from_player, to_player)

        # 写入缓存
        self._distance_cache.set(from_player.id, to_player.id, dist)
        return dist

    def _calculate_distance_raw(self, from_player: Player, to_player: Player) -> int:
        """计算原始距离 (无缓存)."""
        alive_players = self.get_alive_players()
        if len(alive_players) <= 1:
            return 0

        # 找到两个玩家在存活玩家中的位置
        try:
            from_index = alive_players.index(from_player)
            to_index = alive_players.index(to_player)
        except ValueError:
            return 999  # 其中一个玩家已死亡

        n = len(alive_players)

        # 计算顺时针和逆时针距离
        clockwise = (to_index - from_index) % n
        counter_clockwise = (from_index - to_index) % n

        # 基础距离取较小值
        base_distance = min(clockwise, counter_clockwise)

        # 应用距离修正
        # -1马：from_player 到其他角色距离-1
        distance_modifier = from_player.equipment.distance_to_others
        # +1马：to_player 被其他角色计算距离时+1
        distance_modifier += to_player.equipment.distance_from_others

        return max(1, base_distance + distance_modifier)

    def is_in_attack_range(self, attacker: Player, target: Player) -> bool:
        """检查目标是否在攻击范围内.

        Args:
            attacker: 攻击者
            target: 目标

        Returns:
            是否在攻击范围内
        """
        distance = self.calculate_distance(attacker, target)
        attack_range = attacker.equipment.attack_range
        return distance <= attack_range

    def get_targets_in_range(self, player: Player) -> list[Player]:
        """获取攻击范围内的所有目标."""
        targets = []
        for other in self.get_other_players(player):
            if self.is_in_attack_range(player, other):
                targets.append(other)
        return targets

    # ==================== 回合流程 ====================

    def run_turn(self) -> None:
        """执行当前玩家的回合（委托给 TurnManager）."""
        player = self.current_player

        if not player.is_alive:
            self.next_turn()
            return

        self.turn_manager.run_turn(player)

    def phase_prepare(self, player: Player) -> None:
        """准备阶段 — 委托给 TurnManager (Phase 2.6)."""
        self.phase = GamePhase.PREPARE
        self.turn_manager._execute_prepare_phase(player)

    def phase_judge(self, player: Player) -> None:
        """判定阶段 — 委托给 TurnManager (Phase 2.6)."""
        self.phase = GamePhase.JUDGE
        self.turn_manager._execute_judge_phase(player)

    def phase_draw(self, player: Player) -> None:
        """摸牌阶段 — 委托给 TurnManager (Phase 2.6)."""
        self.phase = GamePhase.DRAW
        self.turn_manager._execute_draw_phase(player)

    def phase_play(self, player: Player) -> None:
        """出牌阶段 — 委托给 TurnManager (Phase 2.6)."""
        self.phase = GamePhase.PLAY
        self.turn_manager._execute_play_phase(player)

    def phase_discard(self, player: Player) -> None:
        """弃牌阶段 — 委托给 TurnManager (Phase 2.6)."""
        self.phase = GamePhase.DISCARD
        self.turn_manager._execute_discard_phase(player)

    def phase_end(self, player: Player) -> None:
        """结束阶段 — 委托给 TurnManager (Phase 2.6)."""
        self.phase = GamePhase.END
        self.turn_manager._execute_end_phase(player)

    def next_turn(self) -> None:
        """进入下一个玩家的回合."""
        previous_index = self.current_player_index

        # 找到下一个存活的玩家
        for i in range(1, len(self.players) + 1):
            next_index = (self.current_player_index + i) % len(self.players)
            if self.players[next_index].is_alive:
                self.current_player_index = next_index
                break

        # 如果回到主公，回合数+1
        if (
            self.current_player_index == self.lord_player_index
            and previous_index != self.lord_player_index
        ):
            self.event_bus.emit(
                EventType.ROUND_END,
                round=self.round_count,
                player=self.players[previous_index],
            )
            self.round_count += 1
            for player in self.players:
                player.reset_round()
            self.event_bus.emit(
                EventType.ROUND_START,
                round=self.round_count,
                player=self.current_player,
            )

    # ==================== 卡牌使用 ====================

    def use_card(self, player: Player, card: Card, targets: list[Player] | None = None) -> bool:
        """使用卡牌（M1-T02: 优先通过 effect_registry 路由）.

        Args:
            player: 使用者
            card: 卡牌
            targets: 目标列表

        Returns:
            是否成功使用
        """
        if targets is None:
            targets = []

        if (
            self.skill_system
            and self.phase == GamePhase.PLAY
            and targets
            and player.has_skill(SkillId.XIAOSHI)
        ):
            self.skill_system.trigger_skill(
                SkillId.XIAOSHI,
                player,
                self,
                card=card,
                targets=targets,
            )

        # 移除手牌
        card_was_in_hand = card in player.hand
        if card in player.hand:
            player.remove_card(card)

        # 杀类卡牌（普通杀/火杀/雷杀）特殊处理（含 subtype 变体）
        if card.name == CardName.SHA or card.subtype in [
            CardSubtype.ATTACK,
            CardSubtype.FIRE_ATTACK,
            CardSubtype.THUNDER_ATTACK,
        ]:
            result = self.combat.use_sha(player, card, targets)
            if card_was_in_hand and card not in player.hand:
                self.notify_cards_lost(player, [card], source=player, reason="use_card")
            if result:
                self.record_card_usage(player, card, targets)
            return result

        # M1-T02: 优先通过效果注册表路由
        effect = self.effect_registry.get(card.name)
        if effect:
            result = effect.resolve(self, player, card, targets)
            if card_was_in_hand and card not in player.hand:
                self.notify_cards_lost(player, [card], source=player, reason="use_card")
            if result:
                self.record_card_usage(player, card, targets)
            return result

        # 借刀杀人单独路由
        if card.name == CardName.JIEDAO:
            result = self.card_resolver.use_jiedao(player, card, targets)
            if card_was_in_hand and card not in player.hand:
                self.notify_cards_lost(player, [card], source=player, reason="use_card")
            if result:
                self.record_card_usage(player, card, targets)
            return result

        # 按子类型 fallback
        if card.subtype == CardSubtype.ALCOHOL:
            result = self.card_resolver.use_jiu(player, card)
            if card_was_in_hand and card not in player.hand:
                self.notify_cards_lost(player, [card], source=player, reason="use_card")
            if result:
                self.record_card_usage(player, card, targets)
            return result
        elif card.subtype == CardSubtype.CHAIN:
            result = self.card_resolver.use_tiesuo(player, card, targets)
            if card_was_in_hand and card not in player.hand:
                self.notify_cards_lost(player, [card], source=player, reason="use_card")
            if result:
                self.record_card_usage(player, card, targets)
            return result
        elif card.is_type(CardType.EQUIPMENT):
            result = self.equipment_sys.equip(player, card)
            if card_was_in_hand and card not in player.hand:
                self.notify_cards_lost(player, [card], source=player, reason="use_card")
            if result:
                self.record_card_usage(player, card, targets)
            return result

        # 将使用的牌放入弃牌堆
        self.deck.discard([card])
        if card_was_in_hand and card not in player.hand:
            self.notify_cards_lost(player, [card], source=player, reason="use_card")
        self.record_card_usage(player, card, targets)
        return True

    # ==================== GameContext 协议方法 ====================

    def _request_wuxie(
        self, trick_card: Card, source: Player, target: Player | None = None, is_delay: bool = False
    ) -> bool:
        """请求无懈可击响应 — 委托给 CombatSystem (Phase 2.2)."""
        return self.combat.request_wuxie(trick_card, source, target, is_delay)

    def _ai_should_wuxie(
        self,
        responder: Player,
        source: Player,
        target: Player | None,
        trick_card: Card,
        currently_cancelled: bool,
    ) -> bool:
        """AI 决定是否使用无懈可击.

        简单策略：
        - 对敌方使用的有害锦囊（目标是己方）更倾向无懈
        - 对己方收益锦囊不无懈
        - 如果当前已被无懈，考虑是否反无懈
        """
        from ai.strategy import is_enemy

        # 获取 AI bot 进行更智能的判断
        if responder.id in self.ai_bots:
            self.ai_bots[responder.id]
            # 判断敌友关系（使用共享工具函数）
            is_source_enemy = is_enemy(responder, source)
            is_target_friendly = target and not is_enemy(responder, target)
            is_target_self = target == responder

            # 有害锦囊列表
            harmful_tricks = [
                CardName.JUEDOU,
                CardName.NANMAN,
                CardName.WANJIAN,
                CardName.GUOHE,
                CardName.SHUNSHOU,
                CardName.LEBUSISHU,
                CardName.BINGLIANG,
            ]

            # 锦囊当前未被抵消
            if not currently_cancelled:
                # 有害锦囊且目标是自己或友方 → 无懈
                if trick_card.name in harmful_tricks and (is_target_self or is_target_friendly):
                    return True
                # 收益锦囊且来源是敌人 → 可能无懈（如敌方无中生有）
                if trick_card.name == CardName.WUZHONG and is_source_enemy:
                    # 随机决定是否无懈敌方的无中生有
                    return random.random() < 0.3
            else:
                # 锦囊当前已被抵消，考虑反无懈
                # 有害锦囊被抵消了，且来源是敌人 → 不反无懈（让它失效）
                # 有害锦囊被抵消了，且来源是己方 → 考虑反无懈
                if trick_card.name in harmful_tricks:
                    if not is_source_enemy and (is_target_self or is_target_friendly):
                        # 己方对己方的有害锦囊被抵消？不太可能，跳过
                        pass
                    elif is_source_enemy:
                        # 敌方的有害锦囊被（友方？）抵消了，不需要反无懈
                        pass

        return False

    def discard_cards(self, player: Player, cards: list[Card]) -> None:
        """弃置卡牌."""
        discarded_cards = []
        for card in cards:
            if player.remove_card(card):
                discarded_cards.append(card)
        self.notify_cards_lost(player, discarded_cards, source=player, reason="discard")
        self.deck.discard(discarded_cards)
        if discarded_cards:
            player.set_turn_flag(
                "discarded_card_count",
                player.get_turn_flag("discarded_card_count", 0) + len(discarded_cards),
            )

        if discarded_cards:
            cards_str = ", ".join(c.display_name for c in discarded_cards)
            from i18n import t as _t

            self.log_event("discard", _t("game.discard", player=player.name, cards=cards_str))

    # ==================== 伤害和死亡 ====================

    def deal_damage(
        self,
        source: Player | None,
        target: Player,
        damage: int,
        damage_type: str = "normal",
        _chain_propagating: bool = False,
    ) -> None:
        """造成伤害（支持属性伤害与铁索连环传导）.

        Args:
            source: 伤害来源，None 表示系统伤害（如闪电）
            target: 目标玩家
            damage: 伤害值，必须大于 0
            damage_type: 伤害类型 ("normal", "fire", "thunder")
            _chain_propagating: 内部参数，标记是否为连环传导伤害

        Raises:
            ValueError: 当 damage <= 0 或 target 无效时
        """
        # 输入验证
        if damage <= 0:
            logger.warning(f"deal_damage called with invalid damage={damage}")
            return
        if not target or not target.is_alive:
            logger.warning("deal_damage called with invalid target")
            return
        from i18n import t as _t

        source_name = source.name if source else _t("game.damage_system")
        old_hp = target.hp

        # 伤害前事件：允许技能或系统修改/阻止伤害
        damage_event = self.event_bus.emit(
            EventType.DAMAGE_INFLICTING,
            source=source,
            target=target,
            damage=damage,
            damage_type=damage_type,
        )
        if damage_event.cancelled or damage_event.prevented:
            return
        damage = damage_event.damage
        if damage <= 0:
            return

        # 伤害类型显示
        damage_type_display = {
            "normal": "",
            "fire": _t("game.damage_fire"),
            "thunder": _t("game.damage_thunder"),
        }.get(damage_type, "")

        # Phase 2.3: 装备护甲修正伤害 (藤甲/白银狮子)
        damage = self.equipment_sys.modify_damage(target, damage, damage_type)

        target.take_damage(damage, source)

        # 详细的伤害日志
        self.log_event(
            "damage",
            _t(
                "game.damage",
                target=target.name,
                source=source_name,
                damage=damage,
                type=damage_type_display,
                old_hp=old_hp,
                new_hp=target.hp,
                max_hp=target.max_hp,
            ),
        )

        # M1-T04: 发布 DAMAGE_INFLICTED 语义事件（被动技能通过 EventBus 监听触发）
        self.event_bus.emit(
            EventType.DAMAGE_INFLICTED,
            source=source,
            target=target,
            damage=damage,
            damage_type=damage_type,
        )

        # 铁索连环传导
        if damage_type in ["fire", "thunder"] and target.is_chained and not _chain_propagating:
            target.break_chain()  # 解除当前目标的连环状态
            self.log_event("chain", _t("game.chain_trigger", player=target.name))

            # 传导给其他被连环的角色（按座位顺序）
            for p in self.players:
                if p.is_alive and p != target and p.is_chained:
                    self.log_event("chain", _t("game.chain_propagate", player=p.name))
                    p.break_chain()  # 解除连环状态
                    self.deal_damage(source, p, damage, damage_type, _chain_propagating=True)

        # 检查濒死
        if target.is_dying:
            self._handle_dying(target)

    def _handle_dying(self, player: Player) -> None:
        """处理濒死状态.

        当玩家体力 <= 0 时触发，向所有玩家请求桃救援

        Args:
            player: 濒死的玩家
        """
        if not player:
            logger.error("_handle_dying called with None player")
            return

        from i18n import t as _t

        hero_name = player.hero.name if player.hero else "???"
        self.log_event("dying", _t("game.dying", player=player.name, hero=hero_name, hp=player.hp))

        # 请求所有玩家使用桃救援
        saved = False

        # 从当前玩家开始
        start_index = self.players.index(player)
        for i in range(len(self.players)):
            current_index = (start_index + i) % len(self.players)
            savior = self.players[current_index]

            if not savior.is_alive:
                continue

            while player.hp <= 0:
                card = self.request_handler.request_tao(savior, player)
                if card:
                    savior.remove_card(card)
                    player.heal(1)
                    self.deck.discard([card])
                    self.log_event("save", _t("game.save", savior=savior.name, player=player.name))

                    # 救援技能（孙权）
                    if (
                        player.has_skill(SkillId.JIUYUAN)
                        and player.identity == Identity.LORD
                        and savior.hero
                        and savior.hero.kingdom == Kingdom.WU
                    ):
                        player.heal(1)
                        self.log_event("skill", _t("game.jiuyuan", player=player.name))
                else:
                    break

            if player.hp > 0:
                saved = True
                break

        if not saved and player.hp <= 0:
            self._handle_death(player)

    def _ai_should_save(self, savior: Player, dying: Player) -> bool:
        """AI决定是否救援."""
        # 简单逻辑：同阵营救援
        if savior.identity == dying.identity:
            return True
        if savior.identity == Identity.LOYALIST and dying.identity == Identity.LORD:
            return True
        if dying.identity == Identity.LORD:
            # 内奸在最后阶段可能不救主公
            if savior.identity == Identity.SPY:
                alive_count = len(self.get_alive_players())
                if alive_count <= 2:
                    return False
            return True
        return False

    def _handle_death(self, player: Player) -> None:
        """处理死亡."""
        player.die()
        from i18n import t as _t

        self.log_event(
            "death", _t("game.death", player=player.name, identity=player.identity.chinese_name)
        )

        # M1-T04: 发布 DEATH 语义事件
        self.event_bus.emit(
            EventType.DEATH,
            target=player,
            source=self.current_player,
        )

        # 弃置所有牌
        all_cards = player.get_all_cards()
        player.hand.clear()
        player.equipment = type(player.equipment)()
        self.deck.discard(all_cards)

        # 检查奖惩
        if self.current_player.is_alive:
            killer = self.current_player

            # 杀死反贼，摸三张牌
            if player.identity == Identity.REBEL:
                cards = self.deck.draw(3)
                killer.draw_cards(cards)
                self.log_event("reward", _t("game.reward_rebel", killer=killer.name))

            # 主公杀死忠臣，弃置所有牌
            if killer.identity == Identity.LORD and player.identity == Identity.LOYALIST:
                discard_cards = killer.get_all_cards()
                killer.hand.clear()
                killer.equipment = type(killer.equipment)()
                self.deck.discard(discard_cards)
                self.log_event("penalty", _t("game.penalty_loyalist", killer=killer.name))

        # 检查游戏是否结束
        self.check_game_over()

    def check_game_over(self) -> bool:
        """检查游戏是否结束."""
        alive_players = self.get_alive_players()

        # 检查主公是否存活
        lord = None
        for p in self.players:
            if p.identity == Identity.LORD:
                lord = p
                break

        if lord and not lord.is_alive:
            # 主公死亡
            # 检查是否只剩内奸
            spy_count = sum(1 for p in alive_players if p.identity == Identity.SPY)
            if len(alive_players) == spy_count and spy_count > 0:
                self.winner_identity = Identity.SPY
                self.state = GameState.FINISHED
                from i18n import t as _t

                self.log_event("game_over", _t("game.over_spy_wins"))
                return True
            else:
                from i18n import t as _t

                self.winner_identity = Identity.REBEL
                self.state = GameState.FINISHED
                self.log_event("game_over", _t("game.over_rebel_wins"))
                return True

        # 检查反贼和内奸是否全部死亡
        rebel_alive = any(p.identity == Identity.REBEL and p.is_alive for p in self.players)
        spy_alive = any(p.identity == Identity.SPY and p.is_alive for p in self.players)

        if not rebel_alive and not spy_alive:
            self.winner_identity = Identity.LORD
            self.state = GameState.FINISHED
            from i18n import t as _t

            self.log_event("game_over", _t("game.over_lord_wins"))
            return True

        return False

    def is_game_over(self) -> bool:
        """检查游戏是否结束."""
        return self.state == GameState.FINISHED

    def get_winner_message(self) -> str:
        """获取胜利消息."""
        from i18n import t as _t

        if self.winner_identity == Identity.LORD:
            return _t("game.over_lord_wins")
        elif self.winner_identity == Identity.REBEL:
            return _t("game.over_rebel_wins")
        elif self.winner_identity == Identity.SPY:
            return _t("game.over_spy_wins")
        return _t("game.over_generic")

    # ==================== 无 UI 对战接口（用于压测/AI研究） ====================

    def setup_headless_game(
        self, player_count: int, ai_difficulty: str = "normal", seed: int | None = None
    ) -> None:
        """设置无 UI 对战（用于压力测试与 AI 研究）.

        Args:
            player_count: 玩家数量（2-8）
            ai_difficulty: AI 难度 ("easy", "normal", "hard")
            seed: 随机种子（用于复现对局），None 则自动生成

        Raises:
            ValueError: 当玩家数量不在 2-8 范围内时
        """
        from ai.bot import AIBot, AIDifficulty

        if player_count < 2 or player_count > 8:
            from i18n import t as _t

            raise ValueError(_t("error.player_count"))

        # M3-T01: 统一随机种子注入与记录
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        self.game_seed = seed
        random.seed(seed)
        from i18n import t as _t

        self.log_event("system", _t("game.random_seed", seed=seed))

        # 初始化动作日志（用于回放）
        self.action_log = []
        self.ai_bots.clear()

        # 创建玩家（全部为 AI）
        self.players.clear()
        self._assign_identities_for_count(player_count)

        # 随机选择武将
        all_heroes = self.hero_repo.get_all_heroes()
        random.shuffle(all_heroes)

        # 设置 AI 难度
        difficulty_map = {
            "easy": AIDifficulty.EASY,
            "normal": AIDifficulty.NORMAL,
            "hard": AIDifficulty.HARD,
        }
        difficulty = difficulty_map.get(ai_difficulty, AIDifficulty.NORMAL)

        # 先创建玩家并分配身份，再分配武将（确保 set_hero 能正确识别主公 +1 HP）
        for i in range(player_count):
            player = Player(id=i, name=f"AI_{i + 1}", is_ai=True, seat=i, game_engine=self)
            self.players.append(player)

        # BUG-FIX: 先分配身份，再分配武将——否则 set_hero 无法识别主公身份，导致主公缺少 +1 HP
        self._assign_identities()

        for i, player in enumerate(self.players):
            # 分配武将
            if i < len(all_heroes):
                import copy

                hero = copy.deepcopy(all_heroes[i])
                player.set_hero(hero)

            # 创建 AI
            self.ai_bots[player.id] = AIBot(player, difficulty)
        self._ensure_skill_system()

        # 重置牌堆
        self.deck.reset()
        self._deal_initial_hand_cards()
        self._begin_started_game()

    def setup_room_game(
        self,
        connected_players: list[tuple[int, str]],
        total_player_count: int | None = None,
        ai_difficulty: str = "normal",
        seed: int | None = None,
    ) -> None:
        """根据房间玩家创建网络权威对局."""
        from ai.bot import AIBot, AIDifficulty

        if total_player_count is None:
            total_player_count = len(connected_players)

        if total_player_count < 2 or total_player_count > 8:
            from i18n import t as _t

            raise ValueError(_t("error.player_count"))

        if len(connected_players) > total_player_count:
            raise ValueError("connected_players exceeds total_player_count")

        player_ids = [player_id for player_id, _ in connected_players]
        if len(set(player_ids)) != len(player_ids):
            raise ValueError("duplicate connected player ids")

        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        self.game_seed = seed
        random.seed(seed)
        from i18n import t as _t

        self.log_event("system", _t("game.random_seed", seed=seed))
        self.action_log = []
        self.players.clear()
        self.ai_bots.clear()
        self.human_player = None

        for seat, (player_id, name) in enumerate(connected_players):
            player = Player(id=player_id, name=name, is_ai=False, seat=seat)
            player.game_engine = self
            self.players.append(player)
            if self.human_player is None:
                self.human_player = player

        next_ai_id = max(player_ids, default=0) + 1
        ai_slots = total_player_count - len(connected_players)
        for ai_index in range(ai_slots):
            player = Player(
                id=next_ai_id + ai_index,
                name=f"AI_{ai_index + 1}",
                is_ai=True,
                seat=len(self.players),
                game_engine=self,
            )
            self.players.append(player)

        self._assign_identities()

        all_heroes = self.hero_repo.get_all_heroes()
        random.shuffle(all_heroes)
        difficulty_map = {
            "easy": AIDifficulty.EASY,
            "normal": AIDifficulty.NORMAL,
            "hard": AIDifficulty.HARD,
        }
        difficulty = difficulty_map.get(ai_difficulty, AIDifficulty.NORMAL)

        for i, player in enumerate(self.players):
            if i < len(all_heroes):
                import copy

                hero = copy.deepcopy(all_heroes[i])
                player.set_hero(hero)

            if player.is_ai:
                self.ai_bots[player.id] = AIBot(player, difficulty)
        self._ensure_skill_system()

        self.deck.reset()
        self._deal_initial_hand_cards()
        self._begin_started_game()

    def _assign_identities_for_count(self, player_count: int) -> None:
        """为指定人数分配身份配置."""
        # 预配置身份（稍后在 _assign_identities 中使用）
        pass  # _assign_identities 会处理

    def run_headless_turn(self, max_actions: int = 50) -> bool:
        """执行当前玩家的无 UI 回合（委托给 TurnManager）.

        Args:
            max_actions: 单回合最大操作数（防止死循环）

        Returns:
            回合是否正常完成
        """
        player = self.current_player

        if not player.is_alive:
            self.next_turn()
            return True

        self.turn_manager.run_turn(player)
        return True

    def export_action_log(self, filepath: str | None = None) -> str:
        """导出 action_log 为 JSON 文件（M3-T02）.

        Args:
            filepath: 导出路径，None 则自动生成

        Returns:
            导出的文件路径
        """
        import json
        from datetime import datetime

        if not hasattr(self, "action_log"):
            self.action_log = []

        # 汇总来源统计
        source_channel_stats: dict[str, int] = {}
        for item in self.action_log:
            source = item.get("source_channel", "unknown")
            source_channel_stats[source] = source_channel_stats.get(source, 0) + 1

        # 构建导出数据
        export_data = {
            "version": "1.1",
            "action_log_schema_version": "1.1",
            "exported_at": datetime.now().isoformat(),
            "game_seed": getattr(self, "game_seed", None),
            "player_count": len(self.players),
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "hero": p.hero.name if p.hero else None,
                    "identity": p.identity.value if p.identity else None,
                }
                for p in self.players
            ],
            "winner": self.winner_identity.value if self.winner_identity else None,
            "rounds": self.round_count,
            "action_count": len(self.action_log),
            "source_channel_stats": source_channel_stats,
            "actions": self.action_log,
        }

        # 生成文件路径
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            seed_str = f"_seed{self.game_seed}" if hasattr(self, "game_seed") else ""
            filepath = f"logs/action_log_{timestamp}{seed_str}.json"

        # 确保目录存在
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        from i18n import t as _t

        self.log_event("system", _t("game.action_log_exported", filepath=filepath))
        return filepath

    def run_headless_battle(self, max_rounds: int = 100) -> dict[str, Any]:
        """运行完整的无 UI 对局.

        Args:
            max_rounds: 最大回合数

        Returns:
            对局结果字典
        """
        from i18n import t as _t

        round_count = 0

        while self.state == GameState.IN_PROGRESS and round_count < max_rounds:
            round_count += 1

            for _ in range(len(self.players)):
                if self.state != GameState.IN_PROGRESS:
                    break

                self.run_headless_turn()
                self.next_turn()

        return {
            "winner": self.winner_identity.chinese_name
            if self.winner_identity
            else _t("game.timeout"),
            "rounds": round_count,
            "players": [p.name for p in self.players],
            "heroes": [p.hero.name if p.hero else _t("game.no_hero") for p in self.players],
            "identities": [p.identity.chinese_name for p in self.players],
            "finished": self.state == GameState.FINISHED,
        }
