# Domain Skill Conversion Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route combat-related conversion skills through `request_skill_card` consistently so combat logic no longer special-cases AI vs human when selecting conversion cards.

**Architecture:** Keep `CombatSystem` responsible for combat flow, but move card selection for conversion skills behind one request boundary. `DefaultRequestHandler.request_skill_card()` already knows how to handle AI and human callers, so `CombatSystem` should delegate instead of branching on `player.is_ai`.

**Tech Stack:** Python 3.10+, pytest, unittest.mock, existing `CombatSystem` and `RequestHandler`

---

### Task 1: Add Failing Regression Tests

**Files:**
- Test: `tests/test_subsystems.py`

- [x] **Step 1: Write the failing tests**

```python
def test_request_shan_ai_longdan_routes_through_request_skill_card(self, engine):
    player = engine.players[0]
    player.is_ai = True
    player.hand = [make_card(CardName.SHA, card_id="longdan_sha")]
    player.has_skill = MagicMock(side_effect=lambda sid: sid == SkillId.LONGDAN)
    engine.request_handler.request_skill_card = MagicMock(return_value=player.hand[0])

    count = engine.combat.request_shan(player, 1)

    assert count == 1
    engine.request_handler.request_skill_card.assert_called_once_with(
        player, "longdan_as_shan", player.hand
    )
```

```python
def test_request_sha_ai_wusheng_routes_through_request_skill_card(self, engine):
    player = engine.players[0]
    red_card = make_card(CardName.SHAN, suit=CardSuit.HEART, card_id="wusheng_red")
    player.is_ai = True
    player.hand = [red_card]
    player.has_skill = MagicMock(side_effect=lambda sid: sid == SkillId.WUSHENG)
    engine.request_handler.request_skill_card = MagicMock(return_value=red_card)

    count = engine.combat.request_sha(player, 1)

    assert count == 1
    engine.request_handler.request_skill_card.assert_called_once_with(
        player, "wusheng_as_sha", [red_card]
    )
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_subsystems.py -q`
Expected: FAIL because `CombatSystem` still special-cases AI conversion selection.

### Task 2: Implement Unified Conversion Card Routing

**Files:**
- Modify: `game/combat.py`

- [x] **Step 1: Add a tiny helper for conversion-card selection**

```python
def _request_skill_conversion_card(
    self,
    player: Player,
    skill_name: str,
    candidates: list[Card],
) -> Card | None:
    if not candidates:
        return None
    return self.ctx.request_handler.request_skill_card(player, skill_name, candidates)
```

- [x] **Step 2: Replace AI-special-case branches with the helper**

```python
card = self._request_skill_conversion_card(player, "longdan_as_shan", sha_cards)
card = self._request_skill_conversion_card(player, "zhongshen_as_shan", red_cards)
card = self._request_skill_conversion_card(player, "wusheng_as_sha", red_cards)
card = self._request_skill_conversion_card(player, "longdan_as_sha", shan_cards)
```

- [x] **Step 3: Run focused verification**

Run: `python -m pytest tests/test_subsystems.py tests/test_request_handler_coverage.py -q`
Expected: PASS

- [x] **Step 4: Run style verification**

Run: `python -m ruff check game/combat.py tests/test_subsystems.py`
Expected: All checks pass

- [ ] **Step 5: Commit**

```bash
git add game/combat.py tests/test_subsystems.py docs/superpowers/plans/2026-04-08-domain-request-skill-routing.md
git commit -m "refactor: unify combat skill card routing"
```
