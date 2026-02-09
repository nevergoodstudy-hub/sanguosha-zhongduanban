"""困难 AI 策略 — 深度策略 + 嘲讽值系统 + 身份推断

实现 AIStrategy 协议，用于 HARD 难度。
组合 ThreatEvaluator 和 IdentityPredictor 两个独立组件。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.card import CardName
from game.player import Identity

from .normal_strategy import NormalStrategy
from .strategy import is_enemy, smart_discard

if TYPE_CHECKING:
    from game.card import Card
    from game.engine import GameEngine
    from game.player import Player


class ThreatEvaluator:
    """嘲讽值/威胁评估系统

    独立组件，仅在困难模式下使用。
    负责计算各玩家的威胁值和战力评分。
    """

    def __init__(self, owner: Player):
        self.owner = owner
        self.threat_values: dict[int, float] = {}

    def update(self, engine: GameEngine) -> None:
        """更新所有玩家的嘲讽值"""
        for p in engine.players:
            if p.id == self.owner.id:
                continue

            threat = 0.0

            # 基础威胁值基于体力
            threat += (5 - p.hp) * 10

            # 手牌数量影响威胁
            threat += p.hand_count * 5

            # 装备影响威胁
            if p.equipment.weapon:
                threat += 15
            if p.equipment.armor:
                threat += 10

            # 特定武将增加威胁
            if p.hero:
                if p.hero.id == "lvbu":  # 吕布
                    threat += 20
                elif p.hero.id == "zhugeliang":  # 诸葛亮
                    threat += 15

            # 身份影响
            if p.identity == Identity.LORD:
                threat += 30  # 主公是重点目标

            self.threat_values[p.id] = threat

    def get_threat(self, player_id: int) -> float:
        """获取指定玩家的嘲讽值"""
        return self.threat_values.get(player_id, 0)

    def get_highest_threat_enemy(self, player: Player,
                                 engine: GameEngine) -> Player | None:
        """获取威胁值最高的敌人"""
        enemies = [p for p in engine.get_other_players(player)
                   if is_enemy(player, p)]
        if not enemies:
            return None
        enemies.sort(key=lambda p: self.threat_values.get(p.id, 0), reverse=True)
        return enemies[0]

    def calculate_player_power(self, player: Player,
                               engine: GameEngine) -> float:
        """计算玩家战力评分"""
        if not player.is_alive:
            return 0.0

        power = 0.0

        # 生命值评分（满血100分，每少1点减20分）
        hp_ratio = player.hp / player.max_hp
        power += hp_ratio * 100

        # 手牌评分（每张牌10分，上限50分）
        power += min(player.hand_count * 10, 50)

        # 装备评分
        if player.equipment.weapon:
            power += 20
        if player.equipment.armor:
            power += 25
        if player.equipment.horse_plus:
            power += 10
        if player.equipment.horse_minus:
            power += 10

        # 特殊卡牌加成
        tao_count = len(player.get_cards_by_name("桃"))
        power += tao_count * 15

        # 武将技能加成
        if player.hero:
            skill_bonus = len(player.hero.skills) * 5
            power += skill_bonus

        return power

    def calculate_danger_level(self, player: Player,
                               engine: GameEngine) -> float:
        """计算玩家危险等级（0-100）"""
        danger = 0.0

        # 低血量危险
        if player.hp <= 1:
            danger += 50
        elif player.hp <= 2:
            danger += 30

        # 无闪危险
        if not player.get_cards_by_name("闪"):
            danger += 20

        # 无桃危险
        if not player.get_cards_by_name("桃"):
            danger += 15

        # 敌人数量和威胁
        enemies = [p for p in engine.get_other_players(player)
                   if is_enemy(player, p)]
        for enemy in enemies:
            if enemy.is_alive:
                danger += enemy.hand_count * 2
                if enemy.equipment.weapon:
                    danger += 10

        return min(danger, 100)


class IdentityPredictor:
    """身份推断系统

    独立组件，仅在困难模式下使用。
    基于玩家行为记录推断身份概率。
    """

    def __init__(self, owner: Player):
        self.owner = owner
        self.identity_guess: dict[int, Identity] = {}

    def infer_identity(self, target: Player,
                       engine: GameEngine) -> dict[str, float]:
        """基于行为推断目标身份概率

        Returns:
            各身份的概率字典
        """
        # 主公身份公开
        if target.identity == Identity.LORD:
            return {'lord': 1.0, 'loyalist': 0.0, 'rebel': 0.0, 'spy': 0.0}

        # 初始概率（基于人数分布）
        probs = {
            'lord': 0.0,
            'loyalist': 0.25,
            'rebel': 0.50,
            'spy': 0.25
        }

        # 基于已知行为调整概率
        if target.id in self.identity_guess:
            guessed = self.identity_guess[target.id]
            if guessed == Identity.LOYALIST:
                probs['loyalist'] = 0.7
                probs['rebel'] = 0.15
                probs['spy'] = 0.15
            elif guessed == Identity.REBEL:
                probs['rebel'] = 0.7
                probs['loyalist'] = 0.15
                probs['spy'] = 0.15
            elif guessed == Identity.SPY:
                probs['spy'] = 0.6
                probs['rebel'] = 0.2
                probs['loyalist'] = 0.2

        return probs

    def record_behavior(self, actor: Player, action_type: str,
                        target: Player | None = None) -> None:
        """记录玩家行为用于身份推断

        Args:
            actor: 行为发起者
            action_type: 行为类型 ('attack', 'save', 'help', 'harm')
            target: 行为目标
        """
        if actor.id == self.owner.id:
            return

        if not target:
            return

        # 攻击主公 → 可能是反贼
        if action_type == "attack" and target.identity == Identity.LORD:
            self.identity_guess[actor.id] = Identity.REBEL

        # 救援主公 → 可能是忠臣
        elif action_type == "save" and target.identity == Identity.LORD:
            self.identity_guess[actor.id] = Identity.LOYALIST

        # 帮助主公/忠臣 → 可能是忠臣
        elif action_type == "help" and target.identity in [Identity.LORD,
                                                           Identity.LOYALIST]:
            if actor.id not in self.identity_guess:
                self.identity_guess[actor.id] = Identity.LOYALIST

        # 伤害忠臣 → 可能是反贼
        elif action_type == "harm" and target.identity == Identity.LOYALIST:
            if actor.id not in self.identity_guess:
                self.identity_guess[actor.id] = Identity.REBEL


class HardStrategy:
    """困难模式策略：深度策略 + 嘲讽值系统 + 局势评估

    组合 ThreatEvaluator 和 IdentityPredictor 两个组件，
    复用 NormalStrategy 的基础出牌逻辑。
    """

    def __init__(self, player: Player):
        self.threat_evaluator = ThreatEvaluator(player)
        self.identity_predictor = IdentityPredictor(player)
        self._normal = NormalStrategy()
        self._player = player

    def play_phase(self, player: Player, engine: GameEngine) -> None:
        """困难模式：深度策略 + 嘲讽值系统 + 局势评估"""
        self.threat_evaluator.update(engine)
        state = self.evaluate_game_state(engine)

        # 危险时优先回血
        if state['danger_level'] > 60 and player.hp < player.max_hp:
            tao = player.get_cards_by_name(CardName.TAO)
            if tao:
                engine.use_card(player, tao[0])

        # 使用普通AI逻辑（目标选择已利用嘲讽值）
        self._normal.play_phase(player, engine)

    def choose_discard(self, player: Player, count: int,
                       engine: GameEngine) -> list[Card]:
        """智能弃牌（同普通模式）"""
        return smart_discard(player, count)

    def should_use_qinglong(self, player: Player, target: Player,
                            engine: GameEngine) -> bool:
        """有杀且是敌人就继续"""
        sha_count = len(player.get_cards_by_name(CardName.SHA))
        if sha_count > 1:
            return is_enemy(player, target)
        return False

    # ==================== 局势评估 ====================

    def evaluate_game_state(self, engine: GameEngine) -> dict[str, float]:
        """评估当前局势

        返回各阵营的综合评分和关键指标
        """
        player = self._player

        lord_score = 0.0
        rebel_score = 0.0
        spy_score = 0.0

        lord_alive = False
        rebel_count = 0
        loyalist_count = 0
        spy_count = 0

        for p in engine.players:
            if not p.is_alive:
                continue

            power = self.threat_evaluator.calculate_player_power(p, engine)

            if p.identity == Identity.LORD:
                lord_score += power * 1.5
                lord_alive = True
            elif p.identity == Identity.LOYALIST:
                lord_score += power
                loyalist_count += 1
            elif p.identity == Identity.REBEL:
                rebel_score += power
                rebel_count += 1
            elif p.identity == Identity.SPY:
                spy_score += power
                spy_count += 1

        total_score = lord_score + rebel_score + spy_score
        if total_score == 0:
            total_score = 1

        return {
            'lord_advantage': lord_score / total_score,
            'rebel_advantage': rebel_score / total_score,
            'spy_advantage': spy_score / total_score,
            'lord_alive': lord_alive,
            'rebel_count': rebel_count,
            'loyalist_count': loyalist_count,
            'spy_count': spy_count,
            'my_power': self.threat_evaluator.calculate_player_power(player, engine),
            'danger_level': self.threat_evaluator.calculate_danger_level(player, engine)
        }

    def choose_best_target(self, player: Player, targets: list[Player],
                           engine: GameEngine) -> Player:
        """选择最佳攻击目标（困难模式 — 综合评分系统）

        综合考虑：嘲讽值、危险等级、战力评分
        """
        if not targets:
            return None

        self.threat_evaluator.update(engine)

        def calc_attack_value(target: Player) -> float:
            value = 0.0

            # 嘲讽值权重
            threat = self.threat_evaluator.get_threat(target.id)
            value += threat * 0.4

            # 低血量高价值（更容易击杀）
            if target.hp <= 1:
                value += 50
            elif target.hp <= 2:
                value += 30

            # 无闪更容易命中
            shan_count = len(target.get_cards_by_name(CardName.SHAN))
            if shan_count == 0:
                value += 25

            # 无桃更容易击杀
            tao_count = len(target.get_cards_by_name(CardName.TAO))
            if tao_count == 0:
                value += 15

            # 敌方战力高的优先攻击
            power = self.threat_evaluator.calculate_player_power(target, engine)
            value += power * 0.2

            return value

        targets_with_value = [(t, calc_attack_value(t)) for t in targets]
        targets_with_value.sort(key=lambda x: x[1], reverse=True)
        return targets_with_value[0][0]
