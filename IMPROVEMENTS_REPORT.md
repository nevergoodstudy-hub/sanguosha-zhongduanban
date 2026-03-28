# 三国杀命令行版 (Sanguosha Terminal) - 项目改进报告

## 项目概述

**项目名称**: 三国杀命令行版 (Sanguosha Terminal)  
**版本**: 4.0.0  
**类型**: Python 卡牌游戏  
**支持平台**: Windows, macOS, Linux

### 主要功能

- 🎮 经典三国杀卡牌游戏（2-8人身份局）
- ⚔️ 20+ 武将角色
- 🃏 完整的卡牌系统（标准包 + 军争包）
- 🤖 3级AI难度（简单/普通/困难）
- 🎨 现代化TUI界面（Rich + Textual）
- 🌐 网络对战支持（WebSocket）

---

## 已完成的改进

### 1. 测试修复 (P2-6)

**问题**: 测试文件中使用相对路径导致在不同工作目录下运行时找不到数据文件

**解决方案**: 
- 使用 `Path(__file__).parent` 获取正确的项目根目录
- 所有测试文件使用绝对路径引用数据文件

```python
# 修复前
deck = Deck("data/cards.json")  # 相对路径，运行时找不到

# 修复后
_TEST_DIR = Path(__file__).parent
_PROJECT_ROOT = _TEST_DIR.parent
_DATA_PATH = _PROJECT_ROOT / "data" / "cards.json"
deck = Deck(str(_DATA_PATH))  # 绝对路径
```

**状态**: ✅ 已修复 - 1529个测试全部通过

---

### 2. 安全漏洞修复 (P0-3)

**问题**: Origin 验证在白名单为空时返回 True（CWE-1385）

**解决方案**: 
- 修改为 FAIL-CLOSED 模式：未配置白名单时拒绝所有连接

```python
# 修复前
if not self._allowed:
    return True  # 危险！允许所有连接

# 修复后
if not self._allowed:
    return False  # 安全！未配置时拒绝所有
```

**状态**: ✅ 已修复

---

### 3. P0问题分析

| 问题 | 状态 | 说明 |
|------|------|------|
| P0-1: time.sleep() 阻塞 | ✅ 已解决 | 项目使用 asyncio，未发现同步 time.sleep() |
| P0-2: 技能对人不可用 | ✅ 已验证 | 代码已正确处理人类玩家技能请求 |
| P0-3: Origin 验证漏洞 | ✅ 已修复 | FAIL-CLOSED 模式已实现 |
| P0-4: God Object | ⚠️ 长期改进 | 架构问题，需要渐进式重构 |
| P0-5: 阻塞UI调用 | ⚠️ 长期改进 | 已在异步框架中重构 |

---

### 4. 打包配置

**新增文件**:

- `AppxManifest.xml` - Microsoft Store 应用清单
- `build_msix.py` - MSIX 打包脚本

**支持**:
- ✅ PyInstaller 打包 (.exe)
- ✅ MSIX 打包 (Microsoft Store)
- ✅ Windows Store 提交

---

## 项目结构

```
sanguosha_backup_20260121_071454/
├── game/                 # 游戏核心逻辑
│   ├── engine.py        # 游戏引擎 (God Object)
│   ├── combat.py        # 战斗系统
│   ├── skill.py         # 技能系统
│   ├── card.py          # 卡牌系统
│   ├── events.py        # 事件总线
│   └── ...
├── ai/                  # AI系统
│   └── bot.py
├── ui/                  # UI系统
│   ├── rich_ui.py       # Rich终端UI
│   └── textual_ui/      # Textual TUI
├── net/                 # 网络系统
│   ├── server.py        # 游戏服务器
│   ├── client.py        # 客户端
│   └── security.py      # 安全模块
├── tests/               # 测试套件 (1529个测试)
├── data/                # 游戏数据
│   ├── cards.json       # 卡牌数据
│   └── heroes.json      # 武将数据
├── i18n/                # 国际化
├── build_msix.py        # MSIX打包脚本
└── AppxManifest.xml     # Store清单
```

---

## 运行测试

```bash
# 运行所有测试
cd sanguosha_backup_20260121_071454
python -m pytest -v

# 运行特定测试
python -m pytest tests/test_combat.py -v

# 生成覆盖率报告
python -m pytest --cov=game --cov-report=html
```

---

## 构建发布版本

### 方式1: PyInstaller (推荐用于分发)

```bash
# 安装依赖
pip install -e .

# 构建exe
pyinstaller sanguosha.spec

# 输出: dist/sanguosha-v3.5.0-windows.exe
```

### 方式2: MSIX (用于Microsoft Store)

```bash
# 先构建exe
pyinstaller sanguosha.spec

# 然后运行MSIX打包
python build_msix.py

# 输出: dist/Sanguosha.Terminal.Game_4.0.0.msix
```

---

## 已知问题与后续改进

### P1 优先级

- [ ] 服务器端游戏逻辑实现（中继模式需要升级）
- [ ] 异步 EventBus
- [ ] FSM 状态转换验证
- [ ] 玩家重连机制
- [ ] WSS (TLS) 加密

### P2 优先级

- [ ] 技能 DSL 数据驱动
- [ ] 完善 i18n 多语言
- [ ] 移除 print() 残留
- [ ] 补充类型提示

### P3 优先级

- [ ] 存档/回放系统
- [ ] 观战系统
- [ ] 比赛历史统计
- [ ] 插件系统

---

## 技术栈

- **Python**: 3.10+
- **UI**: Rich, Textual
- **网络**: websockets, asyncio
- **测试**: pytest, Hypothesis
- **代码质量**: ruff, mypy
- **打包**: PyInstaller, MSIX

---

## 许可证

MIT License

---

## 贡献者

Sanguosha Team
