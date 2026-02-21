"""游戏异常模块
定义三国杀游戏中的各类异常，提供明确的错误类型和信息
"""

from i18n import t as _t


class GameError(Exception):
    """游戏异常基类

    所有游戏相关的异常都应该继承此类，
    提供统一的异常处理接口。
    """

    def __init__(self, message: str, details: dict | None = None):
        """初始化游戏异常

        Args:
            message: 错误消息
            details: 额外的错误详情（可选）
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ==================== 动作相关异常 ====================


class InvalidActionError(GameError):
    """无效动作异常

    当玩家尝试执行不合法的动作时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        action_type: str | None = None,
        player_id: int | None = None,
    ):
        if message is None:
            message = _t("exc.invalid_action")
        details = {}
        if action_type:
            details["action_type"] = action_type
        if player_id is not None:
            details["player_id"] = player_id
        super().__init__(message, details)
        self.action_type = action_type
        self.player_id = player_id


class InvalidTargetError(GameError):
    """无效目标异常

    当选择的目标不合法时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        target_ids: list[int] | None = None,
        reason: str | None = None,
    ):
        if message is None:
            message = _t("exc.invalid_target")
        details = {}
        if target_ids:
            details["target_ids"] = target_ids
        if reason:
            details["reason"] = reason
        super().__init__(message, details)
        self.target_ids = target_ids
        self.reason = reason


class InsufficientCardsError(GameError):
    """卡牌不足异常

    当玩家没有足够的卡牌执行操作时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        required: int = 0,
        available: int = 0,
        card_type: str | None = None,
    ):
        if message is None:
            message = _t("exc.insufficient_cards")
        details = {
            "required": required,
            "available": available,
        }
        if card_type:
            details["card_type"] = card_type
        super().__init__(message, details)
        self.required = required
        self.available = available
        self.card_type = card_type


class CardNotFoundError(GameError):
    """卡牌未找到异常

    当指定的卡牌不存在时抛出
    """

    def __init__(self, message: str | None = None, card_id: str | None = None):
        if message is None:
            message = _t("exc.card_not_found")
        details = {}
        if card_id:
            details["card_id"] = card_id
        super().__init__(message, details)
        self.card_id = card_id


# ==================== 技能相关异常 ====================


class SkillError(GameError):
    """技能异常基类

    所有技能相关异常的父类
    """

    def __init__(
        self,
        message: str | None = None,
        skill_id: str | None = None,
        player_id: int | None = None,
    ):
        if message is None:
            message = _t("exc.skill_error")
        details = {}
        if skill_id:
            details["skill_id"] = skill_id
        if player_id is not None:
            details["player_id"] = player_id
        super().__init__(message, details)
        self.skill_id = skill_id
        self.player_id = player_id


class SkillNotFoundError(SkillError):
    """技能未找到异常

    当指定的技能不存在时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        skill_id: str | None = None,
        player_id: int | None = None,
    ):
        if message is None:
            message = _t("exc.skill_not_found")
        super().__init__(message, skill_id, player_id)


class SkillCooldownError(SkillError):
    """技能冷却异常

    当技能处于冷却状态无法使用时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        skill_id: str | None = None,
        player_id: int | None = None,
        remaining_cooldown: int = 0,
    ):
        if message is None:
            message = _t("exc.skill_cooldown")
        super().__init__(message, skill_id, player_id)
        self.remaining_cooldown = remaining_cooldown
        self.details["remaining_cooldown"] = remaining_cooldown


class SkillConditionError(SkillError):
    """技能条件不满足异常

    当技能的使用条件不满足时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        skill_id: str | None = None,
        player_id: int | None = None,
        condition: str | None = None,
    ):
        if message is None:
            message = _t("exc.skill_condition")
        super().__init__(message, skill_id, player_id)
        self.condition = condition
        if condition:
            self.details["condition"] = condition


class SkillUsageLimitError(SkillError):
    """技能使用次数超限异常

    当技能本回合/本局已达使用次数上限时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        skill_id: str | None = None,
        player_id: int | None = None,
        limit: int = 0,
        used: int = 0,
    ):
        if message is None:
            message = _t("exc.skill_usage_limit")
        super().__init__(message, skill_id, player_id)
        self.limit = limit
        self.used = used
        self.details.update({"limit": limit, "used": used})


# ==================== 游戏状态相关异常 ====================


class GameStateError(GameError):
    """游戏状态异常

    当游戏处于不允许某操作的状态时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        current_state: str | None = None,
        expected_state: str | None = None,
    ):
        if message is None:
            message = _t("exc.game_state")
        details = {}
        if current_state:
            details["current_state"] = current_state
        if expected_state:
            details["expected_state"] = expected_state
        super().__init__(message, details)
        self.current_state = current_state
        self.expected_state = expected_state


class GameNotStartedError(GameStateError):
    """游戏未开始异常

    当游戏尚未开始就尝试执行游戏内操作时抛出
    """

    def __init__(self, message: str | None = None):
        if message is None:
            message = _t("exc.game_not_started")
        super().__init__(message, current_state="not_started")


class GameAlreadyFinishedError(GameStateError):
    """游戏已结束异常

    当游戏已结束但尝试继续操作时抛出
    """

    def __init__(self, message: str | None = None):
        if message is None:
            message = _t("exc.game_finished")
        super().__init__(message, current_state="finished")


class InvalidPhaseError(GameStateError):
    """无效阶段异常

    当在错误的游戏阶段执行操作时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        current_phase: str | None = None,
        expected_phase: str | None = None,
    ):
        if message is None:
            message = _t("exc.invalid_phase")
        super().__init__(message, current_phase, expected_phase)
        self.current_phase = current_phase
        self.expected_phase = expected_phase


# ==================== 玩家相关异常 ====================


class PlayerError(GameError):
    """玩家异常基类

    所有玩家相关异常的父类
    """

    def __init__(self, message: str | None = None, player_id: int | None = None):
        if message is None:
            message = _t("exc.player_error")
        details = {}
        if player_id is not None:
            details["player_id"] = player_id
        super().__init__(message, details)
        self.player_id = player_id


class PlayerNotFoundError(PlayerError):
    """玩家未找到异常

    当指定的玩家不存在时抛出
    """

    def __init__(self, message: str | None = None, player_id: int | None = None):
        if message is None:
            message = _t("exc.player_not_found")
        super().__init__(message, player_id)


class PlayerDeadError(PlayerError):
    """玩家已死亡异常

    当对已死亡玩家执行需要存活的操作时抛出
    """

    def __init__(self, message: str | None = None, player_id: int | None = None):
        if message is None:
            message = _t("exc.player_dead")
        super().__init__(message, player_id)


class NotPlayerTurnError(PlayerError):
    """非玩家回合异常

    当非当前回合玩家尝试执行回合专属操作时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        player_id: int | None = None,
        current_player_id: int | None = None,
    ):
        if message is None:
            message = _t("exc.not_player_turn")
        super().__init__(message, player_id)
        self.current_player_id = current_player_id
        if current_player_id is not None:
            self.details["current_player_id"] = current_player_id


# ==================== 配置/数据相关异常 ====================


class ConfigurationError(GameError):
    """配置错误异常

    当游戏配置有问题时抛出
    """

    def __init__(self, message: str | None = None, config_key: str | None = None):
        if message is None:
            message = _t("exc.config_error")
        details = {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details)
        self.config_key = config_key


class DataLoadError(GameError):
    """数据加载异常

    当加载游戏数据文件失败时抛出
    """

    def __init__(
        self,
        message: str | None = None,
        file_path: str | None = None,
        reason: str | None = None,
    ):
        if message is None:
            message = _t("exc.data_load_error")
        details = {}
        if file_path:
            details["file_path"] = file_path
        if reason:
            details["reason"] = reason
        super().__init__(message, details)
        self.file_path = file_path
        self.reason = reason


# ==================== 工具函数 ====================


def raise_if_game_not_started(game_state: str) -> None:
    """检查游戏是否已开始，未开始则抛出异常

    Args:
        game_state: 当前游戏状态

    Raises:
        GameNotStartedError: 如果游戏未开始
    """
    if game_state == "not_started":
        raise GameNotStartedError()


def raise_if_game_finished(game_state: str) -> None:
    """检查游戏是否已结束，已结束则抛出异常

    Args:
        game_state: 当前游戏状态

    Raises:
        GameAlreadyFinishedError: 如果游戏已结束
    """
    if game_state == "finished":
        raise GameAlreadyFinishedError()


def raise_if_player_dead(is_dead: bool, player_id: int | None = None) -> None:
    """检查玩家是否存活，已死亡则抛出异常

    Args:
        is_dead: 玩家是否已死亡
        player_id: 玩家ID（可选）

    Raises:
        PlayerDeadError: 如果玩家已死亡
    """
    if is_dead:
        raise PlayerDeadError(player_id=player_id)
