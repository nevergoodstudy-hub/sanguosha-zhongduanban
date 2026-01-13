# 三国杀命令行终端版：开发者可执行改进实施文档

> 文档目的：把现有的《IMPROVEMENT_PLAN.md / PROJECT_ROADMAP.md / GAMEPLAY_IMPROVEMENTS.md》中“方向性规划”，细化为开发者可直接落地执行的任务清单（含：范围、里程碑、依赖、验收标准、测试计划、风险与回滚、安全审计清单、协作规范）。

---

## 0. 文档元信息

- **文档状态**：Active
- **适用版本**：v1.1.0（以仓库当前 `main` 分支为基线）
- **维护者角色**：Maintainer / Core Dev
- **最后更新**：2026-01-12

---

## 1. 摘要（Summary）

本仓库实现了一个可玩的三国杀命令行版本，并已具备事件系统（`game/events.py`）与动作系统（`game/actions.py`）的基础架构。下一阶段的重点是：

- **规则完整性**：让“数据文件中出现的牌/机制”在引擎与压测中都能完整使用与结算（尤其是【无懈可击】与延时锦囊）。
- **统一入口**：把“人类与 AI 的操作入口”统一到动作系统，以降低耦合并为联机/回放/更强 AI 做准备。
- **工程化**：补齐测试覆盖与可诊断性（复现、日志、种子），并引入更稳定的开发协作规范。

---

## 2. 动机（Motivation）

- **可维护性**：当前 `game/engine.py` 仍较大（1600+ 行），新增规则/武将可能继续把逻辑堆叠到引擎内部。
- **可扩展性**：动作系统与事件系统已经存在，但尚未形成闭环；若未来要做 GUI/联机/回放或 AI 搜索，需要统一的“输入/输出协议”。
- **可验证性**：目前已有军争与自动对战测试，但仍存在“headless 流程与正式流程不一致”的风险点（例如 `run_headless_turn` 跳过判定阶段处理）。

---

## 3. 范围（Scope）

### 3.1 目标（Goals）

- **G1：规则正确性与一致性**
  - 所有可在 `data/cards.json` 抽到的关键牌，至少具备可用/可结算/可测试的实现。
  - headless（压测/AI研究）对局的阶段流程与正式引擎一致。

- **G2：动作系统落地**
  - 人类与 AI 行为统一封装为 `GameAction`，并通过统一入口验证与执行。
  - 引擎不直接依赖 UI（逐步迁移，允许短期向后兼容）。

- **G3：可观察与可复现**
  - 对局可记录：随机种子、动作序列、关键事件，支持复现与回放。

### 3.2 非目标（Non-Goals）

- **NG1**：本阶段不做 GUI（PyQt/Web）或联机。
- **NG2**：不承诺把所有技能完全数据驱动（先从关键通用机制与少数技能试点）。
- **NG3**：不做完整平衡性改动（除非修复明显规则错误）。

---

## 4. 当前状态盘点（Baseline Inventory）

> 该章节用于告诉开发者：哪些已经完成、哪些仍是缺口，避免“重复造轮子”。

### 4.1 已完成（基线能力）

- **事件总线**：`game/events.py` 提供 `EventBus / EventType / GameEvent`。
- **动作系统骨架**：`game/actions.py` 提供 `GameAction` 与若干 Action/Request/Response 类型。
- **军争基础**：
  - `酒`（`Player.use_alcohol/consume_drunk` 与 `engine._use_jiu`）
  - 火杀/雷杀（`engine._use_sha` 传递 `damage_type`）
  - 铁索连环（`engine._use_tiesuo` 与 `deal_damage` 属性伤害传导）
  - 藤甲：普通杀无效、AOE免疫、火焰伤害+1（见 `engine._use_sha/_use_nanman/_use_wanjian/deal_damage`）
- **关键缺失项已补齐（历史高优先级问题）**：
  - `engine._use_juedou_forced` 已实现（供离间技能调用）。
- **压测已对齐正式引擎**：`tests/test_auto_battle_stress.py` 使用 `engine.setup_headless_game + run_headless_battle`。
- **军争测试已存在**：`tests/test_juunzheng.py` 覆盖酒/属性伤害/铁索/藤甲等。

### 4.2 已知缺口（需要纳入本实施计划）

- **K1：无懈可击**
  - `data/cards.json` 存在【无懈可击】与 `RequestType.PLAY_WUXIE`，但引擎尚未建立“锦囊生效前可被无懈抵消”的统一拦截点。

- **K2：延时锦囊完整闭环**
  - 引擎有 `phase_judge` 的处理逻辑，但 `run_headless_turn` 当前未调用 `phase_judge`（仅标注“简化：跳过延时锦囊”），导致 headless 与正式对局不一致。
  - 需要确认延时锦囊在出牌阶段是否可被使用并放入 `Player.judge_area`（目前 `use_card` 未包含延时锦囊的 handler）。

- **K3：Action/Request 未形成闭环**
  - `main.py` 与 `ai/bot.py` 仍直接调用 `engine.use_card/skill_system.use_skill`，ActionValidator 存在但未成为唯一入口。

- **K4：可复现性不足**
  - 压测虽运行稳定，但“固定随机种子 + 动作序列记录 + 可重放”尚未形成标准接口。

---

## 5. 协作与工程规范（建议执行）

### 5.1 分支与提交规范

- **分支命名建议**：
  - `fix/<topic>`：规则/bug 修复
  - `feat/<topic>`：新增机制/新卡牌/新模式
  - `refactor/<topic>`：重构（不改变玩法或只做等价改动）
  - `test/<topic>`：新增/修复测试

- **提交信息建议**：采用 Conventional Commits（参考：conventionalcommits.org）。
  - 例：`fix(engine): correct wusheng conversion rule`
  - 例：`feat(engine): add wuxie counter chain`
  - 例：`test(juunzheng): add tiesuo propagation cases`

### 5.2 Definition of Done（DoD）

每个任务合并前必须满足：

- [ ] 通过 `python -m pytest tests/ -v`
- [ ] 新增/修改规则必须有对应测试（至少单元测试）
- [ ] 关键路径变更（伤害/判定/濒死/死亡）必须补充“边界用例”
- [ ] 若涉及对外接口/行为变化，更新 `README.md` 的“版本历史/变更说明”或增加说明段

---

## 6. 里程碑与任务拆解（Milestones & Tasks）

> 任务编号格式：`M<里程碑>-T<序号>`，并标注优先级：P0（必须）、P1（高）、P2（中）、P3（低）。

### 6.0 角色分工与依赖关系

#### 角色分工（简化 RACI）

- **Maintainer**：把控里程碑范围与合并策略；处理 release/tag；最终验收签字
- **Engine Dev**：实现 `game/engine.py` 规则与阶段流程；确保 headless 与正式一致
- **AI Dev**：实现 `ai/bot.py` 的出牌/响应策略；确保 AI 行为不绕过校验
- **UI Dev**：实现/调整 `ui/rich_ui.py` 与交互流程；对接 Action/Request
- **QA/Test**：补齐 `tests/` 覆盖；维护回归用例与压测稳定性指标

#### 里程碑依赖

- **M1 → M2**：规则闭环与 headless 一致后，再迁移为 Action（避免一边重构一边修规则导致定位困难）
- **M2 → M3**：动作统一入口建立后，才能稳定记录 action_log 并支持回放复现
- **M1/M2 → M4**：AI 强化建立在规则正确与统一入口之上，否则容易“学坏/作弊”

### 6.1 里程碑 M1：规则闭环与 headless 一致性（P0）

#### 目标

- headless 对局的阶段流程与正式流程一致（至少：准备/判定/摸牌/出牌/弃牌/结束）。
- `data/cards.json` 中“延时锦囊/无懈可击”等关键牌具备完整结算链路。

#### 输出物

- 引擎支持：延时锦囊可用 + 判定可结算（正式与 headless 一致）
- 引擎支持：无懈可击链式响应（至少 1 轮）
- 新增测试：覆盖上述机制（单测 + 自动对战）

#### 任务列表

##### M1-T01（P0）：headless 判定阶段对齐正式逻辑

- **问题**：`GameEngine.run_headless_turn` 当前跳过判定区处理，与 `phase_judge` 不一致。
- **改动点**：`game/engine.py`
- **实施步骤**：
  - [ ] 将 `run_headless_turn` 的“简化判定阶段”替换为调用 `self.phase_judge(player)`（或保证同等逻辑）。
  - [ ] 确保 `phase_judge` 内部抽牌耗尽等边界有防护（至少不会抛异常导致压测崩溃）。
- **验收标准**：
  - [ ] `tests/test_auto_battle_stress.py` 100 局不因判定阶段崩溃
  - [ ] 增加最小单测：构造 `judge_area` 含【乐不思蜀/兵粮寸断/闪电】能触发相应跳过阶段/伤害/传递行为

##### M1-T02（P0）：延时锦囊“出牌 → 入判定区”闭环

- **问题**：`phase_judge` 已实现，但玩家/AI 可能无法在出牌阶段把延时锦囊放入判定区（缺少 handler）。
- **改动点**：
  - `game/engine.py`：为 `CardSubtype.DELAY` 或按 `card.name` 增加处理器（如 `_use_delay_trick`）。
  - `ai/bot.py`：普通/困难 AI 增加延时锦囊的出牌优先级（可先低优先级，保证可用即可）。
- **实施步骤**：
  - [ ] 定义规则：
    - 【乐不思蜀】对其他角色使用，置于其判定区。
    - 【兵粮寸断】对距离 1 角色使用，置于其判定区。
    - 【闪电】对自己使用，置于自己判定区（并在判定阶段向下家传递）。
  - [ ] 增加 `engine.use_card` 对上述牌名的 handler，将牌移动到 `target.judge_area`。
- **验收标准**：
  - [ ] 新增单测覆盖：使用延时锦囊后，目标 `judge_area` 数量变化正确
  - [ ] 触发判定时能正确跳过阶段/造成伤害/传递闪电

##### M1-T03（P0）：无懈可击（Wuxie）机制实现（最小可用）

- **问题**：目前【无懈可击】只是数据存在，缺少“锦囊生效前拦截”。
- **改动点**：`game/engine.py`、（可选）`game/actions.py`、`ui/rich_ui.py`、`ai/bot.py`
- **实施步骤（最小闭环版本）**：
  - [ ] 在所有“锦囊生效前”插入统一拦截点，例如：
    - 在 `use_card` 中，当 `card.card_type == TRICK` 且非【无懈可击】本身时：
      - 先触发 `_request_wuxie(trick_card, source, targets)`
      - 若被无懈，则本次锦囊效果取消
  - [ ] 实现 `_request_wuxie` 的最小规则：
    - 从使用者开始按座位顺序询问所有存活玩家是否打出【无懈可击】
    - 若有人打出无懈：翻转“是否抵消”状态（支持链式：无懈可击也可被无懈）
    - 最终若状态为“抵消”，则锦囊无效
  - [ ] AI 版本先做简单策略：
    - 对敌方锦囊更倾向无懈
    - 对己方收益锦囊不无懈
- **验收标准**：
  - [ ] 新增单测：
    - 单张锦囊被 1 张无懈抵消
    - 锦囊 → 无懈 → 无懈：最终锦囊生效
  - [ ] 自动对战/压测可稳定运行

##### M1-T04（P1）：牌堆耗尽与判定抽牌边界防护

- **问题**：部分逻辑默认 `draw(1)` 一定返回 1 张；当摸牌堆+弃牌堆耗尽时可能返回空列表。
- **改动点**：`game/engine.py` 关键 draw 点；`game/card.py` 可保持现状（已有 `is_empty`）。
- **实施步骤**：
  - [ ] 统一在 `engine` 层对 `draw()` 结果做保护：空则记录日志并采取可接受的退化行为（跳过/结束/判定失败）。
  - [ ] 定义“牌堆耗尽策略”（建议之一）：
    - 若两堆为空，继续流程但任何 `draw()` 返回空
    - 或直接判定游戏结束为超时/平局（需要明确在 `get_winner_message` 里描述）
- **验收标准**：
  - [ ] 人工构造“空牌堆”场景，核心流程不崩溃

#### M1 验收总表

- [ ] 延时锦囊可使用、可进入判定区、可在判定阶段结算
- [ ] headless 回合包含判定阶段处理
- [ ] 无懈可击可抵消锦囊（含链式）
- [ ] `pytest` 全通过

---

### 6.2 里程碑 M2：动作系统闭环（P1）

#### 目标（M2）

- 人类玩家与 AI 的行为统一走 `GameAction` → `ActionValidator` → `ActionExecutor`。
- 引擎逐步去 UI 耦合：通过 `GameRequest/GameResponse` 与事件通知 UI。

#### 输出物（M2）

- `GameEngine.execute_action(action)` 或等价统一入口
- `main.py` 主要交互改为派发 Action
- AI 操作改为派发 Action

#### 任务列表（M2）

##### M2-T01（P1）：引擎统一动作入口

- **改动点**：`game/engine.py`、`game/actions.py`
- **实施步骤**：
  - [ ] 在 `GameEngine` 中新增 `self.action_executor = ActionExecutor(self)`（或提供方法惰性创建）。
  - [ ] 提供 `execute_action(action: GameAction) -> bool`：
    - 内部调用 `ActionExecutor.execute(action)`
    - 并在关键动作前后发出事件（长期目标）
- **验收标准**：
  - [ ] 现有逻辑不破坏（向后兼容：仍允许旧代码直接调用 `use_card`）
  - [ ] 新增最小单测：构造 `PlayCardAction` 能正确出牌

##### M2-T02（P1）：main.py 出牌/技能/弃牌迁移为 Action

- **改动点**：`main.py`
- **实施步骤**：
  - [ ] 将 `_handle_play_specific_card` / `_handle_use_skill` / `_human_discard_phase` 的核心执行替换为构造 Action 并 `engine.execute_action()`。
  - [ ] 逐步移除 `main.py::_check_card_usable` 与 `ActionValidator` 的重复逻辑（短期可保留，但以 ActionValidator 为准）。
- **验收标准**：
  - [ ] 人类对局可正常进行（至少 2-4 人）
  - [ ] 单元测试不回退

##### M2-T03（P1）：AI 出牌迁移为 Action（避免“作弊式”直接调用引擎）

- **改动点**：`ai/bot.py`
- **实施步骤**：
  - [ ] 将 `engine.use_card(...)` 替换为构造 `PlayCardAction`（目标用 player_id/target_ids）。
  - [ ] AI 技能使用替换为 `UseSkillAction`。
- **验收标准**：
  - [ ] 自动对局仍能跑通
  - [ ] 行为合法性统一由 `ActionValidator` 把关

---

### 6.3 里程碑 M3：可复现性与回放（P2）

#### 目标（M3）

- 压测/异常对局可复现：固定随机种子 + 动作序列 + 最小状态快照。

#### 任务列表（M3）

##### M3-T01（P2）：统一随机种子注入与记录

- **改动点**：`game/engine.py`、`tests/test_auto_battle_stress.py`
- **实施步骤**：
  - [ ] `setup_headless_game` 接受可选 `seed` 参数；记录到对局结果。
  - [ ] 压测在失败时输出 seed，方便复现。

##### M3-T02（P2）：动作序列记录

- **改动点**：`game/actions.py`、`game/engine.py`
- **实施步骤**：
  - [ ] `ActionExecutor.execute` 成功后，把 action 追加到 `engine.action_log`。
  - [ ] 对局结束后可导出到 JSON（可选）。

##### M3-T03（P2）：最小回放工具（开发用）

- **改动点**：新增工具脚本或测试辅助（例如 `tools/replay.py`）
- **实施步骤**：
  - [ ] 根据 action_log 回放：重建 engine → 依次 execute_action。
  - [ ] 校验关键状态（回合数、玩家存活、赢家）一致。

---

### 6.4 里程碑 M4：AI 增强（P2/P3）

> 该里程碑不影响规则正确性，但会影响体验与研究价值。

#### 建议任务

- **M4-T01（P2）**：建立“局势评分函数”（血量、手牌、装备、身份关系等）
- **M4-T02（P2）**：身份推断（基于攻击/救援/用牌行为的概率模型）
- **M4-T03（P3）**：行为树/策略模块化（替代深层 if-else）

---

## 7. 测试计划（Test Plan）

### 7.1 必跑用例

- [ ] `python -m pytest tests/ -v`
- [ ] `python tests/test_auto_battle_stress.py`（至少 100 局）

### 7.2 新增测试建议（按任务映射）

- M1 延时锦囊：
  - [ ] `test_delay_trick_put_to_judge_area`
  - [ ] `test_lebusishu_skip_play_phase`
  - [ ] `test_bingliang_skip_draw_phase`
  - [ ] `test_shandian_transfer_or_damage`
- M1 无懈可击：
  - [ ] `test_wuxie_cancels_trick`
  - [ ] `test_wuxie_chain_reverses`

---

## 8. 风险控制与回滚（Risk & Rollback）

- **小步提交**：每个任务独立 PR，避免“大而全”。
- **回滚点**：在进入 M1 前打 Tag（例如 `v1.1.0-baseline`）。
- **风险点**：
  - 无懈可击/延时锦囊会引入大量交互分支，容易出现“静默规则错误”。
  - headless 与正式流程统一后，压测可能暴露更多历史隐藏问题。
- **回滚策略**：
  - 若出现高频崩溃/规则回归：优先回滚到 Tag；或通过 Feature Flag 关闭新机制（建议仅用于开发阶段）。

---

## 9. 安全审计清单（Security Review Checklist）

> 注意：当前项目为单机终端游戏，但动作系统/联机规划会引入“恶意输入/作弊”风险。本清单用于提前约束。

### 9.1 输入与动作校验

- [ ] 所有进入引擎的玩家行为必须走 `ActionValidator`（未来联机的第一道防线）
- [ ] `PlayCardAction` 必须校验：回合归属、手牌归属、目标合法、距离合法、次数限制
- [ ] `UseSkillAction` 必须校验：技能是否拥有、次数限制、目标合法

### 9.2 状态一致性

- [ ] 伤害/回复/濒死/死亡的状态变更必须单点收敛（避免多处写 hp/is_dying/is_alive）
- [ ] 对局日志记录不得影响游戏流程（异常应捕获并记录）

### 9.3 供应链与依赖

- [ ] `requirements.txt` 依赖更新需说明原因
- [ ] 不在仓库中写入任何密钥/Token

---

## 10. 参考资料（References）

- [RFC Template (Markdown)](https://gist.github.com/michaelcurry/e0132058fcd6d588a1299afd69638df4)
- [GitHub spec-kit（规范驱动与验收清单思想）](https://github.com/github/spec-kit)
- [Conventional Commits 规范](https://github.com/conventional-commits/conventionalcommits.org)
- [Keep a Changelog（如后续引入 CHANGELOG.md）](https://github.com/olivierlacan/keep-a-changelog)
