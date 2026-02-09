"""GameContext 协议 (Phase 2 — 引擎分解)

定义子系统 (CombatSystem / EquipmentSystem / JudgeSystem / CardResolver 等)
与游戏引擎交互的最小接口。子系统依赖此 Protocol 而非 GameEngine 具体类,
从而实现解耦、可测试性和模块化。

设计原则:
- 仅暴露子系统需要的 *最小* 表面积
- 属性为只读 (@property), 修改通过方法进行
- 使用 typing.Protocol 实现结构子类型化, GameEngine 无需显式继承
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Protocol,
    runtime_checkable,
)

if TYPE_CHECKING:
    from .card import Card, Deck
    from .events import EventBus
    from .player import Player
    from .request_handler import RequestHandler


@runtime_checkable
class GameContext(Protocol):
    """子系统与引擎交互的最小接口。

    GameEngine 隐式实现此协议 (结构子类型化),
    测试时可替换为轻量 stub。
    """

    # ==================== 只读属性 ====================

    @property
    def players(self) -> list[Player]:
        """所有玩家列表 (含已死亡)。"""
        ...

    @property
    def current_player(self) -> Player:
        """当前回合玩家。"""
        ...

    @property
    def deck(self) -> Deck:
        """牌堆 (摸牌/弃牌)。"""
        ...

    @property
    def event_bus(self) -> EventBus:
        """事件总线。"""
        ...

    @property
    def request_handler(self) -> RequestHandler:
        """玩家请求路由 (AI/UI 输入统一入口)。"""
        ...

    @property
    def ai_bots(self) -> dict[int, object]:
        """AI Bot 映射 (player_id → AIBot)。"""
        ...

    # ==================== 玩家查询 ====================

    def get_alive_players(self) -> list[Player]:
        """获取所有存活玩家。"""
        ...

    def get_other_players(self, player: Player) -> list[Player]:
        """获取除指定玩家外的其他存活玩家。"""
        ...

    def get_player_by_id(self, player_id: int) -> Player | None:
        """根据 ID 获取玩家。"""
        ...

    def get_next_player(self, player: Player | None = None) -> Player:
        """获取下一个存活玩家 (座位顺序)。"""
        ...

    # ==================== 距离与范围 ====================

    def calculate_distance(self, from_player: Player, to_player: Player) -> int:
        """计算两个玩家之间的距离 (含马匹修正)。"""
        ...

    def is_in_attack_range(self, attacker: Player, target: Player) -> bool:
        """检查目标是否在攻击范围内。"""
        ...

    def get_targets_in_range(self, player: Player) -> list[Player]:
        """获取攻击范围内的所有目标。"""
        ...

    # ==================== 游戏动作 ====================

    def deal_damage(
        self,
        source: Player | None,
        target: Player,
        damage: int,
        damage_type: str = "normal",
        _chain_propagating: bool = False,
    ) -> None:
        """造成伤害 (支持属性伤害与连环传导)。"""
        ...

    def discard_cards(self, player: Player, cards: list[Card]) -> None:
        """弃置玩家的卡牌到弃牌堆。"""
        ...

    def use_card(
        self,
        player: Player,
        card: Card,
        targets: list[Player] | None = None,
    ) -> bool:
        """使用卡牌 (主入口, 路由到具体效果)。"""
        ...

    # ==================== 子系统交互 ====================

    def _request_wuxie(
        self,
        trick_card: Card,
        source: Player,
        target: Player | None = None,
        is_delay: bool = False,
    ) -> bool:
        """请求无懈可击响应 (延时锯囊/普通锯囊通用)."""
        ...

    # ==================== 日志与事件 ====================

    def log_event(
        self,
        event_type: str,
        message: str,
        source: Player | None = None,
        target: Player | None = None,
        card: Card | None = None,
        **extra_data: object,
    ) -> None:
        """记录游戏事件并通过事件总线发布。"""
        ...
