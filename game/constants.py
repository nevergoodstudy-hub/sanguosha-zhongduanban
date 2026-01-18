# -*- coding: utf-8 -*-
"""
游戏常量模块
定义游戏中使用的各类常量和枚举

本模块集中管理所有魔法字符串和常量值，
避免硬编码分散在代码各处。
"""

from enum import Enum


class SkillId(str, Enum):
    """
    技能ID枚举

    继承 str 以便直接与字符串比较
    """
    # ========== 蜀国武将技能 ==========
    RENDE = "rende"             # 刘备 - 仁德
    JIJIANG = "jijiang"         # 刘备 - 激将（主公技）
    WUSHENG = "wusheng"         # 关羽 - 武圣
    PAOXIAO = "paoxiao"         # 张飞 - 咆哮
    GUANXING = "guanxing"       # 诸葛亮 - 观星
    KONGCHENG = "kongcheng"     # 诸葛亮 - 空城
    LONGDAN = "longdan"         # 赵云 - 龙胆
    MASHU = "mashu"             # 马超 - 马术
    TIEJI = "tieji"             # 马超 - 铁骑
    JIZHI = "jizhi"             # 黄月英 - 集智
    QICAI = "qicai"             # 黄月英 - 奇才
    LIEGONG = "liegong"         # 黄忠 - 烈弓
    KUANGGU = "kuanggu"         # 魏延 - 狂骨

    # ========== 魏国武将技能 ==========
    JIANXIONG = "jianxiong"     # 曹操 - 奸雄
    HUJIA = "hujia"             # 曹操 - 护驾（主公技）
    FANKUI = "fankui"           # 司马懿 - 反馈
    GUICAI = "guicai"           # 司马懿 - 鬼才
    GANGLIE = "ganglie"         # 夏侯惇 - 刚烈
    TUXI = "tuxi"               # 张辽 - 突袭
    DUANLIANG = "duanliang"     # 徐晃 - 断粮
    JUSHOU = "jushou"           # 曹仁 - 据守
    SHENSU = "shensu"           # 夏侯渊 - 神速

    # ========== 吴国武将技能 ==========
    ZHIHENG = "zhiheng"         # 孙权 - 制衡
    JIUYUAN = "jiuyuan"         # 孙权 - 救援（主公技）
    YINGZI = "yingzi"           # 周瑜 - 英姿
    FANJIAN = "fanjian"         # 周瑜 - 反间
    GUOSE = "guose"             # 大乔 - 国色
    LIULI = "liuli"             # 大乔 - 流离
    QIXI = "qixi"               # 甘宁 - 奇袭
    KEJI = "keji"               # 吕蒙 - 克己
    KUROU = "kurou"             # 黄盖 - 苦肉
    JIEYIN = "jieyin"           # 孙尚香 - 结姻
    XIAOJI = "xiaoji"           # 孙尚香 - 枭姬

    # ========== 群雄武将技能 ==========
    WUSHUANG = "wushuang"       # 吕布 - 无双
    QINGNANG = "qingnang"       # 华佗 - 青囊
    JIJIU = "jijiu"             # 华佗 - 急救
    LIJIAN = "lijian"           # 貂蝉 - 离间
    BIYUE = "biyue"             # 貂蝉 - 闭月


class SkillTiming(str, Enum):
    """技能触发时机"""
    PREPARE = "prepare"         # 准备阶段
    JUDGE = "judge"             # 判定阶段
    DRAW = "draw"               # 摸牌阶段
    PLAY = "play"               # 出牌阶段
    DISCARD = "discard"         # 弃牌阶段
    END = "end"                 # 结束阶段
    DAMAGE_TAKEN = "damage_taken"   # 受到伤害后
    DAMAGE_DEALT = "damage_dealt"   # 造成伤害后
    DYING = "dying"             # 濒死时
    DEATH = "death"             # 死亡时
    PASSIVE = "passive"         # 被动/锁定技


class SkillCategory(str, Enum):
    """技能类别"""
    ACTIVE = "active"           # 主动技
    PASSIVE = "passive"         # 被动技/锁定技
    LORD = "lord"               # 主公技


class DamageTypeStr(str, Enum):
    """伤害类型字符串"""
    NORMAL = "normal"
    FIRE = "fire"
    THUNDER = "thunder"


class IdentityValue(str, Enum):
    """身份值"""
    LORD = "lord"
    LOYALIST = "loyalist"
    REBEL = "rebel"
    SPY = "spy"


class KingdomValue(str, Enum):
    """势力值"""
    SHU = "shu"
    WEI = "wei"
    WU = "wu"
    QUN = "qun"


# ==================== 游戏配置常量 ====================


class GameConfig:
    """游戏配置常量"""
    MIN_PLAYERS = 2
    MAX_PLAYERS = 8
    INITIAL_HAND_SIZE = 4
    DEFAULT_DRAW_COUNT = 2
    DEFAULT_SHA_LIMIT = 1
    MAX_HAND_OVERFLOW_TOLERANCE = 0  # 手牌超出上限容忍度


class IdentityConfig:
    """
    身份配置

    根据玩家人数分配身份数量
    """
    CONFIGS = {
        2: {"lord": 1, "loyalist": 0, "rebel": 1, "spy": 0},
        3: {"lord": 1, "loyalist": 0, "rebel": 1, "spy": 1},
        4: {"lord": 1, "loyalist": 1, "rebel": 1, "spy": 1},
        5: {"lord": 1, "loyalist": 1, "rebel": 2, "spy": 1},
        6: {"lord": 1, "loyalist": 1, "rebel": 3, "spy": 1},
        7: {"lord": 1, "loyalist": 2, "rebel": 3, "spy": 1},
        8: {"lord": 1, "loyalist": 2, "rebel": 4, "spy": 1},
    }

    @classmethod
    def get_config(cls, player_count: int) -> dict:
        """获取指定人数的身份配置"""
        return cls.CONFIGS.get(player_count, cls.CONFIGS[2])


# ==================== 装备常量 ====================


class WeaponRange:
    """武器攻击范围"""
    ZHUGE = 1       # 诸葛连弩
    QINGGANG = 2    # 青釭剑
    CIXIONG = 2     # 雌雄双股剑
    GUANSHI = 3     # 贯石斧
    QINGLONG = 3    # 青龙偃月刀
    ZHANGBA = 3     # 丈八蛇矛
    HANBING = 2     # 寒冰剑
    QILIN = 5       # 麒麟弓
    FANGTIANN = 4   # 方天画戟
    GUDINGDAO = 2   # 古锭刀
    ZHUQUE = 4      # 朱雀羽扇


# ==================== 显示常量 ====================


class DisplaySymbols:
    """显示符号"""
    DAMAGE = "💔"
    HEAL = "💚"
    FIRE = "🔥"
    THUNDER = "⚡"
    CHAIN = "🔗"
    SHIELD = "🛡"
    SWORD = "⚔"
    PEACH = "🍑"
    WINE = "🍺"
    WARNING = "⚠️"
    DEATH = "💀"


class CardSuitSymbol:
    """卡牌花色符号"""
    SPADE = "♠"
    HEART = "♥"
    CLUB = "♣"
    DIAMOND = "♦"


# ==================== 工具函数 ====================


def get_skill_chinese_name(skill_id: str) -> str:
    """
    获取技能中文名称

    Args:
        skill_id: 技能ID

    Returns:
        技能中文名称
    """
    names = {
        SkillId.RENDE: "仁德",
        SkillId.JIJIANG: "激将",
        SkillId.WUSHENG: "武圣",
        SkillId.PAOXIAO: "咆哮",
        SkillId.GUANXING: "观星",
        SkillId.KONGCHENG: "空城",
        SkillId.LONGDAN: "龙胆",
        SkillId.MASHU: "马术",
        SkillId.TIEJI: "铁骑",
        SkillId.JIZHI: "集智",
        SkillId.QICAI: "奇才",
        SkillId.LIEGONG: "烈弓",
        SkillId.KUANGGU: "狂骨",
        SkillId.JIANXIONG: "奸雄",
        SkillId.HUJIA: "护驾",
        SkillId.FANKUI: "反馈",
        SkillId.GUICAI: "鬼才",
        SkillId.GANGLIE: "刚烈",
        SkillId.TUXI: "突袭",
        SkillId.DUANLIANG: "断粮",
        SkillId.JUSHOU: "据守",
        SkillId.SHENSU: "神速",
        SkillId.ZHIHENG: "制衡",
        SkillId.JIUYUAN: "救援",
        SkillId.YINGZI: "英姿",
        SkillId.FANJIAN: "反间",
        SkillId.GUOSE: "国色",
        SkillId.LIULI: "流离",
        SkillId.QIXI: "奇袭",
        SkillId.KEJI: "克己",
        SkillId.KUROU: "苦肉",
        SkillId.JIEYIN: "结姻",
        SkillId.XIAOJI: "枭姬",
        SkillId.WUSHUANG: "无双",
        SkillId.QINGNANG: "青囊",
        SkillId.JIJIU: "急救",
        SkillId.LIJIAN: "离间",
        SkillId.BIYUE: "闭月",
    }
    return names.get(skill_id, skill_id)
