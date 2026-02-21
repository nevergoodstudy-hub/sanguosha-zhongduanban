"""WebSocket 游戏客户端 (M4-T03)

功能:
- 连接服务端
- 房间管理 (创建/加入/准备/开始)
- 接收游戏事件并驱动 UI 更新
- 发送玩家操作
- 断线自动重连
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

from .protocol import ClientMsg, MsgType, ServerMsg

logger = logging.getLogger(__name__)


class GameClient:
    """三国杀 WebSocket 客户端

    职责:
    1. 维护与服务端的 WebSocket 连接
    2. 收发消息
    3. 通过回调函数将事件通知上层 (UI)
    4. 断线自动重连
    """

    def __init__(self, server_url: str = "ws://localhost:8765"):
        self.server_url = server_url
        self.player_id: int = 0
        self.player_name: str = ""
        self.room_id: str | None = None
        self.last_seq: int = 0  # 最后收到的事件序号
        self.auth_token: str = ""  # 服务端签发的连接令牌

        # WebSocket 连接
        self._ws: ClientConnection | None = None
        self._connected: bool = False
        self._running: bool = False

        # 事件回调
        self._handlers: dict[MsgType, Callable] = {}
        self._on_connect: Callable | None = None
        self._on_disconnect: Callable | None = None

        # 重连配置
        self.auto_reconnect: bool = True
        self.reconnect_delay: float = 2.0
        self.max_reconnect_attempts: int = 5

        # 心跳
        self._heartbeat_interval: float = 15.0

    # ==================== 事件回调注册 ====================

    def on(self, msg_type: MsgType, handler: Callable) -> None:
        """注册消息处理回调"""
        self._handlers[msg_type] = handler

    def on_connect(self, handler: Callable) -> None:
        """注册连接成功回调"""
        self._on_connect = handler

    def on_disconnect(self, handler: Callable) -> None:
        """注册断连回调"""
        self._on_disconnect = handler

    # ==================== 连接管理 ====================

    async def connect(self) -> bool:
        """连接到服务端"""
        try:
            import websockets

            self._ws = await websockets.connect(self.server_url)
            self._connected = True
            logger.info(f"已连接到 {self.server_url}")
            if self._on_connect:
                await self._on_connect()
            return True
        except ImportError:
            logger.error("需要安装 websockets: pip install websockets")
            return False
        except Exception as e:
            logger.error(f"连接失败: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        self._running = False
        self._connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        logger.info("已断开连接")
        if self._on_disconnect:
            await self._on_disconnect()

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    # ==================== 消息收发 ====================

    async def send(self, msg: ClientMsg) -> bool:
        """发送消息"""
        if not self.is_connected:
            logger.warning("未连接，无法发送消息")
            return False
        try:
            await self._ws.send(msg.to_json())
            return True
        except Exception as e:
            logger.warning(f"发送失败: {e}")
            self._connected = False
            return False

    async def _receive_loop(self) -> None:
        """消息接收循环"""
        try:
            async for raw in self._ws:
                await self._dispatch(raw)
        except Exception as e:
            logger.warning(f"接收循环中断: {e}")
            self._connected = False

    async def _dispatch(self, raw: str) -> None:
        """分发收到的消息"""
        try:
            msg = ServerMsg.from_json(raw)

            # 更新事件序号
            if msg.seq > 0:
                self.last_seq = msg.seq

            # 提取服务端签发的令牌 (欢迎消息)
            if msg.type == MsgType.HEARTBEAT_ACK and "token" in msg.data:
                self.auth_token = msg.data["token"]
                pid = msg.data.get("player_id", 0)
                if pid:
                    self.player_id = pid

            # 调用注册的回调
            handler = self._handlers.get(msg.type)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    await handler(msg)
                else:
                    handler(msg)
            else:
                logger.debug(f"未处理的消息类型: {msg.type.value}")

        except Exception as e:
            logger.warning(f"消息分发异常: {e}")

    # ==================== 心跳 ====================

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running and self.is_connected:
            await asyncio.sleep(self._heartbeat_interval)
            if self.is_connected:
                await self.send(ClientMsg.heartbeat(self.player_id))

    # ==================== 重连 ====================

    async def _reconnect(self) -> bool:
        """尝试重连 (携带令牌用于身份验证)"""
        for attempt in range(1, self.max_reconnect_attempts + 1):
            logger.info(f"重连尝试 {attempt}/{self.max_reconnect_attempts}...")
            await asyncio.sleep(self.reconnect_delay * attempt)

            if await self.connect():
                # 重连后请求重放缺失的事件 (携带令牌)
                if self.room_id:
                    await self.send(
                        ClientMsg(
                            type=MsgType.ROOM_JOIN,
                            player_id=self.player_id,
                            data={
                                "room_id": self.room_id,
                                "reconnect": True,
                                "last_seq": self.last_seq,
                                "token": self.auth_token,
                            },
                        )
                    )
                return True

        logger.error("重连失败，已达最大尝试次数")
        return False

    # ==================== 主循环 ====================

    async def run(self) -> None:
        """客户端主循环"""
        if not await self.connect():
            return

        self._running = True

        try:
            # 并行运行接收循环和心跳
            await asyncio.gather(
                self._receive_loop(),
                self._heartbeat_loop(),
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"客户端异常: {e}")
        finally:
            if self._running and self.auto_reconnect:
                if await self._reconnect():
                    await self.run()  # 重连成功后重新运行
            else:
                await self.disconnect()

    # ==================== 便捷操作方法 ====================

    async def create_room(
        self, player_name: str, max_players: int = 4, ai_fill: bool = True
    ) -> None:
        """创建房间"""
        self.player_name = player_name
        await self.send(ClientMsg.room_create(self.player_id, player_name, max_players, ai_fill))

    async def join_room(self, player_name: str, room_id: str) -> None:
        """加入房间"""
        self.player_name = player_name
        await self.send(ClientMsg.room_join(self.player_id, player_name, room_id))

    async def leave_room(self) -> None:
        """离开房间"""
        await self.send(ClientMsg.room_leave(self.player_id))
        self.room_id = None

    async def set_ready(self, ready: bool = True) -> None:
        """设置准备状态"""
        await self.send(ClientMsg.room_ready(self.player_id, ready))

    async def start_game(self) -> None:
        """开始游戏 (房主)"""
        await self.send(ClientMsg.room_start(self.player_id))

    async def list_rooms(self) -> None:
        """获取房间列表"""
        await self.send(ClientMsg.room_list())

    async def play_card(self, card_id: int, target_ids: list[int] = None) -> None:
        """出牌"""
        await self.send(
            ClientMsg.game_action(
                self.player_id,
                "play_card",
                {"card_id": card_id, "target_ids": target_ids or []},
            )
        )

    async def use_skill(self, skill_id: str, target_ids: list[int] = None) -> None:
        """使用技能"""
        await self.send(
            ClientMsg.game_action(
                self.player_id,
                "use_skill",
                {"skill_id": skill_id, "target_ids": target_ids or []},
            )
        )

    async def end_turn(self) -> None:
        """结束回合"""
        await self.send(ClientMsg.game_action(self.player_id, "end_turn"))

    async def respond(self, request_type: str, accepted: bool, card_id: int = None) -> None:
        """响应请求"""
        data = {"card_id": card_id} if card_id is not None else {}
        await self.send(ClientMsg.game_response(self.player_id, request_type, accepted, data))

    async def choose_hero(self, hero_id: str) -> None:
        """选择武将"""
        await self.send(ClientMsg.hero_chosen(self.player_id, hero_id))

    async def chat(self, message: str) -> None:
        """发送聊天"""
        await self.send(ClientMsg.chat(self.player_id, message))


# ==================== CLI 客户端 ====================


async def cli_client_main(server_url: str, player_name: str):
    """简化的命令行客户端"""
    client = GameClient(server_url)
    client.player_name = player_name

    # 注册回调
    cli_log = logging.getLogger("sanguosha.cli")

    def on_room_created(msg: ServerMsg):
        client.room_id = msg.data.get("room_id", "")
        cli_log.info("✓ 房间已创建: %s", client.room_id)

    def on_room_joined(msg: ServerMsg):
        client.room_id = msg.data.get("room_id", "")
        client.player_id = msg.data.get("player_id", 0)
        cli_log.info("✓ 已加入房间 %s, 你的 ID: %s", client.room_id, client.player_id)

    def on_room_update(msg: ServerMsg):
        players = msg.data.get("players", [])
        state = msg.data.get("state", "")
        cli_log.info("房间状态: %s, 玩家: %s", state, [p["name"] for p in players])

    def on_game_event(msg: ServerMsg):
        event_type = msg.data.get("event_type", "")
        cli_log.info("[事件] %s: %s", event_type, msg.data)

    def on_game_over(msg: ServerMsg):
        cli_log.info("游戏结束! 胜者: %s", msg.data.get("winner"))

    def on_chat(msg: ServerMsg):
        cli_log.info("💬 %s: %s", msg.data.get("player_name"), msg.data.get("message"))

    def on_error(msg: ServerMsg):
        cli_log.error("❌ 错误: %s", msg.data.get("message"))

    client.on(MsgType.ROOM_CREATED, on_room_created)
    client.on(MsgType.ROOM_JOINED, on_room_joined)
    client.on(MsgType.ROOM_UPDATE, on_room_update)
    client.on(MsgType.GAME_EVENT, on_game_event)
    client.on(MsgType.GAME_OVER, on_game_over)
    client.on(MsgType.CHAT_BROADCAST, on_chat)
    client.on(MsgType.ERROR, on_error)

    await client.run()


def main():
    """命令行客户端入口"""
    import argparse

    parser = argparse.ArgumentParser(description="三国杀客户端")
    parser.add_argument("--server", default="ws://localhost:8765", help="服务端地址")
    parser.add_argument("--name", default="玩家", help="玩家名称")

    args = parser.parse_args()
    asyncio.run(cli_client_main(args.server, args.name))


if __name__ == "__main__":
    main()
