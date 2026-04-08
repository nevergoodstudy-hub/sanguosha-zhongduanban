# Controller Skill Log Async Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move async skill-interaction logging in `GameController` onto the `ControllerIO` boundary so `_handle_use_skill()` and `_select_cards_for_skill()` stop calling `GameUI.show_log()` directly.

**Architecture:** Route zhiheng/fanjian skill prompt logs and skill-card selection logs through `await ControllerIO.show_log(...)`. Keep target selection, prompt input, and skill-system effects unchanged.

**Tech Stack:** Python 3.10+, asyncio, pytest, unittest.mock

---

### Task 1: Add Failing Tests

**Files:**
- Test: `tests/test_game_controller_coverage.py`

- [ ] **Step 1: Add focused async boundary tests**

```python
@pytest.mark.asyncio
async def test_handle_use_skill_zhiheng_logs_via_controller_io(self): ...

@pytest.mark.asyncio
async def test_handle_use_skill_fanjian_logs_via_controller_io(self): ...

@pytest.mark.asyncio
async def test_select_cards_for_skill_uses_controller_io_logs(self): ...
```

- [ ] **Step 2: Run focused tests to verify they fail**

Run: `python -m pytest tests/test_game_controller_coverage.py -q -k "zhiheng_logs_via_controller_io or fanjian_logs_via_controller_io or select_cards_for_skill_uses_controller_io_logs"`

Expected: FAIL because the methods still write logs through `self.ui.show_log(...)`.

### Task 2: Implement Async Skill Log Routing

**Files:**
- Modify: `game/game_controller.py`

- [ ] **Step 1: Route `_handle_use_skill()` prompt logs through `ControllerIO.show_log()`**

```python
await self._controller_io.show_log(_t("controller.choose_discard_cards"))
await self._controller_io.show_log(_t("controller.choose_show_card"))
```

- [ ] **Step 2: Route `_select_cards_for_skill()` logs through `ControllerIO.show_log()`**

```python
await self._controller_io.show_log(...)
```

- [ ] **Step 3: Verify focused tests**

Run: `python -m pytest tests/test_game_controller_coverage.py -q -k "zhiheng_logs_via_controller_io or fanjian_logs_via_controller_io or select_cards_for_skill_uses_controller_io_logs"`

Expected: PASS

### Task 3: Slice Verification

**Files:**
- Modify: `game/game_controller.py`
- Modify: `tests/test_game_controller_coverage.py`

- [ ] **Step 1: Run controller coverage**

Run: `python -m pytest tests/test_game_controller_coverage.py -q`

- [ ] **Step 2: Run regression slice**

Run: `python -m pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py tests/test_subsystems.py -q`

- [ ] **Step 3: Run style checks**

Run: `python -m ruff check game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-skill-log-async.md`

- [ ] **Step 4: Commit**

```bash
git add game/game_controller.py tests/test_game_controller_coverage.py docs/superpowers/plans/2026-04-08-controller-skill-log-async.md
git commit -m "refactor: asyncify controller skill log io"
```
