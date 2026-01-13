from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from time import sleep

def make_layout() -> Layout:
    layout = Layout(name="root")
    
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=10),
    )
    
    layout["main"].split_row(
        Layout(name="players", ratio=2),
        Layout(name="table", ratio=3),
        Layout(name="log", ratio=2),
    )
    
    return layout

def generate_header():
    return Panel(Text("三国杀 Sanguosha TUI - Round 3", justify="center", style="bold white on blue"), style="blue")

def generate_player_list():
    table = Table(title="其他玩家", expand=True, border_style="green")
    table.add_column("座位", justify="center", style="cyan", no_wrap=True)
    table.add_column("武将", style="magenta")
    table.add_column("状态", justify="right")
    
    table.add_row("2", "刘备", "HP:4/4 🎴:4")
    table.add_row("3", "曹操", "HP:3/4 🎴:2 [🗡️]")
    table.add_row("4", "孙权", "HP:2/4 🎴:5")
    
    return Panel(table, title="Players", border_style="green")

def generate_table():
    content = Text()
    content.append("\n\n")
    content.append("   🗡️  曹操 使用了 【杀】 -> 刘备\n", style="bold red")
    content.append("   🛡️  刘备 打出了 【闪】\n", style="bold yellow")
    return Panel(content, title="Table Area", border_style="yellow")

def generate_log():
    log_text = Text()
    log_text.append("[System] 游戏开始\n", style="dim")
    log_text.append("[Turn] 曹操的回合\n", style="bold")
    log_text.append("[Card] 曹操 使用了 杀\n", style="red")
    return Panel(log_text, title="Game Log", border_style="white")

def generate_footer():
    hand_cards = Table.grid(padding=1)
    hand_cards.add_column("1", justify="center")
    hand_cards.add_column("2", justify="center")
    hand_cards.add_column("3", justify="center")
    
    c1 = Panel("杀\n♠ 7", style="white on red", width=8)
    c2 = Panel("闪\n♥ K", style="black on yellow", width=8)
    c3 = Panel("桃\n♥ 3", style="white on green", width=8)
    
    hand_cards.add_row(c1, c2, c3)
    
    return Panel(hand_cards, title="My Hand (HP: 3/3)", border_style="blue")

layout = make_layout()
layout["header"].update(generate_header())
layout["players"].update(generate_player_list())
layout["table"].update(generate_table())
layout["log"].update(generate_log())
layout["footer"].update(generate_footer())

console = Console()
console.print(layout)
