# Architecture Overview

## Module Dependency Graph

```
main.py → GameController → GameEngine → [CombatSystem, CardResolver, EquipmentSystem, JudgeSystem, TurnManager]
                        → GameUI (Textual)
net/server.py → GameServer → Room → GameEngine (headless)
ai/bot.py → AIBot → [EasyStrategy, NormalStrategy, HardStrategy]
```

## Data Flow

1. **Player input** → UI/Network → RequestHandler → GameEngine
2. **GameEngine** → EventBus → [CombatSystem, EquipmentSystem, JudgeSystem, ...]
3. **State change** → EventBus → UI update / Network broadcast

## Key Design Patterns

- **Event Bus** (`game/events.py`): Decoupled game event handling with priority-based dispatch. Supports both sync and async handlers.
- **Strategy Pattern** (`ai/`): 3-tier AI system (EasyStrategy → NormalStrategy → HardStrategy) via AIBot thin coordinator.
- **Observer** (`game/events.py`): UI reacts to engine state changes via EventBus subscriptions.
- **Facade** (`game/engine.py`): GameEngine coordinates subsystems without exposing internals.
- **Protocol** (`game/context.py`): GameContext Protocol for structural subtyping — subsystems depend on interface, not concrete class.
- **FSM** (`game/phase_fsm.py`): Phase transitions validated by finite state machine.

## Directory Structure

```
game/           Core game logic
  engine.py         GameEngine facade
  combat.py         SHA/SHAN/JUEDOU/Wuxie combat system
  card.py           Card, Deck, CardName
  card_resolver.py  Trick card effect resolution
  equipment_system.py  Equipment equip/unequip/effects
  judge_system.py   Delayed scroll judgment
  turn_manager.py   Turn phase execution
  phase_fsm.py      FSM phase transition validation
  player.py         Player model
  player_manager.py Extracted player list management
  events.py         EventBus + EventType enum
  context.py        GameContext Protocol
  config.py         Centralized configuration (env-var overridable)
  exceptions.py     Exception hierarchy
  skill.py          SkillSystem (DSL + Python handlers)
  skill_resolver.py Data-driven skill parameter resolver
  distance_cache.py Distance calculation cache
  replay.py         Replay recorder/player
  ...
ai/             AI system
  bot.py            AIBot coordinator
  strategy.py       AIStrategy base
  easy_strategy.py  Random play
  normal_strategy.py Rule-based play
  hard_strategy.py  Threat evaluation + identity inference
  decision_log.py   AI decision transparency logging
net/            Network/multiplayer
  server.py         WebSocket game server (async game loop)
  client.py         WebSocket client
  session.py        Session/reconnection management
  security.py       Origin validation, rate limiting, tokens
  rate_limiter.py   Token bucket rate limiter
  protocol.py       Message types and serialization
  models.py         Message validation
ui/             Terminal UI (Textual)
  ...
i18n/           Internationalization (zh_CN, en_US)
data/           Game data (JSON)
  cards.json        Card definitions
  heroes.json       Hero definitions
  skill_dsl.json    Skill behavior DSL
  skill_config.json Skill parameter config
tools/          Development tools
  profiling.py      Performance profiling (@timed)
  replay.py         CLI replay tool
tests/          Test suite (1400+ tests)
```

## Subsystem Interactions

### Combat Flow (SHA)
```
use_card() → CombatSystem.use_sha()
  → check: range, kongcheng, renwang, tengjia
  → request_shan() via RequestHandler
  → deal_damage() → EventBus(DAMAGE_INFLICTED)
    → passive skills react (jianxiong, fankui, ganglie)
    → chain propagation if fire/thunder
    → dying check → request_tao() → death handling
```

### Event-Driven Architecture
All subsystems communicate through EventBus. Key event types:
- `DAMAGE_INFLICTED` / `DEATH` → trigger passive skills, invalidate distance cache
- `EQUIPMENT_EQUIPPED` / `EQUIPMENT_UNEQUIPPED` → invalidate distance cache
- `TURN_START` / `TURN_END` → UI updates, skill resets
- `CARD_USED` / `CARD_EFFECT` → logging, UI notifications
