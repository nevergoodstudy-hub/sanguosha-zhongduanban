# 项目运行机理、问题分级、修复与架构焕新报告（中英双语）
# Project Runtime, Issues, Fixes, and Deep Renovation Plan (ZH/EN)

> Date: 2026-03-28  
> Scope: `sanguosha_backup_20260121_071454`  
> Role: Project Development Team

---

## 1) 运行机理（直观版）/ Runtime Mechanism (Intuitive)

### 中文
项目整体是“**输入 -> 规则引擎 -> 事件总线 -> UI/AI/网络反馈**”的闭环：

1. **入口层**：`main.py`
   - 本地 TUI 启动：`python main.py`
   - 服务器模式：`python main.py --server`
   - 客户端连接：`python main.py --connect ...`
2. **规则核心**：`game/`
   - `engine.py` 负责对局主流程协同；
   - `turn_manager.py` 控制回合阶段；
   - `combat.py`、`damage_system.py`、`judge_system.py` 分别处理战斗、伤害、判定；
   - `card_resolver.py` 做卡牌效果路由。
3. **UI 层**：`ui/textual_ui/`
   - `screens/game_play.py` 呈现牌桌状态；
   - `bridge.py` 把引擎请求映射为交互弹窗/响应。
4. **AI 层**：`ai/`
   - easy/normal/hard 三策略在引擎上下文中决策。
5. **网络层**：`net/`
   - `server.py` 与 `client.py` 基于 WebSocket 协议同步房间状态和动作。

### English
The project forms a closed loop of **Input -> Rule Engine -> Event Bus -> UI/AI/Network feedback**:

1. **Entry**: `main.py`
   - Local TUI: `python main.py`
   - Server mode: `python main.py --server`
   - Client mode: `python main.py --connect ...`
2. **Game Core**: `game/`
   - `engine.py` orchestrates game flow;
   - `turn_manager.py` controls phases;
   - `combat.py`, `damage_system.py`, `judge_system.py` process combat/damage/judge;
   - `card_resolver.py` routes card effects.
3. **UI**: `ui/textual_ui/`
   - `screens/game_play.py` renders battle screen;
   - `bridge.py` maps engine requests to modal interactions.
4. **AI**: `ai/`
   - easy/normal/hard strategy pipelines over engine context.
5. **Network**: `net/`
   - `server.py` and `client.py` synchronize room state/actions over WebSocket.

---

## 2) 项目问题调查（按优先级）/ Detailed Issue Survey (Prioritized)

### P0 (Critical)

1. **核心文件体量过大 / Overgrown core files**
   - `game/engine.py` (~1496 lines), `ui/textual_ui/screens/game_play.py` (~1339 lines), `net/server.py` (~1246 lines).
   - 风险：高耦合、改动回归成本高、review 难度增大。

2. **运行路径复杂度高 / High runtime path complexity**
   - 交互请求在 controller/handler/bridge 多处可触达，长期存在“逻辑分叉”风险。

### P1 (High)

3. **网络层职责混合 / Mixed responsibilities in network server**
   - 连接管理、房间状态、协议处理、广播等集中在单文件。

4. **测试门禁结构可继续强化 / Test gates can be further hardened**
   - 已有广泛测试，但建议分层执行（快速门禁 + 夜间全量）与快照回归常态化。

### P2 (Medium)

5. **旧产物管理风险 / Legacy artifacts management risk**
   - 本地性能产物、编辑器状态目录等可能混入版本控制，增加噪音和误提交概率。

---

## 3) 对应解决方案（详细）/ Detailed Solutions

### S1 (for P0): 模块化切分与边界收敛 / Modular split and boundary convergence

- 将超大文件按“职责”拆分（引擎协同、动作执行、渲染状态、网络会话管理）。
- 保证规则判定“单一入口”，避免同规则多地实现。
- 目标：单文件控制在 400~700 行区间，新增特性仅触达单模块。

### S2 (for P1): 网络层分层 / Network layering

- `server.py` 拆分为：
  - `session_manager.py`（连接与会话）
  - `room_service.py`（房间生命周期）
  - `protocol_dispatcher.py`（消息路由）
  - `security_guard.py`（安全与限流）
- 目标：降低故障定位时间，提升协议演进速度。

### S3 (for P1/P2): 测试与质量基线升级 / Quality & testing baseline upgrades

- 强化 `Textual run_test()/Pilot` 的关键路径 UI 用例；
- 引入快照测试用于视觉回归；
- CI 分层：PR 快速检查 + 夜间全量。

### S4 (for P2): 旧文件与本地产物治理 / Legacy/local artifact governance

- 已落地：更新 `.gitignore`，新增忽略项：
  - `perf_*.prof`
  - `.cursor/`
- 目的：减少噪音、避免本地临时/工具状态污染仓库。

---

## 4) 深度架构焕新（从里到外、可执行）
## Deep Architecture Renovation (Inside-Out, Executable)

### Phase A (1~2 weeks): 内核稳定化 / Core stabilization
- 统一动作入口与规则判定路径（Single Rule Path）。
- 引擎仅保留 orchestration，子系统负责可测试的纯规则逻辑。
- 交付物：架构边界图 + 单元测试补强。

### Phase B (2~4 weeks): 体验与工程并进 / UX + engineering
- `game_play` 进一步组件化（状态同步、交互、动画反馈分层）。
- `net` 细分服务并补结构化审计日志。
- 交付物：可观测性面板（事件/错误/延迟）与回归脚本。

### Phase C (4~8 weeks): 长期可演进 / Long-term evolvability
- 规则数据化与版本化（DSL + schema + compatibility gate）。
- 网络对局状态机显式化（match->ready->playing->settlement->replay）。
- 结合最新安全规范（OWASP Top 10 2025）持续检查输入、会话、日志。
- 交付物：发布级架构手册 + 迁移脚本 + 验收 checklist。

---

## 5) 本次任务进度 / Task Progress

### 已完成 / Completed
- [x] 项目运行机理梳理（中英双语）
- [x] 问题调查并分级（P0/P1/P2）
- [x] 提出逐项解决方案
- [x] 输出深度架构焕新分阶段计划
- [x] 整理旧文件治理的首轮落地（`.gitignore`）

### 待继续（建议下一迭代）/ Next iteration recommendations
- [ ] 启动 `engine.py` / `server.py` / `game_play.py` 的结构化拆分 PR
- [ ] 增补 UI 快照回归基线
- [ ] 增补网络层结构化审计报表

---

## 6) 本文依据的外部规范 / External references used

- Textual Testing Guide: https://textual.textualize.io/guide/testing/
- OWASP Top 10 (current release): https://owasp.org/www-project-top-ten/

