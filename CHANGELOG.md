# Changelog

本文件记录三国杀命令行终端版的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [3.3.0] - 2026-02-09

### Fixed
- shensu 测试目标闪避不确定性 (BUG-001)
- CSS 动画类缺失 `fade-in` / `slide-in` (BUG-002)
- F821 undefined name `GameAction` — 添加 `TYPE_CHECKING` 条件导入 (BUG-004)
- Python 3.10 f-string 兼容性: `game_play.py` 健康条渲染 (BUG-004)
- `ganglie` 技能人类玩家 UI 路由缺失 (BUG-007)
- `guicai` 技能人类玩家 UI 路由缺失 (BUG-008)
- `requirements.txt` 与 `pyproject.toml` 依赖不同步 (BUG-006)
- `test_guose` / `test_duanliang` / `test_qixi` / `test_request_sha_no_cards` 测试不确定性

### Changed
- 覆盖率配置: 排除 UI 深层模块, 阈值 60%, branch=true (BUG-003)
- Ruff 自动修复 2453 条代码风格问题
- 技能处理器拆分为按势力分包 `game/skills/{wei,shu,wu,qun}.py`
- AI 策略拆分为独立文件 `ai/{easy,normal,hard}_strategy.py`

### Added
- `test_report.txt` — 综合测试报告 (1256 用例, 75.71% 覆盖率)
- `test_issues_found.txt` — 测试问题报告
- `coverage.xml` — 覆盖率 XML 数据
- 属性测试: `tests/property/` (Hypothesis)
- 子系统测试: `tests/test_subsystems.py` (Combat/Equipment/Judge)
- Pilot UI 测试: `tests/test_pilot_ui.py`
- 模糊测试: `tests/test_fuzz.py`
- 压力测试: `tests/test_stress.py`

## [3.2.0] - 2026-02

### Added
- **阶段指示器实时更新**: 显示当前阶段、回合数、牌堆/弃牌堆计数、当前玩家名
- **对手面板增强**: 判定区延时锦囊⚠、铁索连环🔗、翻面🔄状态标记
- **距离/攻击范围标记**: 玩家面板显示距离数值和⚔/✖攻击范围指示
- **卡牌 Tooltip 增强**: 30+ 卡牌效果描述、花色点数、武器范围、坐骑修正
- **目标高亮**: 出牌时合法目标 PlayerPanel 自动添加 `.targetable` CSS 类
- **30 秒出牌倒计时**: 可视化倒计时（绿/黄/红颜色变化），超时自动结束出牌阶段
- **人类玩家弃牌阶段**: DiscardModal 弹窗交互，带超时自动弃牌兜底
- **借刀杀人锦囊**: 完整实现（武器验证 → 攻击范围 → 无懈可击 → 出杀/交武器）
- **国色技能**: 方块牌当乐不思蜀，创建虚拟延时锦囊
- **断粮技能**: 黑色基本/装备牌当兵粮寸断，距离≤2 限制
- **奇袭技能**: 黑色牌当过河拆桥，支持无懈可击拦截
- **神速技能**: 跳过阶段视为使用杀，支持出闪/无双
- **苦肉技能**: 失去体力（非伤害）+ 濒死检查 + 摸牌
- **AI 策略增强**: 转化技能决策、借刀目标选择、Hard 模式局势评估

### Fixed
- **兵粮寸断判定条件修正**: 原逻辑完全相反，现为“非梅花则跳过摸牌阶段”
- **延时锦囊判定顺序**: `judge_area.pop(0)` 修正为后放先判
- **DamageType 枚举统一**: `damage_system.py` 从 `card.py` 导入，消除重复定义
- **规则界面修复**: Esc 键绑定修复 + 添加返回按钮

## [3.1.0] - 2026-02

### Changed
- **UI 架构简化**: Textual TUI 作为唯一 UI 模式，移除 Rich / Plain 文本 UI
- `main.py` 不再提供 `--ui` 参数，默认启动 Textual TUI
- 移除 `colorama` 依赖（不再需要）

### Removed
- `ui/terminal.py` (TerminalUI 纯文本)
- `ui/rich_ui.py` (RichTerminalUI 富文本)
- `ui/base_terminal_ui.py` (旧 UI 基类)
- `ui/ascii_art.py` (ASCII 艺术素材)
- `sanguosha_v2/` (废弃的 v2 原型目录)
- `tests/test_rich_ui.py` (Rich UI 测试)

## [3.0.0] - 2026-02

### Added
- **工程基建**: Ruff 统一工具链 (替代 Black + isort + flake8)，新增 N/D 规则
- **类型安全**: MyPy 渐进严格化 (`disallow_untyped_defs = true`)，`py.typed` PEP 561 标记
- **文档**: `CHANGELOG.md`、`docs/architecture.md` 模块依赖图
- **TUI**: Textual 7.5.0 鼠标触控焕新，ModalScreen 交互 (英雄选择 / 手牌拾取 / 目标选择)

### Changed
- `pyproject.toml` 版本号统一为 `3.0.0`
- `main.py` 版本号改为 `importlib.metadata` 动态读取
- `requires-python` 升至 `>=3.10`
- MyPy `python_version` 升至 `3.14`
- Ruff `target-version` 保持 `py310` (最低支持版本)
- README 更新 TUI 使用说明与正确的 Python / 代码风格 badge

### Fixed
- `main.py` 版本号 "1.0.0" 与 `pyproject.toml` "2.0.0" 不一致问题
- MyPy 配置 `python_version = "3.9"` 过时问题
- README 中 Python 3.8+ 和 code style: black 旧标识

## [2.0.0] - 2026-01

### Added
- **Textual TUI**: 全新 Textual 图形界面 (`--ui textual`)
  - 主菜单 / 游戏设置 / 英雄选择 / 游戏主界面 / 规则 Screen
  - CardWidget 手牌组件，点击出牌交互
  - ModalScreen: 目标选择 / 无懈可击 / 花色猜测 / 手牌拾取
  - EquipmentSlots / HpBar / PhaseIndicator / PlayerPanel 组件
- **网络模块**: WebSocket 服务端/客户端 (`--server` / `--connect`)
- **Rich UI**: `RichTerminalUI` 富文本终端模式 (`--ui rich`)
- **UI Protocol**: `ui/protocol.py` 统一 UI 抽象接口
- **存档系统**: `game/save_system.py` JSON 序列化游戏状态
- **伤害系统**: `game/damage_system.py` 独立伤害计算模块
- **请求处理**: `game/request_handler.py` UI 请求分发
- **效果注册**: `game/effects/` 数据驱动卡牌效果系统
- **技能 DSL**: `game/skill_dsl.py` + `game/skill_interpreter.py` 声明式技能定义
- **胜负检查**: `game/win_checker.py` 独立胜负判定
- **回合管理**: `game/turn_manager.py` 独立回合控制
- **常量定义**: `game/constants.py` `SkillId` 枚举集中管理

### Changed
- 引擎重构: `GameEngine` 拆分辅助模块 (effects / damage / turn / win)
- 事件总线升级: 支持优先级、一次性订阅
- AI Bot: 嘲讽值 + 局势评分 + 身份推断深度集成

## [1.3.0] - 2026-01

### Added
- 古锭刀武器效果 (目标无手牌时杀伤害+1)
- `export_action_log()` JSON 导出功能
- `tools/replay.py` 最小回放工具
- 安全审计报告 `docs/SECURITY_AUDIT.md`
- 卡牌覆盖率映射 `docs/CARD_COVERAGE.md`

### Changed
- AI 目标选择接入局势评分深度函数
- 综合攻击价值计算 (嘲讽值 + 战力 + 状态)

### Fixed
- 火攻处理器未正确传递目标参数

## [1.2.0] - 2025-01

### Added
- **M1 规则闭环**: headless 判定阶段、延时锦囊、无懈可击完整机制
- **M2 动作系统**: `execute_action()` 统一入口 + 动作序列记录
- **M3 可复现性**: 统一随机种子 + 动作日志
- **M4 AI 增强**: 局势评分 / 战力评估 / 危险等级 / 身份推断
- Rich UI 稳定性修复: `MarkupError` 修复、`ask_for_wuxie()` 接口

### Changed
- 压力测试: 100 局全部通过，成功率 100%

## [1.1.0] - 2025-11

### Added
- **军争基础机制**: 酒、火杀/雷杀、铁索连环、藤甲
- headless 对战 API
- 13 个军争机制测试用例
- Windows 可执行文件 `sanguosha.exe`

### Changed
- 压力测试重构: 使用正式引擎规则

## [1.0.0] - 2024

### Added
- 初始版本发布
- 完整基础游戏机制 (回合制、身份模式、卡牌系统)
- 8 个标准版武将 (刘备/曹操/孙权/关羽/张飞/诸葛亮/周瑜/吕布)
- 3 种 AI 难度 (简单/普通/困难)
- 命令行终端界面
- 事件驱动架构与动作系统
