# Deep Refactor Progress Report

This document summarizes the branch-level refactor work on
`codex/deep-refactor`. It replaces the older report that described the project
 as a mostly monolithic CLI build with a partially outdated multiplayer and
packaging story.

## Refactor Scope

The current branch is focused on four major areas:

1. Runtime, controller, and network architecture cleanup
2. Build and release pipeline hardening
3. MSIX packaging alignment with the PyInstaller build flow
4. Documentation refresh so contributors see the current system, not the
   pre-refactor layout

## Major Improvements Landed

### 1. Local runtime orchestration is now split by concern

The local game controller is no longer carrying long inline implementations for
session startup, turn flow, and play-phase prompts.

- `game.game_controller.GameController` is now a thin facade over runtime
  coordinators
- `game.runtime.session.SessionCoordinator` owns session lifecycle and game-over
  handling
- `game.runtime.turns.TurnCoordinator` owns phase and turn sequencing
- `game.runtime.play_phase.PlayPhaseCoordinator` owns play-phase interaction
  branches and async prompt logging
- `game.runtime.startup.StartupCoordinator` owns hero selection and AI bot
  startup

This removes the old unreachable legacy fallback tail from
`game/game_controller.py` and keeps controller seams small enough for targeted
tests and monkeypatch-based coverage.

### 2. Multiplayer responsibilities are now split by concern

The multiplayer stack is no longer described or implemented as a single
"session" blob.

- `net.client.py` is the high-level multiplayer client facade
- `net.client_session.py` owns transport lifecycle, reconnect, heartbeat, and
  receive loops
- `net.server.py` owns room-level runtime and WebSocket server orchestration
- `net.server_dispatcher.py` owns decoded message routing and room/action
  commands
- `net.server_session.py` owns reconnect replay and room cleanup behavior
- `net.settings.py` validates startup configuration with Pydantic models before
  runtime

This split reduces coupling between transport, request routing, and game-room
state transitions.

### 3. Build outputs are now name-aware

The desktop build flow is centered on `build.py`.

- `python build.py --name <value>` controls the produced artifact name
- `build.expected_output_path(...)` is the authoritative way to resolve output
  paths
- CI and release workflows now package named outputs instead of assuming a
  single hard-coded executable path

This makes local builds, CI builds, and release assets follow the same naming
model.

### 4. Release automation is tag-driven and cross-platform

Release automation now builds and publishes platform artifacts through GitHub
Actions.

- CI installs the project from `pyproject.toml`
- Release artifacts are created from tag pushes matching `v*.*.*`
- Windows assets are shipped as `.zip`
- Linux and macOS assets are shipped as `.tar.gz` so executable permissions are
  preserved

### 5. MSIX packaging now follows the selected build output

`build_msix.py` was refactored so it no longer assumes a single fixed file like
`dist/sanguosha.exe`.

Current capabilities:

- package a build selected by `--exe-name`
- package an explicit file selected by `--exe-path`
- support both onefile and onedir PyInstaller outputs
- rename the executable referenced inside the package with
  `--package-executable`
- stage from the chosen PyInstaller payload instead of copying unrelated source
  directories into the package root

### 6. Packaging docs were refreshed

The packaging docs now describe:

- real asset requirements in `Assets/`
- placeholder assets as a local-validation-only path
- the current `build.py` -> `build_msix.py` handoff
- current Microsoft tooling expectations around `makeappx.exe` and signing

## Verification Run During This Refactor Slice

The following targeted checks were run during the controller/runtime, build,
and network refactor slices:

```bash
pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py tests/test_subsystems.py -q
pytest tests/test_build_script.py tests/test_build_msix.py tests/test_dependency_metadata.py tests/test_versioning.py -q
pytest tests/test_net_client.py tests/test_net_client_session.py tests/test_net_server.py tests/test_net_server_session.py tests/test_net_server_dispatcher.py tests/test_net_settings.py tests/test_main_connect_cli_integration.py tests/test_main_server_cli_integration.py -q
ruff check game/game_controller.py tests/test_game_controller_coverage.py
```

Targeted result:

- controller/runtime regression slice: passing
- build/release regression slice: passing
- network/client/server regression slice: passing
- targeted controller lint checks: passing

Final branch verification was then rerun against the whole repository before
GitHub publication:

```bash
python -m pytest tests -q --randomly-seed=1318985398
python -m ruff check .
```

Final result:

- full test suite: `1694 passed`
- repository-wide Ruff check: passing

The verification coverage now includes:

- controller hero-selection, skill-log, discard, play-card, and game-over async
  boundaries
- build-script naming, dependency metadata, versioning, and MSIX packaging
- client/session reconnect lifecycle and server dispatcher/session behavior

## Files Most Directly Affected

- `build.py`
- `build_msix.py`
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `net/client.py`
- `net/client_session.py`
- `net/server.py`
- `net/server_dispatcher.py`
- `net/server_session.py`
- `net/settings.py`
- `ARCHITECTURE.md`
- `docs/architecture.md`
- `docs/release-process.md`

## Remaining Follow-Up

This branch has moved the codebase a long way, but there is still follow-up
work worth doing:

- run the broader build-script and release-path verification set before cutting
  a release
- keep README and contributor docs aligned with the branch architecture
- continue shrinking responsibility inside the core gameplay engine where it is
  still acting as a large coordinator
- add end-to-end validation for release packaging and signed MSIX builds on a
  Windows machine with the required SDK tools installed

## Bottom Line

The project is no longer just a terminal card game with an add-on network mode.
It now has a clearer multiplayer architecture, a reproducible build/release
pipeline, and an MSIX packaging flow that matches the actual build artifacts
being produced.
