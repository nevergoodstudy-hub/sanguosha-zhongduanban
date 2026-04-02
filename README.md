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
  <img src="https://img.shields.io/badge/tests-targeted%20regressions%20passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/identity%20sync-5%20heroes-blue" alt="Identity Sync">
</p>

---

## 🎮 游戏概览

> Release 规范说明：
> - 当前仅保留最新稳定版本 `v4.1.1`
> - 新版本发布仅使用语义化版本标签 `vX.Y.Z`（例如 `v4.1.2`）
> - 发布流程文档：`docs/release-process.md`


全鼠标点击交互的终端三国杀，基于 [Textual](https://textual.textualize.io/) TUI 框架构建。
支持 2-8 人身份模式、32 名武将、完整卡牌系统、三级 AI 对战，以及 headless / 房间模式共用的技能生命周期。

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

### 🧠 武将技能（含 2026-03 同步批次）
- **新增同步武将** — 谋袁术(矜名/枭噬/厌粱)、胡金定(轻缘/重身)、界刘表(自守/宗室)、界法正(眩惑/恩怨)、向宠(固营/睦阵)
- **既有核心技能** — 国色、断粮、奇袭、神速、苦肉、借刀杀人
- 以及：武圣、咆哮、仁德、制衡、反间、观星、空城、无双、鬼才、刚烈、突袭、流离、青囊、急救、离间、闭月、烈弓、狂骨、据守、克己、结姻、枭姬……

### 🤖 AI 系统
- 🟢 **简单** — 随机出牌
- 🟡 **普通** — 基础策略 + 转化技能（国色/断粮/奇袭/神速/苦肉）+ 借刀杀人 + 眩惑 / 睦阵 / 厌粱
- 🔴 **困难** — 嘲讽值系统 + 局势评估 + 综合攻击价值计算 + 身份推断
- **自动对战验证** — headless / 房间模式会正确初始化 SkillSystem，并能稳定跑完含新增武将的身份局

### 🆕 2026-03 身份模式同步批次
- 新增 5 名同步武将：谋袁术、胡金定、界刘表、界法正、向宠
- 新增技能事件与轮次状态支持：牌张获得/失去、回血、回合开始与回合重置语义
- headless / 房间模式与 TUI 共用 `GAME_START` / `ROUND_START` 生命周期
- 普通 / 困难 AI 已能在自动对战中使用 `眩惑`、`睦阵`、`厌粱`

## 📥 安装与运行

### 方式一：直接下载（Windows）

无需安装 Python，双击即可运行：

👉 [下载最新版 sanguosha.exe](https://github.com/nevergoodstudy-hub/sanguosha-zhongduanban/releases/latest)

### 方式二：源码运行

**系统要求：** Python 3.10+ / Windows / macOS / Linux / 支持 UTF-8 的终端

```bash
git clone https://github.com/nevergoodstudy-hub/sanguosha-zhongduanban.git
cd sanguosha-zhongduanban
pip install -e .
python main.py
```

### 方式三：自行构建

```bash
pip install pyinstaller
python build.py                               # 生成 dist/sanguosha.exe (单文件)
python build.py --onedir                      # 目录模式
python build_msix.py --allow-placeholder-assets  # Windows 本地验证 MSIX（开发占位资源）
```

GitHub Release 标签构建会产出 Windows / Linux / macOS 的 PyInstaller 制品；`build_msix.py` 主要用于本地 Windows 打包验证。

### 其他模式

```bash
python main.py --server                         # 启动 WebSocket 服务端 (127.0.0.1:8765)
python main.py --connect HOST:PORT              # 连接到 ws://HOST:PORT
python main.py --connect ws://localhost:8765    # 显式 ws URL
python main.py --connect wss://game.example.com # 显式 wss URL
python main.py --replay FILE                    # 回放存档
python main.py --lang en_US                     # 英文界面
```

> 网络安全默认值：`SANGUOSHA_WS_ALLOWED_ORIGINS` 为空时，服务端会拒绝所有 WebSocket 连接（fail-closed）。
> 生产环境请显式配置白名单，例如：
> `SANGUOSHA_WS_ALLOWED_ORIGINS="https://game.example.com,http://localhost:3000"`

## 🌐 联机启动故障排查

如果你使用 `--server` / `--connect` 联机时遇到“连不上”或“握手失败”，可按下面顺序检查：

### 1) 先确认运行目录
服务端启动时会检查当前目录是否包含 `main.py`、`pyproject.toml`、`data/`、`game/`、`ui/`。
若目录不对，先切换到项目根目录再启动。

### 2) 检查 Origin 白名单（最常见）
默认安全策略是 **fail-closed**：
- `SANGUOSHA_WS_ALLOWED_ORIGINS` 为空时，会拒绝所有 WebSocket 连接。

生产环境建议：

```bash
SANGUOSHA_WS_ALLOWED_ORIGINS="https://game.example.com"
```

本地开发快速联调（二选一）：

```bash
# 方式 A：显式白名单
SANGUOSHA_WS_ALLOWED_ORIGINS="http://localhost:3000"

# 方式 B：开发快捷开关（仅放行 localhost/127.0.0.1/::1）
SANGUOSHA_DEV_ALLOW_LOCALHOST=1
```

### 3) 关注启动期“非阻断告警”（`validate_warnings()`）
服务端启动时除了阻断型校验（失败会退出），还会输出配置告警（不阻断启动）：

- 启用 `SANGUOSHA_DEV_ALLOW_LOCALHOST=1` 会提示“仅建议开发使用”
- 同时启用 `SANGUOSHA_DEV_ALLOW_LOCALHOST` 与 `SANGUOSHA_WS_ALLOWED_ORIGINS` 会提示“生产建议仅保留显式白名单”

这类提示用于降低“开发便捷开关误带到生产”的风险。

### 4) 检查 TLS / URL 协议是否匹配
- 未配置 `SANGUOSHA_WS_SSL_CERT` + `SANGUOSHA_WS_SSL_KEY` 时，服务端是 `ws://`
- 配置证书后，服务端是 `wss://`

客户端 URL 必须匹配协议，否则会握手失败。

### 5) 检查端口与监听地址
默认监听：`127.0.0.1:8765`

```bash
python main.py --server --host 0.0.0.0 --port 8765
```

如果前端/客户端不在同机，通常需要 `--host 0.0.0.0`。

### 6) 查看服务端日志关键字
- `Origin allowlist enabled`：白名单已启用
- `Reject websocket handshake: origin not allowed`：Origin 不在白名单
- `Reject websocket handshake: origin allowlist disabled`：白名单未配置，按安全默认拒绝

### 7) 最小安全生产配置模板（建议）

```bash
# 必配：显式 Origin 白名单（不要留空）
SANGUOSHA_WS_ALLOWED_ORIGINS="https://game.example.com"

# 生产建议关闭开发快捷开关
SANGUOSHA_DEV_ALLOW_LOCALHOST=0

# 建议启用 TLS（客户端使用 wss://）
SANGUOSHA_WS_SSL_CERT="/path/to/fullchain.pem"
SANGUOSHA_WS_SSL_KEY="/path/to/privkey.pem"

# 可选：按容量规划调整
SANGUOSHA_WS_MAX_CONN=200
SANGUOSHA_WS_MAX_CONN_PER_IP=8
SANGUOSHA_WS_RATE_MAX=30
```

### 8) `--connect` 参数合法/非法示例

| 输入示例 | 结果 | 说明 |
|---|---|---|
| `--connect localhost:8765` | ✅ 连接 `ws://localhost:8765` | 自动补全 `ws://` |
| `--connect "  localhost:8765  "` | ✅ 连接 `ws://localhost:8765` | 自动去除首尾空白 |
| `--connect ws://127.0.0.1:8765` | ✅ 直接使用 | 已是合法 ws URL |
| `--connect wss://game.example.com` | ✅ 直接使用 | 已是合法 wss URL |
| `--connect "   "` | ❌ 退出码 2 | 空值，提示 `--connect 参数无效` |
| `--connect http://example.com` | ❌ 退出码 2 | 仅支持 `ws://` / `wss://` |
| `--connect ws://:8765` | ❌ 退出码 2 | 缺少主机名 |
| `--connect localhost:abc` | ❌ 退出码 2 | 端口必须是数字 |
| `--connect localhost:70000` | ❌ 退出码 2 | 端口需在 `1-65535` |

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

## 👥 武将列表（32）

**蜀（13）**：刘备(仁德/激将)、界关羽(武圣/义绝)、张飞(咆哮)、诸葛亮(观星/空城)、界赵云(龙胆/涯角)、马超(马术/铁骑)、黄月英(集智/奇才)、黄忠(烈弓)、魏延(狂骨)、徐庶(推心/祤福)、胡金定(轻缘/重身)、界法正(眩惑/恩怨)、向宠(固营/睦阵)

**魏（7）**：曹操(奸雄/护驾)、司马懿(反馈/鬼才)、夏侯惇(刚烈)、界张辽(突袭)、徐晃(断粮)、曹仁(据守)、夏侯渊(神速)

**吴（7）**：孙权(制衡/救援)、周瑜(英姿/反间)、大乔(国色/流离)、甘宁(奇袭)、吕蒙(克己)、黄盖(苦肉)、孙尚香(结姻/枭姬)

**群（5）**：吕布(无双)、华佗(青囊/急救)、貂蝉(离间/闭月)、谋袁术(矜名/枭噬/厌粱)、界刘表(自守/宗室)

## 📁 项目结构

```
sanguosha/
├── main.py                          # 入口（TUI / 服务端 / 客户端 / 回放）
├── pyproject.toml                   # 项目配置 & 依赖
├── game/                            # 🎯 游戏核心逻辑
│   ├── engine.py                    #   游戏引擎 (异步)
│   ├── player.py                    #   玩家 / 身份 / 装备
│   ├── player_manager.py            #   统一玩家管理器
│   ├── card.py                      #   卡牌 / 牌堆 / 枚举
│   ├── hero.py                      #   武将加载
│   ├── skill.py                     #   技能系统（DSL-first + Python fallback）
│   ├── skill_resolver.py            #   技能解析器
│   ├── skill_plugin.py              #   插件系统
│   ├── skills/                      #   按势力分包的技能处理器
│   │   ├── wei.py / shu.py / wu.py / qun.py
│   ├── phase_fsm.py                 #   回合阶段状态机
│   ├── context.py                   #   GameContext 协议
│   ├── exceptions.py                #   层次化异常体系
│   ├── replay.py                    #   回放系统
│   ├── match_history.py             #   战绩历史
│   ├── combat.py                    #   战斗子系统
│   ├── card_resolver.py             #   卡牌结算
│   ├── damage_system.py             #   伤害计算 / 濒死 / 死亡
│   ├── equipment_system.py          #   装备子系统
│   ├── judge_system.py              #   判定子系统
│   ├── game_controller.py           #   游戏控制器 (异步)
│   ├── config.py                    #   配置校验系统
│   ├── events.py                    #   异步事件总线
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
python -m pytest tests/ -v                                                                 # 全量测试
python -m pytest tests/test_identity_sync_state.py tests/test_identity_sync_heroes.py tests/test_identity_sync_ai.py tests/test_integration.py -q
python -m pytest --cov=game --cov=ai                                                       # 含覆盖率报告
python -m ruff check .                                                                     # 静态分析
python -m mypy game ai net                                                                 # 类型检查
```

### 性能 Profiling（Phase 5 收口）

```bash
# 1) 采集带 pytest 开销的性能快照
python -m cProfile -o perf_auto_battle.prof -m pytest tests/test_auto_battle.py::TestAutoBattle::test_multiple_battles -q

# 2) 查看 Top 热点（累计耗时）
python -c "import pstats; p=pstats.Stats('perf_auto_battle.prof'); p.sort_stats('cumtime').print_stats(30)"

# 3) 采集去除 pytest 框架开销的纯模拟快照
python -c "import cProfile,pstats; from tests.test_auto_battle import AutoBattleSimulator; pr=cProfile.Profile(); pr.enable(); sim=AutoBattleSimulator(player_count=6,max_rounds=120); sim.run_game(); pr.disable(); pr.dump_stats('perf_sim.prof'); p=pstats.Stats('perf_sim.prof'); p.sort_stats('cumtime').print_stats(40)"
```

已完成的低风险优化：`i18n.card_name()` 引入翻译反向索引缓存，避免重复全表扫描。

### 扩展武将

1. `data/heroes.json` — 添加武将数据
2. `game/skills/<faction>.py` — 实现对应势力的技能处理器（使用 `@skill_handler` 装饰器注册）
3. `ai/` — 在对应策略文件中添加 AI 技能决策

### 扩展卡牌

1. `data/cards.json` — 添加卡牌数据
2. `game/engine.py` — 添加 `use_card` 处理路由
3. `ui/textual_ui/widgets/card_widget.py` — 添加 `CARD_EFFECT_DESC` tooltip

## 📝 版本历史

### v4.1.1 (2026-03-11) — MSIX 打包资源校验加固

- `build_msix.py` 默认拒绝 `Assets/` 中的占位 PNG，避免把占位图误打进正式 MSIX 包
- 仅在显式传入 `--allow-placeholder-assets` 时才允许开发态继续复用占位资源，并输出警告
- 补充对应测试与 `MSIX_README.md` 说明

### v4.1.0 (2026-03-11) — 身份模式内容同步 & AI/Headless 补强

**身份模式同步：**
- 新增 5 名 OL 同步武将：谋袁术、胡金定、界刘表、界法正、向宠
- 补齐对应技能与事件语义：`矜名/枭噬/厌粱`、`轻缘/重身`、`自守/宗室`、`眩惑/恩怨`、`固营/睦阵`
- headless / 房间模式启动路径统一初始化 `SkillSystem`，并补齐 `GAME_START` / `ROUND_START` 生命周期
- 普通 / 困难 AI 支持 `眩惑`、`睦阵`、`厌粱` 自动使用
- 新增 `tests/test_identity_sync_heroes.py` 与 `tests/test_identity_sync_ai.py`，相关状态/集成回归通过

### v4.0.0 (2026-02-21) — 架构升级 & 全面强化

**架构重构（28 项改进）：**
- 异步引擎转换 — 全异步 async/await 底层，支持真实并发
- PlayerManager 统一玩家管理 — 单一职责玩家生命周期管理
- 阶段状态机 (PhaseFSM) — 形式化回合流转，消除程序性 bug
- 异常体系标准化 — GameError 层次化异常代替裸 raise
- GameContext 协议 — 解耦引擎依赖，提升可测试性

**网络 & 安全：**
- WebSocket TLS 支持 + 会话重连机制 + 速率限制
- is_ai 门控 — 防止协议层混淆 AI/人类操作

**游戏系统：**
- 无懂可击链式响应 — 支持连环无懂
- 数据驱动技能 (skill_config.json) — DSL 优先 + Python 回退
- 回放系统 / 战绩历史 / 插件系统
- 主题系统 (classic/dark/solarized)

**质量：**
- 1503 测试用例全部通过，覆盖率 77.91%
- i18n 完整审计 (zh_CN / en_US)
- 统一日志标准 (tools/log_config.py)
- 配置校验 + 无障碍支持 + ARCHITECTURE.md

### v3.3.1 (2026-02-10) — PyInstaller 打包支持

- 新增 `build.py` 自动化构建脚本（PyInstaller 6.18 + Python 3.14）
- 支持单文件 exe 双击运行，无需安装 Python
- 发布 GitHub Release 附带可执行文件

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