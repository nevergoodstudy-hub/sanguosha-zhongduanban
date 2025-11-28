# -*- coding: utf-8 -*-
"""
压力测试模块
进行100+次随机对局，检测潜在问题
"""

import sys
import os
import random
import traceback
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.engine import GameEngine, GameState
from game.player import Player, Identity
from game.card import Card, CardType, CardName
from game.hero import Hero
from ai.bot import AIBot, AIDifficulty


@dataclass
class BattleResult:
    """对局结果"""
    battle_id: int
    winner: Optional[str]
    rounds: int
    players: List[str]
    heroes: List[str]
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    duration_ms: int = 0


class StressTester:
    """压力测试器"""
    
    def __init__(self, num_battles: int = 100):
        self.num_battles = num_battles
        self.results: List[BattleResult] = []
        self.errors: List[BattleResult] = []
        self.issues_found: List[str] = []
        
    def run_single_battle(self, battle_id: int) -> BattleResult:
        """运行单场对局"""
        start_time = datetime.now()
        
        try:
            # 初始化引擎
            engine = GameEngine()
            
            # 随机玩家数量 (2-4)
            num_players = random.choice([2, 3, 4])
            
            # 随机分配身份
            identities = self._get_random_identities(num_players)
            
            # 随机选择武将
            all_heroes = engine.hero_repo.get_all_heroes()
            selected_heroes = random.sample(all_heroes, min(num_players, len(all_heroes)))
            
            # 创建玩家
            for i in range(num_players):
                player = Player(
                    id=i,
                    name=f"AI_{i}",
                    identity=identities[i],
                    is_ai=True
                )
                player.hero = selected_heroes[i]
                player.max_hp = selected_heroes[i].max_hp
                player.hp = player.max_hp
                engine.players.append(player)
            
            # 设置主公
            for p in engine.players:
                if p.identity == Identity.LORD:
                    p.max_hp += 1
                    p.hp = p.max_hp
                    break
            
            # 创建 AI
            difficulty = random.choice([AIDifficulty.EASY, AIDifficulty.NORMAL, AIDifficulty.HARD])
            bots = {p.id: AIBot(p, difficulty) for p in engine.players}
            
            # 发初始手牌
            for player in engine.players:
                cards = engine.deck.draw(4)
                player.draw_cards(cards)
            
            # 开始游戏
            engine.state = GameState.IN_PROGRESS
            
            # 运行对局（最多100回合防止死循环）
            max_rounds = 100
            round_count = 0
            
            while engine.state == GameState.IN_PROGRESS and round_count < max_rounds:
                round_count += 1
                
                for player in engine.players:
                    if not player.is_alive:
                        continue
                    
                    if engine.state != GameState.IN_PROGRESS:
                        break
                    
                    # AI 回合
                    self._run_ai_turn(engine, player, bots[player.id])
                    
                    # 检查游戏是否结束
                    self._check_game_over(engine)
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return BattleResult(
                battle_id=battle_id,
                winner=engine.winner_identity.chinese_name if engine.winner_identity else "超时",
                rounds=round_count,
                players=[p.name for p in engine.players],
                heroes=[p.hero.name if p.hero else "无" for p in engine.players],
                duration_ms=int(duration)
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            tb = traceback.format_exc()
            return BattleResult(
                battle_id=battle_id,
                winner=None,
                rounds=0,
                players=[],
                heroes=[],
                error=str(e),
                error_traceback=tb,
                duration_ms=int(duration)
            )
    
    def _get_random_identities(self, num_players: int) -> List[Identity]:
        """随机分配身份"""
        if num_players == 2:
            return [Identity.LORD, Identity.REBEL]
        elif num_players == 3:
            return [Identity.LORD, Identity.REBEL, Identity.SPY]
        else:  # 4人
            return [Identity.LORD, Identity.LOYALIST, Identity.REBEL, Identity.SPY]
    
    def _run_ai_turn(self, engine: GameEngine, player: Player, bot: AIBot) -> None:
        """运行 AI 回合"""
        if not player.is_alive:
            return
        
        # 准备阶段 - 处理延时锦囊
        self._handle_delay_tricks(engine, player)
        
        # 判定阶段
        # （略）
        
        # 摸牌阶段
        cards = engine.deck.draw(2)
        player.draw_cards(cards)
        
        # 出牌阶段
        self._ai_play_phase(engine, player, bot)
        
        # 弃牌阶段
        self._ai_discard_phase(engine, player)
        
        # 重置回合状态
        player.reset_turn()
    
    def _handle_delay_tricks(self, engine: GameEngine, player: Player) -> None:
        """处理延时锦囊（简化版本）"""
        # 简化处理：跳过延时锦囊逻辑
        pass
    
    def _ai_play_phase(self, engine: GameEngine, player: Player, bot: AIBot) -> None:
        """AI 出牌阶段"""
        # 最多操作20次防止死循环
        for _ in range(20):
            if not player.is_alive:
                break
            
            action = self._ai_choose_action(engine, player, bot)
            if action is None:
                break
            
            action_type, data = action
            
            if action_type == "use_card":
                card, target = data
                self._use_card(engine, player, card, target)
            elif action_type == "equip":
                card = data
                self._equip_card(engine, player, card)
            elif action_type == "end":
                break
    
    def _ai_choose_action(self, engine: GameEngine, player: Player, bot: AIBot) -> Optional[Tuple[str, Any]]:
        """AI 选择行动"""
        # 优先使用装备
        for card in player.hand:
            if card.card_type == CardType.EQUIPMENT:
                return ("equip", card)
        
        # 使用锦囊
        for card in player.hand:
            if card.card_type == CardType.TRICK:
                target = self._choose_target(engine, player, card)
                if target is not None or card.name in ["无中生有", "桃园结义", "南蛮入侵", "万箭齐发"]:
                    return ("use_card", (card, target))
        
        # 使用杀
        if player.can_use_sha():
            sha_cards = [c for c in player.hand if c.name in ["杀", "火杀", "雷杀"]]
            if sha_cards:
                card = sha_cards[0]
                target = self._choose_attack_target(engine, player)
                if target:
                    return ("use_card", (card, target))
        
        # 使用桃（低血量时）
        if player.hp < player.max_hp:
            tao_cards = [c for c in player.hand if c.name == "桃"]
            if tao_cards:
                return ("use_card", (tao_cards[0], player))
        
        return None
    
    def _choose_target(self, engine: GameEngine, player: Player, card: Card) -> Optional[Player]:
        """选择目标"""
        alive = [p for p in engine.players if p.is_alive and p != player]
        if not alive:
            return None
        
        # 根据身份选择目标
        enemies = self._get_enemies(player, alive)
        if enemies:
            return random.choice(enemies)
        
        return random.choice(alive) if alive else None
    
    def _choose_attack_target(self, engine: GameEngine, player: Player) -> Optional[Player]:
        """选择攻击目标（简化版本）"""
        alive = [p for p in engine.players if p.is_alive and p != player]
        if not alive:
            return None
        
        # 简化：假设所有人都在范围内
        enemies = self._get_enemies(player, alive)
        if enemies:
            return random.choice(enemies)
        
        return random.choice(alive)
    
    def _get_enemies(self, player: Player, candidates: List[Player]) -> List[Player]:
        """获取敌人列表"""
        enemies = []
        for p in candidates:
            if player.identity == Identity.LORD or player.identity == Identity.LOYALIST:
                if p.identity in [Identity.REBEL, Identity.SPY]:
                    enemies.append(p)
            elif player.identity == Identity.REBEL:
                if p.identity in [Identity.LORD, Identity.LOYALIST]:
                    enemies.append(p)
            elif player.identity == Identity.SPY:
                # 内奸策略复杂，暂时随机
                enemies.append(p)
        return enemies
    
    def _use_card(self, engine: GameEngine, player: Player, card: Card, target: Optional[Player]) -> None:
        """使用卡牌"""
        player.remove_card(card)
        
        if card.name in ["杀", "火杀", "雷杀"]:
            player.use_sha()
            if target:
                # 简化处理：50%概率造成伤害
                if random.random() > 0.5:
                    damage = 1
                    if card.name == "火杀":
                        damage_type = "fire"
                    elif card.name == "雷杀":
                        damage_type = "thunder"
                    else:
                        damage_type = "normal"
                    target.take_damage(damage, player)
                    self._check_dying(engine, target)
        
        elif card.name == "桃":
            if target:
                target.heal(1)
        
        elif card.name == "无中生有":
            cards = engine.deck.draw(2)
            player.draw_cards(cards)
        
        elif card.name in ["南蛮入侵", "万箭齐发"]:
            for p in engine.players:
                if p.is_alive and p != player:
                    # 简化：50%概率受伤
                    if random.random() > 0.5:
                        p.take_damage(1, player)
                        self._check_dying(engine, p)
        
        elif card.name == "决斗":
            if target:
                # 简化：随机决定胜负
                loser = random.choice([player, target])
                loser.take_damage(1, player if loser == target else target)
                self._check_dying(engine, loser)
        
        elif card.name in ["顺手牵羊", "过河拆桥"]:
            if target and target.hand:
                stolen = random.choice(target.hand)
                target.remove_card(stolen)
                if card.name == "顺手牵羊":
                    player.draw_cards([stolen])
                else:
                    engine.deck.discard([stolen])
        
        engine.deck.discard([card])
    
    def _equip_card(self, engine: GameEngine, player: Player, card: Card) -> None:
        """装备卡牌"""
        player.remove_card(card)
        old_equip = player.equip_card(card)
        if old_equip:
            engine.deck.discard([old_equip])
    
    def _ai_discard_phase(self, engine: GameEngine, player: Player) -> None:
        """AI 弃牌阶段"""
        while player.hand_count > player.hand_limit:
            if player.hand:
                # 弃置价值最低的牌
                card = player.hand[0]
                player.remove_card(card)
                engine.deck.discard([card])
            else:
                break
    
    def _check_dying(self, engine: GameEngine, player: Player) -> None:
        """检查濒死"""
        while player.hp <= 0 and player.is_alive:
            # 尝试求桃
            saved = False
            for p in engine.players:
                if p.is_alive:
                    tao_cards = [c for c in p.hand if c.name == "桃"]
                    if tao_cards and (p == player or random.random() > 0.5):
                        card = tao_cards[0]
                        p.remove_card(card)
                        engine.deck.discard([card])
                        player.heal(1)
                        saved = True
                        break
            
            if not saved:
                player.die()
                break
    
    def _check_game_over(self, engine: GameEngine) -> None:
        """检查游戏是否结束"""
        alive_players = [p for p in engine.players if p.is_alive]
        
        # 检查主公是否死亡
        lord_alive = any(p.identity == Identity.LORD for p in alive_players)
        
        if not lord_alive:
            # 检查是否只剩内奸
            if len(alive_players) == 1 and alive_players[0].identity == Identity.SPY:
                engine.winner_identity = Identity.SPY
            else:
                engine.winner_identity = Identity.REBEL
            engine.state = GameState.FINISHED
            return
        
        # 检查反贼和内奸是否全灭
        rebels_alive = any(p.identity == Identity.REBEL for p in alive_players)
        spies_alive = any(p.identity == Identity.SPY for p in alive_players)
        
        if not rebels_alive and not spies_alive:
            engine.winner_identity = Identity.LORD
            engine.state = GameState.FINISHED
    
    def run_all_battles(self) -> None:
        """运行所有对局"""
        print(f"\n{'='*60}")
        print(f"  三国杀压力测试 - 共 {self.num_battles} 局对局")
        print(f"{'='*60}\n")
        
        for i in range(self.num_battles):
            result = self.run_single_battle(i + 1)
            self.results.append(result)
            
            if result.error:
                self.errors.append(result)
                print(f"[{i+1:3d}/{self.num_battles}] ❌ 错误: {result.error[:50]}...")
            else:
                status = "✓" if result.winner else "?"
                print(f"[{i+1:3d}/{self.num_battles}] {status} 胜者: {result.winner:<6} "
                      f"| 回合: {result.rounds:3d} | 耗时: {result.duration_ms:4d}ms "
                      f"| 武将: {', '.join(result.heroes[:2])}...")
        
        self._print_summary()
    
    def _print_summary(self) -> None:
        """打印测试总结"""
        print(f"\n{'='*60}")
        print(f"  测试总结")
        print(f"{'='*60}")
        
        total = len(self.results)
        errors = len(self.errors)
        success = total - errors
        
        print(f"\n总对局数: {total}")
        print(f"成功: {success} ({success/total*100:.1f}%)")
        print(f"错误: {errors} ({errors/total*100:.1f}%)")
        
        if self.errors:
            print(f"\n{'='*60}")
            print("  错误详情")
            print(f"{'='*60}")
            
            # 统计错误类型
            error_types: Dict[str, int] = {}
            for err in self.errors:
                err_key = err.error.split('\n')[0][:80] if err.error else "Unknown"
                error_types[err_key] = error_types.get(err_key, 0) + 1
            
            for err_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                print(f"  [{count:3d}次] {err_type}")
            
            # 打印第一个错误的完整堆栈
            if self.errors[0].error_traceback:
                print(f"\n第一个错误的完整堆栈:")
                print(self.errors[0].error_traceback)
        
        # 统计胜率
        print(f"\n{'='*60}")
        print("  胜率统计")
        print(f"{'='*60}")
        
        winners: Dict[str, int] = {}
        for r in self.results:
            if r.winner:
                winners[r.winner] = winners.get(r.winner, 0) + 1
        
        for winner, count in sorted(winners.items(), key=lambda x: -x[1]):
            print(f"  {winner}: {count} 局 ({count/success*100:.1f}%)" if success > 0 else f"  {winner}: {count} 局")
        
        # 平均回合数
        rounds = [r.rounds for r in self.results if not r.error]
        if rounds:
            avg_rounds = sum(rounds) / len(rounds)
            print(f"\n平均回合数: {avg_rounds:.1f}")
        
        # 平均耗时
        durations = [r.duration_ms for r in self.results]
        if durations:
            avg_duration = sum(durations) / len(durations)
            print(f"平均耗时: {avg_duration:.1f}ms")


def main():
    """主函数"""
    tester = StressTester(num_battles=100)
    tester.run_all_battles()
    
    # 返回错误数作为退出码
    return len(tester.errors)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
