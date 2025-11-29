# -*- coding: utf-8 -*-
"""
游戏引擎模块
负责游戏核心逻辑、回合流程和规则执行
"""

from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Tuple, TYPE_CHECKING
import random
from pathlib import Path

from .card import Card, CardType, CardSubtype, CardSuit, Deck, CardName, DamageType
from .hero import Hero, HeroRepository, Kingdom, Skill, SkillType
from .player import Player, Identity, EquipmentSlot
from .events import EventBus, EventType, GameEvent, EventEmitter

if TYPE_CHECKING:
    from ai.bot import AIBot
    from ui.terminal import TerminalUI
    from .skill import SkillSystem


class GamePhase(Enum):
    """游戏阶段枚举"""
    PREPARE = "prepare"       # 准备阶段
    JUDGE = "judge"           # 判定阶段
    DRAW = "draw"             # 摸牌阶段
    PLAY = "play"             # 出牌阶段
    DISCARD = "discard"       # 弃牌阶段
    END = "end"               # 结束阶段


class GameState(Enum):
    """游戏状态枚举"""
    NOT_STARTED = "not_started"   # 未开始
    CHOOSING_HEROES = "choosing_heroes"  # 选将阶段
    IN_PROGRESS = "in_progress"   # 进行中
    FINISHED = "finished"         # 已结束


@dataclass
class GameEvent:
    """
    游戏事件类
    用于记录游戏日志
    """
    event_type: str
    message: str
    source: Optional[Player] = None
    target: Optional[Player] = None
    card: Optional[Card] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return self.message


class GameEngine:
    """
    游戏引擎类
    负责管理整个游戏流程
    
    重构说明：
    - 集成事件总线系统，实现模块解耦
    - UI 通过订阅事件来获取游戏状态变化
    - 技能系统通过监听事件来触发
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化游戏引擎
        
        Args:
            data_dir: 数据文件目录路径
        """
        # 获取正确的数据目录路径
        base_path = Path(__file__).parent.parent / data_dir
        
        # 事件总线（核心解耦组件）
        self.event_bus: EventBus = EventBus()
        
        # 核心组件
        self.deck: Deck = Deck(str(base_path / "cards.json"))
        self.hero_repo: HeroRepository = HeroRepository(str(base_path / "heroes.json"))
        
        # 玩家管理
        self.players: List[Player] = []
        self.current_player_index: int = 0
        self.human_player: Optional[Player] = None
        
        # 游戏状态
        self.state: GameState = GameState.NOT_STARTED
        self.phase: GamePhase = GamePhase.PREPARE
        self.round_count: int = 0
        self.winner_identity: Optional[Identity] = None
        
        # 事件日志（保留兼容）
        self.event_log: List[GameEvent] = []
        self.max_log_size: int = 100
        
        # UI和AI回调
        self.ui: Optional['TerminalUI'] = None
        self.ai_bots: Dict[int, 'AIBot'] = {}
        
        # 技能系统引用
        self.skill_system: Optional['SkillSystem'] = None
    
    def set_ui(self, ui: 'TerminalUI') -> None:
        """设置UI组件"""
        self.ui = ui
    
    def set_skill_system(self, skill_system: 'SkillSystem') -> None:
        """设置技能系统"""
        self.skill_system = skill_system
    
    def log_event(self, event_type: str, message: str, 
                  source: Optional[Player] = None,
                  target: Optional[Player] = None,
                  card: Optional[Card] = None,
                  **extra_data) -> None:
        """
        记录游戏事件并通过事件总线发布
        
        Args:
            event_type: 事件类型（字符串，兼容旧代码）
            message: 事件消息
            source: 事件来源玩家
            target: 事件目标玩家
            card: 相关卡牌
            **extra_data: 额外数据
        """
        # 通过事件总线发布日志消息
        self.event_bus.emit(
            EventType.LOG_MESSAGE,
            message=message,
            log_type=event_type,
            source=source,
            target=target,
            card=card,
            **extra_data
        )
        
        # 兼容旧的 UI 调用方式
        if self.ui:
            self.ui.show_log(message)
    
    def setup_game(self, player_count: int, human_player_index: int = 0) -> None:
        """
        设置游戏
        
        Args:
            player_count: 玩家数量（2-8）
            human_player_index: 人类玩家索引
        """
        if player_count < 2 or player_count > 8:
            raise ValueError("玩家数量必须在2-8之间")
        
        # 创建玩家
        self.players.clear()
        self.human_player = None
        for i in range(player_count):
            is_human = (i == human_player_index and human_player_index >= 0)
            player = Player(
                id=i,
                name=f"玩家{i + 1}" if is_human else f"AI_{i + 1}",
                is_ai=not is_human,
                seat=i
            )
            self.players.append(player)
            if is_human:
                self.human_player = player
        
        # 分配身份
        self._assign_identities()
        
        # 重置牌堆
        self.deck.reset()
        
        self.state = GameState.CHOOSING_HEROES
        self.log_event("game_setup", f"游戏设置完成，共{player_count}名玩家")
    
    def _assign_identities(self) -> None:
        """分配身份（支持2-8人）"""
        player_count = len(self.players)
        
        # 根据人数分配身份（标准身份局）
        identity_configs = {
            2: [Identity.LORD, Identity.REBEL],
            3: [Identity.LORD, Identity.REBEL, Identity.SPY],
            4: [Identity.LORD, Identity.LOYALIST, Identity.REBEL, Identity.SPY],
            5: [Identity.LORD, Identity.LOYALIST, Identity.REBEL, Identity.REBEL, Identity.SPY],
            6: [Identity.LORD, Identity.LOYALIST, Identity.REBEL, Identity.REBEL, Identity.REBEL, Identity.SPY],
            7: [Identity.LORD, Identity.LOYALIST, Identity.LOYALIST, Identity.REBEL, Identity.REBEL, Identity.REBEL, Identity.SPY],
            8: [Identity.LORD, Identity.LOYALIST, Identity.LOYALIST, Identity.REBEL, Identity.REBEL, Identity.REBEL, Identity.REBEL, Identity.SPY]
        }
        
        identities = identity_configs.get(player_count, [Identity.LORD, Identity.REBEL])
        
        # 第一个玩家固定为主公
        self.players[0].identity = identities[0]
        
        # 随机分配其他身份
        remaining_identities = identities[1:]
        random.shuffle(remaining_identities)
        
        for i, player in enumerate(self.players[1:], 1):
            if i - 1 < len(remaining_identities):
                player.identity = remaining_identities[i - 1]
    
    def choose_heroes(self, choices: Dict[int, str]) -> None:
        """
        为所有玩家选择武将
        
        Args:
            choices: 玩家ID到武将ID的映射
        """
        for player_id, hero_id in choices.items():
            player = self.get_player_by_id(player_id)
            hero = self.hero_repo.get_hero(hero_id)
            if player and hero:
                # 复制武将对象，避免共享状态
                import copy
                player_hero = copy.deepcopy(hero)
                player.set_hero(player_hero)
                self.log_event("hero_chosen", f"{player.name} 选择了 {hero.name}")
    
    def auto_choose_heroes_for_ai(self) -> Dict[int, str]:
        """
        为AI玩家自动选择武将
        
        Returns:
            AI玩家的武将选择
        """
        available_heroes = self.hero_repo.get_all_heroes()
        random.shuffle(available_heroes)
        
        choices = {}
        used_heroes = set()
        
        for player in self.players:
            if player.is_ai and player.hero is None:
                for hero in available_heroes:
                    if hero.id not in used_heroes:
                        choices[player.id] = hero.id
                        used_heroes.add(hero.id)
                        break
        
        return choices
    
    def start_game(self) -> None:
        """开始游戏"""
        if self.state != GameState.CHOOSING_HEROES:
            raise RuntimeError("游戏状态错误，无法开始")
        
        # 确保所有玩家都有武将
        for player in self.players:
            if player.hero is None:
                raise RuntimeError(f"玩家 {player.name} 还没有选择武将")
        
        # 发初始手牌（每人4张）
        for player in self.players:
            cards = self.deck.draw(4)
            player.draw_cards(cards)
            self.log_event("draw_cards", f"{player.name} 获得了 {len(cards)} 张初始手牌")
        
        self.state = GameState.IN_PROGRESS
        self.current_player_index = 0
        self.round_count = 1
        
        self.log_event("game_start", "=== 游戏开始 ===")
    
    @property
    def current_player(self) -> Player:
        """获取当前回合玩家"""
        return self.players[self.current_player_index]
    
    def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """根据ID获取玩家"""
        for player in self.players:
            if player.id == player_id:
                return player
        return None
    
    def get_alive_players(self) -> List[Player]:
        """获取所有存活玩家"""
        return [p for p in self.players if p.is_alive]
    
    def get_other_players(self, player: Player) -> List[Player]:
        """获取除指定玩家外的其他存活玩家"""
        return [p for p in self.players if p.is_alive and p != player]
    
    def get_next_player(self, player: Optional[Player] = None) -> Player:
        """获取下一个存活玩家"""
        if player is None:
            player = self.current_player
        
        start_index = self.players.index(player)
        for i in range(1, len(self.players) + 1):
            next_index = (start_index + i) % len(self.players)
            if self.players[next_index].is_alive:
                return self.players[next_index]
        
        return player  # 如果只剩一个玩家
    
    def calculate_distance(self, from_player: Player, to_player: Player) -> int:
        """
        计算两个玩家之间的距离
        
        Args:
            from_player: 起始玩家
            to_player: 目标玩家
            
        Returns:
            距离值
        """
        if from_player == to_player:
            return 0
        
        alive_players = self.get_alive_players()
        if len(alive_players) <= 1:
            return 0
        
        # 找到两个玩家在存活玩家中的位置
        try:
            from_index = alive_players.index(from_player)
            to_index = alive_players.index(to_player)
        except ValueError:
            return 999  # 其中一个玩家已死亡
        
        n = len(alive_players)
        
        # 计算顺时针和逆时针距离
        clockwise = (to_index - from_index) % n
        counter_clockwise = (from_index - to_index) % n
        
        # 基础距离取较小值
        base_distance = min(clockwise, counter_clockwise)
        
        # 应用距离修正
        # -1马：from_player 到其他角色距离-1
        distance_modifier = from_player.equipment.distance_to_others
        # +1马：to_player 被其他角色计算距离时+1
        distance_modifier -= to_player.equipment.distance_from_others
        
        return max(1, base_distance + distance_modifier)
    
    def is_in_attack_range(self, attacker: Player, target: Player) -> bool:
        """
        检查目标是否在攻击范围内
        
        Args:
            attacker: 攻击者
            target: 目标
            
        Returns:
            是否在攻击范围内
        """
        distance = self.calculate_distance(attacker, target)
        attack_range = attacker.equipment.attack_range
        return distance <= attack_range
    
    def get_targets_in_range(self, player: Player) -> List[Player]:
        """获取攻击范围内的所有目标"""
        targets = []
        for other in self.get_other_players(player):
            if self.is_in_attack_range(player, other):
                targets.append(other)
        return targets
    
    # ==================== 回合流程 ====================
    
    def run_turn(self) -> None:
        """执行当前玩家的回合"""
        player = self.current_player
        
        if not player.is_alive:
            self.next_turn()
            return
        
        self.log_event("turn_start", f"=== {player.name} 的回合 ===")
        player.reset_turn()
        
        # 各阶段执行
        self.phase_prepare(player)
        self.phase_judge(player)
        self.phase_draw(player)
        self.phase_play(player)
        self.phase_discard(player)
        self.phase_end(player)
        
        self.log_event("turn_end", f"=== {player.name} 的回合结束 ===")
    
    def phase_prepare(self, player: Player) -> None:
        """准备阶段"""
        self.phase = GamePhase.PREPARE
        self.log_event("phase", f"【准备阶段】")
        
        # 触发准备阶段技能（如观星）
        if self.skill_system and player.hero:
            for skill in player.hero.skills:
                if skill.timing and skill.timing.value == "prepare":
                    self.skill_system.trigger_skill(skill.id, player, self)
    
    def phase_judge(self, player: Player) -> None:
        """判定阶段"""
        self.phase = GamePhase.JUDGE
        # 判定阶段处理延时锦囊等（暂不实现）
    
    def phase_draw(self, player: Player) -> None:
        """摸牌阶段"""
        self.phase = GamePhase.DRAW
        self.log_event("phase", f"【摸牌阶段】")
        
        # 基础摸牌数
        draw_count = 2
        
        # 英姿技能：多摸一张
        if player.has_skill("yingzi"):
            draw_count += 1
            self.log_event("skill", f"{player.name} 发动【英姿】，多摸一张牌")
        
        cards = self.deck.draw(draw_count)
        player.draw_cards(cards)
        self.log_event("draw_cards", f"{player.name} 摸了 {len(cards)} 张牌")
    
    def phase_play(self, player: Player) -> None:
        """出牌阶段"""
        self.phase = GamePhase.PLAY
        self.log_event("phase", f"【出牌阶段】")
        
        if player.is_ai:
            self._ai_play_phase(player)
        else:
            self._human_play_phase(player)
    
    def _ai_play_phase(self, player: Player) -> None:
        """AI出牌阶段"""
        if player.id in self.ai_bots:
            bot = self.ai_bots[player.id]
            bot.play_phase(player, self)
    
    def _human_play_phase(self, player: Player) -> None:
        """人类玩家出牌阶段（由UI控制）"""
        # UI会在主循环中调用 process_human_action
        pass
    
    def phase_discard(self, player: Player) -> None:
        """弃牌阶段"""
        self.phase = GamePhase.DISCARD
        
        discard_count = player.need_discard
        if discard_count > 0:
            self.log_event("phase", f"【弃牌阶段】需要弃置 {discard_count} 张牌")
            
            if player.is_ai:
                self._ai_discard(player, discard_count)
            else:
                # 人类玩家弃牌由UI处理
                pass
    
    def _ai_discard(self, player: Player, count: int) -> None:
        """AI弃牌"""
        if player.id in self.ai_bots:
            bot = self.ai_bots[player.id]
            cards_to_discard = bot.choose_discard(player, count, self)
            self.discard_cards(player, cards_to_discard)
    
    def phase_end(self, player: Player) -> None:
        """结束阶段"""
        self.phase = GamePhase.END
    
    def next_turn(self) -> None:
        """进入下一个玩家的回合"""
        # 找到下一个存活的玩家
        for i in range(1, len(self.players) + 1):
            next_index = (self.current_player_index + i) % len(self.players)
            if self.players[next_index].is_alive:
                self.current_player_index = next_index
                break
        
        # 如果回到主公，回合数+1
        if self.current_player_index == 0:
            self.round_count += 1
    
    # ==================== 卡牌使用 ====================
    
    def use_card(self, player: Player, card: Card, 
                 targets: Optional[List[Player]] = None) -> bool:
        """
        使用卡牌
        
        Args:
            player: 使用者
            card: 卡牌
            targets: 目标列表
            
        Returns:
            是否成功使用
        """
        if targets is None:
            targets = []
        
        # 移除手牌
        if card in player.hand:
            player.remove_card(card)
        
        # 根据卡牌类型处理
        # 杀类卡牌（普通杀/火杀/雷杀）
        if card.name == CardName.SHA or card.subtype in [CardSubtype.ATTACK, CardSubtype.FIRE_ATTACK, CardSubtype.THUNDER_ATTACK]:
            return self._use_sha(player, card, targets)
        elif card.name == CardName.TAO:
            return self._use_tao(player, card)
        elif card.name == CardName.JUEDOU:
            return self._use_juedou(player, card, targets)
        elif card.name == CardName.NANMAN:
            return self._use_nanman(player, card)
        elif card.name == CardName.WANJIAN:
            return self._use_wanjian(player, card)
        elif card.name == CardName.WUZHONG:
            return self._use_wuzhong(player, card)
        elif card.name == CardName.GUOHE:
            return self._use_guohe(player, card, targets)
        elif card.name == CardName.SHUNSHOU:
            return self._use_shunshou(player, card, targets)
        elif card.name == CardName.TAOYUAN:
            return self._use_taoyuan(player, card)
        elif card.subtype == CardSubtype.ALCOHOL:
            return self._use_jiu(player, card)
        elif card.subtype == CardSubtype.CHAIN:
            return self._use_tiesuo(player, card, targets)
        elif card.is_type(CardType.EQUIPMENT):
            return self._use_equipment(player, card)
        
        # 将使用的牌放入弃牌堆
        self.deck.discard([card])
        return True
    
    def _use_sha(self, player: Player, card: Card, targets: List[Player]) -> bool:
        """
        使用杀（支持酒加成、火杀/雷杀属性伤害）
        
        Args:
            player: 使用者
            card: 杀牌
            targets: 目标列表
            
        Returns:
            是否成功使用
        """
        if not targets:
            self.deck.discard([card])
            return False
        
        target = targets[0]
        
        # 检查是否可以使用杀
        if not player.can_use_sha():
            self.log_event("error", f"{player.name} 本回合已经使用过杀了")
            player.draw_cards([card])  # 退回手牌
            return False
        
        # 检查距离
        if not self.is_in_attack_range(player, target):
            self.log_event("error", f"{target.name} 不在攻击范围内")
            player.draw_cards([card])
            return False
        
        # 检查空城
        if target.has_skill("kongcheng") and target.hand_count == 0:
            self.log_event("skill", f"{target.name} 发动【空城】，不是【杀】的合法目标")
            player.draw_cards([card])
            return False
        
        # 确定杀的类型和伤害类型
        card_name = card.name
        if card.subtype == CardSubtype.FIRE_ATTACK:
            card_name = "火杀"
            damage_type = "fire"
        elif card.subtype == CardSubtype.THUNDER_ATTACK:
            card_name = "雷杀"
            damage_type = "thunder"
        else:
            damage_type = "normal"
        
        # 检查仁王盾（只对黑色普通杀有效）
        if card.is_black and damage_type == "normal" and target.equipment.armor:
            if target.equipment.armor.name == CardName.RENWANG:
                self.log_event("equipment", f"{target.name} 的【仁王盾】使黑色的【杀】无效")
                player.use_sha()
                self.deck.discard([card])
                return True
        
        # 藤甲对普通杀无效（火杀在 deal_damage 中处理伤害加成）
        if damage_type == "normal" and target.equipment.armor:
            if target.equipment.armor.name == "藤甲":
                self.log_event("equipment", f"{target.name} 的【藤甲】使普通【杀】无效")
                player.use_sha()
                self.deck.discard([card])
                return True
        
        # 消耗酒状态，计算伤害
        base_damage = 1
        is_drunk = player.consume_drunk()
        if is_drunk:
            base_damage += 1
            self.log_event("effect", f"  🍺 {player.name} 的酒劲发作，伤害+1！")
        
        player.use_sha()
        dist = self.calculate_distance(player, target)
        
        # 显示杀的类型
        type_icon = {"fire": "🔥", "thunder": "⚡"}.get(damage_type, "⚔")
        self.log_event("use_card", 
            f"{type_icon} {player.name} → {target.name} 使用【{card_name}】{card.suit.symbol}{card.number_str} (距离:{dist})", 
            source=player, target=target, card=card)
        
        # 无双技能：需要两张闪
        required_shan = 2 if player.has_skill("wushuang") else 1
        if required_shan > 1:
            self.log_event("skill", f"  ⚡ {player.name} 【无双】发动，需要 {required_shan} 张【闪】")
        
        # 请求目标出闪
        shan_count = self._request_shan(target, required_shan)
        
        if shan_count >= required_shan:
            self.log_event("dodge", f"  🛡 {target.name} 打出【闪】，成功闪避！")
            
            # 青龙偃月刀效果
            if player.equipment.weapon and player.equipment.weapon.name == CardName.QINGLONG:
                self._trigger_qinglong(player, target)
        else:
            # 造成伤害（传递属性伤害类型）
            self.deal_damage(player, target, base_damage, damage_type)
        
        self.deck.discard([card])
        return True
    
    def _request_shan(self, player: Player, count: int = 1) -> int:
        """
        请求玩家出闪
        
        Args:
            player: 需要出闪的玩家
            count: 需要的闪数量
            
        Returns:
            实际打出的闪数量
        """
        shan_played = 0
        
        for _ in range(count):
            # 八卦阵效果
            if player.equipment.armor and player.equipment.armor.name == CardName.BAGUA:
                if self._trigger_bagua(player):
                    shan_played += 1
                    continue
            
            # 检查武圣技能（红色牌当闪）
            if player.has_skill("wusheng"):
                red_cards = player.get_red_cards()
                if red_cards:
                    # AI自动选择，人类需要UI交互
                    if player.is_ai:
                        card = red_cards[0]
                        player.remove_card(card)
                        self.deck.discard([card])
                        self.log_event("skill", f"{player.name} 发动【武圣】，将 {card.display_name} 当【闪】打出")
                        shan_played += 1
                        continue
            
            # 正常出闪
            shan_cards = player.get_cards_by_name(CardName.SHAN)
            if shan_cards:
                if player.is_ai:
                    # AI自动出闪
                    card = shan_cards[0]
                    player.remove_card(card)
                    self.deck.discard([card])
                    shan_played += 1
                else:
                    # 人类玩家需要UI确认
                    if self.ui:
                        result = self.ui.ask_for_shan(player)
                        if result:
                            card = result
                            player.remove_card(card)
                            self.deck.discard([card])
                            shan_played += 1
                    else:
                        # 无UI时自动出闪
                        card = shan_cards[0]
                        player.remove_card(card)
                        self.deck.discard([card])
                        shan_played += 1
            else:
                break  # 没有闪了
        
        return shan_played
    
    def _request_sha(self, player: Player, count: int = 1) -> int:
        """请求玩家出杀"""
        sha_played = 0
        
        for _ in range(count):
            # 检查武圣技能（红色牌当杀）
            if player.has_skill("wusheng"):
                red_cards = player.get_red_cards()
                if red_cards:
                    if player.is_ai:
                        card = red_cards[0]
                        player.remove_card(card)
                        self.deck.discard([card])
                        self.log_event("skill", f"{player.name} 发动【武圣】，将 {card.display_name} 当【杀】打出")
                        sha_played += 1
                        continue
            
            sha_cards = player.get_cards_by_name(CardName.SHA)
            if sha_cards:
                if player.is_ai:
                    card = sha_cards[0]
                    player.remove_card(card)
                    self.deck.discard([card])
                    sha_played += 1
                else:
                    if self.ui:
                        result = self.ui.ask_for_sha(player)
                        if result:
                            player.remove_card(result)
                            self.deck.discard([result])
                            sha_played += 1
                    else:
                        card = sha_cards[0]
                        player.remove_card(card)
                        self.deck.discard([card])
                        sha_played += 1
            else:
                break
        
        return sha_played
    
    def _trigger_bagua(self, player: Player) -> bool:
        """触发八卦阵判定"""
        self.log_event("equipment", f"{player.name} 尝试发动【八卦阵】")
        
        # 进行判定
        judge_card = self.deck.draw(1)[0]
        self.log_event("judge", f"判定结果: {judge_card.display_name}")
        self.deck.discard([judge_card])
        
        # 红色判定成功
        if judge_card.is_red:
            self.log_event("equipment", f"【八卦阵】判定成功，视为打出了【闪】")
            return True
        
        self.log_event("equipment", f"【八卦阵】判定失败")
        return False
    
    def _trigger_qinglong(self, player: Player, target: Player) -> None:
        """触发青龙偃月刀效果"""
        sha_cards = player.get_cards_by_name(CardName.SHA)
        if sha_cards:
            self.log_event("equipment", f"{player.name} 可以发动【青龙偃月刀】继续使用杀")
            if player.is_ai:
                # AI决定是否继续使用杀
                if player.id in self.ai_bots:
                    bot = self.ai_bots[player.id]
                    if bot.should_use_qinglong(player, target, self):
                        card = sha_cards[0]
                        player.remove_card(card)
                        self._use_sha(player, card, [target])
    
    def _use_tao(self, player: Player, card: Card) -> bool:
        """使用桃"""
        if player.hp >= player.max_hp:
            self.log_event("error", "体力已满，无法使用桃")
            player.draw_cards([card])
            return False
        
        healed = player.heal(1)
        self.log_event("use_card", f"{player.name} 使用了【桃】，回复了 {healed} 点体力",
                      source=player, card=card)
        
        self.deck.discard([card])
        return True
    
    def _use_juedou(self, player: Player, card: Card, targets: List[Player]) -> bool:
        """使用决斗"""
        if not targets:
            self.deck.discard([card])
            return False
        
        target = targets[0]
        
        # 检查空城
        if target.has_skill("kongcheng") and target.hand_count == 0:
            self.log_event("skill", f"{target.name} 发动【空城】，不是【决斗】的合法目标")
            player.draw_cards([card])
            return False
        
        self.log_event("use_card", f"{player.name} 对 {target.name} 使用了【决斗】",
                      source=player, target=target, card=card)
        
        # 无双效果：每次需要两张杀
        attacker_required = 2 if player.has_skill("wushuang") else 1
        defender_required = 2 if player.has_skill("wushuang") else 1
        
        # 目标先出杀
        current_attacker = target
        current_defender = player
        
        while True:
            required = defender_required if current_attacker == target else attacker_required
            sha_count = self._request_sha(current_attacker, required)
            
            if sha_count < required:
                # 当前攻击方受到伤害
                self.deal_damage(current_defender, current_attacker, 1)
                break
            
            # 交换攻击方和防守方
            current_attacker, current_defender = current_defender, current_attacker
        
        self.deck.discard([card])
        return True
    
    def _use_nanman(self, player: Player, card: Card) -> bool:
        """使用南蛮入侵"""
        self.log_event("use_card", f"{player.name} 使用了【南蛮入侵】", source=player, card=card)
        
        for target in self.get_other_players(player):
            sha_count = self._request_sha(target, 1)
            if sha_count < 1:
                self.log_event("effect", f"{target.name} 未能打出【杀】")
                self.deal_damage(player, target, 1)
            else:
                self.log_event("effect", f"{target.name} 打出了【杀】，躲避了伤害")
        
        self.deck.discard([card])
        return True
    
    def _use_wanjian(self, player: Player, card: Card) -> bool:
        """使用万箭齐发"""
        self.log_event("use_card", f"{player.name} 使用了【万箭齐发】", source=player, card=card)
        
        for target in self.get_other_players(player):
            shan_count = self._request_shan(target, 1)
            if shan_count < 1:
                self.log_event("effect", f"{target.name} 未能打出【闪】")
                self.deal_damage(player, target, 1)
            else:
                self.log_event("effect", f"{target.name} 打出了【闪】，躲避了伤害")
        
        self.deck.discard([card])
        return True
    
    def _use_wuzhong(self, player: Player, card: Card) -> bool:
        """使用无中生有"""
        self.log_event("use_card", f"{player.name} 使用了【无中生有】", source=player, card=card)
        
        cards = self.deck.draw(2)
        player.draw_cards(cards)
        self.log_event("effect", f"{player.name} 摸了 2 张牌")
        
        self.deck.discard([card])
        return True
    
    def _use_guohe(self, player: Player, card: Card, targets: List[Player]) -> bool:
        """使用过河拆桥"""
        if not targets:
            self.deck.discard([card])
            return False
        
        target = targets[0]
        
        if not target.has_any_card():
            self.log_event("error", f"{target.name} 没有牌可以被拆")
            player.draw_cards([card])
            return False
        
        self.log_event("use_card", f"{player.name} 对 {target.name} 使用了【过河拆桥】",
                      source=player, target=target, card=card)
        
        # 选择并弃置一张牌
        discarded_card = self._choose_and_discard_card(player, target)
        if discarded_card:
            self.log_event("effect", f"{target.name} 的 {discarded_card.display_name} 被弃置")
        
        self.deck.discard([card])
        return True
    
    def _use_shunshou(self, player: Player, card: Card, targets: List[Player]) -> bool:
        """使用顺手牵羊"""
        if not targets:
            self.deck.discard([card])
            return False
        
        target = targets[0]
        
        # 检查距离
        if self.calculate_distance(player, target) > 1:
            self.log_event("error", f"{target.name} 距离太远，无法使用顺手牵羊")
            player.draw_cards([card])
            return False
        
        if not target.has_any_card():
            self.log_event("error", f"{target.name} 没有牌可以被拿")
            player.draw_cards([card])
            return False
        
        self.log_event("use_card", f"{player.name} 对 {target.name} 使用了【顺手牵羊】",
                      source=player, target=target, card=card)
        
        # 选择并获得一张牌
        stolen_card = self._choose_and_steal_card(player, target)
        if stolen_card:
            self.log_event("effect", f"{player.name} 获得了 {target.name} 的一张牌")
        
        self.deck.discard([card])
        return True
    
    def _use_taoyuan(self, player: Player, card: Card) -> bool:
        """使用桃园结义"""
        self.log_event("use_card", f"{player.name} 使用了【桃园结义】", source=player, card=card)
        
        # 从使用者开始，所有角色回复1点体力
        start_index = self.players.index(player)
        for i in range(len(self.players)):
            current_index = (start_index + i) % len(self.players)
            p = self.players[current_index]
            if p.is_alive and p.hp < p.max_hp:
                p.heal(1)
                self.log_event("effect", f"{p.name} 回复了 1 点体力")
        
        self.deck.discard([card])
        return True
    
    def _use_jiu(self, player: Player, card: Card) -> bool:
        """
        使用酒（军争篇）
        
        效果：
        - 出牌阶段对自己使用，下一张杀伤害+1（本回合限一次）
        - 濒死时对自己使用，回复1点体力
        """
        # 濒死时使用酒回复体力
        if player.is_dying:
            player.heal(1)
            self.log_event("use_card", f"🍺 {player.name} 使用了【酒】回复1点体力！", 
                          source=player, card=card)
            self.deck.discard([card])
            return True
        
        # 出牌阶段使用酒（本回合限一次）
        if player.alcohol_used:
            self.log_event("error", f"{player.name} 本回合已经使用过酒了")
            player.draw_cards([card])
            return False
        
        if player.use_alcohol():
            self.log_event("use_card", f"🍺 {player.name} 使用了【酒】，下一张杀伤害+1！", 
                          source=player, card=card)
            self.deck.discard([card])
            return True
        
        player.draw_cards([card])
        return False
    
    def _use_tiesuo(self, player: Player, card: Card, 
                    targets: Optional[List[Player]] = None) -> bool:
        """
        使用铁索连环（军争篇）
        
        效果：
        - 选择1-2名角色，横置/重置其武将牌
        - 或重铸此牌
        """
        if targets is None:
            targets = []
        
        # 如果没有目标，视为重铸
        if not targets:
            self.log_event("use_card", f"🔗 {player.name} 重铸了【铁索连环】", 
                          source=player, card=card)
            self.deck.discard([card])
            new_cards = self.deck.draw(1)
            player.draw_cards(new_cards)
            if new_cards:
                self.log_event("effect", f"{player.name} 摸了 1 张牌")
            return True
        
        # 对目标使用
        target_names = "、".join(t.name for t in targets[:2])  # 最多2个目标
        self.log_event("use_card", f"🔗 {player.name} 对 {target_names} 使用了【铁索连环】", 
                      source=player, card=card)
        
        for target in targets[:2]:
            target.toggle_chain()
            status = "横置" if target.is_chained else "重置"
            self.log_event("effect", f"  🔗 {target.name} 的武将牌被{status}（连环状态: {target.is_chained}）")
        
        self.deck.discard([card])
        return True
    
    def _use_equipment(self, player: Player, card: Card) -> bool:
        """使用装备牌"""
        old_equipment = player.equip_card(card)
        self.log_event("equip", f"{player.name} 装备了【{card.name}】", source=player, card=card)
        
        if old_equipment:
            self.log_event("equip", f"【{old_equipment.name}】被替换")
            self.deck.discard([old_equipment])
        
        return True
    
    def _choose_and_discard_card(self, player: Player, target: Player) -> Optional[Card]:
        """选择并弃置目标的一张牌"""
        all_cards = target.get_all_cards()
        if not all_cards:
            return None
        
        # AI或简单选择：随机选一张
        if player.is_ai:
            card = random.choice(all_cards)
        else:
            # 人类玩家需要UI选择
            if self.ui:
                card = self.ui.choose_card_from_player(player, target)
            else:
                card = random.choice(all_cards)
        
        if card:
            if card in target.hand:
                target.remove_card(card)
            else:
                # 从装备区移除
                for slot in EquipmentSlot:
                    if target.equipment.get_card_by_slot(slot) == card:
                        target.equipment.unequip(slot)
                        break
            self.deck.discard([card])
        
        return card
    
    def _choose_and_steal_card(self, player: Player, target: Player) -> Optional[Card]:
        """选择并获得目标的一张牌"""
        all_cards = target.get_all_cards()
        if not all_cards:
            return None
        
        if player.is_ai:
            card = random.choice(all_cards)
        else:
            if self.ui:
                card = self.ui.choose_card_from_player(player, target)
            else:
                card = random.choice(all_cards)
        
        if card:
            if card in target.hand:
                target.remove_card(card)
            else:
                for slot in EquipmentSlot:
                    if target.equipment.get_card_by_slot(slot) == card:
                        target.equipment.unequip(slot)
                        break
            player.draw_cards([card])
        
        return card
    
    def discard_cards(self, player: Player, cards: List[Card]) -> None:
        """弃置卡牌"""
        for card in cards:
            player.remove_card(card)
        self.deck.discard(cards)
        
        if cards:
            cards_str = ", ".join(c.display_name for c in cards)
            self.log_event("discard", f"{player.name} 弃置了 {cards_str}")
    
    # ==================== 伤害和死亡 ====================
    
    def deal_damage(self, source: Optional[Player], target: Player, 
                    damage: int, damage_type: str = "normal",
                    _chain_propagating: bool = False) -> None:
        """
        造成伤害（支持属性伤害与铁索连环传导）
        
        Args:
            source: 伤害来源
            target: 目标
            damage: 伤害值
            damage_type: 伤害类型 ("normal", "fire", "thunder")
            _chain_propagating: 内部参数，标记是否为连环传导伤害
        """
        source_name = source.name if source else "系统"
        old_hp = target.hp
        
        # 伤害类型显示
        damage_type_display = {
            "normal": "",
            "fire": "🔥火焰",
            "thunder": "⚡雷电"
        }.get(damage_type, "")
        
        # 藤甲效果：火焰伤害+1，普通杀无效（后续可扩展）
        if damage_type == "fire" and target.equipment.armor:
            if target.equipment.armor.name == "藤甲":
                damage += 1
                self.log_event("equipment", f"  🔥 {target.name} 的【藤甲】被火焰点燃，伤害+1！")
        
        target.take_damage(damage, source)
        
        # 详细的伤害日志
        self.log_event("damage", 
            f"💔 {target.name} 受到 {source_name} 的 {damage} 点{damage_type_display}伤害 "
            f"[{old_hp}→{target.hp}/{target.max_hp}]")
        
        # 奸雄技能：获得造成伤害的牌
        if target.has_skill("jianxiong") and source:
            self.log_event("skill", f"  ⚔ {target.name} 可发动【奸雄】获得伤害牌")
        
        # 铁索连环传导：属性伤害会传导给其他被连环的角色
        if damage_type in ["fire", "thunder"] and target.is_chained and not _chain_propagating:
            target.break_chain()  # 解除当前目标的连环状态
            self.log_event("chain", f"  🔗 {target.name} 的铁索连环被触发！伤害传导中...")
            
            # 传导给其他被连环的角色（按座位顺序）
            for p in self.players:
                if p.is_alive and p != target and p.is_chained:
                    self.log_event("chain", f"  🔗 伤害传导至 {p.name}！")
                    p.break_chain()  # 解除连环状态
                    self.deal_damage(source, p, damage, damage_type, _chain_propagating=True)
        
        # 检查濒死
        if target.is_dying:
            self._handle_dying(target)
    
    def _handle_dying(self, player: Player) -> None:
        """处理濒死"""
        self.log_event("dying", f"⚠️ {player.name}({player.hero.name if player.hero else '???'}) 进入濒死状态！HP: {player.hp}")
        
        # 请求所有玩家使用桃救援
        saved = False
        
        # 从当前玩家开始
        start_index = self.players.index(player)
        for i in range(len(self.players)):
            current_index = (start_index + i) % len(self.players)
            savior = self.players[current_index]
            
            if not savior.is_alive:
                continue
            
            while player.hp <= 0:
                tao_cards = savior.get_cards_by_name(CardName.TAO)
                if tao_cards:
                    if savior.is_ai:
                        # AI决定是否救援
                        should_save = self._ai_should_save(savior, player)
                        if should_save:
                            card = tao_cards[0]
                            savior.remove_card(card)
                            player.heal(1)
                            self.deck.discard([card])
                            self.log_event("save", f"{savior.name} 使用【桃】救援了 {player.name}")
                            
                            # 救援技能（孙权）
                            if player.has_skill("jiuyuan") and player.identity == Identity.LORD:
                                if savior.hero and savior.hero.kingdom == Kingdom.WU:
                                    player.heal(1)
                                    self.log_event("skill", f"{player.name} 发动【救援】，额外回复1点体力")
                        else:
                            break
                    else:
                        # 人类玩家选择是否使用桃
                        if self.ui:
                            result = self.ui.ask_for_tao(savior, player)
                            if result:
                                savior.remove_card(result)
                                player.heal(1)
                                self.deck.discard([result])
                                self.log_event("save", f"{savior.name} 使用【桃】救援了 {player.name}")
                            else:
                                break
                        else:
                            break
                else:
                    break
            
            if player.hp > 0:
                saved = True
                break
        
        if not saved and player.hp <= 0:
            self._handle_death(player)
    
    def _ai_should_save(self, savior: Player, dying: Player) -> bool:
        """AI决定是否救援"""
        # 简单逻辑：同阵营救援
        if savior.identity == dying.identity:
            return True
        if savior.identity == Identity.LOYALIST and dying.identity == Identity.LORD:
            return True
        if dying.identity == Identity.LORD:
            # 内奸在最后阶段可能不救主公
            if savior.identity == Identity.SPY:
                alive_count = len(self.get_alive_players())
                if alive_count <= 2:
                    return False
            return True
        return False
    
    def _handle_death(self, player: Player) -> None:
        """处理死亡"""
        player.die()
        self.log_event("death", f"【{player.name}】阵亡！身份是【{player.identity.chinese_name}】")
        
        # 弃置所有牌
        all_cards = player.get_all_cards()
        player.hand.clear()
        player.equipment = type(player.equipment)()
        self.deck.discard(all_cards)
        
        # 检查奖惩
        if self.current_player.is_alive:
            killer = self.current_player
            
            # 杀死反贼，摸三张牌
            if player.identity == Identity.REBEL:
                cards = self.deck.draw(3)
                killer.draw_cards(cards)
                self.log_event("reward", f"{killer.name} 杀死反贼，摸三张牌")
            
            # 主公杀死忠臣，弃置所有牌
            if killer.identity == Identity.LORD and player.identity == Identity.LOYALIST:
                discard_cards = killer.get_all_cards()
                killer.hand.clear()
                killer.equipment = type(killer.equipment)()
                self.deck.discard(discard_cards)
                self.log_event("penalty", f"{killer.name} 杀死忠臣，弃置所有牌")
        
        # 检查游戏是否结束
        self.check_game_over()
    
    def check_game_over(self) -> bool:
        """检查游戏是否结束"""
        alive_players = self.get_alive_players()
        
        # 检查主公是否存活
        lord = None
        for p in self.players:
            if p.identity == Identity.LORD:
                lord = p
                break
        
        if lord and not lord.is_alive:
            # 主公死亡
            # 检查是否只剩内奸
            spy_count = sum(1 for p in alive_players if p.identity == Identity.SPY)
            if len(alive_players) == spy_count and spy_count > 0:
                self.winner_identity = Identity.SPY
                self.state = GameState.FINISHED
                self.log_event("game_over", "内奸获胜！")
                return True
            else:
                self.winner_identity = Identity.REBEL
                self.state = GameState.FINISHED
                self.log_event("game_over", "反贼获胜！")
                return True
        
        # 检查反贼和内奸是否全部死亡
        rebel_alive = any(p.identity == Identity.REBEL and p.is_alive for p in self.players)
        spy_alive = any(p.identity == Identity.SPY and p.is_alive for p in self.players)
        
        if not rebel_alive and not spy_alive:
            self.winner_identity = Identity.LORD
            self.state = GameState.FINISHED
            self.log_event("game_over", "主公和忠臣获胜！")
            return True
        
        return False
    
    def is_game_over(self) -> bool:
        """检查游戏是否结束"""
        return self.state == GameState.FINISHED
    
    def get_winner_message(self) -> str:
        """获取胜利消息"""
        if self.winner_identity == Identity.LORD:
            return "主公和忠臣获胜！"
        elif self.winner_identity == Identity.REBEL:
            return "反贼获胜！"
        elif self.winner_identity == Identity.SPY:
            return "内奸获胜！"
        return "游戏结束"
    
    # ==================== 无 UI 对战接口（用于压测/AI研究） ====================
    
    def setup_headless_game(self, player_count: int, 
                            ai_difficulty: str = "normal") -> None:
        """
        设置无 UI 对战（用于压力测试与 AI 研究）
        
        Args:
            player_count: 玩家数量（2-8）
            ai_difficulty: AI 难度 ("easy", "normal", "hard")
        """
        from ai.bot import AIBot, AIDifficulty
        
        if player_count < 2 or player_count > 8:
            raise ValueError("玩家数量必须在2-8之间")
        
        # 创建玩家（全部为 AI）
        self.players.clear()
        self._assign_identities_for_count(player_count)
        
        # 随机选择武将
        all_heroes = self.hero_repo.get_all_heroes()
        random.shuffle(all_heroes)
        
        # 设置 AI 难度
        difficulty_map = {
            "easy": AIDifficulty.EASY,
            "normal": AIDifficulty.NORMAL,
            "hard": AIDifficulty.HARD
        }
        difficulty = difficulty_map.get(ai_difficulty, AIDifficulty.NORMAL)
        
        for i in range(player_count):
            player = Player(
                id=i,
                name=f"AI_{i + 1}",
                is_ai=True,
                seat=i
            )
            self.players.append(player)
            
            # 分配武将
            if i < len(all_heroes):
                import copy
                hero = copy.deepcopy(all_heroes[i])
                player.set_hero(hero)
            
            # 创建 AI
            self.ai_bots[player.id] = AIBot(player, difficulty)
        
        # 分配身份
        self._assign_identities()
        
        # 主公额外 +1 体力（set_hero 已处理，但需要确保身份先分配）
        for p in self.players:
            if p.identity == Identity.LORD and p.hero:
                # 重新应用主公加成
                if p.hp == p.max_hp:  # 还没受伤
                    pass  # set_hero 已经处理了
        
        # 重置牌堆
        self.deck.reset()
        
        # 发初始手牌
        for player in self.players:
            cards = self.deck.draw(4)
            player.draw_cards(cards)
        
        self.state = GameState.IN_PROGRESS
        self.current_player_index = 0
        self.round_count = 1
    
    def _assign_identities_for_count(self, player_count: int) -> None:
        """为指定人数分配身份配置"""
        # 预配置身份（稍后在 _assign_identities 中使用）
        pass  # _assign_identities 会处理
    
    def run_headless_turn(self, max_actions: int = 50) -> bool:
        """
        执行当前玩家的无 UI 回合
        
        Args:
            max_actions: 单回合最大操作数（防止死循环）
            
        Returns:
            回合是否正常完成
        """
        player = self.current_player
        
        if not player.is_alive:
            self.next_turn()
            return True
        
        player.reset_turn()
        
        # 准备阶段
        self.phase = GamePhase.PREPARE
        if self.skill_system and player.hero:
            for skill in player.hero.skills:
                if skill.timing and skill.timing.value == "prepare":
                    self.skill_system.trigger_skill(skill.id, player, self)
        
        # 判定阶段（简化：跳过延时锦囊）
        self.phase = GamePhase.JUDGE
        
        # 摸牌阶段
        self.phase = GamePhase.DRAW
        draw_count = 2
        if player.has_skill("yingzi"):
            draw_count += 1
        cards = self.deck.draw(draw_count)
        player.draw_cards(cards)
        
        # 出牌阶段
        self.phase = GamePhase.PLAY
        if player.id in self.ai_bots:
            bot = self.ai_bots[player.id]
            bot.play_phase(player, self)
        
        # 弃牌阶段
        self.phase = GamePhase.DISCARD
        discard_count = player.need_discard
        if discard_count > 0 and player.id in self.ai_bots:
            bot = self.ai_bots[player.id]
            cards_to_discard = bot.choose_discard(player, discard_count, self)
            self.discard_cards(player, cards_to_discard)
        
        # 结束阶段
        self.phase = GamePhase.END
        
        return True
    
    def run_headless_battle(self, max_rounds: int = 100) -> Dict[str, Any]:
        """
        运行完整的无 UI 对局
        
        Args:
            max_rounds: 最大回合数
            
        Returns:
            对局结果字典
        """
        round_count = 0
        
        while self.state == GameState.IN_PROGRESS and round_count < max_rounds:
            round_count += 1
            
            for _ in range(len(self.players)):
                if self.state != GameState.IN_PROGRESS:
                    break
                
                self.run_headless_turn()
                self.next_turn()
        
        return {
            "winner": self.winner_identity.chinese_name if self.winner_identity else "超时",
            "rounds": round_count,
            "players": [p.name for p in self.players],
            "heroes": [p.hero.name if p.hero else "无" for p in self.players],
            "identities": [p.identity.chinese_name for p in self.players],
            "finished": self.state == GameState.FINISHED
        }
