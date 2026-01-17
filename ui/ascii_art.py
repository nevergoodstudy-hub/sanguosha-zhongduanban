# -*- coding: utf-8 -*-
"""
ASCII艺术模块
提供游戏中的ASCII图形
"""

from typing import List


class ASCIIArt:
    """ASCII艺术类，提供各种装饰性文字和图形"""

    # 游戏标题
    TITLE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     ████████╗██╗  ██╗██████╗ ███████╗███████╗    ██╗  ██╗██╗███╗   ██╗       ║
║        ██   ██║  ██║██╔══██╗██╔════╝██╔════╝    ██║ ██╔╝██║████╗  ██║       ║
║        ██   ███████║██████╔╝█████╗  █████╗      █████╔╝ ██║██╔██╗ ██║       ║
║        ██   ██╔══██║██╔══██╗██╔══╝  ██╔══╝      ██╔═██╗ ██║██║╚██╗██║       ║
║        ██   ██║  ██║██║  ██║███████╗███████╗    ██║  ██╗██║██║ ╚████║       ║
║        ╚═╝  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝    ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝       ║
║                                                                              ║
║                    ═══════  三 国 杀  ═══════                                 ║
║                         命令行终端版 v1.0                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

    # 简化版标题
    TITLE_SIMPLE = """
╔══════════════════════════════════════════════════════════════╗
║                    【 三 国 杀 】                              ║
║                   命令行终端版 v1.0                           ║
╚══════════════════════════════════════════════════════════════╝
"""

    # 势力图标
    KINGDOM_ICONS = {
        "wei": "【魏】",
        "shu": "【蜀】",
        "wu": "【吴】",
        "qun": "【群】"
    }

    # 身份图标
    IDENTITY_ICONS = {
        "lord": "【主公】",
        "loyalist": "【忠臣】",
        "rebel": "【反贼】",
        "spy": "【内奸】"
    }

    # 花色符号
    SUIT_SYMBOLS = {
        "spade": "♠",
        "heart": "♥",
        "club": "♣",
        "diamond": "♦"
    }

    # 体力符号
    HP_FULL = "♥"
    HP_EMPTY = "○"
    HP_LOST = "×"

    # 分隔线
    SEPARATOR_SINGLE = "─" * 60
    SEPARATOR_DOUBLE = "═" * 60

    # 边框字符
    BORDER_TOP_LEFT = "╔"
    BORDER_TOP_RIGHT = "╗"
    BORDER_BOTTOM_LEFT = "╚"
    BORDER_BOTTOM_RIGHT = "╝"
    BORDER_HORIZONTAL = "═"
    BORDER_VERTICAL = "║"
    BORDER_CROSS = "╬"
    BORDER_T_DOWN = "╦"
    BORDER_T_UP = "╩"
    BORDER_T_RIGHT = "╠"
    BORDER_T_LEFT = "╣"

    # 武将头像（简化版）
    HERO_PORTRAITS = {
        "liubei": [
            "  ╭───╮  ",
            "  │刘备│  ",
            "  │仁德│  ",
            "  ╰───╯  "
        ],
        "caocao": [
            "  ╭───╮  ",
            "  │曹操│  ",
            "  │奸雄│  ",
            "  ╰───╯  "
        ],
        "sunquan": [
            "  ╭───╮  ",
            "  │孙权│  ",
            "  │制衡│  ",
            "  ╰───╯  "
        ],
        "guanyu": [
            "  ╭───╮  ",
            "  │关羽│  ",
            "  │武圣│  ",
            "  ╰───╯  "
        ],
        "zhangfei": [
            "  ╭───╮  ",
            "  │张飞│  ",
            "  │咆哮│  ",
            "  ╰───╯  "
        ],
        "zhugeliang": [
            "  ╭───╮  ",
            "  │诸葛│  ",
            "  │观星│  ",
            "  ╰───╯  "
        ],
        "zhouyu": [
            "  ╭───╮  ",
            "  │周瑜│  ",
            "  │英姿│  ",
            "  ╰───╯  "
        ],
        "lvbu": [
            "  ╭───╮  ",
            "  │吕布│  ",
            "  │无双│  ",
            "  ╰───╯  "
        ]
    }

    # 卡牌边框
    CARD_TOP = "┌─────┐"
    CARD_BOTTOM = "└─────┘"
    CARD_SIDE = "│"

    # 游戏结束画面
    VICTORY = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ██╗   ██╗██╗ ██████╗████████╗ ██████╗ ██████╗ ██╗   ██╗  ║
║     ██║   ██║██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗╚██╗ ██╔╝  ║
║     ██║   ██║██║██║        ██║   ██║   ██║██████╔╝ ╚████╔╝   ║
║     ╚██╗ ██╔╝██║██║        ██║   ██║   ██║██╔══██╗  ╚██╔╝    ║
║      ╚████╔╝ ██║╚██████╗   ██║   ╚██████╔╝██║  ██║   ██║     ║
║       ╚═══╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

    DEFEAT = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║      ██████╗ ███████╗███████╗███████╗ █████╗ ████████╗       ║
║      ██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗╚══██╔══╝       ║
║      ██║  ██║█████╗  █████╗  █████╗  ███████║   ██║          ║
║      ██║  ██║██╔══╝  ██╔══╝  ██╔══╝  ██╔══██║   ██║          ║
║      ██████╔╝███████╗██║     ███████╗██║  ██║   ██║          ║
║      ╚═════╝ ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

    @classmethod
    def get_hp_bar(cls, current_hp: int, max_hp: int) -> str:
        """
        生成体力条

        Args:
            current_hp: 当前体力
            max_hp: 最大体力

        Returns:
            体力条字符串
        """
        full_hearts = cls.HP_FULL * current_hp
        empty_hearts = cls.HP_EMPTY * (max_hp - current_hp)
        return full_hearts + empty_hearts

    @classmethod
    def get_card_display(cls, name: str, suit: str, number: str) -> List[str]:
        """
        生成卡牌显示

        Args:
            name: 卡牌名称
            suit: 花色
            number: 点数

        Returns:
            卡牌显示的字符串列表
        """
        suit_symbol = cls.SUIT_SYMBOLS.get(suit, "?")

        # 确保名称长度为2（中文字符）
        display_name = name[:2] if len(name) >= 2 else name.ljust(2)

        return [
            cls.CARD_TOP,
            f"│{suit_symbol}{number.ljust(3)}│",
            f"│{display_name}  │",
            f"│   {suit_symbol}│",
            cls.CARD_BOTTOM
        ]

    @classmethod
    def get_hero_portrait(cls, hero_id: str) -> List[str]:
        """
        获取武将头像

        Args:
            hero_id: 武将ID

        Returns:
            武将头像的字符串列表
        """
        return cls.HERO_PORTRAITS.get(hero_id, [
            "  ╭───╮  ",
            "  │????│  ",
            "  │????│  ",
            "  ╰───╯  "
        ])

    @classmethod
    def create_box(cls, content: List[str], width: int = 60,
                   title: str = "") -> List[str]:
        """
        创建带边框的文本框

        Args:
            content: 内容行列表
            width: 宽度
            title: 标题

        Returns:
            带边框的文本行列表
        """
        result = []

        # 顶部边框
        if title:
            title_part = f" {title} "
            padding_left = (width - 2 - len(title_part)) // 2
            padding_right = width - 2 - len(title_part) - padding_left
            top_line = (cls.BORDER_TOP_LEFT +
                        cls.BORDER_HORIZONTAL * padding_left +
                        title_part +
                        cls.BORDER_HORIZONTAL * padding_right +
                        cls.BORDER_TOP_RIGHT)
        else:
            top_line = (cls.BORDER_TOP_LEFT +
                        cls.BORDER_HORIZONTAL * (width - 2) +
                        cls.BORDER_TOP_RIGHT)
        result.append(top_line)

        # 内容
        for line in content:
            # 计算实际显示宽度（考虑中文字符）
            display_width = cls._get_display_width(line)
            padding = width - 2 - display_width
            if padding < 0:
                padding = 0
            padded_line = f"{cls.BORDER_VERTICAL}{line}{' ' * padding}{cls.BORDER_VERTICAL}"
            result.append(padded_line)

        # 底部边框
        bottom_line = (cls.BORDER_BOTTOM_LEFT +
                       cls.BORDER_HORIZONTAL * (width - 2) +
                       cls.BORDER_BOTTOM_RIGHT)
        result.append(bottom_line)

        return result

    @classmethod
    def _get_display_width(cls, text: str) -> int:
        """
        计算字符串的显示宽度（中文字符算2个宽度）

        Args:
            text: 文本

        Returns:
            显示宽度
        """
        width = 0
        for char in text:
            if ord(char) > 127:
                width += 2
            else:
                width += 1
        return width

    @classmethod
    def center_text(cls, text: str, width: int) -> str:
        """
        居中文本

        Args:
            text: 文本
            width: 目标宽度

        Returns:
            居中后的文本
        """
        display_width = cls._get_display_width(text)
        padding = (width - display_width) // 2
        return " " * padding + text

    @classmethod
    def get_menu(cls, title: str, options: List[str], width: int = 50) -> List[str]:
        """
        创建菜单

        Args:
            title: 菜单标题
            options: 选项列表
            width: 宽度

        Returns:
            菜单文本行列表
        """
        content = []
        content.append(cls.center_text(title, width - 4))
        content.append(cls.SEPARATOR_SINGLE[:width - 4])
        for i, option in enumerate(options, 1):
            content.append(f"  [{i}] {option}")
        content.append("")

        return cls.create_box(content, width)

    @classmethod
    def get_help_text(cls) -> str:
        """获取帮助文本"""
        return """
╔══════════════════════════════════════════════════════════════╗
║                         游戏帮助                             ║
╠══════════════════════════════════════════════════════════════╣
║  基本操作:                                                   ║
║    [P] 出牌 - 选择手牌使用                                   ║
║    [S] 技能 - 使用武将技能                                   ║
║    [D] 弃牌 - 手动弃牌                                       ║
║    [E] 结束 - 结束当前回合                                   ║
║    [H] 帮助 - 显示此帮助信息                                 ║
║    [Q] 退出 - 退出游戏                                       ║
╠══════════════════════════════════════════════════════════════╣
║  选择目标:                                                   ║
║    输入数字选择对应的玩家或卡牌                              ║
║    输入 0 或 C 取消当前操作                                  ║
╠══════════════════════════════════════════════════════════════╣
║  花色说明:                                                   ║
║    ♠ - 黑桃    ♥ - 红心    ♣ - 梅花    ♦ - 方块              ║
╠══════════════════════════════════════════════════════════════╣
║  体力说明:                                                   ║
║    ♥ - 满体力  ○ - 空体力                                    ║
╚══════════════════════════════════════════════════════════════╝
"""
