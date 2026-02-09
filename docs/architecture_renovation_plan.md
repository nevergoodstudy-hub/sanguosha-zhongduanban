# 三国杀终端版 — 深度架构焕新方案

> **文档版本**: v1.0  
> **审查日期**: 2026-02-08  
> **审查方法**: 全量代码审读 + 3 轮次联网搜索（Python 架构最佳实践 / Textual TUI 模式 / 游戏引擎设计模式 / 卡牌游戏状态机 / WebSocket 网络架构 / CI/CD 与测试策略 / 数据建模与性能优化）  
> **项目规模**: ~80+ 源文件, ~15K LOC Python, 6 子系统 (game / ui / ai / net / tools / i18n)

---

## 一、现状总评

项目已具备完整的单机/联机三国杀玩法、Textual TUI 界面、WebSocket 联网、AI 三级难度、DSL 技能系统和存档系统。作为个人项目，功能完成度极高。以下审查聚焦于 **可维护性、可扩展性、健壮性** 三个维度。

---

## 二、关键问题清单

### 2.1 引擎单体膨胀 (P0 — 最高优先)

**文件**: `game/engine.py` (~82KB, 2000+ 行)

**问题**:
- 一个类 `GameEngine` 承载了牌堆管理、回合流转、出牌处理、伤害结算、濒死/死亡、装备效果、技能触发、胜负判定等 **全部** 核心逻辑
- 方法间深度耦合：`use_sha()` 内联调用 `_request_shan()` → `_trigger_bagua()` → 判定系统，形成 5-6 层调用链
- 新增卡牌/技能时必须修改 engine.py，违反 **开闭原则 (OCP)**
- 单元测试困难：无法单独测试伤害系统而不初始化整个引擎

**改进方案**: 按职责拆分为以下子模块：
```
game/
├── engine.py          → 瘦身为 ~200 行协调器
├── phase_manager.py   → 回合阶段流转
├── combat_system.py   → 杀/闪/决斗战斗结算
├── damage_system.py   → 伤害/濒死/死亡 (已存在但未解耦)
├── card_resolver.py   → 卡牌使用路由与效果结算
├── equipment_system.py→ 装备效果处理
├── judge_system.py    → 判定系统
└── win_checker.py     → 胜负判定 (已存在)
```
每个子系统通过 `GameContext` 接口访问共享状态，而非直接引用 `GameEngine`。

### 2.2 重复定义与数据不一致 (P0)

| 重复项 | 位置 A | 位置 B | 后果 |
|--------|--------|--------|------|
| `SkillTiming` 枚举 | `game/hero.py:57` | `game/constants.py` | 修改一处忘记另一处 |
| 身份配置 | `constants.py: IdentityConfig` | `engine.py: identity_configs` dict | 数据源二义性 |
| 英姿摸牌逻辑 | `turn_manager.py` | `engine.py: phase_draw()` | 技能效果被应用两次或不一致 |
| 卡牌可用性检查 | `game_controller.py:_check_card_usable()` | `engine.py` 内散落检查 | 规则变更需改两处 |

**改进方案**: 建立 **单一事实来源 (SSOT)** 原则 — 所有枚举、配置仅定义一次，其他地方通过 import 引用。

### 2.3 线程模型风险 (P0)

**现状**: 游戏引擎在 `@work(thread=True)` worker 线程中运行，Textual UI 在 asyncio 主线程。二者通过 `call_from_thread()` 和 `threading.Event` 交互。

**问题**:
- `time.sleep()` 阻塞 worker 线程 (AI 回合延迟) — 应使用 `asyncio.sleep()` 或 Textual 的 `set_timer()`
- `threading.Event` 用于 UI 等待玩家响应 — 如果 UI 线程异常退出，worker 线程会永久阻塞
- 共享状态 (`engine` 对象) 无锁保护：worker 线程写、UI 线程读
- `_pending_response` / `_response_event` 模式缺乏超时和错误恢复

**改进方案**:
1. 引入 `asyncio.Queue` 替代 `threading.Event` 做线程间通信
2. 所有 UI 更新通过消息投递，不直接操作 widget
3. 添加超时机制和取消令牌
4. 考虑将游戏引擎也运行在 asyncio 中（用 `asyncio.to_thread` 处理 CPU 密集部分）

### 2.4 错误处理碎片化 (P1)

- 事件系统 `EventBus` 的 handler 错误用 `print()` 输出：`print(f"Error in event handler: {e}")`
- 多处裸 `except Exception` 吞掉异常
- 网络层 `_send()` 用 `logger.warning` 但不重连
- `skill.py` DSL 执行失败静默回退到 Python handler，无告警上报

**改进方案**: 建立统一错误处理策略：
- 可恢复错误 → 日志 + 用户通知
- 不可恢复错误 → 日志 + 优雅降级或终止
- 所有 `print()` 替换为 `logger` 调用
- 自定义异常层次：`GameError` → `CardError` / `SkillError` / `NetworkError`

### 2.5 类型安全不足 (P1)

- `pyproject.toml` mypy 配置 `python_version = "3.14"` 但项目 `requires-python = ">=3.10"` — 版本不匹配
- 大量 `Any` 类型参数 (`net/server.py` websocket 参数都是 `Any`)
- 卡牌名称在某些位置用字符串字面量而非 `CardName` 枚举
- `game_controller.py:193` 使用 `card.card_type.value == "equipment"` 字符串比较而非枚举比较

**改进方案**:
- mypy target 改为 `3.10`
- 关键接口添加 `@overload` / `Protocol` 类型约束
- WebSocket 对象类型用 `websockets.WebSocketServerProtocol`
- 全面消除字符串字面量比较，统一使用枚举

### 2.6 UI 协议臃肿 (P1)

**文件**: `ui/protocol.py` — `GameUI` Protocol 定义了 ~20 个方法。  
**文件**: `ui/textual_ui/bridge.py` — `TextualUIBridge` 大量 stub 方法。

**问题**:
- 协议过大，新增 UI 实现需要 stub 大量无关方法
- Bridge 混合了"显示信息"和"获取输入"两种职责
- 某些方法如 `choose_card_from_player()` 参数设计不一致

**改进方案**: 拆分为三个小协议：
```python
class GameDisplayProtocol(Protocol):
    """只负责展示"""
    def show_log(self, msg: str) -> None: ...
    def show_game_state(self, engine, player) -> None: ...
    def show_phase(self, phase) -> None: ...

class GameInputProtocol(Protocol):
    """只负责获取玩家输入"""
    def get_player_action(self) -> str: ...
    def choose_target(self, player, targets, prompt) -> Optional[Player]: ...
    def choose_cards(self, player, count, prompt) -> List[Card]: ...

class GameNotifyProtocol(Protocol):
    """异步通知（动画、音效等）"""
    def notify_damage(self, source, target, amount) -> None: ...
    def notify_skill(self, player, skill_name) -> None: ...
```

### 2.7 AI 系统结构性问题 (P1)

**文件**: `ai/bot.py`

**问题**:
- 三种难度共用一个类，通过 `if difficulty == ...` 分支 — 应使用策略模式
- 身份推测 (`identity_guess`) 仅声明未实现
- 嘲讽值系统 (`threat_values`) 仅困难模式使用，但数据结构在所有实例上分配
- `_is_enemy()` 判断逻辑对不同身份的处理不完善
- 硬编码动作上限 `max_actions = 10`

**改进方案**:
```python
class AIStrategy(Protocol):
    def play_phase(self, player, engine) -> None: ...
    def choose_discard(self, player, count, engine) -> List[Card]: ...

class EasyStrategy(AIStrategy): ...
class NormalStrategy(AIStrategy): ...
class HardStrategy(AIStrategy):
    threat_evaluator: ThreatEvaluator
    identity_predictor: IdentityPredictor
```

### 2.8 技能系统可维护性 (P2)

**文件**: `game/skill.py` — 30+ 个 `_handle_xxx` 方法在单文件中。

**问题**:
- 单文件 30+ 个处理器方法，超过 1000 行
- DSL 与 Python fallback 的优先级关系不透明
- 新武将技能需要同时修改 `skill.py`（处理器）+ `data/skill_dsl.json`（DSL）+ `constants.py`（SkillId 枚举）

**改进方案**:
- 按势力拆分技能处理器：`skills/shu.py`, `skills/wei.py`, `skills/wu.py`, `skills/qun.py`
- 引入装饰器注册机制替代手动字典维护
- DSL 能力提升后逐步替换 Python handler

### 2.9 网络安全 (P2)

**文件**: `net/server.py`, `net/protocol.py`

**问题**:
- 无身份认证：任何人可连接并发送消息
- 玩家名称无过滤（XSS/注入风险）
- `_assign_player_id()` 使用递增整数 — 可预测
- 速率限制仅按消息数，不按类型区分
- 无 TLS/WSS 支持

**改进方案**:
- 添加 token-based 认证（连接握手阶段验证）
- 输入消息验证与清洗
- player_id 使用 UUID
- 按消息类型设置差异化速率限制
- 文档中注明生产环境需反向代理 + TLS

### 2.10 测试覆盖不足 (P2)

**现状**: 覆盖率阈值 50%，仅有基础单元测试。

**缺失**:
- 无集成测试（完整游戏流程）
- 无 UI 测试（Textual 提供 `pilot` 测试工具）
- 无网络层测试
- 无 AI 决策质量测试
- 无并发/线程安全测试

**改进方案**:
- 提升覆盖率目标至 75%
- 添加 Textual `pilot` 自动化 UI 测试
- 添加游戏引擎状态机集成测试
- 添加网络协议 mock 测试
- 引入 `hypothesis` 做基于属性的测试（随机牌序/技能组合）

---

## 三、架构焕新总方案

### 3.1 目标架构 — 分层清洁架构

```
┌────────────────────────────────────────────────────┐
│                  Presentation Layer                  │
│  Textual TUI / Console UI / Web UI (future)        │
│  通过 Protocol 接口与下层通信                         │
├────────────────────────────────────────────────────┤
│                  Application Layer                   │
│  GameController (回合编排)                            │
│  RequestHandler (玩家交互路由)                        │
│  EventBus (事件分发)                                 │
├────────────────────────────────────────────────────┤
│                   Domain Layer                       │
│  GameEngine (薄协调器)                               │
│  CombatSystem / DamageSystem / JudgeSystem          │
│  SkillSystem / EquipmentSystem / CardResolver       │
│  PhaseManager / WinChecker                          │
├────────────────────────────────────────────────────┤
│                Infrastructure Layer                  │
│  Deck (牌堆) / SaveSystem / NetworkServer           │
│  Logging / i18n / Config                            │
└────────────────────────────────────────────────────┘
```

### 3.2 核心数据建模优化

**现状**: Player / Card / Hero 使用 dataclass，但部分字段使用 `getattr(obj, attr, default)` 访问，说明字段定义不完整。

**方案**:
- 内部游戏状态统一使用 Python `@dataclass(slots=True)` — 比 Pydantic 快 5-15x（见 benchmarks），且标准库无额外依赖
- 网络边界/存档边界使用 Pydantic `BaseModel` 做数据校验
- 引入 `GameState` 不可变快照类用于 UI 渲染和存档
- 消除所有 `getattr` 防御性访问，补全字段定义

### 3.3 线程与并发模型重构

```
[Textual asyncio 主线程]
    ├── UI 渲染 & 事件处理
    ├── 通过 asyncio.Queue 接收 GameEvent
    └── 通过 asyncio.Queue 发送 PlayerAction

[Game Worker 线程]
    ├── 游戏主循环
    ├── 通过 Queue 发送 GameEvent (state changes)
    └── 通过 Queue 接收 PlayerAction (阻塞等待)
```

取消 `threading.Event` + `_pending_response` 模式，改用类型安全的消息队列。

### 3.4 事件系统增强

**现状**: `EventBus` 支持优先级和语义事件类型，但错误处理用 `print()`。

**方案**:
- 错误处理改为 `logger.exception()`
- 添加事件类型枚举约束（防止拼写错误）
- 添加事件历史环形缓冲区（用于调试和回放）
- 支持异步事件处理器

### 3.5 配置中心化

**现状**: `AI_TURN_DELAY`, `PLAY_PHASE_TIMEOUT`, 各种魔法数字散布各处。

**方案**: 创建 `game/config.py`:
```python
@dataclass(frozen=True)
class GameConfig:
    ai_turn_delay: float = 0.5
    play_phase_timeout: int = 30
    max_players: int = 8
    default_draw_count: int = 2
    coverage_threshold: float = 0.75
    ...

# 支持从环境变量 / config.toml 覆盖
config = GameConfig.from_env()
```

### 3.6 国际化完善

**现状**: `i18n/` 目录存在但大量中文字符串硬编码在代码中。

**方案**:
- 所有面向用户的字符串提取到 `i18n/zh_CN.json` / `i18n/en_US.json`
- 使用 `_("key")` 函数做翻译查找
- 卡牌名、技能名、身份名从数据文件而非代码常量获取
- 日志消息保持英文（面向开发者）

### 3.7 CI/CD 与质量门禁

**当前有**: ruff (lint), pytest, coverage 50%。  
**建议添加**:

```yaml
# .github/workflows/ci.yml
jobs:
  quality:
    steps:
      - ruff check .                    # 已有
      - ruff format --check .           # 格式检查
      - mypy --python-version 3.10 .    # 类型检查 (修正版本)
      - pytest --cov --cov-fail-under=75
      - python -m textual pilot tests/  # UI 测试 (新增)
  
  security:
    steps:
      - pip-audit                       # 依赖漏洞扫描
      - bandit -r game/ ai/ net/       # 安全静态分析
```

### 3.8 文档补全

**建议添加**:
- `docs/architecture.md` — 系统架构图与模块职责说明
- `docs/game_rules.md` — 实现的三国杀规则说明
- `docs/skill_dsl.md` — DSL 语法参考
- `docs/network_protocol.md` — WebSocket 消息协议规范
- `docs/contributing.md` — 贡献指南
- 各模块入口文件的 docstring 补全

---

## 四、实施路线图

### Phase 1: 基础设施加固 (1-2 周)

1. ✅ **[已完成]** 修复 mypy 配置 (`python_version = "3.10"`) — pyproject.toml 中已配置正确
2. ✅ **[已完成]** 消除所有 `print()` → `logger` 替换 — EventBus 和 GameController 已修复
3. ✅ **[已完成]** 消除重复定义（SkillTiming、身份配置等），建立SSOT — 已合并到 constants.py
4. ✅ **[已完成]** 创建 `game/config.py` 集中配置 — 支持环境变量覆盖
5. ✅ **[已完成]** 修复线程安全问题（`threading.Event` → `asyncio.Queue`）— game_play.py 已重构为 asyncio.Queue + run_coroutine_threadsafe
6. ✅ **[已完成]** 修复字符串比较为枚举比较 — target_modal.py identity.value=="lord" → Identity.LORD
7. ✅ **[已完成]** 建立 GitHub Actions CI pipeline — 修正 Python 版本为 3.10，添加 ruff format 检查、pip-audit、bandit 安全扫描

### Phase 2: 引擎分解 (2-3 周)

1. ✅ **[已完成]** 定义 `GameContext` 协议接口 — game/context.py, 包含玩家查询/距离/牌堆/伤害/事件/请求路由最小接口, GameEngine 结构子类型化验证通过
2. ✅ **[已完成]** 提取 `CombatSystem` (杀/闪/决斗) — game/combat.py, 包含 use_sha/request_shan/request_sha/use_juedou/request_wuxie/装备触发, engine.py 对应方法委托给 self.combat; 修复 skill.py 中 damage_system 引用错误和 test_kurou_low_hp 测试
3. ✅ **[已完成]** 提取 `EquipmentSystem` (装备效果) — game/equipment_system.py, 包含 equip/remove/modify_damage/is_immune_to_normal_aoe; engine.py 委托 _use_equipment/_remove_equipment/deal_damage护甲修正/藤甲AOE免疫; 同时修复 _use_juedou/_use_juedou_forced 未委托问题
4. ✅ **[已完成]** 提取 `JudgeSystem` (判定) — game/judge_system.py, 包含 phase_judge/乐不思蜀/兵粮寸断/闪电结算; engine.py 委托 phase_judge; 扩展 GameContext 协议添加 _request_wuxie
5. ✅ **[已完成]** 提取 `CardResolver` (卡牌效果路由) — game/card_resolver.py, 包含 use_tao/use_jiu/use_nanman/use_wanjian/use_taoyuan/use_wuzhong/use_guohe/use_shunshou/use_jiedao/use_huogong/use_lebusishu/use_bingliang/use_shandian/use_tiesuo/choose_and_discard_card/choose_and_steal_card; engine.py 所有 _use_xxx 方法委托给 self.card_resolver
6. ✅ **[已完成]** 提取 `PhaseManager` (增强现有 turn_manager) — TurnManager 成为阶段逻辑唯一权威; engine.py 的 phase_prepare/phase_judge/phase_draw/phase_play/phase_discard/phase_end 全部委托给 turn_manager; TurnManager._execute_judge_phase 直接调用 judge_sys 消除循环回调
7. ✅ **[已完成]** `GameEngine` 瘦身为组合协调器 — engine.py 从 2132 行缩减至 ~1233 行 (~42%); 模块文档更新为 Facade/协调器角色; 所有卡牌效果/阶段逻辑/战斗/装备/判定均已委托给对应子系统
8. ✅ **[已完成]** 每个子系统配套独立单元测试 — tests/test_subsystems.py, 38 个测试覆盖 CombatSystem/EquipmentSystem/JudgeSystem/CardResolver 功能测试 + Engine 委托集成测试; 全套 706 测试通过

### Phase 3: 接口与类型 (1-2 周)

1. ✅ **[已完成]** 拆分 `GameUI` Protocol 为 Display / Input / Notify 三协议 — ui/protocol.py 拆分为 GameDisplay(纯展示)/GameInput(交互输入)/GameNotify(生命周期通知) 三个子协议; GameUI 作为组合协议向后兼容; 6个新测试通过; 709 测试全通过
2. ✅ **[已完成]** WebSocket 对象类型标注 — net/server.py: websocket: Any → ServerConnection (websockets v16 asyncio API); ws_to_player/handlers 字典类型精确化; net/client.py: _ws: Any → Optional[ClientConnection]; TYPE_CHECKING 导入避免运行时依赖; 80 个网络测试全通过
3. ✅ **[已完成]** 网络消息添加 Pydantic 校验 — net/models.py: ClientMsgModel + 7个 data 子模型 (RoomCreate/RoomJoin/RoomReady/GameAction/GameResponse/HeroChosen/Chat); validate_client_message() 两层校验 (外层结构 + data 子结构); 服务端 _handle_message 集成校验; ConfigDict(extra="forbid") 防注入; 21 个新测试全通过
4. ✅ **[已完成]** `@dataclass(slots=True)` 优化关键数据类 — Card/GameEvent/DamageEvent/DamageResult/GameOverInfo/CardHandlerInfo/GameLogEntry 7个高频实例化数据类添加 slots=True; GameConfig 已有 frozen=True; 跳过有继承关系的 GameAction 子类; 730 测试全通过
5. ✅ **[已完成]** 消除所有 `Any` 类型（除确实需要的泛型场景） — card.py: game_engine: Any → GameEngine (TYPE_CHECKING); server.py: engine: Any → Optional[GameEngine], handler 返回类型 Any → Awaitable[None]; skill.py: event_bus/event 参数类型标注, _skill_handlers Callable[..., bool]; actions.py: option: Any → Optional[Union[str,int,bool,List[int]]]; exceptions.py/client.py: 移除未使用的 Any 导入; Dict[str, Any] 保留用于 JSON/DSL/事件数据等正当泛型场景; 730 测试全通过

### Phase 4: 子系统优化 (2-3 周)

1. ✅ **[已完成]** AI 策略模式重构 — AIStrategy Protocol + EasyStrategy/NormalStrategy/HardStrategy 三策略实现; ThreatEvaluator 和 IdentityPredictor 拆分为独立组件; AIBot 瘦身为薄协调器委托给策略; 消除 if difficulty 分支; max_actions 改为 config 读取; 730 测试全通过
2. ✅ **[已完成]** 技能系统按势力拆分 — 创建 game/skills/ 包，拆分为 shu.py(13个)/wei.py(9个)/wu.py(11个)/qun.py(5个) 四个势力模块; 处理器从方法转为独立函数; SkillSystem.__init__ 通过 get_all_skill_handlers() 加载; __getattr__ 提供 _handle_xxx 向后兼容; skill.py 从 ~1186 行缩减至 ~352 行; 730 测试全通过
3. ✅ **[已完成]** 技能注册装饰器机制 — 创建 game/skills/registry.py 实现 @skill_handler("id") 装饰器自动注册; 四个势力模块 38 个 handler 全部迁移为装饰器注册; __init__.py 优先读取装饰器注册表并保留字典回退兼容; 6 个新测试覆盖注册表完整性/可调用性/副本安全/装饰器透明性/引擎集成; 737 测试全通过
4. ✅ **[已完成]** 网络安全加固 — net/security.py (ConnectionTokenManager + IPConnectionTracker + sanitize_chat_message); game/config.py 添加 6 项安全配置; server.py 集成 token 认证/连接限额/心跳超时/消息体积限制/聊天消毒; client.py 存储并回传 token; 17 个安全测试; 754 测试全通过
5. ✅ **[已完成]** 国际化字符串提取 — damage_system/combat/card_resolver/equipment_system/judge_system/turn_manager/engine/skill.py/skills/*.py/actions.py/win_checker.py/effects/*.py/skill_interpreter.py/net/server.py 全部面向用户字符串提取至 i18n JSON; ~190 个 i18n 键覆盖 zh_CN 和 en_US; skill.* 短名键与 skill_msg.* 日志键正确分离; 1159 测试全通过
6. ✅ **[已完成]** 测试覆盖率提升至 75% — 从 73% 提升至 75.35%; 新增 92 个针对性测试覆盖 win_checker 辅助函数/turn_manager 辅助函数/damage_system 死亡与奖惩/skills/wei.py 处理器/ai/strategy.py 工具函数/actions.py 验证器; 1251 测试通过

### Phase 5: 高级特性 (可选, 3-4 周)

1. ✅ **[已完成]** Textual `pilot` UI 自动化测试 — tests/test_pilot_ui.py, 29 个 pilot 测试覆盖 GameScreen 渲染/玩家面板/手牌展示/操作按钮/游戏日志/阶段显示/装备区域等 UI 组件; async with app.run_test() 模式
2. ✅ **[已完成]** `hypothesis` 属性测试 — tests/property/ 目录, 52 个属性测试覆盖 Card 不变量/Deck 洗牌守恒/Player 生命值边界/DamageSystem 属性/GameEvent 序列化往返/ActionValidator 一致性; @given + @settings 配置
3. ✅ **[已完成]** 游戏回放系统完善 — tools/replay.py ReplayTool 类, 支持 record/load/step/goto/rewind/info 命令; JSON 文件持久化; tests/test_replay_cli.py 6 个测试
4. ⏭️ **[跳过]** 性能 profiling 与优化 — 当前规模下无性能瓶颈, 留待后续按需执行
5. ✅ **[已完成]** Docker 化部署方案 — Dockerfile 多阶段构建 (builder+runtime), 非 root 用户, healthcheck; docker-compose.yml 服务编排含环境变量/日志卷/存档卷; .dockerignore 排除测试/文档/IDE 文件
6. ✅ **[已完成]** WebSocket TLS 支持文档 — docs/tls_setup.md, Nginx 反向代理 WSS 配置, Let's Encrypt 证书自动化, Docker Compose 集成, 安全建议 (HSTS/OCSP/TLS1.2+)

---

## 五、文件级问题明细

### game/engine.py
- **行 800-860**: `use_sha()` 内联处理朱雀羽扇/仁王盾/藤甲/酒/古锭刀效果 → 应委托给 `EquipmentSystem`
- **行 864-944**: `_request_shan()` / `_request_sha()` 内联处理龙胆/武圣技能 → 应委托给 `SkillSystem`
- **行 946-1000**: `_request_wuxie()` 座位顺序询问逻辑 → 可提取为独立响应链处理器

### game/game_controller.py
- **行 193**: `card.card_type.value == "equipment"` — 应为 `card.card_type == CardType.EQUIPMENT`
- **行 277-292**: `time.sleep(AI_TURN_DELAY)` 阻塞线程 — 应异步化
- **行 325-330**: `print()` 直接输出到控制台而非通过 UI 协议 — 在 TUI 模式下会破坏界面
- **行 368-396**: 卡牌可用性检查逻辑与 engine 内重复

### game/hero.py
- **行 57-73**: `SkillTiming` 枚举与 `constants.py` 重复
- **行 101-102**: `used_count` 运行时状态混入数据模型 — 应分离为 `SkillState`

### game/skill.py
- **行 49-93**: 30+ 个处理器映射在 `__init__` 中硬编码 — 应使用注册表模式
- **行 183-184**: DSL 执行失败仅 `logger.warning` — 应统计失败率和上报

### game/save_system.py
- **行 96-101**: `serialize_card()` 中 `card.name if isinstance(card.name, str) else card.name.value` — 类型判断表明字段类型不一致
- **行 125-127**: `getattr(player, "sha_used", 0)` — 字段应在 Player 类中明确定义

### ui/textual_ui/screens/game_play.py
- **行 100-101**: `_pending_response` + `_response_event` — 线程安全风险
- **行 108**: `self.app._engine` — 访问私有属性，应改为公开接口

### ai/bot.py
- **行 48-51**: `threat_values` 和 `identity_guess` 在所有难度实例上分配但仅困难模式使用
- **行 112**: `max_actions = 10` 硬编码 — 应从配置读取

### net/server.py
- **行 34**: `websocket: Any` — 应为具体 WebSocket 类型
- **行 109**: `_next_player_id: int = 1` — 可预测的递增 ID，安全性低
- **行 147**: `f"玩家 {pid} 已连接"` — 日志中文硬编码

### logging_config.py
- 设计良好，支持环境变量覆盖、日志轮转、幂等初始化
- **建议**: 添加 structured logging (JSON 格式) 选项，便于日志分析

### pyproject.toml
- `mypy: python_version = "3.14"` → 应改为 `"3.10"`
- 建议添加 `[tool.ruff.format]` 配置确保代码格式一致
- 建议添加 `pre-commit` hooks 配置

---

## 六、总结

本项目功能完备，架构上最大的技术债务是 **engine.py 单体** 和 **线程安全** 问题。按照上述路线图渐进式重构，可在不中断功能开发的前提下，显著提升代码的可维护性和可靠性。建议优先执行 Phase 1 和 Phase 2，这两个阶段的投入产出比最高。
