# 三国杀项目代码审查与改进建议报告

## 1. 总体评价

项目已经实现了一个功能完整的命令行版三国杀游戏，包含了核心的游戏流程（回合制、阶段流转）、卡牌系统（基本牌、锦囊、装备）、武将系统和AI对抗。代码结构清晰，使用了 Python 的 Type Hints 进行类型标注，具备良好的可读性。

然而，随着项目规模的扩大（如增加更多武将和技能），当前的架构可能会面临扩展性瓶颈。主要问题在于**高耦合度**和**硬编码的业务逻辑**。

## 2. 核心问题分析

### 2.1 架构耦合 (God Class Anti-pattern)
- **GameEngine 职责过重**：`GameEngine` 类集成了游戏流程控制、规则裁决、卡牌效果处理、伤害结算甚至部分 UI 交互逻辑。这使得该类变得非常庞大且难以维护。
- **UI 与 逻辑混杂**：虽然有 `TerminalUI` 类，但 `GameEngine` 中仍大量存在 `self.ui.show_xxx` 或 `print` 调用。这意味着如果未来想开发 GUI 版本（如 PyGame 或 PyQt）或网络联机版，需要重写大量核心逻辑。

### 2.2 技能系统扩展性不足
- **硬编码逻辑**：`SkillSystem` 使用字典映射 (`_skill_handlers`) 和大量的 `if-else` 逻辑来处理技能。每增加一个新技能，都需要修改 `SkillSystem` 类，违反了**开闭原则 (OCP)**。
- **缺乏统一的时机/事件机制**：目前的技能触发是在 `engine` 的各个阶段方法中手动调用的（如 `phase_prepare` 中调用 `trigger_skill`）。如果技能需要在特殊时机触发（如"造成伤害时"、"判定前"），需要在引擎的深层逻辑中到处打补丁。

### 2.3 AI 系统局限
- **过程化决策**：目前的 AI (`AIBot`) 主要是基于规则的 `if-else` 判断。虽然有简单的"嘲讽值"系统，但缺乏对局势的整体评估。
- **作弊式交互**：AI 直接调用 `engine` 的方法进行操作，而不是像玩家一样通过统一的"命令"或"动作"接口。

## 3. 具体的改进建议

### 3.1 架构重构：引入事件总线 (Event Bus)

**建议**：引入观察者模式或事件总线机制，解耦核心模块。

- **实现方式**：
  - 创建一个 `EventManager`。
  - 游戏中的任何动作（出牌、造成伤害、回合开始）都作为一个 `Event` 发布。
  - 技能系统注册监听特定的 `Event`。
  - UI 系统监听状态变化 `Event` 进行界面更新。

```python
# 伪代码示例
class EventType(Enum):
    DAMAGE_CAUSED = "damage_caused"
    CARD_USED = "card_used"

class GameEngine:
    def deal_damage(self, source, target, amount):
        # 核心逻辑只负责修改数据
        target.hp -= amount
        # 发布事件
        self.event_bus.publish(EventType.DAMAGE_CAUSED, source=source, target=target, amount=amount)
```

### 3.2 技能系统重构：数据驱动与效果原子化

**建议**：将技能拆分为"触发时机 (Trigger)"、"消耗 (Cost)" 和 "效果 (Effect)" 的组合，尽量实现数据驱动。

- **原子化效果**：将复杂的技能逻辑拆解为基础原子操作，如 `DrawCard`, `DiscardCard`, `ModifyDamage`, `ConvertCard`。
- **配置化**：简单的技能可以直接在 JSON 中定义，而不需要写 Python 代码。

```json
{
  "id": "yingzi",
  "type": "trigger",
  "trigger": "phase_draw_start",
  "effect": {
    "type": "draw_card",
    "amount": 1
  }
}
```

### 3.3 UI/逻辑完全分离 (MVC/MVP 模式)

**建议**：`GameEngine` 不应持有 `UI` 的引用，也不应产生任何控制台输出。

- **交互接口**：设计一个 `Action` 层。玩家的操作被封装为 `PlayCardAction`, `UseSkillAction` 等对象传递给引擎。
- **回调/请求机制**：当引擎需要玩家输入（如"请出闪"）时，应抛出一个 `Request` 事件，挂起当前协程或状态机，等待 UI 层返回 `Response`。

### 3.4 AI 优化

- **状态评估函数**：为 AI 设计一个评分函数（Value Function），评估当前场面优势（手牌数、血量、装备价值）。
- **行为树 (Behavior Tree)**：使用行为树替代复杂的嵌套 `if-else`，使 AI 逻辑更清晰，易于调试和扩展。

## 4. 代码质量与工程化建议

### 4.1 单元测试
- 目前测试覆盖率较低。建议为核心规则（如伤害结算、距离计算）编写详细的 `pytest` 单元测试。
- 模拟各种复杂的结算场景（如连环、多重技能结算）。

### 4.2 类型安全与 Lint
- 使用 `mypy` 进行严格的静态类型检查，减少运行时错误。
- 引入 `pylint` 或 `flake8` 规范代码风格。

### 4.3 异常处理与安全性
- **输入验证**：在 `GameEngine` 处理任何 `Action` 之前，必须进行严格的合法性校验（如：是否轮到该玩家、手牌是否存在、目标是否合法）。这不仅是为了防止 Bug，也是为了防止未来可能的联机作弊。

## 5. 执行路线图

1.  ✅ **阶段一（基础重构）**：剥离 `GameEngine` 中的 `print` 语句，改为日志/事件系统。
2.  ✅ **阶段二（事件驱动）**：实现简单的事件总线，重构 `SkillSystem` 以监听事件而非硬编码调用。
3.  ✅ **阶段三（接口标准化）**：定义标准化的 `Action` 和 `Request` 接口，实现 UI 与逻辑的彻底解耦。
4.  🔄 **阶段四（AI升级）**：基于新的接口重写 AI 逻辑。（进行中）

---

## 6. 已完成的改进 (v1.1.0)

### 6.1 新增事件总线系统 (`game/events.py`)
- `EventBus`: 事件发布/订阅中心
- `EventType`: 40+ 种游戏事件类型枚举
- `GameEvent`: 事件数据载体，支持取消和修改
- `EventEmitter`: 混入类，方便其他模块发布事件

### 6.2 新增动作/请求系统 (`game/actions.py`)
- `GameAction`: 玩家操作基类
- `PlayCardAction`, `UseSkillAction`, `DiscardAction` 等具体动作
- `GameRequest` / `GameResponse`: 引擎与 UI 的标准化交互接口
- `ActionValidator`: 集中式动作合法性校验
- `ActionExecutor`: 动作执行器

### 6.3 GameEngine 重构
- 集成 `EventBus` 作为核心解耦组件
- `log_event` 方法现在同时发布事件到事件总线
- 保持向后兼容，旧的 UI 调用方式仍然有效

### 6.4 新增测试
- `tests/test_events.py`: 事件系统单元测试

---

**总结**：项目基础良好，但为了支持长期的功能扩展和可能的联机需求，建议尽快进行**事件驱动架构**的重构，将业务逻辑从"过程式"转变为"响应式"。

**当前状态**：已完成事件系统和动作系统的基础架构，下一步可逐步将更多业务逻辑迁移到事件驱动模式。
