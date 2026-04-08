# Controller Play-Card Log Async Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move play-card branch logging in `GameController._handle_play_specific_card()` onto the `ControllerIO` boundary and make its caller await the method.

**Architecture:** Convert `_handle_play_specific_card()` to `async`, update `_human_play_phase()` to await it, and route existing `self.ui.show_log(...)` calls through `await ControllerIO.show_log(...)`. Keep card rules, targeting, and engine effects unchanged.

**Tech Stack:** Python 3.10+, asyncio, pytest, unittest.mock

---

### Task 1: Add Failing Tests

**Files:**
- Test: `tests/test_game_controller_coverage.py`

- [x] **Step 1: Convert play-card tests to async call style and add focused log-boundary assertions**

Representative focused tests:

```python
@pytest.mark.asyncio
async def test_handle_play_specific_card_equipment_logs_via_controller_io(self): ...

@pytest.mark.asyncio
async def test_handle_play_specific_card_sha_no_targets_logs_via_controller_io(self): ...

@pytest.mark.asyncio
async def test_handle_play_specific_card_tao_hp_full_logs_via_controller_io(self): ...
```

- [x] **Step 2: Run focused tests to verify they fail**

Run:

`python -m pytest tests/test_game_controller_coverage.py -q -k "equipment_logs_via_controller_io or sha_no_targets_logs_via_controller_io or tao_hp_full_logs_via_controller_io"`

Expected: FAIL because `_handle_play_specific_card()` still calls `self.ui.show_log(...)` directly and is not yet async.

### Task 2: Implement Async Play-Card Log Routing

**Files:**
- Modify: `game/game_controller.py`

- [x] **Step 1: Convert `_handle_play_specific_card()` to async**

Update `_human_play_phase()` call site to:

```python
await self._handle_play_specific_card(player, card)
```

- [x] **Step 2: Route play-card logs through `ControllerIO.show_log()`**

Replace direct UI logging with:

```python
await self._controller_io.show_log(...)
```

- [x] **Step 3: Re-run focused tests**

Run:

`python -m pytest tests/test_game_controller_coverage.py -q -k "equipment_logs_via_controller_io or sha_no_targets_logs_via_controller_io or tao_hp_full_logs_via_controller_io"`

Expected: PASS

### Task 3: Slice Verification

**Files:**
- Modify: `game/game_controller.py`
- Modify: `tests/test_game_controller_coverage.py`

- [x] **Step 1: Run controller coverage**

Run:

`python -m pytest tests/test_game_controller_coverage.py -q`

- [ ] **Step 2: Run regression slice**

Observed blocker:
- `python -m pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py tests/test_subsystems.py -q`
  fails on `tests/test_subsystems.py::TestCardResolver::test_use_tiesuo_reforge`
- reproduced standalone with `python -m pytest tests/test_subsystems.py -q -k test_use_tiesuo_reforge --randomly-seed=1207118530 -vv`
- this failure is outside the files touched in this slice and appears to be a pre-existing seed-dependent subsystem test issue

Run:

`python -m pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py tests/test_subsystems.py -q`

- [x] **Step 3: Run style checks**

Run:

`python -m ruff check game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-play-card-log-async.md`

- [ ] **Step 4: Commit**

```bash
git add game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-play-card-log-async.md
git commit -m "refactor: asyncify controller play card log io"
```
