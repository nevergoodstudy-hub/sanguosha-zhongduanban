"""网络消息 Pydantic 校验模型 (Phase 3.3)

为 net/protocol.py 中的 ClientMsg / ServerMsg 提供严格的输入校验。
服务端在 _handle_message 中解析原始 JSON 后，先经 Pydantic 模型校验，
再构造内部 ClientMsg 对象 — 拒绝不合法的字段类型/缺失字段。

设计原则:
  - 校验模型与内部 dataclass 分离 (校验层 vs 业务层)
  - 校验失败抛出 pydantic.ValidationError，由调用方统一处理
  - 使用 model_config = ConfigDict(extra="forbid") 防止未知字段注入
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ====================================================================== #
#  客户端 → 服务端 消息校验模型                                             #
# ====================================================================== #


class ClientMsgModel(BaseModel):
    """客户端消息校验模型"""

    model_config = ConfigDict(extra="forbid")

    type: str
    player_id: int = 0
    timestamp: float = 0.0
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def type_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("消息类型不能为空")
        return v


class RoomCreateData(BaseModel):
    """room_create 消息的 data 校验"""

    model_config = ConfigDict(extra="forbid")

    player_name: str = Field(min_length=1, max_length=20)
    max_players: int = Field(default=4, ge=2, le=8)
    ai_fill: bool = True


class RoomJoinData(BaseModel):
    """room_join 消息的 data 校验"""

    model_config = ConfigDict(extra="forbid")

    player_name: str = Field(min_length=1, max_length=20)
    room_id: str = Field(min_length=1, max_length=36)
    reconnect: bool = False
    last_seq: int = Field(default=0, ge=0)


class RoomReadyData(BaseModel):
    """room_ready 消息的 data 校验"""

    model_config = ConfigDict(extra="forbid")

    ready: bool = True


class GameActionData(BaseModel):
    """game_action 消息的 data 校验"""

    model_config = ConfigDict(extra="ignore")

    action_type: str = Field(min_length=1)


class GameResponseData(BaseModel):
    """game_response 消息的 data 校验"""

    model_config = ConfigDict(extra="ignore")

    request_type: str = Field(min_length=1)
    accepted: bool = False


class HeroChosenData(BaseModel):
    """hero_chosen 消息的 data 校验"""

    model_config = ConfigDict(extra="forbid")

    hero_id: str = Field(min_length=1, max_length=50)


class ChatData(BaseModel):
    """chat 消息的 data 校验"""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=500)


# ====================================================================== #
#  消息类型 → data 校验模型映射                                              #
# ====================================================================== #

# 有专门 data 校验的消息类型；不在此映射中的类型仅校验外层结构
DATA_VALIDATORS: dict[str, type[BaseModel]] = {
    "room_create": RoomCreateData,
    "room_join": RoomJoinData,
    "room_ready": RoomReadyData,
    "game_action": GameActionData,
    "game_response": GameResponseData,
    "hero_chosen": HeroChosenData,
    "chat": ChatData,
}


def validate_client_message(raw_json: str) -> ClientMsgModel:
    """校验原始 JSON 字符串，返回经过校验的 ClientMsgModel。

    流程:
      1. 用 ClientMsgModel.model_validate_json 校验外层结构
      2. 根据 type 字段查找 DATA_VALIDATORS 校验 data 子结构

    Raises:
        pydantic.ValidationError: 校验失败
    """
    msg = ClientMsgModel.model_validate_json(raw_json)
    validator_cls = DATA_VALIDATORS.get(msg.type)
    if validator_cls is not None:
        validator_cls.model_validate(msg.data)
    return msg
