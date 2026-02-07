# Changelog

本文件记录三国杀命令行终端版的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

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
