# Controller Game Over Async Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move game-over rendering in `GameController` onto the async `ControllerIO` boundary so controller completion no longer invokes `GameUI` directly.

**Architecture:** Add `ControllerIO.show_game_over(...)` as an async wrapper around the synchronous UI method, convert `GameController._handle_game_over()` to async, and await it from `_game_loop()`. Keep win/loss computation unchanged.

**Tech Stack:** Python 3.10+, asyncio, pytest, unittest.mock

---

### Task 1: Add Failing Tests

**Files:**
- Test: `tests/test_game_controller_coverage.py`

- [x] **Step 1: Convert `_handle_game_over` tests to async boundary expectations**

```python
@pytest.mark.asyncio
async def test_lord_wins_lord_player(self):
    ...
    ctrl._controller_io = MagicMock()
    ctrl._controller_io.show_game_over = AsyncMock()

    await ctrl._handle_game_over()
```

- [x] **Step 2: Run focused tests to verify they fail**

Run: `python -m pytest tests/test_game_controller_coverage.py -q -k "handle_game_over"`

Expected: FAIL because `_handle_game_over()` is still synchronous / not awaitable.

### Task 2: Implement Async Game-Over Routing

**Files:**
- Modify: `game/runtime/controller_io.py`
- Modify: `game/game_controller.py`

- [x] **Step 1: Add async game-over wrapper to `ControllerIO`**

```python
async def show_game_over(self, winner_message: str, is_victory: bool) -> None:
    await self._run(self._ui.show_game_over, winner_message, is_victory)
```

- [x] **Step 2: Convert `_handle_game_over()` to async**

```python
async def _handle_game_over(self) -> None:
    ...
    await self._controller_io.show_game_over(winner_message, is_victory)
```

- [x] **Step 3: Await the helper from `_game_loop()`**

```python
await self._handle_game_over()
```

- [x] **Step 4: Verify focused tests**

Run: `python -m pytest tests/test_game_controller_coverage.py -q -k "handle_game_over"`

Expected: PASS

### Task 3: Slice Verification

**Files:**
- Modify: `game/runtime/controller_io.py`
- Modify: `game/game_controller.py`
- Modify: `tests/test_game_controller_coverage.py`

- [x] **Step 1: Run controller coverage**

Run: `python -m pytest tests/test_game_controller_coverage.py -q`

- [x] **Step 2: Run regression slice**

Run: `python -m pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py tests/test_subsystems.py -q`

- [x] **Step 3: Run style checks**

Run: `python -m ruff check game/runtime/controller_io.py game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-game-over-async.md`

- [x] **Step 4: Commit**

```bash
git add game/runtime/controller_io.py game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-game-over-async.md
git commit -m "refactor: asyncify controller game over io"
```
