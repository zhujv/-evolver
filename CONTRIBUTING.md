# Contributing to Evolver

感谢你对 Evolver 的关注！欢迎各种形式的贡献——无论是修 Bug、加功能、改进文档，还是提建议。

## 快速开始

### 1. Fork & Clone

```bash
git clone https://github.com/你的用户名/evolver.git
cd evolver
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend && npm install && cd ..
cp .env.example .env  # 填入你的 API Key
```

### 2. 创建分支

```bash
git checkout -b feature/你的功能名
```

### 3. 开发 & 提交

```bash
git add .
git commit -m "feat: 简要描述你的改动"
```

### 4. 推送 & PR

```bash
git push origin feature/你的功能名
# 在 GitHub 上创建 Pull Request
```

## 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加代码审查技能` |
| `fix` | 修复 Bug | `fix: 修复 MCP 连接超时问题` |
| `docs` | 文档更新 | `docs: 更新 API 文档` |
| `refactor` | 重构 | `refactor: 优化工具注册流程` |
| `test` | 测试 | `test: 添加安全模块单元测试` |
| `chore` | 杂项 | `chore: 更新依赖版本` |

## 代码风格

### Python
- 遵循 PEP 8
- 类型注解推荐但非强制
- 函数和类需要有 docstring

### TypeScript / React
- 使用 ESLint + Prettier（项目已配置）
- 组件使用函数式写法 + Hooks
- Props 需要类型定义

## 测试

提交 PR 前请确保测试通过：

```bash
pytest test_security_regressions.py -v
```

如果你添加了新功能，请一并添加对应的测试用例。

## 项目结构

```
evolver/
├── agent/        # 多智能体系统
├── config/       # 配置管理
├── mcp/          # MCP 协议客户端
├── memory/       # 记忆系统
├── providers/    # LLM 供应商适配
├── skills/       # 技能系统
├── tools/        # 工具系统（28 个内置工具）
├── ui/           # 终端 TUI
└── utils/        # 工具函数
frontend/         # React + Vite 前端
scripts/          # 辅助脚本
```

## 添加新功能

### 添加新工具

在 `evolver/tools/` 下创建新文件，参考现有工具的结构：

```python
from evolver.tools.registry import tool

@tool(name="your_tool", description="你的工具描述")
async def your_tool(params: dict) -> str:
    """工具实现"""
    pass
```

### 添加新技能

1. 在 `~/.evolver/skills/` 下创建技能目录
2. 编写 `SKILL.md` 技能描述文件
3. 技能会被自动加载

### 添加新 LLM 供应商

1. 在 `evolver/providers/adapter.py` 中添加新的适配器
2. 在 `evolver/providers/router.py` 中注册路由

## Bug 报告

提交 Issue 时请包含：
- **复现步骤**
- **预期行为 vs 实际行为**
- **运行环境**（OS、Python 版本、Node 版本）
- **相关日志**

## 许可

贡献的代码将遵循 [MIT License](LICENSE)。
