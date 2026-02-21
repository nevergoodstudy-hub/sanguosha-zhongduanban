"""简体中文翻译表。"""

STRINGS: dict[str, str] = {
    # ── BaseTerminalUI ──
    "ui.wait_continue": "按回车键继续...",
    "ui.invalid_choice": "无效选择",
    # ask_for_shan
    "ui.ask_shan.prompt": "\n{name} 需要出【闪】!",
    "ui.ask_shan.count": "你有 {count} 张【闪】",
    "ui.ask_shan.confirm": "是否出闪? [Y/N]: ",
    # ask_for_sha
    "ui.ask_sha.prompt": "\n{name} 需要出【杀】!",
    "ui.ask_sha.count": "你有 {count} 张【杀】",
    "ui.ask_sha.confirm": "是否出杀? [Y/N]: ",
    # ask_for_tao
    "ui.ask_tao.prompt": "\n{dying} 濒死! {savior} 是否使用【桃】救援?",
    "ui.ask_tao.count": "你有 {count} 张【桃】",
    "ui.ask_tao.confirm": "是否使用桃? [Y/N]: ",
    # ask_for_wuxie
    "ui.ask_wuxie.prompt": "\n{name} 是否使用【无懈可击】{action}【{card}】?",
    "ui.ask_wuxie.cancel": "抵消",
    "ui.ask_wuxie.activate": "使其生效",
    "ui.ask_wuxie.source_target": "来源: {source}  目标: {target}",
    "ui.ask_wuxie.count": "你有 {count} 张【无懈可击】",
    "ui.ask_wuxie.confirm": "是否使用无懈可击? [Y/N]: ",
    # ask_for_jijiang / hujia
    "ui.ask_jijiang.prompt": "\n主公发动【激将】! {name} 是否响应?",
    "ui.ask_jijiang.confirm": "是否打出杀? [Y/N]: ",
    "ui.ask_hujia.prompt": "\n主公发动【护驾】! {name} 是否响应?",
    "ui.ask_hujia.confirm": "是否打出闪? [Y/N]: ",
    # choose_suit
    "ui.choose_suit.title": "\n选择花色:",
    "ui.choose_suit.spade": "  [1] ♠ 黑桃",
    "ui.choose_suit.heart": "  [2] ♥ 红心",
    "ui.choose_suit.club": "  [3] ♣ 梅花",
    "ui.choose_suit.diamond": "  [4] ♦ 方块",
    "ui.choose_suit.confirm": "请选择 [1-4]: ",
    # ── main.py ──
    "main.interrupted": "\n\n游戏被中断，再见！",
    "main.error": "\n发生错误: {error}",
}
