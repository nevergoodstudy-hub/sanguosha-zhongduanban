# Controller Turn Phase Async Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move turn-header and phase-log UI work in `GameController` onto the async `ControllerIO` boundary so controller turn execution no longer mixes async flow with direct synchronous log rendering.

**Architecture:** Convert `_show_turn_header()`, `_execute_prepare_phase()`, `_execute_draw_phase()`, and `_execute_end_phase()` to async helpers that delegate logging through `ControllerIO.show_log()`. Update AI and human turn runners to await those helpers. Keep gameplay sequencing and engine mutations unchanged.

**Tech Stack:** Python 3.10+, asyncio, pytest, unittest.mock

---

### Task 1: Add Failing Tests

**Files:**
- Test: `tests/test_game_controller_coverage.py`

- [x] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_shows_header_via_controller_io():
    ...
    await ctrl._show_turn_header(player)
```

```python
@pytest.mark.asyncio
async def test_execute_prepare_phase():
    ...
    await ctrl._execute_prepare_phase(player)
```

```python
@pytest.mark.asyncio
async def test_execute_draw_phase():
    ...
    drawn = await ctrl._execute_draw_phase(player)
```

```python
@pytest.mark.asyncio
async def test_execute_end_phase_ai():
    ...
    await ctrl._execute_end_phase(player)
```

- [x] **Step 2: Run focused tests to verify they fail**

Run: `python -m pytest tests/test_game_controller_coverage.py -q -k "show_turn_header or execute_prepare_phase or execute_draw_phase or execute_end_phase"`

Expected: FAIL because the helpers are still synchronous and cannot be awaited.

### Task 2: Implement Async Turn/Phase Routing

**Files:**
- Modify: `game/game_controller.py`

- [x] **Step 1: Convert turn/phase helpers to async**

```python
async def _show_turn_header(self, player: Player) -> None: ...
async def _execute_prepare_phase(self, player: Player) -> None: ...
async def _execute_draw_phase(self, player: Player, show_count: bool = True) -> int: ...
async def _execute_end_phase(self, player: Player) -> None: ...
```

- [x] **Step 2: Delegate phase logging through `ControllerIO`**

```python
await self._controller_io.show_log(_t("controller.phase_prepare"))
await self._controller_io.show_log(_t("controller.phase_draw"))
await self._controller_io.show_log(_t("controller.phase_end"))
```

- [x] **Step 3: Await the helpers from turn runners**

```python
await self._show_turn_header(player)
await self._execute_prepare_phase(player)
await self._execute_draw_phase(player)
await self._execute_end_phase(player)
```

- [x] **Step 4: Verify focused tests**

Run: `python -m pytest tests/test_game_controller_coverage.py -q -k "show_turn_header or execute_prepare_phase or execute_draw_phase or execute_end_phase"`

Expected: PASS

### Task 3: Slice Verification

**Files:**
- Modify: `tests/test_game_controller_coverage.py`
- Modify: `game/game_controller.py`

- [x] **Step 1: Run controller coverage**

Run: `python -m pytest tests/test_game_controller_coverage.py -q`

- [x] **Step 2: Run regression slice**

Run: `python -m pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py tests/test_subsystems.py -q`

- [x] **Step 3: Run style checks**

Run: `python -m ruff check game/game_controller.py tests/test_game_controller_coverage.py`

- [ ] **Step 4: Commit**

```bash
git add game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-turn-phase-async.md
git commit -m "refactor: asyncify controller turn phase io"
```
