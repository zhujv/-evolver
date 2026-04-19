# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 多智能体系统（Agent Loop）：支持多角色切换、会话管理
- 技能系统：支持 SKILL.md 定义、热加载、审批机制
- 记忆系统：SQLite + 向量搜索混合存储，隐私过滤
- 28 个内置工具：文件操作、Bash 执行、MCP 工具、搜索、Office 等
- MCP 协议支持：连接外部 MCP 服务器扩展能力
- 多 LLM 供应商：Claude、OpenAI、Ollama、OpenRouter、DeepSeek
- Web UI：React + Vite 前端，聊天式交互界面
- Tauri 桌面应用：原生桌面体验
- 终端 TUI：纯命令行交互模式
- 流式响应：实时输出 AI 回复
- 安全机制：API Key 加密存储、内容过滤、执行沙箱
- Docker 支持：一键部署
- 监控模块：性能指标采集

### Security
- API Key 加密存储（AES-256）
- .env 环境变量隔离
- 命令执行沙箱
- 内容安全策略
- 服务器 Token 认证
