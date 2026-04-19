# Evolver

> 可进化的 AI 编程助手 — 多智能体 · 技能系统 · 记忆存储 · MCP 集成

一个本地运行的 AI 编程工具。配置你的 API Key，它就能像编程搭档一样帮你写代码、改 Bug、搜索资料、操作文件。

---

## 项目简介

**Evolver** 是一个开源的 AI 编程助手，定位类似 Cursor / WorkBuddy，但完全本地化运行。你通过自然语言对话的方式下达指令，后端的多智能体系统会自动拆解任务、调用工具、迭代执行，最终帮你完成编程工作。

**它适合：**
- 想要本地私有 AI 编程环境的开发者
- 需要接入多个 LLM 模型的团队
- 想要深度定制 AI 助手能力的进阶用户

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ · FastAPI · uvicorn · SQLite |
| 前端 | React 18 · TypeScript · Vite · TailwindCSS |
| 桌面 | Tauri 2.x (Rust) |
| AI | Anthropic Claude · OpenAI GPT · Ollama · DeepSeek · OpenRouter |
| 协议 | MCP (Model Context Protocol) · HTTP/JSON-RPC · WebSocket |
| 部署 | Docker · NSIS Installer · PowerShell 脚本 |

## 项目亮点

**多智能体系统** — 内置 Coder、Reviewer、Researcher 等角色，Agent Loop 自动迭代完成复杂任务。不是一问一答，而是真正像搭档一样多轮协作。

**28 个内置工具** — 文件读写、终端执行、代码搜索、Web 搜索、Gmail/Outlook 邮件、Google 日历、飞书/钉钉……开箱即用，不用自己写。

**技能热加载** — 一个 SKILL.md 文件就能定义新能力，加载、审批、沙箱隔离全部自动，无需重启。

**跨会话记忆** — SQLite + 向量搜索混合存储，带隐私过滤。跨会话记住上下文，越用越懂你。

**多模型自由切换** — Claude、GPT、Ollama、OpenRouter、DeepSeek 随时切换，还能通过 OpenRouter 一个 Key 用多个模型。本地模型也支持。

**MCP 协议扩展** — 接入外部 MCP 服务器，无限扩展能力边界，社区生态直接复用。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层                            │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│   │  Web UI      │  │ Tauri 桌面    │  │  终端 TUI    │     │
│   │  React+Vite  │  │  Rust 原生    │  │  Textual    │     │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└──────────┼─────────────────┼─────────────────┼─────────────┘
           │                 │                 │
           └────────────┬────┴─────────────────┘
                        │  HTTP / JSON-RPC (:16888)
┌───────────────────────▼─────────────────────────────────────┐
│                      后端服务层                              │
│                    AgentServer                              │
│                   (FastAPI + Thread)                         │
└──────────┬──────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────┐
│                    智能体管理层                              │
│                  AgentManager                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐    │
│  │ AIAgent    │  │ SessionStore│  │  AgentProfiles     │    │
│  │ Agent Loop │  │ 会话管理    │  │  角色定义/切换      │    │
│  └─────┬──────┘  └────────────┘  └────────────────────┘    │
└────────┼───────────────────────────────────────────────────┘
           │ 调用
    ┌──────▼──────────────────────────────────────────────┐
    │              核心子系统                               │
    │                                                      │
    │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
    │  │ Provider │  │  Tools   │  │     Skills       │  │
    │  │  Router  │  │ Registry │  │    Manager       │  │
    │  │          │  │ 28 个工具 │  │ SKILL.md 加载    │  │
    │  └────┬─────┘  └──────────┘  └──────────────────┘  │
    │       │                                             │
    │  ┌────▼─────────┐  ┌──────────────────┐            │
    │  │   Memory     │  │       MCP        │            │
    │  │   Layer      │  │   Client/Server  │            │
    │  │ SQLite+向量  │  │  外部工具扩展     │            │
    │  └──────────────┘  └──────────────────┘            │
    └─────────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────┐
│                    LLM 供应商层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Anthropic │ │  OpenAI  │ │  Ollama  │ │ OpenRouter│     │
│  │  Claude   │ │  GPT     │ │  本地模型 │ │  多模型   │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
```

**数据流：** 用户输入 → AgentServer → AgentManager 选择角色 → AIAgent 循环调用 Provider 获取 LLM 回复 → 根据需要调用 Tools/Skills/MCP 执行操作 → 结果回传给用户

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/zhujv/evolver.git
cd evolver

# 2. Python 环境
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. 前端依赖
cd frontend && npm install && cd ..

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 API Key（见下方说明）

# 5. 启动
python start.py
# 自动打开浏览器 http://127.0.0.1:5173
```

## API Key 配置

在 `.env` 文件中填入至少一种模型的 Key：

**方式一：直连**
```env
# Claude
ANTHROPIC_API_KEY=sk-ant-xxx

# 或 OpenAI
OPENAI_API_KEY=sk-xxx

# 或 DeepSeek
EVOLVER_API_KEY=sk-xxx
EVOLVER_API_BASE=https://api.deepseek.com/v1
EVOLVER_MAIN_MODEL=deepseek-chat
EVOLVER_PROXY_TYPE=openai
```

**方式二：通过 OpenRouter 中转（推荐，一个 Key 用多个模型）**
```env
EVOLVER_API_BASE=https://openrouter.ai/api/v1
EVOLVER_API_KEY=sk-or-xxx
EVOLVER_MAIN_MODEL=anthropic/claude-3.5-sonnet
EVOLVER_PROXY_TYPE=openai
```

**方式三：本地模型（Ollama，无需 API Key）**
```env
EVOLVER_API_BASE=http://localhost:11434/v1
EVOLVER_MAIN_MODEL=qwen2.5-coder:7b
EVOLVER_PROXY_TYPE=openai
```

## 项目结构

```
evolver/                  # Python 后端
├── agent/                #   多智能体系统（切换、会话管理）
├── config/               #   配置加载（.env + config.json）
├── mcp/                  #   MCP 协议客户端
├── memory/               #   记忆系统（SQLite + 向量搜索）
├── providers/            #   LLM 供应商适配（Claude/GPT/Ollama...）
├── skills/               #   技能系统（加载、审批、沙箱）
├── tools/                #   工具系统（28 个内置工具）
├── ui/                   #   终端 TUI 界面
├── utils/                #   工具函数
└── server.py             #   FastAPI 主服务

frontend/                 # React 前端
├── src/                  #   源码（App、API、样式）
└── src-tauri/            #   Tauri 桌面应用

scripts/                  # 辅助脚本
monitoring/               # 健康检查和监控
```

## 部署方式

**Web 界面**（默认） — `python start.py`，自动打开浏览器

**终端 TUI** — `.\.venv\Scripts\python.exe -m evolver.tui`，纯命令行交互

**Tauri 桌面** — `cd frontend && npm run tauri dev`，原生桌面体验

**Docker** — `docker-compose up -d`，一键部署

## 可选功能

| 功能 | 配置方式 |
|------|---------|
| 邮件/日历 | `~/.evolver/config.json` → `integrations` |
| 飞书/钉钉 | 同上，`integrations.feishu` / `integrations.dingtalk` |
| MCP 工具 | 同上，`mcp.enabled` + `mcp.servers` |
| 安全令牌 | `.env` 中设置 `EVOLVER_SERVER_TOKEN` |

## 参与贡献

欢迎贡献代码、报告 Bug、提建议！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

### 核心思想

Evolver 的诞生深受以下优秀开源项目的启发：

- **[OpenCode](https://github.com/opencode-ai/opencode)** — 提供了模型无关设计理念和终端交互模式
- **[Nous Research / Hermes Agent](https://github.com/nousresearch)** — 揭示了 AI 自我进化的无限可能
- **[OpenClaw](https://github.com/nicholasgasior/openClaw)** — 对多平台连接和工具生态的探索为我们指明了方向

感谢你们的创造力和开源精神。

### 技术依赖

- **[Tauri](https://tauri.app/)** — 让我们能高效地构建跨平台桌面应用
- **[React](https://react.dev/)** / **[Vite](https://vitejs.dev/)** — 现代化的前端开发体验
- **[FastAPI](https://fastapi.tiangolo.com/)** — 高性能的 Python 后端框架
- **[Anthropic](https://www.anthropic.com/)** / **[OpenAI](https://openai.com/)** / **[Ollama](https://ollama.ai/)** — 强大的大语言模型能力

### 合规声明

以上所有项目及其许可证（MIT、Apache 2.0 等）的版权归原作者所有。Evolver 在吸收其思想精华的同时，严格遵守各项目的开源许可条款。我们对此深表谢意。

## License

[MIT](LICENSE)
