# 三国杀 - 模块架构设计文档

## 概览

三国杀命令行终端版采用事件驱动 + 分层架构，核心分为 5 个层级：

```
┌─────────────────────────────────────────────────────────┐
│                    入口层 (Entry)                         │
│  main.py ── SanguoshaGame (CLI 控制器)                   │
│  main.py ── argparse (--ui / --server / --connect)       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼──────────────────────────────┐
│                    UI 层 (Presentation)                   │
│  ui/textual_ui/     ── SanguoshaApp (Textual TUI)       │
│    ├── app.py       ── Textual App + Screen 路由         │
│    ├── bridge.py    ── TextualBridge (引擎↔TUI 适配)     │
│    ├── screens/     ── 6 个独立 Screen                   │
│    ├── widgets/     ── CardWidget / HpBar / PlayerPanel  │
│    ├── modals/      ── TargetModal / WuxieModal / ...    │
│    └── styles/      ── game.tcss                         │
│  ui/protocol.py     ── GameUI Protocol (类型抽象)        │
│  ui/input_safety.py  ── 安全输入模块                     │
└────────────────────────┬──────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  游戏逻辑层 (Game Core)                   │
│  game/engine.py         ── GameEngine (核心引擎)         │
│  game/player.py         ── Player / Identity / Equipment │
│  game/card.py           ── Card / Deck / CardName 枚举   │
│  game/hero.py           ── Hero / HeroRepository / Skill │
│  game/skill.py          ── SkillSystem (技能执行)        │
│  game/skill_dsl.py      ── DSL 定义加载                  │
│  game/skill_interpreter.py ── DSL 解释器                 │
│  game/damage_system.py  ── DamageSystem (伤害计算)       │
│  game/turn_manager.py   ── TurnManager (回合管理)        │
│  game/win_checker.py    ── WinChecker (胜负判定)         │
│  game/constants.py      ── SkillId 枚举 / 常量           │
│  game/exceptions.py     ── 自定义异常                    │
│  game/save_system.py    ── SaveSystem (存档/读档)        │
│  game/effects/          ── 卡牌效果注册系统              │
│    ├── base.py          ── CardEffect 基类               │
│    ├── basic.py         ── 基本牌效果 (杀/闪/桃)         │
│    ├── trick.py         ── 锦囊牌效果                    │
│    ├── data_driven.py   ── 数据驱动效果加载              │
│    └── registry.py      ── EffectRegistry 注册表         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 事件/动作层 (Event Bus)                   │
│  game/events.py    ── EventBus / EventType / GameEvent   │
│  game/actions.py   ── GameAction / GameRequest / Response│
│  game/request_handler.py ── RequestHandler (UI 请求)     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   AI 层 (Intelligence)                    │
│  ai/bot.py  ── AIBot (决策引擎)                          │
│    ├── 嘲讽值系统 (ThreatSystem)                         │
│    ├── 局势评分 (evaluate_game_state)                    │
│    ├── 身份推断 (infer_identity)                         │
│    └── 3 难度级别 (Easy / Normal / Hard)                 │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  网络层 (Network)                         │
│  net/server.py   ── GameServer (WebSocket 服务端)        │
│  net/client.py   ── GameClient (WebSocket 客户端)        │
│  net/protocol.py ── 消息协议定义                         │
└─────────────────────────────────────────────────────────┘
```

## 模块依赖关系

```
main.py
  ├── game/engine.py ─────┐
  │     ├── game/player.py │
  │     ├── game/card.py   │  game/ 内部互相引用
  │     ├── game/hero.py   │
  │     ├── game/events.py │
  │     ├── game/actions.py│
  │     └── game/effects/  │
  ├── ai/bot.py ──────────┤  AI 依赖 game/ 层
  │     └── game/engine    │
  └── ui/textual_ui/ ─────┘  UI 依赖 game/ 层 (Textual TUI 唯一)
```

**关键原则:**
- UI 层通过 `GameUI` Protocol 与引擎解耦
- AI 层仅依赖 game/ 公开接口
- 事件总线 (EventBus) 实现模块间松耦合
- 效果注册表 (EffectRegistry) 实现卡牌效果可插拔

## 数据流

```
用户输入 ──→ UI 层 ──→ main.py (Controller)
                            │
                            ▼
                      GameEngine.execute_action()
                            │
                            ▼
                      EventBus.publish(event)
                            │
                      ┌─────┼─────┐
                      ▼     ▼     ▼
                   SkillSystem  AI  UI (日志更新)
```

## 数据文件

```
data/
  ├── cards.json        ── 108 张标准牌库 (含军争扩展)
  ├── card_effects.json ── 数据驱动卡牌效果定义
  ├── heroes.json       ── 20+ 武将定义
  ├── heroes_new.json   ── 扩展武将 (待合并)
  └── skill_dsl.json    ── 技能 DSL 声明
```

## 已知架构问题 (待 Phase B 改进)

1. **SanguoshaGame 过大** (820 行): 同时承担控制器 + 视图适配器职责
2. **GameEngine 过大** (1000+ 行): 回合管理/效果/伤害/日志/胜负 混合
3. **双重分发路径**: `_card_handlers` 旧字典 与 `effect_registry` 新系统并存
4. **Screen 未拆分**: Textual `app.py` 中所有 Screen 类在同一文件
