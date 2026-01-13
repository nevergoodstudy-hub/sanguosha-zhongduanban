# -*- coding: utf-8 -*-
"""
Rich TUI Module
Uses the 'rich' library to provide a modern terminal user interface.
"""

import sys
import os
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED, DOUBLE
from rich.align import Align
from rich.live import Live
from rich.columns import Columns
from rich import box

from game.card import CardSuit
from ui.ascii_art import ASCIIArt

if TYPE_CHECKING:
    from game.player import Player, Identity
    from game.card import Card
    from game.engine import GameEngine, GamePhase
    from game.hero import Hero

class RichTerminalUI:
    """
    Rich TUI Class
    Replaces TerminalUI with a richer interface.
    """

    def __init__(self, use_color: bool = True):
        self.console = Console(highlight=False)
        self.layout = Layout()
        self.engine: Optional['GameEngine'] = None
        self.log_messages: List[str] = []
        self.max_log_lines = 15  # More space for logs in TUI
        
        # Initialize layout structure
        self._init_layout()

    def _init_layout(self):
        """Initialize the layout tree"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        self.layout["left"].split(
            Layout(name="table", ratio=2),
            Layout(name="player", ratio=1)
        )
        
        self.layout["right"].split(
            Layout(name="logs", ratio=2),
            Layout(name="info", ratio=1)
        )

    def set_engine(self, engine: 'GameEngine') -> None:
        self.engine = engine

    def clear_screen(self) -> None:
        self.console.clear()

    # --- Menu Methods (Reusing simple prints or upgrading) ---
    # For Phase 1, we can reuse some simple logic or simple rich prints for menus,
    # as the complex layout is mostly for the game loop.

    def show_title(self) -> None:
        self.clear_screen()
        # Use a nice panel for title
        title_text = Text(ASCIIArt.TITLE_SIMPLE, style="bold red")
        self.console.print(Panel(title_text, box=DOUBLE, title="Sanguosha CLI"))

    def show_main_menu(self) -> int:
        self.show_title()
        
        menu = Table(box=ROUNDED, show_header=False, show_edge=False)
        menu.add_column("Option", justify="right")
        menu.add_column("Description", justify="left")
        
        menu.add_row("[1]", "Start New Game")
        menu.add_row("[2]", "Game Rules")
        menu.add_row("[3]", "Quit")
        
        self.console.print(Align.center(menu))
        self.console.print()
        
        while True:
            choice = input("Please select [1-3]: ").strip()
            if choice in ['1', '2', '3']:
                return int(choice)
            self.console.print("[red]Invalid selection, please try again[/red]")

    def show_player_count_menu(self) -> int:
        self.clear_screen()
        self.console.print(Panel("Select Number of Players", style="bold blue", box=ROUNDED))
        
        table = Table(box=ROUNDED)
        table.add_column("Players", style="cyan")
        table.add_column("Configuration", style="green")
        
        configs = [
            (2, "Lord vs Rebel"),
            (3, "Lord vs Rebel + Spy"),
            (4, "Lord + Loyalist vs Rebel + Spy"),
            (5, "Lord + Loyalist vs 2 Rebels + Spy"),
            (6, "Lord + Loyalist vs 3 Rebels + Spy"),
            (7, "Lord + 2 Loyalists vs 3 Rebels + Spy"),
            (8, "Lord + 2 Loyalists vs 4 Rebels + Spy"),
        ]
        
        for count, config in configs:
            table.add_row(f"[{count}]", config)
            
        self.console.print(Align.center(table))
        self.console.print()
        
        while True:
            choice = input("Select players [2-8]: ").strip()
            if choice in [str(c) for c, _ in configs]:
                return int(choice)
            self.console.print("[red]Invalid selection[/red]")

    def show_difficulty_menu(self) -> str:
        self.clear_screen()
        self.console.print(Panel("Select AI Difficulty", style="bold yellow", box=ROUNDED))
        
        table = Table(box=ROUNDED, show_header=False)
        table.add_row("[1] Easy", "Random actions")
        table.add_row("[2] Normal", "Basic strategy")
        table.add_row("[3] Hard", "Deep strategy (Simulated)")
        
        self.console.print(Align.center(table))
        
        while True:
            choice = input("Select difficulty [1-3]: ").strip()
            if choice == '1': return "easy"
            if choice == '2': return "normal"
            if choice == '3': return "hard"
            self.console.print("[red]Invalid selection[/red]")

    def show_hero_selection(self, heroes: List['Hero'], selected_count: int = 1, is_lord: bool = False) -> List['Hero']:
        self.clear_screen()
        title = "Lord Hero Selection (5 Choose 1)" if is_lord else "Hero Selection (3 Choose 1)"
        self.console.print(Panel(title, style="bold magenta", box=DOUBLE))
        
        hero_panels = []
        for i, hero in enumerate(heroes, 1):
            kingdom_color = {
                "Wei": "blue", "Shu": "red", "Wu": "green", "Qun": "white"
            }.get(hero.kingdom.value, "white")
            
            content = Text()
            content.append(f"{hero.name} [{hero.kingdom.chinese_name}]\n", style=f"bold {kingdom_color}")
            content.append(f"HP: {hero.max_hp}\n", style="bold white")
            content.append(f"{hero.title}\n\n", style="italic")
            
            for skill in hero.skills:
                content.append(f"[{skill.name}] ", style="bold yellow")
                content.append(f"{skill.description[:50]}...\n")
                
            hero_panels.append(Panel(content, title=f"[{i}]", box=ROUNDED))
            
        self.console.print(Columns(hero_panels))
        self.console.print()
        
        selected = []
        while len(selected) < selected_count:
            remaining = selected_count - len(selected)
            prompt = f"Select hero [1-{len(heroes)}]"
            if selected_count > 1:
                prompt += f" (Need {remaining} more)"
            
            choice = input(prompt + ": ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(heroes):
                    hero = heroes[idx]
                    if hero not in selected:
                        selected.append(hero)
                        self.console.print(f"[green]Selected: {hero.name}[/green]")
                    else:
                        self.console.print("[yellow]Already selected[/yellow]")
                else:
                    self.console.print("[red]Invalid number[/red]")
            except ValueError:
                self.console.print("[red]Please enter a number[/red]")
                
        return selected

    # --- Game State Rendering ---

    def _get_suit_icon(self, suit: CardSuit) -> str:
        icons = {
            CardSuit.SPADE: "♠",
            CardSuit.HEART: "♥",
            CardSuit.CLUB: "♣",
            CardSuit.DIAMOND: "♦"
        }
        return icons.get(suit, "?")
        
    def _get_suit_color(self, suit: CardSuit) -> str:
        return "red" if suit in [CardSuit.HEART, CardSuit.DIAMOND] else "white" # Using white for black suits on dark terminal

    def _render_header(self, engine: 'GameEngine') -> Panel:
        phase_names = {
            "prepare": "Preparation",
            "judge": "Judgement",
            "draw": "Draw",
            "play": "Play",
            "discard": "Discard",
            "end": "End"
        }
        phase_str = phase_names.get(engine.phase.value, engine.phase.value)
        
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right", ratio=1)
        
        round_info = f"Round: {engine.round_count}"
        turn_info = f"Current Turn: {engine.current_player.name}"
        phase_info = f"Phase: {phase_str}"
        
        grid.add_row(round_info, turn_info, phase_info)
        return Panel(grid, style="white on blue")

    def _render_table(self, engine: 'GameEngine', human: 'Player') -> Panel:
        """Render other players"""
        grid = Table.grid(padding=1)
        
        # Simple grid for others for now
        # Ideally, we calculate positions relative to human
        
        others = engine.get_other_players(human)
        if not others:
            return Panel("No other players")
            
        # Create a table for players
        table = Table(box=ROUNDED, show_edge=False, expand=True)
        table.add_column("Name/Hero")
        table.add_column("Status")
        table.add_column("Equips")
        table.add_column("Distance")
        
        for p in others:
            if not p.is_alive:
                table.add_row(f"[strike]{p.name}[/strike]", "[red]Dead[/red]", "", "")
                continue
                
            hero_str = f"{p.hero.name if p.hero else 'Unknown'}"
            kingdom = p.hero.kingdom.chinese_name if p.hero else ""
            color = "white"
            if p.hero:
                color = {
                    "Wei": "blue", "Shu": "red", "Wu": "green", "Qun": "white"
                }.get(p.hero.kingdom.value, "white")
            
            name_txt = Text(f"{p.name}\n")
            name_txt.append(f"{hero_str} [{kingdom}]", style=f"bold {color}")
            if p.identity.value == "lord":
                name_txt.append("\n[LORD]", style="bold yellow")
            
            hp_color = "green" if p.hp > 2 else "red"
            status_txt = Text()
            status_txt.append(f"HP: {p.hp}/{p.max_hp}\n", style=hp_color)
            status_txt.append(f"Hand: {p.hand_count}", style="white")
            if p.judge_area:
                status_txt.append(f"\nJudge: {len(p.judge_area)}", style="yellow")
                
            equips = []
            if p.equipment.weapon: equips.append(f"⚔ {p.equipment.weapon.name}")
            if p.equipment.armor: equips.append(f"🛡 {p.equipment.armor.name}")
            if p.equipment.horse_minus: equips.append(f"-Hp {p.equipment.horse_minus.name}")
            if p.equipment.horse_plus: equips.append(f"+Hp {p.equipment.horse_plus.name}")
            equip_str = "\n".join(equips)
            
            dist = engine.calculate_distance(human, p)
            in_range = dist <= human.equipment.attack_range
            dist_txt = Text(f"{dist}")
            if in_range:
                dist_txt.append(" (In Range)", style="bold green")
                
            table.add_row(name_txt, status_txt, equip_str, dist_txt)
            
        return Panel(table, title="Game Table")

    def _render_player_area(self, player: 'Player') -> Panel:
        """Render human player area"""
        
        # Layout: Info | Equipment | Skills | Hand
        grid = Table.grid(expand=True, padding=1)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        
        # Left side: Stats & Equips
        left_grid = Table.grid(expand=True)
        left_grid.add_row(Text(player.hero.name, style="bold"), f"[{player.hero.kingdom.chinese_name}]")
        left_grid.add_row(f"Identity: {player.identity.chinese_name}")
        left_grid.add_row(Text(f"HP: {player.hp}/{player.max_hp}", style="green"))
        left_grid.add_row("")
        
        left_grid.add_row(Text("Equipment:", style="bold"))
        if player.equipment.weapon: left_grid.add_row(f"⚔ {player.equipment.weapon.name}")
        if player.equipment.armor: left_grid.add_row(f"🛡 {player.equipment.armor.name}")
        if player.equipment.horse_minus: left_grid.add_row(f"-Hp {player.equipment.horse_minus.name}")
        if player.equipment.horse_plus: left_grid.add_row(f"+Hp {player.equipment.horse_plus.name}")
        
        # Right side: Skills & Hand
        right_grid = Table.grid(expand=True)
        right_grid.add_row(Text("Skills:", style="bold"))
        if player.hero:
            for skill in player.hero.skills:
                right_grid.add_row(f"• {skill.name}")
        right_grid.add_row("")
        
        # Hand Cards visualization
        hand_table = Table(box=None, show_header=False, pad_edge=False, collapse_padding=True)
        # Create columns for cards (max 10 per row maybe? handled by auto wrapping or logic)
        
        hand_text = Text()
        for i, card in enumerate(player.hand, 1):
            suit_icon = self._get_suit_icon(card.suit)
            color = self._get_suit_color(card.suit)
            
            card_txt = Text(f"[{i}] {suit_icon}{card.number_str} {card.name}   ", style=color)
            hand_text.append(card_txt)
            
        right_grid.add_row(Text("Hand Cards:", style="bold"))
        right_grid.add_row(hand_text)
        
        grid.add_row(left_grid, right_grid)
        
        return Panel(grid, title=f"{player.name} (You)", border_style="green")

    def _render_logs(self) -> Panel:
        log_text = Text()
        for msg in self.log_messages[-self.max_log_lines:]:
            log_text.append(msg + "\n")
        return Panel(log_text, title="Game Logs", border_style="cyan")
        
    def _render_info_panel(self, engine: 'GameEngine', player: 'Player') -> Panel:
        """Context sensitive help/info"""
        info = Text()
        if engine.phase.value == "play" and engine.current_player == player:
            info.append("Your Turn - Action Phase\n\n", style="bold green")
            info.append("[P] Play Card\n")
            info.append("[S] Use Skill\n")
            info.append("[E] End Turn\n")
            info.append("[H] Help\n")
            info.append("[Q] Quit\n")
        else:
             info.append(f"Waiting for {engine.current_player.name}...\n", style="yellow")
             
        return Panel(info, title="Actions")

    def show_game_state(self, engine: 'GameEngine', current_player: 'Player') -> None:
        """Render the full game interface"""
        self.console.clear()
        
        # Update layout components
        self.layout["header"].update(self._render_header(engine))
        
        human = engine.human_player
        if human:
            self.layout["table"].update(self._render_table(engine, human))
            self.layout["player"].update(self._render_player_area(human))
            self.layout["info"].update(self._render_info_panel(engine, human))
        else:
            self.layout["table"].update(Panel("Spectator Mode"))
            
        self.layout["logs"].update(self._render_logs())
        
        # Render the layout
        self.console.print(self.layout)

    def show_log(self, message: str) -> None:
        self.log_messages.append(message)
        # We don't auto-refresh here to avoid flickering if multiple logs come in
        # The next game state update will show it.
        # But if we want instant feedback for events we might print?
        # For TUI, it's better to update state. 
        # But since we use input() which blocks, we might not see logs until input returns?
        # Actually, we print the layout BEFORE input.
        
    def get_player_action(self) -> str:
        # State is already shown
        while True:
            action = input("\nEnter Action [P/S/E/H/Q] or Card Index: ").strip().upper()
            if action in ['P', 'S', 'E', 'H', 'Q', 'D']:
                return action
            if action.isdigit():
                return action
            self.console.print("[red]Invalid action[/red]")

    # --- Interaction Methods (Wrappers around input/rendering) ---

    def _selection_menu(self, title: str, items: List[Any], item_formatter) -> Optional[Any]:
        """Generic selection menu helper"""
        self.console.print(f"\n[bold cyan]{title}[/bold cyan] (0 to cancel):")
        for i, item in enumerate(items, 1):
            self.console.print(f"  [{i}] {item_formatter(item)}")
            
        while True:
            choice = input(f"Select [0-{len(items)}]: ").strip()
            try:
                idx = int(choice)
                if idx == 0: return None
                if 1 <= idx <= len(items):
                    return items[idx-1]
            except ValueError:
                pass
            self.console.print("[red]Invalid selection[/red]")

    def choose_card_to_play(self, player: 'Player') -> Optional['Card']:
        if not player.hand:
            self.console.print("[yellow]No cards in hand[/yellow]")
            return None
            
        def format_card(card):
            return f"{card.display_name} - {card.description[:30]}..."
            
        return self._selection_menu("Select Card to Play", player.hand, format_card)

    def choose_target(self, player: 'Player', targets: List['Player'], prompt: str = "Select Target") -> Optional['Player']:
        if not targets:
            self.console.print("[yellow]No available targets[/yellow]")
            return None
            
        def format_target(t):
            hero_name = t.hero.name if t.hero else "???"
            return f"{t.name} ({hero_name}) HP:{t.hp}/{t.max_hp}"
            
        return self._selection_menu(prompt, targets, format_target)

    def choose_cards_to_discard(self, player: 'Player', count: int) -> List['Card']:
        self.console.print(f"\n[bold yellow]Discard {count} cards:[/bold yellow]")
        for i, card in enumerate(player.hand, 1):
            self.console.print(f"  [{i}] {card.display_name}")
            
        selected = []
        while len(selected) < count:
            remaining = count - len(selected)
            choice = input(f"Select card to discard ({remaining} more): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(player.hand):
                    card = player.hand[idx]
                    if card not in selected:
                        selected.append(card)
                        self.console.print(f"[green]Selected: {card.display_name}[/green]")
                    else:
                        self.console.print("[yellow]Already selected[/yellow]")
                else:
                    self.console.print("[red]Invalid index[/red]")
            except ValueError:
                self.console.print("[red]Enter a number[/red]")
        return selected

    def ask_for_shan(self, player: 'Player') -> Optional['Card']:
        shan_cards = player.get_cards_by_name("闪")
        if not shan_cards: return None
        
        self.console.print(f"\n[bold red]ATTACKED![/bold red] {player.name}, use 'Shan'?")
        if input("Use Shan? [Y/N]: ").strip().upper() == 'Y':
            return shan_cards[0]
        return None

    def ask_for_sha(self, player: 'Player') -> Optional['Card']:
        sha_cards = player.get_cards_by_name("杀")
        if not sha_cards: return None
        
        self.console.print(f"\n{player.name}, need to use 'Sha'!")
        if input("Use Sha? [Y/N]: ").strip().upper() == 'Y':
            return sha_cards[0]
        return None

    def ask_for_tao(self, savior: 'Player', dying: 'Player') -> Optional['Card']:
        tao_cards = savior.get_cards_by_name("桃")
        if not tao_cards: return None
        
        self.console.print(f"\n[bold red]DYING![/bold red] {dying.name} is dying!")
        if input(f"{savior.name}, use Peach? [Y/N]: ").strip().upper() == 'Y':
            return tao_cards[0]
        return None

    def ask_for_wuxie(self, responder: 'Player', trick_card: 'Card', 
                      source: 'Player', target: Optional['Player'], 
                      currently_cancelled: bool) -> Optional['Card']:
        wuxie_cards = responder.get_cards_by_name("无懈可击")
        if not wuxie_cards:
            return None

        action = "抵消" if not currently_cancelled else "使其生效"
        target_name = target.name if target else "-"
        self.console.print(
            f"\n[bold cyan]{responder.name}[/bold cyan] 是否使用【无懈可击】{action}【{trick_card.name}】?"
        )
        self.console.print(f"来源: {source.name}  目标: {target_name}")
        if input("Use Wuxie? [Y/N]: ").strip().upper() == 'Y':
            return wuxie_cards[0]
        return None

    def choose_card_from_player(self, chooser: 'Player', target: 'Player') -> Optional['Card']:
        all_cards = target.get_all_cards()
        if not all_cards: return None
        
        self.console.print(f"\nChoosing card from {target.name}:")
        
        # Display simplified view to avoid cheating (though logic handles this, UI should match)
        # engine should handle what is visible, here we just list indices usually
        # But `get_all_cards` returns actual objects.
        
        # Group by hand vs equipment for display
        hand_count = len(target.hand)
        if hand_count > 0:
            self.console.print(f"  [1-{hand_count}] Hand Cards ({hand_count})")
            
        equips = target.equipment.get_all_cards()
        offset = hand_count
        for i, card in enumerate(equips, 1):
            self.console.print(f"  [{offset + i}] Equipment: {card.display_name}")
            
        while True:
            try:
                idx = int(input(f"Select [1-{len(all_cards)}]: ")) - 1
                if 0 <= idx < len(all_cards):
                    return all_cards[idx]
            except ValueError:
                pass

    def choose_suit(self, player: 'Player') -> CardSuit:
        self.console.print("\nChoose Suit:")
        self.console.print("  [1] ♠ SPADE")
        self.console.print("  [2] ♥ HEART")
        self.console.print("  [3] ♣ CLUB")
        self.console.print("  [4] ♦ DIAMOND")
        
        while True:
            c = input("Select [1-4]: ").strip()
            if c == '1': return CardSuit.SPADE
            if c == '2': return CardSuit.HEART
            if c == '3': return CardSuit.CLUB
            if c == '4': return CardSuit.DIAMOND

    def guanxing_selection(self, player: 'Player', cards: List['Card']) -> Tuple[List['Card'], List['Card']]:
        self.console.print("\n[bold purple]Guanxing (Star Gazing)[/bold purple]")
        for i, card in enumerate(cards, 1):
            self.console.print(f"  [{i}] {card.display_name}")
            
        self.console.print("Enter indices for TOP of deck (space separated). Others go to BOTTOM.")
        choice = input("Top cards indices: ").strip()
        
        if not choice:
            return [], cards[:]
            
        try:
            indices = [int(x)-1 for x in choice.split()]
            top = [cards[i] for i in indices if 0 <= i < len(cards)]
            bottom = [c for c in cards if c not in top]
            return top, bottom
        except ValueError:
            return [], cards[:] # Fail safe

    def show_skill_menu(self, player: 'Player', usable_skills: List[str]) -> Optional[str]:
        if not usable_skills: return None
        
        def format_skill(sid):
            s = player.get_skill(sid)
            return f"{s.name} - {s.description[:40]}..."
            
        return self._selection_menu("Select Skill", usable_skills, format_skill)

    def show_help(self) -> None:
        self.console.print(Panel(ASCIIArt.get_help_text(), title="Help"))
        input("Press Enter...")

    def show_game_over(self, winner_message: str, is_victory: bool) -> None:
        self.clear_screen()
        style = "bold green" if is_victory else "bold red"
        title = ASCIIArt.VICTORY if is_victory else ASCIIArt.DEFEAT
        
        self.console.print(Panel(title + "\n\n" + winner_message, style=style, box=DOUBLE))
        input("Press Enter to return...")

    def show_rules(self) -> None:
        self.clear_screen()
        # Simplified rules display
        rules = """
        [bold]Game Goal:[/bold]
        Lord: Kill all Rebels and Spies.
        Rebel: Kill the Lord.
        Loyalist: Protect the Lord.
        Spy: Kill everyone else, then the Lord.
        
        [bold]Turn Flow:[/bold]
        1. Prepare
        2. Judge
        3. Draw (2 cards)
        4. Play (Use cards/skills)
        5. Discard (Keep cards <= HP)
        6. End
        """
        self.console.print(Panel(rules, title="Rules", box=ROUNDED))
        input("Press Enter...")

    def wait_for_continue(self, message: str = "Press Enter to continue...") -> None:
        input(message)

    def ask_for_jijiang(self, player: 'Player') -> Optional['Card']:
        sha_cards = player.get_cards_by_name("杀")
        if not sha_cards: return None
        if input(f"{player.name}, respond to Lord's Jijiang (Strike)? [Y/N]: ").upper() == 'Y':
            return sha_cards[0]
        return None

    def ask_for_hujia(self, player: 'Player') -> Optional['Card']:
        shan_cards = player.get_cards_by_name("闪")
        if not shan_cards: return None
        if input(f"{player.name}, respond to Lord's Hujia (Dodge)? [Y/N]: ").upper() == 'Y':
            return shan_cards[0]
        return None
