# Identity Mode 2025-2026 Content Sync Design

## Problem Statement
This project already implements a stable identity-mode Sanguosha experience with a Textual UI, headless battle support, AI strategies, cross-platform packaging, and a sizable automated test suite. The requested change is to sync a curated set of recent Sanguosha OL identity-mode content into the existing project without expanding scope into other major game modes such as 斗地主、国战、排位 or time-limited event rules.

## Approved Scope
The sync targets the existing identity-mode experience only. The first batch will add five heroes that are recent and practical for the current engine shape: 谋袁术、胡金定、界刘表、界法正、向宠. This batch includes hero data, skill behavior, AI support, automated tests, updated docs, updated release information, and release artifacts. The identity-mode ruleset, seat logic, win conditions, and core deck structure remain unchanged.

## Current State
Hero definitions are loaded from `data/heroes.json` through `game/hero.py`. Skill execution is mixed between DSL entries in `data/skill_dsl.json` and Python handlers wired through `game/skill.py` and `game/skills/*.py`. Player turn state currently lives mostly in `game/player.py` as counters and transient flags such as `skill_used`, `sha_count`, and delayed-trick markers. AI behavior is split between `ai/normal_strategy.py` and `ai/hard_strategy.py`, both of which already know how to drive a subset of active and transform skills. Release packaging already exists for local Windows builds through `build.py` and `build_msix.py`, while `.github/workflows/release.yml` builds Windows, Linux, and macOS artifacts from tags.

## Design Goals
The implementation should fit the current engine instead of introducing a parallel subsystem. The new heroes must be selectable in identity mode, play correctly in both human and AI games, preserve determinism in seeded headless runs, and avoid destabilizing existing identity-mode flow. State-heavy skills should be represented explicitly and testably instead of being squeezed into the current DSL where the DSL cannot express the full behavior cleanly.

## Proposed Design
### Hero and skill data
All five heroes will be added directly to `data/heroes.json`. Their skills will follow the current schema so they can be discovered by selection UI, AI, serialization, and tests without introducing a new repository or content-pack layer.

### Runtime state model
The player runtime model in `game/player.py` will be extended with a dedicated per-skill state container, alongside helper methods for round-level and turn-level resets. This state will hold information such as the current `矜名` selection and deleted options, `轻缘` linked targets, `重身` red-card conversion window, `宗室` faction-based prevention tracking, and `固营` trigger counts. The new container will be designed to avoid collisions with existing `skill_used` counters and to make complex skills inspectable in tests.

### Event and engine hooks
The existing event bus in `game/events.py` already exposes card loss, card gain, damage, and phase boundaries, but it does not yet provide enough structured hooks for every approved skill. The implementation will expand event publishing and consumption around gain/loss, damage prevention or replacement, and phase-end windows so complex skills can run from centralized control points rather than scattered ad hoc checks. The main integration points will be `game/engine.py`, `game/card_resolver.py`, `game/combat.py`, and `game/skill.py`.

### Skill implementation strategy
The first batch will use Python handlers as the primary implementation path. `data/skill_dsl.json` may still receive lightweight helper entries where appropriate, but complex behavior will live in `game/skills/*.py` plus targeted orchestration inside `game/skill.py`. This keeps multi-branch, stateful, or replacement-style skills explicit and debuggable.

### AI behavior
AI support will aim for competent execution rather than perfect OL parity. `ai/normal_strategy.py` and `ai/hard_strategy.py` will be extended so AI can recognize profitable activation windows, choose sensible targets, and avoid obviously wasteful plays for the new heroes. The heuristics will stay lightweight and deterministic so they remain compatible with current headless battle tests.

### Release and packaging
Release-facing metadata will be updated in `README.md`, `CHANGELOG.md`, and version metadata. Local packaging verification will cover Windows executable and MSIX generation. Cross-platform release publishing will continue to use the existing GitHub Actions release workflow by pushing the updated branch and a new version tag. Because the user explicitly chose to continue in the current working tree, the release may include pre-existing uncommitted work in addition to the new identity-mode sync; this risk will be surfaced again before commit and tag creation.

## Testing Strategy
The implementation will add focused tests for each hero’s core skill paths, regression tests for new runtime state and event hooks, identity-mode integration coverage for hero selection and full-battle stability, and AI smoke coverage for normal and hard strategies. Final verification will include project tests, Ruff, MyPy, local Windows packaging checks, and release workflow sanity review before any completion claim.
