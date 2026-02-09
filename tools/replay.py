"""最小回放工具（M3-T03）
根据 action_log 重建对局，用于开发调试和失败复现
"""

import json
import random
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.engine import GameEngine


class ReplayTool:
    """回放工具类"""

    def __init__(self, log_path: str):
        """初始化回放工具
        
        Args:
            log_path: action_log JSON 文件路径
        """
        self.log_path = log_path
        self.log_data: dict[str, Any] | None = None
        self.engine: GameEngine | None = None
        self.errors: list = []

    def load_log(self) -> bool:
        """加载日志文件"""
        try:
            with open(self.log_path, encoding='utf-8') as f:
                self.log_data = json.load(f)
            print(f"✓ 日志已加载: {self.log_path}")
            print(f"  版本: {self.log_data.get('version', 'unknown')}")
            print(f"  种子: {self.log_data.get('game_seed', 'N/A')}")
            print(f"  玩家数: {self.log_data.get('player_count', 0)}")
            print(f"  回合数: {self.log_data.get('rounds', 0)}")
            print(f"  动作数: {len(self.log_data.get('actions', []))}")
            return True
        except Exception as e:
            self.errors.append(f"加载日志失败: {e}")
            return False

    def setup_game(self) -> bool:
        """根据日志设置游戏"""
        if not self.log_data:
            self.errors.append("日志未加载")
            return False

        try:
            # 设置随机种子
            seed = self.log_data.get('game_seed')
            if seed is not None:
                random.seed(seed)
                print(f"✓ 随机种子已设置: {seed}")

            # 创建引擎
            player_count = self.log_data.get('player_count', 4)
            self.engine = GameEngine()
            self.engine.setup_headless_game(player_count, seed=seed)

            print(f"✓ 游戏已初始化: {player_count} 名玩家")
            return True

        except Exception as e:
            self.errors.append(f"设置游戏失败: {e}")
            import traceback
            self.errors.append(traceback.format_exc())
            return False

    def replay_actions(self, step_by_step: bool = False) -> bool:
        """回放动作
        
        Args:
            step_by_step: 是否逐步执行（等待用户输入）
            
        Returns:
            是否成功回放
        """
        if not self.engine or not self.log_data:
            self.errors.append("引擎或日志未准备好")
            return False

        actions = self.log_data.get('actions', [])
        print(f"\n开始回放 {len(actions)} 个动作...")

        for i, action in enumerate(actions):
            try:
                action_type = action.get('action_type', 'UNKNOWN')
                player_id = action.get('player_id', -1)

                print(f"[{i+1}/{len(actions)}] {action_type} by Player {player_id}")

                if step_by_step:
                    input("按 Enter 继续...")

                # 此处可扩展具体的动作重放逻辑
                # 目前仅记录和验证

            except Exception as e:
                self.errors.append(f"回放动作 {i+1} 失败: {e}")
                return False

        print(f"\n✓ 回放完成，共 {len(actions)} 个动作")
        return True

    def verify_result(self) -> bool:
        """验证回放结果是否与日志一致"""
        if not self.engine or not self.log_data:
            return False

        expected_winner = self.log_data.get('winner')
        actual_winner = self.engine.winner_identity.value if self.engine.winner_identity else None

        if expected_winner == actual_winner:
            print(f"✓ 结果验证通过: 胜者 = {expected_winner}")
            return True
        else:
            print(f"✗ 结果不一致: 期望 {expected_winner}, 实际 {actual_winner}")
            return False

    def run(self, step_by_step: bool = False) -> dict[str, Any]:
        """运行完整回放
        
        Args:
            step_by_step: 是否逐步执行
            
        Returns:
            回放结果
        """
        result = {
            'success': False,
            'errors': [],
            'verified': False
        }

        # 加载日志
        if not self.load_log():
            result['errors'] = self.errors
            return result

        # 设置游戏
        if not self.setup_game():
            result['errors'] = self.errors
            return result

        # 回放动作
        if not self.replay_actions(step_by_step):
            result['errors'] = self.errors
            return result

        # 验证结果
        result['verified'] = self.verify_result()
        result['success'] = True
        result['errors'] = self.errors

        return result


def list_logs(log_dir: str = "logs") -> list:
    """列出可用的日志文件"""
    log_path = Path(log_dir)
    if not log_path.exists():
        return []

    logs = list(log_path.glob("action_log_*.json"))
    return sorted(logs, key=lambda p: p.stat().st_mtime, reverse=True)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="三国杀对局回放工具")
    parser.add_argument('log_file', nargs='?', help='日志文件路径')
    parser.add_argument('-l', '--list', action='store_true', help='列出可用日志')
    parser.add_argument('-s', '--step', action='store_true', help='逐步执行')

    args = parser.parse_args()

    if args.list:
        logs = list_logs()
        if logs:
            print("可用的日志文件:")
            for i, log in enumerate(logs[:10], 1):
                print(f"  [{i}] {log.name}")
        else:
            print("没有找到日志文件")
        return

    if not args.log_file:
        # 尝试使用最新的日志
        logs = list_logs()
        if logs:
            args.log_file = str(logs[0])
            print(f"使用最新日志: {args.log_file}")
        else:
            print("请指定日志文件路径")
            return

    # 运行回放
    tool = ReplayTool(args.log_file)
    result = tool.run(step_by_step=args.step)

    if result['success']:
        print("\n✓ 回放成功完成")
    else:
        print("\n✗ 回放失败")
        for err in result['errors']:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
