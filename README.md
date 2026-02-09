# 三国杀 - 终端版 (Textual TUI)

<p align="center">
  <strong>⚔ 基于 Textual 框架的现代终端三国杀卡牌游戏 ⚔</strong>
</p>

<p align="center">
  <a href="https://github.com/nevergoodstudy-hub/sanguosha-zhongduanban/releases/latest">
    <img src="https://img.shields.io/github/v/release/nevergoodstudy-hub/sanguosha-zhongduanban?label=%E6%9C%80%E6%96%B0%E7%89%88%E6%9C%AC" alt="Latest Release">
  </a>
  <a href="https://github.com/nevergoodstudy-hub/sanguosha-zhongduanban/actions/workflows/ci.yml">
    <img src="https://github.com/nevergoodstudy-hub/sanguosha-zhongduanban/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/TUI-Textual-blueviolet" alt="Textual">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green" alt="Platform">
  <img src="https://img.shields.io/badge/code%20style-ruff-261230.svg" alt="Code style: ruff">
  <img src="https://img.shields.io/badge/tests-1256%20passed-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-75.71%25-yellowgreen" alt="Coverage">
</p>

---

## 🎮 游戏概览

全鼠标点击交互的终端三国杀，基于 [Textual](https://textual.textualize.io/) TUI 框架构建。
支持 2-8 人身份模式、20+ 武将、完整卡牌系统和三级 AI 对战。

```
┌─────────────────────────────────────────────────────────────────────┐
│ ▶ 准备 → 判定 → 摸牌 → [出牌] → 弃牌 → 结束  | R3 🃏52 🗑12     │ ← 阶段指示器+牌堆计数
├─────────────────────────────────────────────────────────────────────┤
│ ▌ AI_曹操 ●●●● 🃏5 │距2 ⚔  ⚔青龙偃月刀 🛡八卦阵                 │ ← 对手面板
│ ▌ AI_周瑜 ●●●○ 🃏3 │距3 ✖  🔗连环  ⚠乐不思蜀                    │ ← 连环/判定区状态
├─────────────────────────────────────────────────────────────────────┤
│ ♠A        ♥K        ♦Q        ♣J        ♠10                       │
│ [  杀  ]  [  杀  ]  [  闪  ]  [  桃  ]  [ 决斗 ]                  │ ← 可点击手牌
│  基本牌     基本牌    基本牌    基本牌    📜锦囊牌                    │
├─────────────────────────────────────────────────────────────────────┤
│ [🃏 出牌]   [⚡ 技能]   [⏭ 结束]              ⏱ 剩余 25 秒        │ ← 倒计时
└─────────────────────────────────────────────────────────────────────┘
```

## ✨ 核心特性

### 🖥️ Textual TUI 界面
- **全鼠标交互** — 点击手牌出牌、点击面板选目标、弹窗式操作
- **阶段指示器** — 实时显示当前阶段 + 回合数 + 牌堆/弃牌堆计数
- **玩家面板** — 势力色条、武将名、HP 条、手牌数、装备、距离标记（⚔可攻击 / ✖不可）
- **状态显示** — 判定区延时锦囊⚠、铁索连环🔗、翻面🔄
- **目标高亮** — 出牌时合法目标面板自动高亮
- **卡牌 Tooltip** — 悬停显示花色点数、效果描述、武器范围、坐骑修正
- **30 秒倒计时** — 出牌阶段可视化倒计时，超时自动结束
- **弹窗交互** — 目标选择、无懈可击响应、濒死求桃、弃牌、花色猜测

### ⚔ 游戏逻辑（对标原版规则）
- **完整回合流程** — 准备→判定→摸牌→出牌→弃牌→结束，判定阶段后放先判
- **延时锦囊** — 乐不思蜀、兵粮寸断（判定条件已修正）、闪电
- **借刀杀人** — 完整实现：武器验证→攻击范围→无懈可击→出杀/交武器
- **无懈可击** — 每个锦囊生效前均可响应，支持连环无懈
- **濒死求桃** — 体力归零进入濒死，所有角色可出桃救援
- **弃牌阶段** — 人类玩家弹窗选择弃牌（带倒计时兜底）
- **军争机制** — 酒、火杀/雷杀、铁索连环传导、藤甲

### 🧠 武将技能（已完整实现）
- **国色** — 方块牌当乐不思蜀 | **断粮** — 黑色牌当兵粮寸断（距离≤2）
- **奇袭** — 黑色牌当过河拆桥 | **神速** — 跳过阶段视为使用杀
- **苦肉** — 失去体力+濒死检查+摸牌 | **借刀杀人** — 令他人出杀或交武器
- 以及：武圣、咆哮、仁德、制衡、反间、观星、空城、无双、鬼才、刚烈、突袭、流离、青囊、急救、离间、闭月、烈弓、狂骨、据守、克己、结姻、枭姬……

### 🤖 AI 系统
- 🟢 **简单** — 随机出牌
- 🟡 **普通** — 基础策略 + 转化技能（国色/断粮/奇袭/神速/苦肉）+ 借刀杀人
- 🔴 **困难** — 嘲讽值系统 + 局势评估 + 综合攻击价值计算 + 身份推断

## 📥 安装与运行

### 系统要求
- Python 3.10+
- Windows / macOS / Linux
- 支持 UTF-8 的终端（Windows Terminal / iTerm2 / 任意现代终端）

### 安装

```bash
git clone https://github.com/nevergoodstudy-hub/sanguosha-zhongduanban.git
cd sanguosha-zhongduanban
pip install -e .
```

### 启动游戏

```bash
python main.py
```

### 其他模式

```bash
python main.py --server              # 启动 WebSocket 服务端 (0.0.0.0:8765)
python main.py --connect HOST:PORT   # 连接到服务端
python main.py --replay FILE         # 回放存档
python main.py --lang en_US          # 英文界面
```

## 📖 游戏规则

### 身份与胜利条件

| 身份 | 胜利条件 |
|------|----------|
| 👑 主公 | 消灭所有反贼和内奸 |
| 忠臣 | 保护主公获胜 |
| 反贼 | 消灭主公 |
| 内奸 | 最后存活 |

### 回合流程

1. **准备阶段** — 触发准备阶段技能（观星等）
2. **判定阶段** — 处理判定区延时锦囊（后放先判）
3. **摸牌阶段** — 从牌堆摸 2 张牌
4. **出牌阶段** — 使用手牌和技能（每回合限 1 张杀，特殊情况除外）
5. **弃牌阶段** — 手牌超过体力值须弃牌
6. **结束阶段** — 触发结束阶段技能

### 操作说明

| 操作 | 方式 |
|------|------|
| 出牌 | 点击手牌 → 选择目标 |
| 技能 | 点击「⚡ 技能」按钮 |
| 结束出牌 | 点击「⏭ 结束」或按 `E` |
| 帮助 | 按 `H` |
| 退出 | 按 `Q` |

## 🃏 卡牌一览

### 基本牌
杀、火杀🔥、雷杀⚡、闪、桃、酒🍺

### 锦囊牌
决斗、南蛮入侵、万箭齐发、无中生有、过河拆桥、顺手牵羊、借刀杀人、桃园结义、无懈可击、铁索连环🔗、乐不思蜀、兵粮寸断、闪电

### 装备牌
- **武器**：诸葛连弩(1)、寒冰剑(2)、古锭刀(2)、青龙偃月刀(3)、丈八蛇矛(3)、贯石斧(3)、方天画戟(4)、朱雀羽扇(4)、麒麟弓(5)
- **防具**：八卦阵、仁王盾、藤甲🌿、白银狮子
- **坐骑**：赤兔(-1)、大宛(-1)、紫骍(-1)、的卢(+1)、爪黄飞电(+1)、绝影(+1)

## 👥 武将列表（20+）

**蜀**：刘备(仁德/激将)、关羽(武圣)、张飞(咆哮)、诸葛亮(观星/空城)、马超(马术/铁骑)、黄月英(集智/奇才)、魏延(狂骨)

**魏**：曹操(奸雄/护驾)、司马懿(反馈/鬼才)、夏侯惇(刚烈)、张辽(突袭)、徐晃(断粮)、曹仁(据守)

**吴**：孙权(制衡/救援)、周瑜(英姿/反间)、大乔(国色/流离)、吕蒙(克己)、甘宁(奇袭)、黄盖(苦肉)、孙尚香(结姻/枭姬)

**群**：吕布(无双)、华佗(青囊/急救)、貂蝉(离间/闭月)

## 📁 项目结构

```
sanguosha/
├── main.py                          # 入口（TUI / 服务端 / 客户端 / 回放）
├── pyproject.toml                   # 项目配置 & 依赖
├── game/                            # 🎯 游戏核心逻辑
│   ├── engine.py                    #   游戏引擎
│   ├── player.py                    #   玩家 / 身份 / 装备
│   ├── card.py                      #   卡牌 / 牌堆 / 枚举
│   ├── hero.py                      #   武将加载
│   ├── skill.py                     #   技能系统（DSL-first + Python fallback）
│   ├── skills/                      #   按势力分包的技能处理器
│   │   ├── wei.py                   #     魏势力技能
│   │   ├── shu.py                   #     蜀势力技能
│   │   ├── wu.py                    #      吴势力技能
│   │   └── qun.py                   #     群势力技能
│   ├── combat.py                    #   战斗子系统
│   ├── card_resolver.py             #   卡牌结算
│   ├── damage_system.py             #   伤害计算 / 濒死 / 死亡
│   ├── equipment_system.py          #   装备子系统
│   ├── judge_system.py              #   判定子系统
│   ├── game_controller.py           #   游戏控制器
│   ├── request_handler.py           #   UI 请求分发
│   ├── turn_manager.py              #   回合管理
│   ├── save_system.py               #   存档 / 回放
│   ├── events.py                    #   事件总线
│   ├── actions.py                   #   动作系统
│   ├── effects/                     #   数据驱动卡牌效果
│   └── skill_dsl.py                 #   技能 DSL
├── ui/                              # 🖥️ Textual TUI 界面
│   ├── textual_ui/
│   │   ├── app.py                   #   Textual App 入口
│   │   ├── bridge.py                #   引擎 ↔ TUI 桥接层
│   │   ├── screens/                 #   6 个 Screen（主菜单/设置/选将/游戏/结算/规则）
│   │   ├── modals/                  #   弹窗（目标/无懈/求桃/弃牌/花色/拾取）
│   │   ├── widgets/                 #   组件（卡牌/面板/阶段条/血条/装备栏）
│   │   └── styles/game.tcss         #   全局样式
│   └── protocol.py                  #   GameUI 抽象接口
├── ai/                              # 🤖 三级 AI 系统
│   ├── bot.py                       #   AI 入口 + 嘲讽值 + 局势评估
│   ├── easy_strategy.py             #   简单策略
│   ├── normal_strategy.py           #   普通策略（转化技能+借刀）
│   └── hard_strategy.py             #   困难策略（综合评估+身份推断）
├── net/                             # 🌐 WebSocket 网络对战
├── i18n/                            # 🌍 国际化（中文 / 英文）
├── data/                            # 📦 卡牌 / 武将 / 效果数据 (JSON)
├── tests/                           # 🧪 单元 / 集成 / 压力 / 模糊 / 属性测试
└── docs/                            # 📚 架构文档
```

## 🔧 开发

### 代码规范
- [Ruff](https://docs.astral.sh/ruff/) 统一工具链
- MyPy 渐进严格模式
- PEP 561 `py.typed` 类型标记

### 运行测试

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v              # 全量测试 (1256 用例)
python -m pytest --cov=game --cov=ai    # 含覆盖率报告
python -m ruff check .                  # 静态分析
```

### 扩展武将

1. `data/heroes.json` — 添加武将数据
2. `game/skills/<faction>.py` — 实现对应势力的技能处理器（使用 `@skill_handler` 装饰器注册）
3. `ai/` — 在对应策略文件中添加 AI 技能决策

### 扩展卡牌

1. `data/cards.json` — 添加卡牌数据
2. `game/engine.py` — 添加 `use_card` 处理路由
3. `ui/textual_ui/widgets/card_widget.py` — 添加 `CARD_EFFECT_DESC` tooltip

## 📝 版本历史

### v3.3.0 (2026-02-09) — 质量强化：BUG 修复 + 测试全覆盖

**BUG 修复（8 项）：**
- 修复 shensu 测试闪避不确定性、CSS 动画类缺失
- 修复 F821 undefined name 静态分析错误（GameAction 类型导入）
- 修复 Python 3.10 f-string 兼容性（game_play.py 健康条）
- 修复 ganglie/guicai 技能人类玩家 UI 路由缺失
- 同步 requirements.txt 与 pyproject.toml 依赖
- 优化覆盖率配置（排除 UI 深层模块，阈值 60%）

**测试改进：**
- 修复 4 个不确定性测试（guose/duanliang/qixi/request_sha）
- Ruff 自动修复 2453 条代码风格问题
- 1256 测试用例全部通过，覆盖率 75.71%
- 属性测试（Hypothesis）、模糊测试、压力测试、Textual Pilot UI 测试

### v3.2.0 (2026-02) — 深度改进：18 项全量修复

**界面改进：**
- 阶段指示器实时更新 + 回合数/牌堆/弃牌堆计数
- 对手面板：判定区⚠、连环🔗、翻面🔄、距离/攻击范围标记
- 卡牌 tooltip 增强（30+ 效果描述）
- 出牌目标高亮、30 秒倒计时、规则界面修复

**逻辑修复：**
- 兵粮寸断判定修正、延时锦囊后放先判、人类弃牌阶段
- 国色/断粮/奇袭/神速/苦肉技能完整实现
- 借刀杀人锦囊、AI 策略增强

### v3.0 ~ v3.1 (2026-02)
- Textual TUI 唯一 UI、Ruff 工具链、MyPy 严格化

### v2.0 (2026-01)
- 架构重构：Textual TUI、网络对战、存档系统、效果注册、技能 DSL

### v1.x (2024-2025)
- 军争机制、规则闭环、AI 增强、初始版本

## 📄 许可证

本项目仅供学习和娱乐目的。三国杀是游卡桌游的注册商标。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**享受游戏！** 🎮 如果觉得有帮助，请 ⭐ Star 支持一下！