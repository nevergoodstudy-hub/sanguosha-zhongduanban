"""存档与读档系统 (M4-T06)

功能:
- 序列化完整游戏状态为 JSON
- 从存档恢复游戏状态
- 支持 action_log 回放
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .card import Card
    from .engine import GameEngine
    from .player import Player

logger = logging.getLogger(__name__)

SAVE_VERSION = "2.0.0"
SAVE_DIR = "saves"

# ==================== 存档 Schema 版本管理 ====================

# 整数 schema 版本，独立于显示用的 SAVE_VERSION 字符串
SCHEMA_VERSION: int = 2

# 迁移注册表: source_schema → (target_schema, migration_fn)
_MIGRATIONS: dict[int, tuple[int, Callable[[dict[str, Any]], dict[str, Any]]]] = {}


def register_migration(from_schema: int, to_schema: int):
    """注册存档迁移函数的装饰器。

    Args:
        from_schema: 源 schema 版本
        to_schema: 目标 schema 版本 (必须 > from_schema)
    """

    def decorator(fn: Callable[[dict[str, Any]], dict[str, Any]]):
        _MIGRATIONS[from_schema] = (to_schema, fn)
        return fn

    return decorator


@register_migration(from_schema=1, to_schema=2)
def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """v1 → v2: 为玩家补充 judge_area / is_chained / is_flipped 字段。"""
    for player in data.get("players", []):
        player.setdefault("judge_area", [])
        player.setdefault("is_chained", False)
        player.setdefault("is_flipped", False)
    data["schema_version"] = 2
    return data


def apply_migrations(data: dict[str, Any]) -> dict[str, Any]:
    """按链式顺序将存档数据迁移到当前 schema 版本。

    无 schema_version 字段的旧存档视为 schema 1。

    Raises:
        ValueError: 无可用迁移路径或存档版本高于当前版本
    """
    schema = data.get("schema_version", 1)

    if schema > SCHEMA_VERSION:
        raise ValueError(
            f"存档 schema {schema} 高于当前支持的最大版本 {SCHEMA_VERSION}，请升级游戏版本"
        )

    while schema < SCHEMA_VERSION:
        if schema not in _MIGRATIONS:
            raise ValueError(f"无法从 schema {schema} 迁移到 {SCHEMA_VERSION}: 缺少迁移路径")
        target, fn = _MIGRATIONS[schema]
        logger.info(f"存档迁移: schema {schema} → {target}")
        data = fn(data)
        schema = target

    return data


# ==================== 序列化 ====================


def serialize_card(card: Card) -> dict[str, Any]:
    """序列化单张卡牌"""
    return {
        "name": card.name
        if isinstance(card.name, str)
        else card.name.value
        if hasattr(card.name, "value")
        else str(card.name),
        "suit": card.suit.value if hasattr(card.suit, "value") else str(card.suit),
        "number": card.number,
        "card_type": card.card_type.value
        if hasattr(card.card_type, "value")
        else str(card.card_type),
    }


def serialize_player(player: Player) -> dict[str, Any]:
    """序列化玩家状态"""
    data = {
        "id": player.id,
        "name": player.name,
        "is_ai": player.is_ai,
        "seat": player.seat,
        "hp": player.hp,
        "max_hp": player.max_hp,
        "is_alive": player.is_alive,
        "identity": player.identity.value if player.identity else None,
        "hero_id": player.hero.id if player.hero else None,
        "hero_name": player.hero.name if player.hero else None,
        "hand": [serialize_card(c) for c in player.hand],
        "hand_count": player.hand_count,
        "equipment": {
            "weapon": serialize_card(player.equipment.weapon) if player.equipment.weapon else None,
            "armor": serialize_card(player.equipment.armor) if player.equipment.armor else None,
            "horse_minus": serialize_card(player.equipment.horse_minus)
            if player.equipment.horse_minus
            else None,
            "horse_plus": serialize_card(player.equipment.horse_plus)
            if player.equipment.horse_plus
            else None,
        },
        "sha_used": getattr(player, "sha_used", 0),
        "is_chained": getattr(player, "is_chained", False),
        "is_flipped": getattr(player, "is_flipped", False),
    }
    # 判定区
    if hasattr(player, "judge_area"):
        data["judge_area"] = [serialize_card(c) for c in player.judge_area]
    return data


def serialize_engine(engine: GameEngine) -> dict[str, Any]:
    """序列化完整游戏状态

    Returns:
        可 JSON 化的 dict，包含所有重建游戏所需信息
    """
    data = {
        "save_version": SAVE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "saved_at": datetime.now().isoformat(),
        "timestamp": time.time(),
        # 游戏配置
        "game_seed": getattr(engine, "game_seed", None),
        "player_count": len(engine.players),
        # 游戏状态
        "state": engine.state.value if engine.state else None,
        "phase": engine.phase.value if engine.phase else None,
        "round_count": engine.round_count,
        "current_player_index": engine.current_player_index,
        "winner_identity": engine.winner_identity.value if engine.winner_identity else None,
        # 玩家
        "players": [serialize_player(p) for p in engine.players],
        # 牌堆状态
        "deck_remaining": engine.deck.remaining if engine.deck else 0,
        "discard_pile_count": engine.deck.discarded if engine.deck else 0,
        # 动作日志 (用于回放)
        "action_log": getattr(engine, "action_log", []),
    }
    return data


# ==================== 持久化 ====================


def save_game(engine: GameEngine, filepath: str | None = None) -> str:
    """保存游戏到文件

    Args:
        engine: 游戏引擎
        filepath: 保存路径 (None 则自动生成)

    Returns:
        保存的文件路径
    """
    save_dir = Path(SAVE_DIR)
    save_dir.mkdir(exist_ok=True)

    if filepath is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = str(save_dir / f"save_{ts}.json")

    data = serialize_engine(engine)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def load_game(filepath: str) -> dict[str, Any]:
    """从文件加载存档数据

    Args:
        filepath: 存档文件路径

    Returns:
        反序列化的存档数据 dict

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式错误
        ValueError: 版本不兼容
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    # Schema 迁移
    data = apply_migrations(data)

    return data


def list_saves(save_dir: str = SAVE_DIR) -> list[dict[str, Any]]:
    """列出所有存档文件

    Returns:
        存档信息列表 (路径、时间、玩家数、回合数)
    """
    path = Path(save_dir)
    if not path.exists():
        return []

    saves = []
    for f in sorted(path.glob("save_*.json"), reverse=True):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            saves.append(
                {
                    "filepath": str(f),
                    "saved_at": data.get("saved_at", "?"),
                    "player_count": data.get("player_count", 0),
                    "round_count": data.get("round_count", 0),
                    "state": data.get("state", "?"),
                    "winner": data.get("winner_identity"),
                }
            )
        except Exception:
            continue

    return saves


def delete_save(filepath: str) -> bool:
    """删除存档"""
    try:
        Path(filepath).unlink()
        return True
    except Exception:
        return False


# ==================== 回放增强 ====================


class EnhancedReplay:
    """增强回放器 (M4-T06)

    支持:
    - 单步前进
    - 跳转到指定步骤
    - 变速播放
    """

    def __init__(self, save_data: dict[str, Any]):
        self.save_data = save_data
        self.action_log: list[dict[str, Any]] = save_data.get("action_log", [])
        self.current_step: int = 0
        self.total_steps: int = len(self.action_log)
        self.speed: float = 1.0  # 1.0 = 正常速度

    @property
    def progress(self) -> float:
        """当前进度 (0.0 ~ 1.0)"""
        if self.total_steps == 0:
            return 1.0
        return self.current_step / self.total_steps

    @property
    def current_action(self) -> dict[str, Any] | None:
        """当前步骤的动作"""
        if 0 <= self.current_step < self.total_steps:
            return self.action_log[self.current_step]
        return None

    def step_forward(self) -> dict[str, Any] | None:
        """前进一步"""
        if self.current_step < self.total_steps:
            action = self.action_log[self.current_step]
            self.current_step += 1
            return action
        return None

    def step_back(self) -> bool:
        """后退一步"""
        if self.current_step > 0:
            self.current_step -= 1
            return True
        return False

    def jump_to(self, step: int) -> bool:
        """跳转到指定步骤"""
        if 0 <= step <= self.total_steps:
            self.current_step = step
            return True
        return False

    def reset(self) -> None:
        """重置到开头"""
        self.current_step = 0

    def set_speed(self, speed: float) -> None:
        """设置播放速度 (0.25x ~ 4.0x)"""
        self.speed = max(0.25, min(4.0, speed))

    @property
    def delay(self) -> float:
        """当前步骤间的延迟 (秒)"""
        return 0.5 / self.speed

    def get_summary(self) -> dict[str, Any]:
        """获取回放摘要"""
        return {
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "progress": f"{self.progress:.1%}",
            "speed": f"{self.speed:.1f}x",
            "player_count": self.save_data.get("player_count", 0),
            "round_count": self.save_data.get("round_count", 0),
            "seed": self.save_data.get("game_seed"),
        }
