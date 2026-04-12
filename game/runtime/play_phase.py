"""Play-phase coordination helpers extracted from ``GameController``."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from i18n import t as _t

from ..card import Card, CardName, CardType
from ..config import get_config
from ..constants import SkillId
from ..engine import GameEngine, GamePhase, GameState

if TYPE_CHECKING:
    from ..player import Player
    from .controller_io import ControllerIO


class PlayPhaseCoordinator:
    """Owns play-phase interaction logic while keeping controller wrappers stable."""

    def __init__(
        self,
        *,
        engine_getter: Callable[[], GameEngine | None],
        controller_io_getter: Callable[[], ControllerIO],
    ) -> None:
        self._engine_getter = engine_getter
        self._controller_io_getter = controller_io_getter

    @property
    def engine(self) -> GameEngine | None:
        return self._engine_getter()

    @property
    def controller_io(self) -> ControllerIO:
        return self._controller_io_getter()

    def check_card_usable(self, player: Player, card: Card) -> bool:
        """Return whether a card is currently playable in the play phase."""
        engine = self.engine
        if not engine:
            return False

        if card.card_type == CardType.EQUIPMENT:
            return True
        if card.name == CardName.SHA:
            if not player.can_use_sha():
                return False
            targets = engine.get_targets_in_range(player)
            return len(targets) > 0
        if card.name == CardName.TAO:
            return player.hp < player.max_hp
        if card.name == CardName.SHAN:
            return False
        if card.name == CardName.SHUNSHOU:
            others = engine.get_other_players(player)
            valid = [
                target
                for target in others
                if engine.calculate_distance(player, target) <= 1 and target.has_any_card()
            ]
            return len(valid) > 0
        if card.name == CardName.GUOHE:
            others = engine.get_other_players(player)
            valid = [target for target in others if target.has_any_card()]
            return len(valid) > 0
        if card.name == CardName.JUEDOU:
            return len(engine.get_other_players(player)) > 0
        return True

    def get_playable_mask(self, player: Player) -> list[bool]:
        """Return the current playable mask for every card in hand."""
        return [self.check_card_usable(player, card) for card in player.hand]

    def update_playable_mask(self, player: Player) -> None:
        """Update the engine-visible playable mask used by the UI."""
        engine = self.engine
        if not engine:
            return

        if engine.phase == GamePhase.PLAY:
            engine._playable_mask = self.get_playable_mask(player)
        else:
            engine._playable_mask = []

    def has_usable_cards(self, player: Player) -> bool:
        """Return whether the player still has any usable cards."""
        if not player.hand:
            return False
        return any(self.check_card_usable(player, card) for card in player.hand)

    def has_usable_skills(self, player: Player) -> bool:
        """Return whether the player still has any usable play-phase skills."""
        engine = self.engine
        if not engine or not engine.skill_system:
            return False
        usable_skills = engine.skill_system.get_usable_skills(player)
        return len(usable_skills) > 0

    def can_do_anything(self, player: Player) -> bool:
        """Return whether the player can continue acting this phase."""
        return self.has_usable_cards(player) or self.has_usable_skills(player)

    async def handle_play_specific_card(self, player: Player, card: Card) -> None:
        """Handle playing a specific hand card chosen by the user."""
        engine = self.engine
        if not engine:
            return

        controller_io = self.controller_io

        if card.card_type == CardType.EQUIPMENT:
            await controller_io.show_log(_t("controller.equipped", card=card.name))
            engine.use_card(player, card)

        elif card.name == CardName.SHA:
            if not player.can_use_sha():
                await controller_io.show_log(_t("controller.sha_used"))
                has_paoxiao = player.has_skill(SkillId.PAOXIAO)
                if has_paoxiao:
                    await controller_io.show_log(_t("controller.sha_paoxiao"))
                else:
                    return

            targets = engine.get_targets_in_range(player)
            if not targets:
                await controller_io.show_log(_t("controller.no_targets"))
                return

            target = controller_io.choose_target(player, targets, _t("controller.choose_attack"))
            if target:
                await controller_io.show_log(_t("controller.use_sha", target=target.name))
                engine.use_card(player, card, [target])

        elif card.name == CardName.TAO:
            if player.hp >= player.max_hp:
                await controller_io.show_log(_t("controller.hp_full"))
                return
            await controller_io.show_log(_t("controller.use_tao"))
            engine.use_card(player, card)

        elif card.name == CardName.SHAN:
            await controller_io.show_log(_t("controller.shan_passive"))
            return

        elif card.name == CardName.WUZHONG:
            await controller_io.show_log(_t("controller.use_wuzhong"))
            engine.use_card(player, card)

        elif card.name in [CardName.NANMAN, CardName.WANJIAN]:
            await controller_io.show_log(_t("controller.use_card", card=card.name))
            engine.use_card(player, card)

        elif card.name == CardName.TAOYUAN:
            await controller_io.show_log(_t("controller.use_taoyuan"))
            engine.use_card(player, card)

        elif card.name == CardName.JUEDOU:
            others = engine.get_other_players(player)
            if not others:
                await controller_io.show_log(_t("controller.no_other_targets"))
                return
            target = controller_io.choose_target(
                player, others, _t("controller.choose_duel_target")
            )
            if target:
                await controller_io.show_log(_t("controller.use_juedou", target=target.name))
                engine.use_card(player, card, [target])

        elif card.name == CardName.GUOHE:
            others = engine.get_other_players(player)
            valid = [target for target in others if target.has_any_card()]
            if not valid:
                await controller_io.show_log(_t("controller.no_card_targets"))
                return
            target = controller_io.choose_target(
                player, valid, _t("controller.choose_guohe_target")
            )
            if target:
                await controller_io.show_log(_t("controller.use_guohe", target=target.name))
                engine.use_card(player, card, [target])

        elif card.name == CardName.SHUNSHOU:
            others = engine.get_other_players(player)
            valid = [
                target
                for target in others
                if engine.calculate_distance(player, target) <= 1 and target.has_any_card()
            ]
            if not valid:
                await controller_io.show_log(_t("controller.no_shunshou_targets"))
                return
            target = controller_io.choose_target(
                player, valid, _t("controller.choose_shunshou_target")
            )
            if target:
                await controller_io.show_log(_t("controller.use_shunshou", target=target.name))
                engine.use_card(player, card, [target])
        else:
            engine.use_card(player, card)

    async def handle_use_skill(
        self,
        player: Player,
        *,
        select_cards_for_skill: Callable[[Player, int, int], Awaitable[list[Card]]],
    ) -> None:
        """Handle invoking a skill from the play-phase skill menu."""
        engine = self.engine
        if not engine or not engine.skill_system:
            return

        controller_io = self.controller_io
        usable_skills = engine.skill_system.get_usable_skills(player)
        skill_id = controller_io.show_skill_menu(player, usable_skills)
        if not skill_id:
            return

        if skill_id == "zhiheng":
            if player.hand:
                await controller_io.show_log(_t("controller.choose_discard_cards"))
                cards = await select_cards_for_skill(player, 1, len(player.hand))
                if cards:
                    engine.skill_system.use_skill(skill_id, player, cards=cards)
        elif skill_id == "rende":
            if player.hand:
                cards = await select_cards_for_skill(player, 1, len(player.hand))
                if cards:
                    others = engine.get_other_players(player)
                    target = controller_io.choose_target(
                        player, others, _t("controller.choose_give_target")
                    )
                    if target:
                        engine.skill_system.use_skill(
                            skill_id, player, targets=[target], cards=cards
                        )
        elif skill_id == "fanjian" and player.hand:
            await controller_io.show_log(_t("controller.choose_show_card"))
            card = controller_io.choose_card_to_play(player)
            if card:
                others = engine.get_other_players(player)
                target = controller_io.choose_target(
                    player, others, _t("controller.choose_fanjian_target")
                )
                if target:
                    engine.skill_system.use_skill(skill_id, player, targets=[target], cards=[card])

    async def select_cards_for_skill(
        self, player: Player, min_count: int, max_count: int
    ) -> list[Card]:
        """Prompt the user to select cards used as a skill cost/target input."""
        controller_io = self.controller_io

        await controller_io.show_log(_t("controller.select_cards", min=min_count, max=max_count))
        for index, card in enumerate(player.hand, 1):
            await controller_io.show_log(f"  [{index}] {card.display_name}")

        while True:
            choice = await controller_io.prompt_text(_t("controller.input_prompt"))
            if not choice:
                return []

            try:
                indices = [int(value) - 1 for value in choice.split()]
                if min_count <= len(indices) <= max_count and all(
                    0 <= index < len(player.hand) for index in indices
                ):
                    return [player.hand[index] for index in indices]
            except ValueError:
                pass

            await controller_io.show_log(
                _t("controller.select_cards_range", min=min_count, max=max_count)
            )

    async def human_play_phase(
        self,
        player: Player,
        *,
        confirm_quit: Callable[[], Awaitable[bool]],
        update_playable_mask: Callable[[Player], None],
        can_do_anything: Callable[[Player], bool],
        handle_use_skill: Callable[[Player], Awaitable[None]],
        handle_play_specific_card: Callable[[Player, Card], Awaitable[None]],
    ) -> None:
        """Drive the human play-phase loop while delegating hooks back to the controller."""
        engine = self.engine
        if not engine:
            return

        controller_io = self.controller_io

        if not can_do_anything(player):
            update_playable_mask(player)
            await controller_io.show_game_state(engine, player)
            await controller_io.show_log(_t("controller.auto_skip"))
            await controller_io.show_log(_t("controller.auto_skip_detail"))
            cfg = get_config()
            if cfg.ai_turn_delay > 0:
                await asyncio.sleep(cfg.ai_turn_delay * 3)
            return

        while True:
            update_playable_mask(player)
            await controller_io.show_game_state(engine, player)

            action = await controller_io.get_player_action()

            if action == "E":
                await controller_io.show_log(_t("controller.end_play"))
                break
            elif action == "H":
                await controller_io.show_help()
            elif action == "Q":
                if await confirm_quit():
                    engine.state = GameState.FINISHED
                    return
            elif action == "S":
                await handle_use_skill(player)
            elif action.isdigit():
                card_index = int(action) - 1
                if 0 <= card_index < len(player.hand):
                    card = player.hand[card_index]
                    await handle_play_specific_card(player, card)
                else:
                    await controller_io.show_log(_t("controller.invalid_card_num"))

            if engine.is_game_over():
                return

            if not can_do_anything(player):
                await controller_io.show_log(_t("controller.auto_end"))
                await controller_io.show_log(_t("controller.auto_skip_detail"))
                cfg = get_config()
                if cfg.ai_turn_delay > 0:
                    await asyncio.sleep(cfg.ai_turn_delay * 1.5)
                break
