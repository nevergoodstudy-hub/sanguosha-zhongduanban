# Controller Discard Async Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the discard-phase UI interaction in `GameController` onto the async `ControllerIO` boundary so the controller’s async turn flow no longer calls blocking discard UI directly.

**Architecture:** Extend `ControllerIO` with an async discard-card chooser, convert `_execute_discard_phase()` and `_human_discard_phase()` to async methods, and update turn execution to await them. Keep the existing gameplay behavior unchanged.

**Tech Stack:** Python 3.10+, asyncio, pytest, unittest.mock

---

### Task 1: Add Failing Tests

**Files:**
- Test: `tests/test_game_controller_coverage.py`

- [x] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_execute_discard_phase_human_routes_through_controller_io():
    engine = _make_engine()
    ctrl = _make_controller(engine=engine)
    player = _make_player(is_ai=False)
    player.need_discard = 2
    ctrl._controller_io = MagicMock()
    ctrl._controller_io.show_log = AsyncMock()
    ctrl._controller_io.show_game_state = AsyncMock()
    ctrl._controller_io.choose_cards_to_discard = AsyncMock(return_value=[MagicMock(), MagicMock()])

    await ctrl._execute_discard_phase(player)

    ctrl._controller_io.choose_cards_to_discard.assert_awaited_once()
```

```python
@pytest.mark.asyncio
async def test_human_discard_phase_no_engine():
    ctrl = _make_controller()
    ctrl.engine = None
    await ctrl._human_discard_phase(MagicMock())
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_game_controller_coverage.py -q`
Expected: FAIL because discard helpers are still synchronous and do not await `ControllerIO`.

### Task 2: Implement Async Discard Routing

**Files:**
- Modify: `game/runtime/controller_io.py`
- Modify: `game/game_controller.py`

- [x] **Step 1: Add async discard helper to `ControllerIO`**

```python
async def choose_cards_to_discard(self, player: Player, count: int):
    return await self._run(self._ui.choose_cards_to_discard, player, count)
```

- [x] **Step 2: Convert controller discard helpers to async**

```python
async def _execute_discard_phase(self, player: Player) -> None: ...
async def _human_discard_phase(self, player: Player) -> None: ...
```

- [x] **Step 3: Await discard helpers from turn execution**

```python
await self._execute_discard_phase(player)
await self._human_discard_phase(player)
```

- [x] **Step 4: Verify focused tests**

Run: `python -m pytest tests/test_game_controller_coverage.py -q`
Expected: PASS

- [x] **Step 5: Verify slice regression**

Run: `python -m pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py tests/test_subsystems.py -q`
Expected: PASS

- [x] **Step 6: Verify style**

Run: `python -m ruff check game/game_controller.py game/runtime/controller_io.py tests/test_game_controller_coverage.py`
Expected: All checks pass

- [x] **Step 7: Commit**

```bash
git add game/runtime/controller_io.py game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-discard-async.md
git commit -m "refactor: asyncify controller discard io"
```
