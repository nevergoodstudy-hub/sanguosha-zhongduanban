# WARP.md

This file gives terminal-first guidance for tools and contributors working in
this repository.

## Project Snapshot

- Project: `sanguosha`
- Current package version: `4.1.1`
- Primary runtime entrypoint: [`main.py`](./main.py)
- Packaging helpers:
  - [`build.py`](./build.py)
  - [`build_msix.py`](./build_msix.py)

## Recommended Setup

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

For CI or release-parity checks, prefer `python -m pip install ".[dev]"` when you need a regular non-editable environment.

## Common Commands

### Run the local game

```bash
python main.py
```

### Run the multiplayer server

```bash
python main.py --server 127.0.0.1:8765
```

### Run the multiplayer client

```bash
python main.py --connect 127.0.0.1:8765
```

### Run tests

```bash
# full suite
python -m pytest tests/ -v --tb=short

# targeted files
python -m pytest tests/test_build_msix.py -q
python -m pytest tests/test_build_script.py -q
python -m pytest tests/test_net_client.py tests/test_net_server.py -q
```

### Lint and format

```bash
python -m ruff check .
python -m ruff format .
python -m mypy main.py game ai net --config-file pyproject.toml
```

### Build desktop artifacts

```bash
# default onefile build
python build.py

# named onefile build
python build.py --name sanguosha-windows-amd64

# onedir build
python build.py --onedir --name sanguosha-dev
```

Expected output paths are computed by `build.expected_output_path(...)`.
Do not assume a hard-coded executable name like `dist/sanguosha.exe`.

### Build an MSIX package

```bash
# package the output produced by build.py --name <value>
python build_msix.py --exe-name sanguosha

# package an explicit executable path
python build_msix.py --exe-path dist/sanguosha.exe

# local validation only: allow placeholder assets
python build_msix.py --allow-placeholder-assets
```

Notes:

- `build_msix.py` stages from the selected PyInstaller payload.
- Onefile and onedir outputs are both supported.
- `--package-executable` controls the filename referenced inside the MSIX
  manifest.
- If `makeappx.exe` is missing, the script still prepares `msix_output/` for
  inspection.

## Current Architecture

### Local runtime

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
```

### Multiplayer runtime

```text
main.py --server
  -> net.settings.ServerSettings
  -> net.server.GameServer
     -> net.server_dispatcher.ServerMessageDispatcher
     -> net.server_session.ServerSessionManager

main.py --connect
  -> net.settings.ClientSettings
  -> net.client.GameClient
     -> net.client_session.ClientSession
```

### Important network split

The old "single session layer" description is no longer accurate.

- `net.client_session.py` owns client transport lifecycle.
- `net.server_dispatcher.py` owns decoded server message routing.
- `net.server_session.py` owns reconnect replay and room cleanup.
- `net.settings.py` validates startup configuration with Pydantic models.

## Release Model

- CI is defined in [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)
- GitHub releases are tag-driven through
  [`.github/workflows/release.yml`](./.github/workflows/release.yml)
- Release assets are currently:
  - `sanguosha-windows-amd64.zip`
  - `sanguosha-linux-amd64.tar.gz`
  - `sanguosha-macos-amd64.tar.gz`

## Contribution Notes

- Prefer updating docs when changing architecture or packaging flows.
- Keep build docs aligned with `build.py` and `build_msix.py`, not with old
  spec-file-only workflows.
- When changing multiplayer behavior, check the client facade, transport
  session, dispatcher, and server session manager together.
