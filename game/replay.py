"""游戏回放系统 (P3-3)

记录游戏事件并支持回放查看。使用 gzip 压缩存储。
可作为 EventBus 全局监听器接入。

与 tools/replay.py (CLI 回放工具) 互补：
- 本模块提供数据录制/读取核心
- tools/replay.py 提供命令行交互界面
"""

from __future__ import annotations

import gzip
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ReplayEvent:
    """回放事件条目。"""

    turn: int = 0
    phase: str = ""
    actor: str = ""
    action: str = ""
    targets: list[str] = field(default_factory=list)
    cards: list[str] = field(default_factory=list)
    result: str = ""
    timestamp: float = field(default_factory=time.time)


class ReplayRecorder:
    """游戏回放录制器。"""

    def __init__(self) -> None:
        self.events: list[ReplayEvent] = []
        self.metadata: dict[str, Any] = {}

    def start(self, metadata: dict[str, Any]) -> None:
        """开始录制，记录元数据。"""
        self.metadata = {
            "version": "1.0",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            **metadata,
        }
        self.events.clear()

    def record(self, event: ReplayEvent) -> None:
        """录制一条事件。"""
        self.events.append(event)

    def save(self, path: str) -> None:
        """保存回放文件 (gzip 压缩 JSON)。"""
        data = {
            "metadata": self.metadata,
            "events": [asdict(e) for e in self.events],
        }
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)


class ReplayPlayer:
    """游戏回放播放器。"""

    def __init__(self, path: str) -> None:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        self.metadata: dict[str, Any] = data.get("metadata", {})
        self.events: list[dict[str, Any]] = data.get("events", [])
        self._index: int = 0

    def next_event(self) -> dict[str, Any] | None:
        """获取下一个事件，到末尾返回 None。"""
        if self._index >= len(self.events):
            return None
        event = self.events[self._index]
        self._index += 1
        return event

    def reset(self) -> None:
        """重置到开头。"""
        self._index = 0

    @property
    def total_events(self) -> int:
        return len(self.events)

    @property
    def current_index(self) -> int:
        return self._index
