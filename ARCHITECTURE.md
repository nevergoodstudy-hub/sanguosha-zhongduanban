# Architecture Overview

This document describes the current codebase shape after the network/session
and CI/release refactors on branch `codex/deep-refactor`.

## Runtime Entry Points

`main.py` is the single runtime entry.

- Local game mode:
  - `main.py`
  - `game.game_controller.GameController`
  - `game.engine.GameEngine`
- Server mode:
  - `python main.py --server [HOST:PORT]`
  - `net.server.GameServer`
- Client mode:
  - `python main.py --connect HOST:PORT`
  - `net.client.cli_client_main()`
  - `net.client.GameClient`

## High-Level Dependency Graph

```text
main.py
  -> game.game_controller.GameController
     -> game.engine.GameEngine
        -> game.turn_manager.TurnManager
        -> game.combat.CombatSystem
        -> game.card_resolver.CardResolver
        -> game.equipment_system.EquipmentSystem
        -> game.judge_system.JudgeSystem
        -> game.skill.SkillSystem
        -> game.events.EventBus

main.py --server
  -> net.settings.ServerSettings
  -> net.server.GameServer
     -> net.server_dispatcher.ServerMessageDispatcher
     -> net.server_session.ServerSessionManager
     -> net.server_types.Room / ConnectedPlayer / PendingGameRequest
     -> net.security / net.rate_limiter
     -> game.engine.GameEngine (headless, per room)

main.py --connect
  -> net.settings.ClientSettings
  -> net.client.cli_client_main()
  -> net.client.GameClient
     -> net.client_session.ClientSession
     -> net.protocol.ClientMsg / ServerMsg
```

## Core Design Patterns

- Facade:
  - `game.engine.GameEngine` coordinates gameplay subsystems.
  - `net.client.GameClient` exposes a high-level multiplayer client API.
- Event Bus:
  - `game.events.EventBus` decouples state changes, logs, and passive reactions.
- Strategy:
  - `ai.AIBot` delegates decisions to `EasyStrategy`, `NormalStrategy`, and
    `HardStrategy`.
- Dispatcher + Codec split:
  - `net.server_dispatcher.ServerMessageDispatcher` owns message routing.
  - `net.action_codec` and `net.request_codec` convert between transport payloads
    and domain-layer actions/requests.
- Session separation:
  - `net.client_session.ClientSession` owns transport lifecycle on the client.
  - `net.server_session.ServerSessionManager` owns room cleanup and reconnect
    replay on the server.
- Validated runtime configuration:
  - `net.settings` uses Pydantic models to validate server/client startup
    options before runtime.

## Local Game Architecture

The local game stack remains centered around `game/`.

### Main responsibilities

- `game/game_controller.py`
  - Thin facade over extracted runtime coordinators.
  - Keeps `main.py` from depending directly on low-level engine details.
- `game/engine.py`
  - Central gameplay coordinator.
  - Wires together subsystems, request handling, logging, and win checks.
- `game/turn_manager.py`
  - Owns phase sequencing and turn progression.
- `game/combat.py`
  - Handles combat-oriented card interactions such as SHA, SHAN, Juedou, and
    related damage flow.
- `game/card_resolver.py`
  - Resolves non-combat card effects and card execution paths.
- `game/equipment_system.py`
  - Equip, unequip, and equipment-triggered effects.
- `game/judge_system.py`
  - Delayed trick judgment handling.
- `game/skill.py`
  - Active and passive skill execution hooks.
- `game/events.py`
  - Event definitions and dispatch bus.
- `game/phase_fsm.py`
  - Validates phase transitions.

### Runtime coordinator split

`game/runtime/` now owns the controller-adjacent orchestration that used to
live inline in `game/game_controller.py`.

- `game/runtime/controller_io.py`
  - Async-friendly adapter around synchronous `GameUI` methods.
- `game/runtime/session.py`
  - Session startup, outer game loop, human discard handling, and game-over
    resolution.
- `game/runtime/turns.py`
  - Turn banners and phase sequencing for AI and human players.
- `game/runtime/play_phase.py`
  - Card-play branches, skill prompts, and play-phase action flow.
- `game/runtime/startup.py`
  - Human hero selection, AI hero assignment, and AI bot initialization.

### AI layer

- `ai/bot.py`
  - Thin coordinator around difficulty strategies.
- `ai/easy_strategy.py`
  - Low-complexity play logic.
- `ai/normal_strategy.py`
  - Rule-based priority decisions.
- `ai/hard_strategy.py`
  - Threat evaluation and stronger tactical choices.

## Network Stack After Refactor

The biggest architectural change in this branch is the network-layer split.
The old documentation treated `net/session.py` as the main live reconnect
layer. That is no longer accurate.

### Transport and protocol

- `net/protocol.py`
  - Transport message schema:
  - `MsgType`
  - `ClientMsg`
  - `ServerMsg`
  - room/game message factories
- `net/models.py`
  - Message validation helpers shared by the transport layer.
- `net/security.py`
  - Origin validation, token handling, connection tracking, and safety limits.
- `net/rate_limiter.py`
  - Token bucket rate limiting.

### Domain/transport bridging

- `net/action_codec.py`
  - Converts client-side JSON payloads into domain `GameAction` objects such as:
  - `PlayCardAction`
  - `UseSkillAction`
  - `DiscardAction`
  - `EndPhaseAction`
- `net/request_codec.py`
  - Converts:
  - `GameRequest` -> `ServerMsg`
  - client response payload -> `GameResponse`
  - This is the bridge between multiplayer transport and the engine request
    system.

### Validated startup settings

- `net/settings.py`
  - `ServerSettings`
  - `ClientSettings`
  - These models normalize and validate runtime inputs such as host, port,
    reconnect timings, heartbeat intervals, and TLS pair configuration.

### Server-side runtime split

- `net/server_types.py`
  - Lightweight server data models:
  - `ConnectedPlayer`
  - `PendingGameRequest`
  - `Room`
- `net/server.py`
  - Owns the async WebSocket server runtime.
  - Keeps room registry, player registry, broadcast helpers, engine startup,
    and room-level game execution.
  - Delegates message routing and reconnect cleanup instead of owning every
    behavior inline.
- `net/server_dispatcher.py`
  - Owns decoded client-message routing.
  - Handles room create/join/leave/list/start.
  - Handles game actions, game responses, hero choices, chat, and heartbeats.
  - Applies payload validation and rate-limit checks before side effects.
- `net/server_session.py`
  - Owns room membership cleanup and reconnect replay behavior.
  - Replays missed room events based on per-room sequence numbers.

### Client-side runtime split

- `net/client.py`
  - `GameClient` is now the high-level facade.
  - Keeps typed handlers, room/player state, message dispatch, and convenience
    APIs such as:
  - `create_room()`
  - `join_room()`
  - `play_card()`
  - `use_skill()`
  - `respond()`
  - `chat()`
  - Also provides `cli_client_main()` for command-line network play.
- `net/client_session.py`
  - Owns the raw WebSocket lifecycle:
  - connect
  - disconnect
  - receive loop
  - heartbeat loop
  - reconnect loop
  - `GameClient` no longer needs to mix transport retry logic with protocol
    dispatch logic.

### Generic session helper retained separately

- `net/session.py`
  - Contains a generic token-based `SessionManager` and `PlayerSession`.
  - It is separate from the live `GameServer` reconnect path, which now uses
    `ServerSessionManager`.
  - This file remains useful as a standalone session utility and is still
    covered by tests, but it is not the primary runtime server-session entry.

## Network Message Flow

### Client -> Server action path

```text
UI / CLI input
  -> net.client.GameClient.send()
  -> net.protocol.ClientMsg
  -> websocket transport
  -> net.server_dispatcher.ServerMessageDispatcher
  -> net.action_codec.decode_client_action()
  -> game.actions.GameAction
  -> game engine
```

### Engine request -> Client response path

```text
game engine emits GameRequest
  -> net.request_codec.encode_game_request()
  -> net.protocol.ServerMsg
  -> client receives request
  -> client responds with ClientMsg.game_response(...)
  -> net.request_codec.decode_game_response()
  -> game.actions.GameResponse
  -> pending request future resolved in server runtime
```

### Reconnect path

```text
disconnect
  -> room event log keeps sequenced ServerMsg entries
  -> reconnect with token + last_seq
  -> net.server_session.ServerSessionManager.reconnect_player()
  -> replay all events where seq > last_seq
```

## Current Directory Structure

```text
ai/            AI decision layer
data/          Card and hero data
docs/          Supporting documentation
game/          Core game rules and subsystems
i18n/          Localization resources
net/           Multiplayer server/client/protocol stack
tests/         Unit and integration tests
tools/         Replay and helper tooling
ui/            Terminal and Textual UI implementations

main.py        Unified runtime entry
build.py       Cross-platform packaging entry
build_msix.py  Windows MSIX packaging path
versioning.py  Version derivation helpers
```

## Notes for Future Refactors

- Keep `GameClient` focused on protocol and public API; transport retries belong
  in `ClientSession`.
- Keep `GameServer` focused on orchestration; message routing belongs in
  `ServerMessageDispatcher`.
- If reconnect behavior grows further, extend `ServerSessionManager` rather than
  moving replay logic back into `server.py`.
- Treat `net/action_codec.py` and `net/request_codec.py` as the boundary between
  transport payloads and the game domain model.
- When changing startup behavior, update both `main.py` CLI help and
  `net/settings.py` validators together.
