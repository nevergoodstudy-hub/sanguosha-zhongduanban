# -*- coding: utf-8 -*-
"""
压力测试模块
进行100+次随机对局，检测潜在问题

重构说明 (T1-1)：
- 使用 GameEngine 提供的 headless 接口运行对局
- 统一规则逻辑，避免压测与正式引擎的差异
- 保留错误统计与诊断能力
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
from game.card import Card, CardType
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
    """
    压力测试器
    
    使用 GameEngine 的 headless 接口运行对局，
    确保压测逻辑与正式游戏一致。
    """
    
    def __init__(self, num_battles: int = 100):
        self.num_battles = num_battles
        self.results: List[BattleResult] = []
        self.errors: List[BattleResult] = []
        self.issues_found: List[str] = []
        
    def run_single_battle(self, battle_id: int) -> BattleResult:
        """
        运行单场对局（使用正式引擎接口）
        
        Args:
            battle_id: 对局编号
            
        Returns:
            对局结果
        """
        start_time = datetime.now()
        
        try:
            # 初始化引擎
            engine = GameEngine()
            
            # 随机玩家数量 (2-4)
            num_players = random.choice([2, 3, 4])
            
            # 随机 AI 难度
            difficulty = random.choice(["easy", "normal", "hard"])
            
            # 使用引擎的 headless 接口设置游戏
            engine.setup_headless_game(num_players, difficulty)
            
            # 运行完整对局
            result = engine.run_headless_battle(max_rounds=100)
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return BattleResult(
                battle_id=battle_id,
                winner=result["winner"],
                rounds=result["rounds"],
                players=result["players"],
                heroes=result["heroes"],
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
    
    # 以下方法已废弃，保留空实现以兼容旧测试代码
    # 所有对局逻辑已迁移到 GameEngine.run_headless_battle()
    
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
