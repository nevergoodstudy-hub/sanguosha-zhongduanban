# 三国杀 - 模块架构设计文档

## 概览

本文档描述 `codex/deep-refactor` 之后的当前代码结构，重点同步以下变化：

- `main.py` 仍是唯一运行入口，但本地模式、服务端模式、客户端模式已经明显分层
- 网络层不再把大部分逻辑都堆在 `net/server.py` / `net/client.py`
- 服务端消息路由、会话生命周期、动作编解码、配置校验都已经拆分到独立模块
- 构建与发布也从“脚本 + 手工说明”升级为“脚本 + GitHub Actions 工作流 + 文档”三件套

如需英文版总览，可参考根目录 [ARCHITECTURE.md](../ARCHITECTURE.md)。

## 入口与运行模式

运行入口统一收敛在 `main.py`：

| 模式 | 命令 | 主要入口 |
|---|---|---|
| 本地单机 / AI 对战 | `python main.py` | `game.game_controller.GameController` |
| 服务端 | `python main.py --server [HOST:PORT]` | `net.settings.ServerSettings` -> `net.server.GameServer` |
| 客户端 | `python main.py --connect HOST:PORT` | `net.settings.ClientSettings` -> `net.client.GameClient` |
| 回放 | `python main.py --replay FILE` | 回放逻辑入口 |

另外，`main.SanguoshaGame` 现在只是一个 legacy 兼容别名，实际推荐入口已经变为 `game.game_controller.GameController`。

## 当前分层结构

```text
main.py
├─ 本地模式
│  └─ game.game_controller.GameController
│     └─ game.engine.GameEngine
│        ├─ game.turn_manager.TurnManager
│        ├─ game.combat.CombatSystem
│        ├─ game.card_resolver.CardResolver
│        ├─ game.equipment_system.EquipmentSystem
│        ├─ game.judge_system.JudgeSystem
│        ├─ game.skill.SkillSystem
│        └─ game.events.EventBus
├─ 服务端模式
│  └─ net.settings.ServerSettings
│     └─ net.server.GameServer
│        ├─ net.server_dispatcher.ServerMessageDispatcher
│        ├─ net.server_session.ServerSessionManager
│        ├─ net.server_types.Room / ConnectedPlayer / PendingGameRequest
│        ├─ net.action_codec / net.request_codec
│        └─ game.engine.GameEngine (每个房间一个无界面引擎)
└─ 客户端模式
   └─ net.settings.ClientSettings
      └─ net.client.GameClient
         └─ net.client_session.ClientSession
```

## 本地游戏核心层

`game/` 依然是规则和回合系统的核心。

### 主要职责

- `game/game_controller.py`
  - 本地流程总控
  - 避免 `main.py` 直接依赖过多细节
- `game/engine.py`
  - 核心引擎协调器
  - 组织阶段推进、请求处理、日志、胜负判定
- `game/turn_manager.py`
  - 管理准备/判定/摸牌/出牌/弃牌/结束的阶段推进
- `game/combat.py`
  - 处理 `杀`、`闪`、`决斗`、伤害等战斗链路
- `game/card_resolver.py`
  - 解析锦囊和非战斗牌效
- `game/equipment_system.py`
  - 装备牌的装备、卸下和效果应用
- `game/judge_system.py`
  - 判定区与延时锦囊结算
- `game/skill.py`
  - 武将技能执行与触发
- `game/events.py`
  - 事件总线与事件类型定义
- `game/phase_fsm.py`
  - 阶段切换合法性约束

### AI 层

- `ai/bot.py`
  - AI 协调器
- `ai/easy_strategy.py`
  - 低复杂度决策
- `ai/normal_strategy.py`
  - 规则型决策
- `ai/hard_strategy.py`
  - 高优先级战术与局势评估

## 网络层：重构后的拆分方式

本次深度重构里，变化最大的就是 `net/`。

### 1. 服务端运行时

- `net/server.py`
  - 负责 WebSocket 服务生命周期
  - 持有房间表、连接表、广播辅助函数、房间引擎启动
  - 不再独占所有消息处理和重连逻辑
- `net/server_dispatcher.py`
  - 负责客户端消息分发
  - 处理建房、入房、离房、准备、开局、聊天、响应、心跳
  - 在真正执行业务逻辑前完成格式校验、速率限制、路由
- `net/server_session.py`
  - 负责房间成员清理和断线重连回放
  - 根据房间事件序号回放遗漏消息
- `net/server_types.py`
  - 放置 `Room`、`ConnectedPlayer`、`PendingGameRequest` 等轻量数据结构

### 2. 客户端运行时

- `net/client.py`
  - `GameClient` 作为高层协议门面
  - 对外暴露 `create_room()`、`join_room()`、`play_card()`、`use_skill()`、`respond()` 等接口
  - 负责服务器消息分发、客户端本地状态、CLI 客户端入口
- `net/client_session.py`
  - 专注底层会话生命周期
  - 包括连接、断开、接收循环、心跳循环、自动重连
  - 使 `GameClient` 不必再同时承担“协议门面 + 传输重试器”双重职责

### 3. 编解码与配置层

- `net/action_codec.py`
  - 把网络层 JSON 动作转换成领域层 `GameAction`
  - 当前支持 `play_card`、`use_skill`、`discard`、`end_turn`
- `net/request_codec.py`
  - 把领域层 `GameRequest` / `GameResponse` 映射到网络消息
- `net/settings.py`
  - 用 Pydantic 模型统一校验 `ServerSettings` / `ClientSettings`
  - 让 `host`、`port`、TLS 成对配置、重连参数、URL scheme 在启动时就被验证

### 4. `net/session.py` 的当前定位

`net/session.py` 仍然保留了通用会话工具，但它已经不是当前服务端断线重连主路径。

当前 live reconnect 主路径是：

```text
GameServer -> ServerSessionManager
```

而不是旧文档中暗示的：

```text
GameServer -> session.py
```

## 当前关键数据流

### 本地模式

```text
玩家输入 / TUI 操作
  -> GameController
  -> GameEngine.execute_action()
  -> EventBus.publish(...)
  -> 技能系统 / 战斗系统 / UI 更新 / AI 响应
```

### 客户端动作 -> 服务端 -> 引擎

```text
GameClient
  -> ClientMsg
  -> WebSocket
  -> ServerMessageDispatcher
  -> action_codec.decode_client_action()
  -> GameAction
  -> GameEngine
```

### 引擎请求 -> 客户端响应

```text
GameEngine 发出 GameRequest
  -> request_codec.encode_game_request()
  -> ServerMsg.game_request(...)
  -> 客户端展示交互
  -> ClientMsg.game_response(...)
  -> request_codec.decode_game_response()
  -> GameResponse
  -> 服务端完成等待中的请求 future
```

### 断线重连

```text
断线
  -> 房间保留按 seq 记录的事件日志
  -> 客户端带 token + last_seq 重连
  -> ServerSessionManager.reconnect_player()
  -> 回放 seq > last_seq 的遗漏事件
```

## 构建与发布层

除了运行时架构，本次重构还补齐了“构建 -> 校验 -> 发布”链路。

### 本地构建脚本

- `build.py`
  - 统一管理 PyInstaller onefile / onedir 构建
  - 新增输出文件名与目标路径辅助逻辑
- `build_msix.py`
  - 本地 Windows MSIX 打包验证入口

### GitHub Actions

- `.github/workflows/ci.yml`
  - `ruff check`
  - `ruff format --check`
  - `mypy`
  - 三平台 `pytest`
  - coverage / junit 工件上传
  - `pip-audit` + `bandit`
  - `python -m build`
- `.github/workflows/release.yml`
  - 用 tag `v*.*.*` 触发正式发布
  - 三平台生成 PyInstaller 资产
  - Windows 打成 zip，Linux / macOS 打成 tar.gz 以保留可执行权限
  - 使用 `gh release create` / `gh release upload` 发布 Release

### 发布文档

- `docs/release-process.md`
  - 说明 tag 驱动发布规则、资产命名、手动校验模式和常见问题

## 目录与数据文件

```text
ai/            AI 决策层
data/          卡牌 / 武将 / 技能 DSL 数据
docs/          中文设计与发布文档
game/          核心规则与子系统
i18n/          国际化资源
net/           联机协议、服务端、客户端、会话与编解码
tests/         单元测试与集成测试
tools/         回放与辅助工具
ui/            Textual TUI 与界面适配

ARCHITECTURE.md        英文同步总览
build.py               PyInstaller 构建脚本
build_msix.py          Windows MSIX 打包脚本
main.py                统一入口
versioning.py          版本号派生逻辑
```

`data/` 目前仍包含卡牌、武将、技能 DSL 等核心资源，是运行时与打包产物必须带上的静态文件集合。

## 当前设计原则

- UI 通过协议与引擎隔离，不直接吞掉所有规则细节
- 服务端的“消息分发”和“会话生命周期”已分开治理
- 客户端的“高层 API”和“底层传输循环”已分开治理
- 网络负载和领域动作之间增加显式编解码边界
- 启动参数优先在配置模型层失败，而不是跑到运行时才出错

## 当前仍需关注的点

1. `GameEngine` 仍然偏大，后续还可以继续按“阶段推进 / 请求协商 / 胜负判定”拆分
2. 文档维护现在分为中英文两份，后续改架构时应同步更新 `ARCHITECTURE.md` 与本文档
3. 若服务端重连策略继续扩展，应该优先增强 `ServerSessionManager`，而不是把逻辑重新塞回 `server.py`
