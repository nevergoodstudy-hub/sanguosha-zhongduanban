# Controller Hero Selection Async Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the hero-selection interaction in `GameController` onto the async `ControllerIO` boundary so controller setup no longer calls blocking UI methods directly during new-game initialization.

**Architecture:** Extend `ControllerIO` with an async hero-selection helper, convert `_choose_heroes()` and `_auto_choose_heroes_for_ai()` to async methods, and update `start_new_game()` to await hero setup. Preserve current hero-pool selection rules and chosen-hero logging behavior.

**Tech Stack:** Python 3.10+, asyncio, pytest, unittest.mock

**Relevant guidance:** Official Python `asyncio.to_thread` docs for wrapping blocking I/O, plus Textual's worker/thread guidance for keeping UI-affecting orchestration off ad-hoc blocking paths.

---

### Task 1: Add Failing Boundary Tests

**Files:**
- Test: `tests/test_game_controller_coverage.py`

- [ ] **Step 1: Add failing tests for hero-selection routing**

```python
@pytest.mark.asyncio
async def test_choose_heroes_lord_routes_through_controller_io(): ...

@pytest.mark.asyncio
async def test_auto_choose_heroes_for_ai_routes_logs_through_controller_io(): ...
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:
`python -m pytest tests/test_game_controller_coverage.py -q -k "choose_heroes or auto_choose_heroes"`

Expected:
Tests fail because hero selection is still synchronous and still routes through `self.ui`.

### Task 2: Implement Async Hero Selection Boundary

**Files:**
- Modify: `game/runtime/controller_io.py`
- Modify: `game/game_controller.py`

- [ ] **Step 1: Add async hero-selection helper to `ControllerIO`**

```python
async def show_hero_selection(self, heroes, selected_count=1, is_lord=False):
    return await self._run(
        self._ui.show_hero_selection, heroes, selected_count, is_lord
    )
```

- [ ] **Step 2: Convert hero setup helpers to async**

```python
async def _choose_heroes(self) -> None: ...
async def _auto_choose_heroes_for_ai(self, used_heroes: list[str]) -> dict[int, str]: ...
```

- [ ] **Step 3: Update new-game initialization to await hero setup**

```python
await self._choose_heroes()
```

- [ ] **Step 4: Verify focused tests**

Run:
`python -m pytest tests/test_game_controller_coverage.py -q -k "choose_heroes or auto_choose_heroes"`

Expected:
PASS

- [ ] **Step 5: Verify broader controller regressions**

Run:
`python -m pytest tests/test_game_controller_coverage.py -q`

Expected:
PASS

- [ ] **Step 6: Verify project regression slice**

Run:
`python -m pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py tests/test_subsystems.py -q`

Expected:
PASS

- [ ] **Step 7: Verify style**

Run:
`python -m ruff check game/game_controller.py game/runtime/controller_io.py tests/test_game_controller_coverage.py`

Expected:
All checks pass

- [ ] **Step 8: Commit**

```bash
git add game/runtime/controller_io.py game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-hero-selection-async.md
git commit -m "refactor: asyncify controller hero selection io"
```
