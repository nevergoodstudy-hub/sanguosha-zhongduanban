# Core Runtime Controller IO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a focused runtime controller I/O adapter that centralizes blocking UI and prompt operations, then refactor `GameController` to use it so controller/runtime boundaries are clearer and Textual-facing flow is safer.

**Architecture:** Add a new `game/runtime/controller_io.py` adapter that wraps blocking UI calls behind async methods powered by `asyncio.to_thread`, while keeping the existing `GameUI` protocol compatible. Refactor `GameController` to delegate menu, prompt, target selection, discard, and logging operations through the adapter, eliminating direct `input()` usage from the controller and absorbing the current local async-offloading direction into a single boundary.

**Tech Stack:** Python 3.10+, asyncio, pytest, unittest.mock, existing `GameUI` protocol

---

### Task 1: Add Failing Tests For The Controller I/O Boundary

**Files:**
- Create: `game/runtime/__init__.py`
- Test: `tests/test_game_controller_coverage.py`

- [x] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_confirm_quit_uses_controller_io_prompt():
    ctrl = _make_controller()
    ctrl._controller_io = MagicMock()
    ctrl._controller_io.prompt_text = AsyncMock(return_value="Y")

    result = await ctrl._confirm_quit()

    assert result is True
    ctrl._controller_io.prompt_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_cards_for_skill_uses_controller_io_prompt():
    ctrl = _make_controller(engine=_make_engine())
    card_a = _make_card(name=CardName.SHA)
    card_b = _make_card(name=CardName.SHAN)
    player = _make_player(hand=[card_a, card_b])
    ctrl._controller_io = MagicMock()
    ctrl._controller_io.show_log = AsyncMock()
    ctrl._controller_io.prompt_text = AsyncMock(return_value="1 2")

    result = await ctrl._select_cards_for_skill(player, 1, 2)

    assert result == [card_a, card_b]
    ctrl._controller_io.prompt_text.assert_awaited_once()
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_game_controller_coverage.py -q`
Expected: FAIL because `GameController` has no `_controller_io` boundary and still uses direct `input()`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_game_controller_coverage.py
git commit -m "test: cover controller io boundary"
```

### Task 2: Implement The Runtime Controller I/O Adapter

**Files:**
- Create: `game/runtime/__init__.py`
- Create: `game/runtime/controller_io.py`
- Modify: `game/game_controller.py`

- [x] **Step 1: Write the minimal implementation**

```python
class ControllerIO:
    def __init__(self, ui: GameUI, prompt: Callable[[str], str] | None = None) -> None:
        self._ui = ui
        self._prompt = prompt or input

    async def show_log(self, message: str) -> None:
        await asyncio.to_thread(self._ui.show_log, message)

    async def show_game_state(self, engine: GameEngine, current_player: Player) -> None:
        await asyncio.to_thread(self._ui.show_game_state, engine, current_player)

    async def prompt_text(self, prompt: str) -> str:
        return (await asyncio.to_thread(self._prompt, prompt)).strip()
```

```python
class GameController:
    def __init__(...):
        self._controller_io = ControllerIO(ui)

    async def _confirm_quit(self) -> bool:
        choice = (await self._controller_io.prompt_text(_t("controller.confirm_quit"))).upper()
        return choice == "Y"

    async def _select_cards_for_skill(...):
        choice = await self._controller_io.prompt_text(_t("controller.input_prompt"))
```

- [x] **Step 2: Expand `ControllerIO` to cover the controller’s blocking UI calls**

```python
async def show_main_menu(self) -> int: ...
async def show_rules(self) -> None: ...
async def show_player_count_menu(self) -> int: ...
async def show_difficulty_menu(self) -> str: ...
async def get_player_action(self) -> str: ...
async def choose_target(self, player: Player, targets: list[Player], prompt: str) -> Player | None: ...
async def show_skill_menu(self, player: Player, usable_skills: list[str]) -> str | None: ...
async def choose_card_to_play(self, player: Player) -> Card | None: ...
async def choose_cards_to_discard(self, player: Player, count: int) -> list[Card]: ...
```

- [x] **Step 3: Refactor `GameController` to delegate through the adapter**

```python
choice = await self._controller_io.show_main_menu()
player_count = await self._controller_io.show_player_count_menu()
difficulty_str = await self._controller_io.show_difficulty_menu()
action = await self._controller_io.get_player_action()
target = await self._controller_io.choose_target(player, targets, prompt)
cards = await self._controller_io.choose_cards_to_discard(player, discard_count)
```

- [x] **Step 4: Run targeted tests to verify the adapter integration passes**

Run: `python -m pytest tests/test_game_controller_coverage.py tests/test_game.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add game/runtime/__init__.py game/runtime/controller_io.py game/game_controller.py tests/test_game_controller_coverage.py
git commit -m "refactor: add controller io runtime boundary"
```

### Task 3: Regress The Core Runtime Slice

**Files:**
- Modify: `progress.md`
- Modify: `findings.md`

- [x] **Step 1: Run slice verification**

Run: `python -m pytest tests/test_game.py tests/test_game_controller_coverage.py tests/test_request_handler_coverage.py tests/test_phase_fsm.py -q`
Expected: PASS

- [x] **Step 2: Run static verification for touched files**

Run: `python -m ruff check game/game_controller.py game/runtime/controller_io.py tests/test_game_controller_coverage.py`
Expected: All checks pass

- [x] **Step 3: Document what changed and why**

```markdown
- Added `ControllerIO` as the first `game/runtime/` execution boundary
- Removed direct `input()` usage from `GameController`
- Centralized thread-offloaded UI operations instead of scattering `asyncio.to_thread`
```

- [ ] **Step 4: Commit**

```bash
git add findings.md progress.md
git commit -m "docs: record controller io refactor slice"
```
