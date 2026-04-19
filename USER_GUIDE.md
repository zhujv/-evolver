# Evolver 用户指南

## 1. 系统要求

### 硬件要求
- CPU: 至少 4 核心
- 内存: 至少 8GB
- 存储空间: 至少 20GB
- 网络: 稳定的互联网连接（用于API调用）

### 软件要求
- Python 3.8 或更高版本
- Docker（用于沙箱执行）
- Node.js 18 或更高版本（用于前端）

## 2. 安装指南

### 2.1 后端安装

```bash
# 克隆项目
git clone https://github.com/yourname/evolver.git
cd evolver

# 安装后端依赖
pip install -e .
```

### 2.2 前端安装

```bash
cd frontend
npm install

# 构建前端
npm run build
```

## 3. 配置说明

### 3.1 环境变量配置

创建 `.env` 文件，添加以下配置：

```bash
# API Keys
OPENROUTER_API_KEY=sk-...
OPENAI_API_KEY=sk-...

# 配置
EVOLVER_HOME=~/.evolver
EVOLVER_MODEL=claude-sonnet-4-20250514

# 安全配置
EVOLVER_SERVER_TOKEN=your-strong-random-token
EVOLVER_RESTART_TOKEN=another-strong-random-token
EVOLVER_HTTP_HOST=127.0.0.1
```

### 3.2 配置选项

| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| EVOLVER_HOME | 数据存储目录 | ~/.evolver |
| EVOLVER_MODEL | 默认模型 | claude-sonnet-4-20250514 |
| EVOLVER_SERVER_TOKEN | 服务器鉴权令牌 | 无（必须设置） |
| EVOLVER_RESTART_TOKEN | 重启鉴权令牌 | 无（必须设置） |
| EVOLVER_HTTP_HOST | 服务器监听地址 | 127.0.0.1 |
| EVOLVER_HTTP_PORT | 服务器监听端口 | 8000 |

## 4. 使用指南

### 4.1 启动服务

```bash
# 启动服务器
python -m evolver.server

# 或使用启动脚本
python start.py
```

### 4.2 CLI 界面使用

在另一个终端中启动CLI：

```bash
python -m evolver.ui.cli
```

#### 常用命令

- `create_session` - 创建新会话
- `chat <消息>` - 发送消息给AI
- `skills` - 列出所有技能
- `health` - 健康检查
- `exit` 或 `quit` - 退出

### 4.3 API 使用

#### 创建会话

```bash
curl -X POST http://localhost:8000/chat/create_session \
  -H "Authorization: Bearer your-server-token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user"}'
```

#### 发送消息

```bash
curl -X POST http://localhost:8000/chat/send \
  -H "Authorization: Bearer your-server-token" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id", "message": "Hello, how are you?"}'
```

## 5. 前端使用

### 5.1 开发模式

```bash
cd frontend
npm run dev
```

### 5.2 一键网页界面（推荐）

在仓库根目录：

```bash
python start.py
```

### 5.3 仅前端开发（需已手动启动后端）

```bash
cd frontend
npm run dev
```

## 6. 常见问题

### 6.1 API 密钥问题

- **问题**: 启动时提示 API 密钥未设置
- **解决方法**: 确保在 `.env` 文件中正确设置了 `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY`

### 6.2 Docker 问题

- **问题**: 沙箱执行失败
- **解决方法**: 确保 Docker 服务正在运行，并且当前用户有权限使用 Docker

### 6.3 内存问题

- **问题**: 系统内存不足
- **解决方法**: 关闭其他占用内存的应用，或增加系统内存

### 6.4 网络问题

- **问题**: API 调用失败
- **解决方法**: 检查网络连接，确保可以访问 API 服务

## 7. 故障排除

### 7.1 查看日志

服务器日志会输出到控制台，您可以查看详细的错误信息。

### 7.2 健康检查

```bash
curl http://localhost:8000/health
```

### 7.3 测试脚本

```bash
# 运行烟测
python scripts/smoke_test_server.py

# 运行安全测试
python -m unittest test_security_regressions.py
```

### 7.4 多供应商 API 与「endpoint / 502」类错误

配置文件位于 `~/.evolver/config.json` 中的 `api.providers`，可同时保存多个供应商。**当前实际使用的线路**大致按下面合并（请同时注意 `.env` 里是否仍有旧的 `EVOLVER_*`）：

1. 磁盘上的 `api.preferred_provider`（在界面点击 **保存** API 配置后会写入）：用于选择 **哪一个供应商块** 时**优先于**环境变量 `EVOLVER_PROXY_TYPE`，避免同一进程里残留的旧 `EVOLVER_PROXY_TYPE` 压过你在界面刚保存的供应商。
2. 若 `preferred_provider` 为空，则使用环境变量 `EVOLVER_PROXY_TYPE`（若存在且在 `providers` 中有对应项）。
3. 若仍无法确定，则按内置顺序选用第一个可用的 endpoint：**智谱 → DeepSeek → OpenAI → Anthropic → Google → 自定义中转**，避免仅因 JSON 键顺序长期命中旧的自定义中转。
4. 合并供应商块之后，若环境变量里仍设置了 `EVOLVER_API_BASE` / `EVOLVER_API_KEY` / `EVOLVER_MAIN_MODEL`，会**再次覆盖**基址、密钥与主模型名（用于「验证连接」等临时场景）；日常若希望完全跟配置文件走，请避免在 `.env` 或系统环境中长期保留与界面不一致的这三项。

**建议排查步骤：**

- 修改供应商或 Key 后务必在弹窗内点击 **保存**；仅改输入框不保存时，聊天前虽会尝试推送配置，但若未填「模型名称」等仍会跳过推送。
- 若曾点击 **验证连接**，随后发现请求仍指向旧地址：请对当前要用的供应商再点一次 **保存**，或重启后端（验证过程曾写入的临时 `EVOLVER_*` 需与磁盘配置对齐）。
- 使用智谱时请在供应商里选「智谱 AI」并保存，确保 `providers` 中出现 `zhipu` 段；聊天实际请求的模型名以弹窗内保存的「模型名称」及主界面模型下拉为准。

## 8. 性能优化

### 8.1 模型选择

- 对于快速响应，建议使用 `gpt-4o-mini`
- 对于复杂任务，建议使用 `claude-sonnet-4-20250514` 或 `gpt-4o`

### 8.2 缓存配置

- 确保 `EVOLVER_HOME` 有足够的存储空间
- 定期清理旧的会话数据

## 9. 安全最佳实践

- 定期更新 API 密钥
- 使用强随机的 `EVOLVER_SERVER_TOKEN` 和 `EVOLVER_RESTART_TOKEN`
- 保持 `EVOLVER_HTTP_HOST` 为 `127.0.0.1`，避免直接暴露在公网
- 定期运行安全测试

## 10. 联系与支持

- 问题反馈: GitHub Issues
- 功能请求: GitHub Discussions
- 社区支持: Discord 频道

---

*本指南会定期更新，以反映最新的功能和最佳实践。*