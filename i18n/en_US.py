"""English translation table."""

STRINGS: dict[str, str] = {
    # ── BaseTerminalUI ──
    "ui.wait_continue": "Press Enter to continue...",
    "ui.invalid_choice": "Invalid choice",

    # ask_for_shan
    "ui.ask_shan.prompt": "\n{name} needs to play [Dodge]!",
    "ui.ask_shan.count": "You have {count} [Dodge] card(s)",
    "ui.ask_shan.confirm": "Play Dodge? [Y/N]: ",

    # ask_for_sha
    "ui.ask_sha.prompt": "\n{name} needs to play [Strike]!",
    "ui.ask_sha.count": "You have {count} [Strike] card(s)",
    "ui.ask_sha.confirm": "Play Strike? [Y/N]: ",

    # ask_for_tao
    "ui.ask_tao.prompt": "\n{dying} is dying! {savior}, use [Peach] to save?",
    "ui.ask_tao.count": "You have {count} [Peach] card(s)",
    "ui.ask_tao.confirm": "Use Peach? [Y/N]: ",

    # ask_for_wuxie
    "ui.ask_wuxie.prompt": "\n{name}: use [Nullification] to {action} [{card}]?",
    "ui.ask_wuxie.cancel": "cancel",
    "ui.ask_wuxie.activate": "re-activate",
    "ui.ask_wuxie.source_target": "Source: {source}  Target: {target}",
    "ui.ask_wuxie.count": "You have {count} [Nullification] card(s)",
    "ui.ask_wuxie.confirm": "Use Nullification? [Y/N]: ",

    # ask_for_jijiang / hujia
    "ui.ask_jijiang.prompt": "\nLord uses [Rouse]! {name}, respond?",
    "ui.ask_jijiang.confirm": "Play Strike? [Y/N]: ",
    "ui.ask_hujia.prompt": "\nLord uses [Royal Escort]! {name}, respond?",
    "ui.ask_hujia.confirm": "Play Dodge? [Y/N]: ",

    # choose_suit
    "ui.choose_suit.title": "\nChoose suit:",
    "ui.choose_suit.spade": "  [1] ♠ Spade",
    "ui.choose_suit.heart": "  [2] ♥ Heart",
    "ui.choose_suit.club": "  [3] ♣ Club",
    "ui.choose_suit.diamond": "  [4] ♦ Diamond",
    "ui.choose_suit.confirm": "Select [1-4]: ",

    # ── main.py ──
    "main.interrupted": "\n\nGame interrupted. Goodbye!",
    "main.error": "\nError: {error}",
}
