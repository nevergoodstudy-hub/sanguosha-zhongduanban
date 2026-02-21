"""AI 决策透明化日志 (P3-1)

记录 AI 每次决策的候选动作、选择理由和评分，
用于调试 AI 行为和平衡性分析。可选启用，不影响性能。

用法:
    logger = AIDecisionLogger(enabled=True)
    logger.log(AIDecision(
        player_id=0,
        ai_tier="hard",
        phase="play",
        action="use_sha",
        chosen={"card": "sha", "target": "player_2"},
        reason="highest_threat",
        score=0.85,
    ))
    logger.export_json("decisions.json")
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AIDecision:
    """AI 决策记录条目。"""

    timestamp: float = field(default_factory=time.time)
    player_id: int = -1
    ai_tier: str = ""  # "easy", "normal", "hard"
    phase: str = ""  # "play", "discard", "response"
    action: str = ""  # "use_sha", "use_tao", "skip", ...
    candidates: list[dict[str, Any]] = field(default_factory=list)
    chosen: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    score: float = 0.0


class AIDecisionLogger:
    """AI 决策日志记录器。

    可通过 enabled 参数控制是否实际记录，
    禁用时所有方法均为空操作。
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._history: list[AIDecision] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def history(self) -> list[AIDecision]:
        return self._history

    def log(self, decision: AIDecision) -> None:
        """记录一条决策。"""
        if not self._enabled:
            return
        self._history.append(decision)
        logger.debug(
            "AI[%s] player=%d %s: %s (score=%.2f, reason=%s)",
            decision.ai_tier,
            decision.player_id,
            decision.phase,
            decision.action,
            decision.score,
            decision.reason,
        )

    def clear(self) -> None:
        """清空历史记录。"""
        self._history.clear()

    def export_json(self, path: str | Path) -> None:
        """导出决策日志为 JSON 文件。"""
        data = [asdict(d) for d in self._history]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def summary(self) -> dict[str, Any]:
        """生成摘要统计。"""
        if not self._history:
            return {"total": 0}

        actions: dict[str, int] = {}
        tiers: dict[str, int] = {}
        total_score = 0.0

        for d in self._history:
            actions[d.action] = actions.get(d.action, 0) + 1
            tiers[d.ai_tier] = tiers.get(d.ai_tier, 0) + 1
            total_score += d.score

        return {
            "total": len(self._history),
            "actions": actions,
            "tiers": tiers,
            "avg_score": total_score / len(self._history),
        }
