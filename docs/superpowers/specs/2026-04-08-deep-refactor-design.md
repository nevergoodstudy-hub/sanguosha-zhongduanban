# Deep Refactor Design

## Summary

This document defines the phased deep refactor for the Sanguosha terminal project across four coupled domains:

1. Core engine and request/runtime boundaries
2. Textual UI orchestration and concurrency model
3. Network, security, and configuration boundaries
4. GitHub CI/release automation and delivery workflow

The refactor will be executed as a staged, compatibility-preserving migration rather than a full rewrite. The project already contains meaningful local changes, a mature test suite, and an active GitHub release pipeline. The design therefore optimizes for controlled evolution, visible progress, and continuous verification.

## Goal

Produce a cleaner, safer, and more maintainable architecture that preserves a working gameplay baseline while making future feature work, debugging, and releases significantly easier.

## Scope

### In Scope

- Refactor shared runtime and action boundaries in `game/`
- Reduce god-object behavior in engine/controller layers
- Rework Textual integration to follow a clearer async/worker model
- Unify network server/client policy, runtime settings, and transport safety
- Rebuild GitHub CI/release workflows to align with the new architecture and current security guidance
- Update project documentation to match the new execution model

### Out of Scope

- A full rewrite into a brand-new repository
- Large-scale gameplay feature expansion unrelated to the four target domains
- Broad content expansion of heroes/cards beyond refactor-driven compatibility fixes
- Major visual redesign unrelated to architectural cleanup

## Current State

### Repository Baseline

- Active repository: `D:\Newidea-3\sanguosha_backup_20260121_071454`
- Remote: `origin -> https://github.com/nevergoodstudy-hub/sanguosha-zhongduanban.git`
- Branch relationship: local `main` is in sync with `origin/main`
- Existing local uncommitted changes are present in:
  - `game/combat.py`
  - `game/game_controller.py`
  - `net/server.py`

These changes are treated as first-class inputs to the refactor and must be integrated rather than overwritten.

### Architectural Hotspots

The highest-risk files by complexity and coupling are:

- `game/engine.py`
- `game/request_handler.py`
- `game/game_controller.py`
- `game/skill.py`
- `game/card_resolver.py`
- `game/combat.py`

These files currently blend domain logic, runtime orchestration, and environment-specific behavior in ways that increase regression risk and make staged evolution harder than necessary.

## External Constraints

The design incorporates current official guidance from the primary technologies used by this project:

- Textual worker model and threaded worker restrictions
- websockets production security and TLS guidance
- GitHub Actions secure-use guidance and least-privilege workflow permissions
- Pydantic Settings guidance for environment-driven configuration

These constraints are not optional implementation details; they shape the target architecture.

## Design Principles

### 1. Contract First

Shared runtime contracts must stabilize before outer layers are refactored. UI, network, tests, and automation all depend on core action/request/state semantics.

### 2. Compatibility-Preserving Migration

The system should remain runnable during the migration. Existing entry points may temporarily delegate into new runtime components until legacy paths can be removed safely.

### 3. Domain Logic Must Stay UI- and Transport-Agnostic

Gameplay rules should not depend directly on Textual widgets, blocking console calls, or WebSocket transport details.

### 4. Configuration Must Be Explicit and Validatable

Configuration should come from one coherent settings layer with clear environment, CLI, and default precedence.

### 5. Production Security by Default

Unsafe development shortcuts must be explicit opt-ins and never the silent default.

### 6. Every Phase Must End in Verification

Each stage ends with targeted tests first, then broader regression checks as the refactor surface expands.

## Target Architecture

### Core Runtime Layer

The `game/` package remains the canonical gameplay package. The refactor does not introduce a disruptive top-level package move. Instead, orchestration responsibilities are pulled out of overloaded files into focused runtime components.

#### Target responsibilities

- `game/engine.py`
  - Compatibility facade
  - Thin composition root for runtime services
  - No longer the primary home of detailed orchestration logic

- `game/game_controller.py`
  - Application-level flow only
  - Coordinates menu/setup/play session lifecycle
  - No direct ownership of large gameplay rule branches

- `game/actions.py`
  - Canonical action/request/response protocol definitions
  - Shared across local UI, AI, and network flows

- `game/request_handler.py`
  - Centralized request routing
  - Bridges runtime prompts to AI, UI, or network responders

- `game/context.py`
  - Stable protocol surface for domain services

- `game/runtime/` (new)
  - `session.py`: owns active game session lifecycle
  - `pipeline.py`: action execution pipeline
  - `turns.py`: turn and phase orchestration
  - `routing.py`: request routing orchestration
  - `state.py`: runtime-only derived state helpers

### Domain Services Layer

Existing rule modules remain in `game/` and continue to represent domain sub-systems. The refactor does not flatten them into the runtime layer. Instead, they will consume a cleaner runtime contract.

#### Target responsibilities

- `game/combat.py`
  - Combat resolution only
  - No environment-specific branching

- `game/card_resolver.py`
  - Card resolution orchestration and effect dispatch

- `game/damage_system.py`
  - Damage, dying, death resolution semantics

- `game/equipment_system.py`
  - Equipment state and derived effects

- `game/judge_system.py`
  - Delayed scroll / judgment handling

- `game/skill.py`, `game/skill_resolver.py`, `game/skill_interpreter.py`
  - Skill registration, parameterization, and DSL/Python fallback

- `game/events.py`
  - Stable gameplay event bus
  - Domain events only, not UI assumptions disguised as domain events

- `game/phase_fsm.py`
  - Single source of truth for legal phase progression

### UI Layer

The Textual app should become a consumer of runtime events and request prompts, not a place where core gameplay flow is improvised through ad-hoc blocking calls and scattered thread offloading.

#### Target responsibilities

- `ui/textual_ui/app.py`
  - Textual app entry and screen management

- `ui/textual_ui/bridge.py`
  - Runtime-to-UI adapter only
  - Converts requests and events into Textual messages and state updates

- `ui/textual_ui/state.py` (new)
  - Screen-visible state container
  - Derived, render-friendly data

- `ui/textual_ui/workers.py` (new)
  - Worker orchestration for long-running or blocking operations
  - Main-thread safe message delivery back to the UI

- `ui/textual_ui/screens/*`
  - Presentation and interaction only

- `ui/textual_ui/widgets/*`
  - Render-only components with localized behavior

### Network and Settings Layer

The network stack must stop being a thinly guarded alternate execution path. It should become another transport over the same runtime contracts.

#### Target responsibilities

- `net/server.py`
  - Server application entrypoint and top-level composition

- `net/client.py`
  - Client connection/session integration

- `net/security.py`
  - Origin, rate-limit, connection-policy, and handshake guards

- `net/session.py`
  - Session/reconnect policy

- `net/protocol.py`, `net/models.py`, `net/request_codec.py`, `net/action_codec.py`
  - Explicit transport schema and translation logic

- `net/settings.py` (new) or shared settings module
  - Network-related validated settings

### Automation Layer

GitHub workflows should reflect the project architecture and quality gates rather than acting as loosely coupled shell wrappers.

#### Target responsibilities

- `.github/workflows/ci.yml`
  - Quality checks
  - Test matrix
  - Artifact generation for validation

- `.github/workflows/release.yml`
  - Tag-driven release
  - Release asset generation
  - Consistent permissions and safer action usage

- `build.py`, `build_msix.py`
  - Local build scripts aligned with CI expectations

## Phase Plan

### Phase 0: Baseline Freeze and Isolation

#### Objective

Protect current local work and establish a clean refactor execution space.

#### Deliverables

- Recorded baseline of current dirty files
- Isolated worktree and feature branch before implementation begins
- Baseline verification log

#### Notes

This phase is required before code-heavy implementation work. If no project-local worktree directory exists, the user must choose a location before implementation begins.

### Phase 1: Core Runtime Refactor

#### Objective

Separate runtime orchestration from overloaded engine/controller code.

#### Primary files

- `game/engine.py`
- `game/game_controller.py`
- `game/request_handler.py`
- `game/actions.py`
- `game/context.py`
- `game/runtime/*` (new)

#### Key outcomes

- Introduce a runtime session abstraction
- Centralize turn and request flow
- Reduce direct controller logic branching
- Replace ad-hoc sync/async boundaries with clearer runtime ownership
- Preserve public compatibility where practical

### Phase 2: Domain Rule Consolidation

#### Objective

Ensure combat, card, skill, event, and phase systems operate on a consistent runtime contract.

#### Primary files

- `game/combat.py`
- `game/card_resolver.py`
- `game/damage_system.py`
- `game/equipment_system.py`
- `game/judge_system.py`
- `game/skill.py`
- `game/skill_resolver.py`
- `game/skill_interpreter.py`
- `game/events.py`
- `game/phase_fsm.py`

#### Key outcomes

- Consistent action -> resolve -> emit ordering
- Integrated handling of current local fixes in `combat.py`
- Reduced duplication of rule branches across modules
- Clearer domain event boundaries

### Phase 3: Textual UI Refactor

#### Objective

Move the UI from mixed orchestration to a state-driven and worker-aware model.

#### Primary files

- `ui/textual_ui/app.py`
- `ui/textual_ui/bridge.py`
- `ui/textual_ui/screens/*`
- `ui/textual_ui/widgets/*`
- `ui/textual_ui/state.py` (new)
- `ui/textual_ui/workers.py` (new)

#### Key outcomes

- Runtime requests are bridged through explicit UI messages
- Blocking work is isolated via worker coordination
- UI no longer depends on direct core-side synchronous callbacks
- Screen and modal state become easier to reason about and test

### Phase 4: Network, Security, and Configuration Refactor

#### Objective

Unify runtime configuration and harden the network path around validated policy.

#### Primary files

- `net/server.py`
- `net/client.py`
- `net/security.py`
- `net/session.py`
- `net/protocol.py`
- `net/models.py`
- `net/request_codec.py`
- `net/action_codec.py`
- `main.py`
- shared settings module or `net/settings.py` (new)

#### Key outcomes

- Explicit validated settings model
- Production-safe defaults
- Integrated handling of current local fixes in `net/server.py`
- Cleaner separation of transport policy from gameplay policy

### Phase 5: GitHub CI/Release Refactor

#### Objective

Align automation with the refactored project structure and current workflow security expectations.

#### Primary files

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `build.py`
- `build_msix.py`
- `docs/release-process.md`

#### Key outcomes

- Clearer job boundaries
- Better permissions hygiene
- More consistent build/test environment definition
- Release workflow aligned to tag-driven delivery and build outputs

### Phase 6: Documentation and Final Alignment

#### Objective

Make repository documentation truthful, current, and operationally useful after the refactor.

#### Primary files

- `README.md`
- `ARCHITECTURE.md`
- `docs/*`
- `CHANGELOG.md`

#### Key outcomes

- Updated architecture narrative
- Accurate run/build/network instructions
- Clear migration notes for contributors

## Verification Strategy

### Phase-level verification

Each phase should run the most relevant targeted tests first:

- Core runtime:
  - `tests/test_game.py`
  - `tests/test_game_controller_coverage.py`
  - `tests/test_request_handler_coverage.py`
  - `tests/test_action_*`
  - `tests/test_phase_fsm.py`

- Domain rules:
  - `tests/test_combat.py`
  - `tests/test_skills.py`
  - `tests/test_skill_*`
  - `tests/test_events*.py`
  - `tests/property/*`

- UI:
  - `tests/test_textual_ui.py`
  - `tests/test_pilot_ui.py`
  - `tests/test_accessibility.py`

- Network/security:
  - `tests/test_security.py`
  - `tests/test_net_*`
  - `tests/test_session.py`
  - `tests/test_main_server_*`
  - `tests/test_main_connect_*`

- Automation/build:
  - local workflow syntax and script checks
  - build script dry-runs where practical

### Broad regression checks

At major milestones:

- `python -m pytest tests/ -q`
- `python -m ruff check .`
- `python -m mypy game ai net`

## Risks and Mitigations

| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Breaking current gameplay flow during core refactor | UI, AI, and network all depend on it | Keep facade compatibility and verify targeted runtime tests before widening changes |
| Overwriting the user's existing local fixes | The tree is already dirty in files that overlap the plan | Treat local diffs as required inputs and isolate implementation in a worktree |
| UI regressions from concurrency cleanup | Textual is sensitive to thread ownership and event flow | Move blocking work into explicit worker orchestration and keep UI updates on the main thread |
| Security regressions while simplifying network code | Safer defaults can accidentally be relaxed | Keep production-safe defaults explicit and test policy behavior directly |
| CI/release drift from local architecture changes | GitHub automation becomes misleading or broken | Refactor workflows as part of the main plan, not as an afterthought |

## Git and Delivery Strategy

### Local strategy

- Do not overwrite existing uncommitted user work
- Create an isolated worktree before implementation begins
- Use staged commits per phase to preserve rollback points

### GitHub strategy

- Prefer a dedicated refactor branch over direct `main` changes
- Keep release semantics tag-driven
- Update workflow permissions and action pinning strategy during the automation phase

## Explicit Non-Goals

- This refactor does not attempt to redesign the entire game from scratch
- This refactor does not require immediate removal of every legacy adapter if compatibility still serves the migration
- This refactor does not prioritize cosmetic churn over architectural clarity

## Success Criteria

The refactor is successful when:

1. Core runtime boundaries are clearer and less coupled
2. Textual UI no longer depends on scattered blocking call patterns
3. Network configuration and security defaults are explicit and validated
4. GitHub workflows reflect the new architecture and remain operational
5. Existing gameplay behavior remains covered by tests
6. The repository documentation accurately describes the system after migration

## Source References

- Textual Workers Guide: https://textual.textualize.io/guide/workers/
- websockets Security Guide: https://websockets.readthedocs.io/en/stable/topics/security.html
- websockets Encryption Guide: https://websockets.readthedocs.io/en/stable/howto/encryption.html
- GitHub Actions Secure Use Reference: https://docs.github.com/en/actions/reference/security/secure-use
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
