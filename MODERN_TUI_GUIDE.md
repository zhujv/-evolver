# Evolver 现代化终端界面

## 简介

Evolver 项目现在提供了两个高级、美观的终端用户界面：

1. **Modern TUI** (`tui_modern.py`) - 全新设计的现代化聊天界面
2. **UI Components** (`ui/components.py`) - 可复用的UI组件库

## 功能特性

### Modern TUI

- 🎨 **现代化设计** - 使用 One Dark 配色方案，视觉美观
- 💬 **消息气泡** - 用户消息和AI回复使用不同颜色的气泡展示
- 🤖 **AI响应渲染** - 支持Markdown格式，自动语法高亮
- 📊 **Token统计** - 实时显示Token使用情况
- 👥 **智能体管理** - 方便切换不同AI智能体
- 🛠️ **技能系统** - 查看和管理可用技能
- ⏳ **动画加载** - 优雅的加载动画效果
- 📜 **历史记录** - 查看历史消息
- 🎯 **状态栏** - 实时显示会话、Agent、消息数等信息

### UI 组件库

组件库提供了丰富的可复用组件：

- `MessageBubble` - 消息气泡（用户、AI、系统、错误、成功）
- `AnimatedSpinner` - 动画加载器
- `StatusBar` - 状态栏
- `Header` / `Footer` - 头部和底部
- `ChatInterface` - 聊天界面主组件
- `AgentManager` - 智能体管理器
- `SkillManager` - 技能管理器
- `TokenTracker` - Token跟踪器
- `MarkdownRenderer` - Markdown渲染器
- `TypewriterEffect` - 打字机效果
- `ColorfulBorder` - 彩色边框

## 安装依赖

确保已安装必要的依赖：

```bash
pip install rich prompt-toolkit
```

## 使用方法

### 方式1: 使用 Modern TUI

启动后端服务后，在另一个终端运行：

```bash
python -m evolver.tui_modern
```

### 方式2: 在代码中使用组件

```python
from evolver.ui.components import (
    ChatInterface,
    MessageBubble,
    AnimatedSpinner,
    Header,
    Footer,
    StatusBar,
)

console = Console()

# 创建聊天界面
chat = ChatInterface(console)
chat.render_header()
chat.render_welcome()

# 使用消息气泡
MessageBubble.user("你好！", console)
MessageBubble.ai("你好！有什么可以帮助你的吗？", console)

# 使用加载动画
with AnimatedSpinner(console) as spinner:
    spinner.start("处理中...")
    # 执行任务
    spinner.update("即将完成...")
    # 任务完成，自动停止
```

## 命令列表

在 Modern TUI 中可用的命令：

| 命令 | 说明 |
|------|------|
| `help` | 显示帮助信息 |
| `health` | 检查系统状态 |
| `agents` | 查看可用智能体 |
| `use <id>` | 切换智能体 |
| `skills` | 查看可用技能 |
| `history` | 查看历史消息 |
| `token` | 查看Token使用统计 |
| `clear` | 清屏 |
| `quit / q` | 退出程序 |

## 界面预览

### 头部设计
```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                      Evolver - 智能AI助手                     ║
║                                                              ║
║              ✓ 多模型支持  ✓ 技能系统  ✓ 记忆管理  ✓ MCP集成    ║
╚══════════════════════════════════════════════════════════════╝
```

### 消息气泡
- 👤 **用户消息**: 青色边框，右侧对齐
- 🤖 **AI消息**: 紫色边框，左侧对齐，支持Markdown

### 状态栏
```
Session: abc123... │ Agent: default │ Messages: 5 │ Tokens: 1,234        │ 14:32:05
```

## 主题颜色

| 颜色 | 用途 |
|------|------|
| `#61AFEF` | 主要颜色（蓝色） |
| `#98C379` | 成功颜色（绿色） |
| `#E5C07B` | 强调颜色（黄色） |
| `#E06C75` | 错误颜色（红色） |
| `#A855F7` | AI消息（紫色） |
| `#2BBDFF` | 用户消息（亮蓝） |
| `#ABB2BF` | 正文文字 |
| `#5C6370` | 暗淡文字 |

## 自定义

### 创建自定义主题

```python
from evolver.ui.components import EvolverTheme

class MyTheme(EvolverTheme):
    PRIMARY = "#FF6B6B"
    SECONDARY = "#4ECDC4"
    # ...
```

### 创建自定义样式

```python
from rich.style import Style

my_style = Style(color="#FF6B6B", bold=True, bgcolor="#2D2D2D")
```

## 技术栈

- **Rich** - 强大的终端格式化库
- **Prompt Toolkit** - 命令行界面组件
- **One Dark** - 配色方案灵感来自 VS Code One Dark 主题

## License

MIT License
