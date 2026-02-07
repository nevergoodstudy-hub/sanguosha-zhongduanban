# -*- coding: utf-8 -*-
"""武将选择界面"""

from __future__ import annotations

import copy
import random
from typing import List, TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Container

if TYPE_CHECKING:
    from game.hero import Hero


class HeroSelectScreen(Screen):
    """武将选择界面"""

    CSS = """
    HeroSelectScreen {
        align: center middle;
    }
    #hero-box {
        width: 80;
        height: auto;
        max-height: 90%;
        border: double magenta;
        padding: 1 2;
        overflow-y: auto;
    }
    #hero-title {
        text-align: center;
        text-style: bold;
        color: magenta;
        margin-bottom: 1;
    }
    .hero-btn {
        width: 100%;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, player_count: int, difficulty: str,
                 role_preference: str = "lord"):
        super().__init__()
        self.player_count = player_count
        self.difficulty = difficulty
        self.role_preference = role_preference
        self.heroes: List[Hero] = []
        self.is_lord = False

    def on_mount(self) -> None:
        """初始化引擎并准备武将选项"""
        from game.engine import GameEngine
        from game.skill import SkillSystem
        from game.player import Identity

        engine = GameEngine()
        engine.setup_game(self.player_count, human_player_index=0,
                          role_preference=self.role_preference)

        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)

        self.app._engine = engine
        self.app._difficulty = self.difficulty

        # 准备武将选项
        all_heroes = engine.hero_repo.get_all_heroes()
        self.is_lord = engine.human_player.identity == Identity.LORD

        lord_heroes = [h for h in all_heroes if any(s.is_lord_skill for s in h.skills)]
        normal_heroes = [h for h in all_heroes if not any(s.is_lord_skill for s in h.skills)]

        if self.is_lord:
            available = lord_heroes.copy()
            remaining = 5 - len(available)
            if remaining > 0:
                extra = random.sample(normal_heroes, min(remaining, len(normal_heroes)))
                available.extend(extra)
            random.shuffle(available)
            self.heroes = available[:5]
        else:
            self.heroes = random.sample(normal_heroes, min(3, len(normal_heroes)))

        # 动态创建按钮
        box = self.query_one("#hero-box")
        if self.is_lord:
            title = "主公选将 (5选1)"
        else:
            identity_name = engine.human_player.identity.chinese_name
            title = f"你的身份: {identity_name} — 选择武将 (3选1)"
        box.query_one("#hero-title").update(f"🎭 {title}")

        for i, hero in enumerate(self.heroes):
            kingdom = hero.kingdom.chinese_name
            skills_text = " / ".join(f"【{s.name}】" for s in hero.skills)
            label = f"{hero.name} [{kingdom}] HP:{hero.max_hp}  {skills_text}"
            btn = Button(label, id=f"hero-{i}", classes="hero-btn", variant="primary")
            box.mount(btn)

    def compose(self) -> ComposeResult:
        yield Container(
            Static("🎭 选择武将", id="hero-title"),
            id="hero-box",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("hero-"):
            idx = int(btn_id.split("-")[1])
            chosen = self.heroes[idx]
            self._finish_setup(chosen)

    def _finish_setup(self, chosen_hero: Hero) -> None:
        """完成选将并进入游戏"""
        from game.player import Identity
        from ai.bot import AIBot, AIDifficulty
        from game.hero import SkillType

        engine = self.app._engine
        hero = copy.deepcopy(chosen_hero)
        engine.human_player.set_hero(hero)

        # AI 选将 — AI 主公优先选主公技武将
        used = [hero.id]
        all_heroes = engine.hero_repo.get_all_heroes()
        available = [h for h in all_heroes if h.id not in used]
        ai_choices = {}
        for p in engine.players:
            if p.is_ai and p.hero is None and available:
                if p.identity == Identity.LORD:
                    # AI 主公优先选有主公技的武将
                    lord_pool = [h for h in available
                                 if any(s.is_lord_skill for s in h.skills)]
                    h = random.choice(lord_pool) if lord_pool else random.choice(available)
                else:
                    h = random.choice(available)
                ai_choices[p.id] = h.id
                available.remove(h)
        engine.choose_heroes(ai_choices)

        # 设置 AI
        difficulty = AIDifficulty(self.app._difficulty)
        for p in engine.players:
            if p.is_ai:
                engine.ai_bots[p.id] = AIBot(p, difficulty)

        engine.start_game()

        # 跳过所有 setup screens，进入游戏
        from .game_play import GamePlayScreen
        self.app.switch_screen(GamePlayScreen())
