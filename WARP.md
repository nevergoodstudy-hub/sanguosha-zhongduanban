# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common commands

### Install deps

```bash
python -m pip install -r requirements.txt
```

### Run the game (CLI)

```bash
python main.py
```

### Run tests

```bash
# full suite
python -m pytest tests/ -v

# a single test file
python -m pytest tests/test_juunzheng.py -v

# a single test (pytest node id)
python -m pytest tests/test_game.py::TestDeck::test_draw_cards -v

# filter by substring (handy when you don’t know the exact test name)
python -m pytest tests/ -k juunzheng -v
```

### Stress / long-running simulations

```bash
# stress test script (100+ AI games)
python tests/test_auto_battle_stress.py
```

### Package to a Windows exe (PyInstaller)

```bat
build.bat
```

Manual equivalent:

```bash
python -m pip install pyinstaller
pyinstaller sanguosha.spec --noconfirm
```

Build outputs land under `dist/` (this repo currently contains both `dist/sanguosha.exe` and `dist/三国杀.exe`).

### Lint/format

No lint/format tool is configured in-repo (no `pyproject.toml`, `ruff.toml`, etc.).

## Architecture overview (big picture)

### Runtime entry points

- `main.py` is the interactive entry point. It wires together:
  - `ui.terminal.TerminalUI` (rendering + user prompts)
  - `game.engine.GameEngine` (rules + state machine)
  - `game.skill.SkillSystem` (skill implementations)
  - `ai.bot.AIBot` instances for AI players

### Core game module (`game/`)

- `game/engine.py` (`GameEngine`) is the authoritative rules engine:
  - Owns the deck (`Deck`) and hero data (`HeroRepository`) and the player list.
  - Implements the turn/phase loop (`phase_prepare/draw/play/discard/end`) and card resolution (`use_card` + per-card handlers like `_use_sha`).
  - Implements damage, death, and win conditions (including “军争” mechanics like 属性伤害与铁索连环传导 via `deal_damage`).
  - Provides a headless API for simulations: `setup_headless_game()`, `run_headless_turn()`, `run_headless_battle()`.

- `game/card.py` defines the card model and deck mechanics:
  - `Card`, `CardType`, `CardSubtype`, `CardSuit`, `DamageType`, and `Deck`.
  - `CardName` is a centralized set of string constants used throughout the engine.

- `game/hero.py` defines the hero/skill data model and loads content:
  - `Hero` + `Skill` dataclasses.
  - `HeroRepository` loads `data/heroes.json`.

- `game/player.py` defines player state:
  - `Player` + `Identity` and the equipment zone (`Equipment`).
  - Tracks per-turn state (e.g., sha usage counts) and “军争” state (chain/alcohol flags).

- `game/skill.py` contains the concrete skill logic:
  - `SkillSystem` is essentially a dispatcher from skill id → handler (`_skill_handlers`).
  - Engine calls into it for timed triggers (e.g. prepare-phase skills) and for active skill use.

- `game/events.py` contains an `EventBus` implementation (subscribe/publish, priorities, cancel/modify) plus `EventEmitter`.
  - Today, the engine uses the bus primarily for log messages (`GameEngine.log_event`), and the event system is covered by `tests/test_events.py`.

- `game/actions.py` defines an action/request abstraction (`GameAction`, `GameRequest`, validators/executor) intended to formalize UI↔engine interaction.
  - The current CLI flow mostly calls engine methods directly; this module is useful when refactoring toward a stricter action-driven interface.

### AI (`ai/`)

- `ai/bot.py` (`AIBot`) implements the AI decision loops (easy/normal/hard). AI primarily interacts with the engine via `engine.use_card(...)` and helper queries like range/targets.

### UI (`ui/`)

- `ui/terminal.py` is a terminal renderer + input handler. The engine calls back into it for prompts during reactive windows (e.g. `ask_for_shan/sha/tao`, plus lord-skill prompts like `ask_for_jijiang/hujia`).

### Data (`data/`)

- `data/cards.json` is loaded by `Deck`.
- `data/heroes.json` is loaded by `HeroRepository`.

This repository is partially data-driven: adding a new hero/card usually means updating the relevant JSON and then implementing the corresponding rule hooks in code (skills in `game/skill.py`, card resolution in `game/engine.py`).
