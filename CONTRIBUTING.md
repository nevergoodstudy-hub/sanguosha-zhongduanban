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

```
sanguosha/
├── game/           # 游戏核心逻辑
│   ├── engine.py   # 游戏引擎
│   ├── card.py     # 卡牌系统
│   ├── player.py   # 玩家系统
│   ├── hero.py     # 武将系统
│   ├── skill.py    # 技能系统
│   └── events.py   # 事件系统
├── ai/             # AI 模块
│   └── bot.py      # AI 决策逻辑
├── ui/             # 界面模块
│   ├── rich_ui.py  # Rich 终端界面
│   └── terminal.py # 基础终端界面
├── tests/          # 测试文件
├── data/           # 数据文件
│   └── cards.json  # 卡牌数据
└── docs/           # 文档
```

## 问题反馈

如有问题或建议，请在 GitHub Issues 中提出。

## 许可证

本项目采用 MIT 许可证。
