# 贡献指南

感谢您有兴趣为三国杀终端版项目做出贡献！

## 快速开始

### 环境准备

```bash
# 克隆仓库
git clone https://github.com/nevergoodstudy-hub/sanguosha-zhongduanban.git
cd sanguosha-zhongduanban

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/ -v
```

### 运行游戏

```bash
python main.py
```

## 代码规范

请遵循 `docs/CODE_REVIEW_SKILL.md` 中的代码规范：

- **PEP8**: 使用4空格缩进，行长度不超过120字符
- **命名**: 类使用 `PascalCase`，函数和变量使用 `snake_case`
- **文档**: 公共函数需要 docstring
- **类型提示**: 建议使用类型注解

### 代码风格检查

```bash
# 检查代码风格
python -m pycodestyle --max-line-length=120 game/ ai/ ui/ main.py

# 自动修复简单问题
python -m autopep8 --in-place --select=W291,W293 <file>
```

## 提交规范

### Commit 消息格式

```
<type>: <简短描述>

[可选的详细描述]
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码风格调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```
feat: 添加古锭刀武器效果
fix: 修复火攻处理器目标参数传递
docs: 更新卡牌覆盖率文档
test: 添加技能系统单元测试
```

## 测试要求

- 新功能需要添加对应的单元测试
- 修复 bug 时建议添加回归测试
- 确保所有测试通过后再提交

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行带覆盖率的测试
python -m pytest tests/ --cov=game --cov-report=term-missing

# 运行特定测试文件
python -m pytest tests/test_skills.py -v
```

## 项目结构

详见 `ARCHITECTURE.md`。主要目录:

- `game/` — 核心游戏逻辑 (engine, combat, events, skills, cards, ...)
- `ai/` — 3层 AI (easy/normal/hard) + 决策日志
- `net/` — WebSocket 服务端/客户端 + 安全 + 会话重连
- `ui/` — Textual 终端 UI
- `i18n/` — 国际化 (zh_CN, en_US)
- `data/` — JSON 数据 (cards, heroes, skill_dsl, skill_config)
- `tools/` — 开发工具 (profiling, replay)
- `tests/` — 测试套件 (1400+ tests)

## 添加新技能

1. 在 `data/skill_config.json` 中添加技能参数
2. 在 `data/skill_dsl.json` 中添加 DSL 定义（如果 DSL 可表达）
3. 若 DSL 不足，在 `game/skills/<kingdom>.py` 中添加 Python handler
4. 在 `game/constants.py` 中添加 `SkillId` 条目
5. 在 `data/heroes.json` 中添加武将数据
6. 在 `tests/` 中编写测试

## 添加新卡牌

1. 在 `data/cards.json` 中添加卡牌数据
2. 更新 `game/card.py` `Deck.EXPECTED_CARD_COUNTS` 字典
3. 如有特殊效果，在 `game/effects/` 或 `game/card_resolver.py` 中添加 handler
4. 编写测试

## 问题反馈

如有问题或建议，请在 GitHub Issues 中提出。

## 许可证

本项目采用 MIT 许可证。
