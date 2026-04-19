# Evolver TUI 使用说明

## 快速开始

### 1. 克隆项目
```bash
git clone <你的仓库地址>
cd <项目目录>
```

### 2. 创建虚拟环境并安装依赖
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 3. 启动后端服务器
```bash
.venv\Scripts\python.exe -m evolver.server
```
保持这个终端运行

### 4. 启动TUI（新开一个终端）
```bash
.venv\Scripts\python.exe -m evolver.tui
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `help` | 显示帮助 |
| `health` | 检查后端状态 |
| `create` | 创建新会话 |
| `chat <消息>` | 发送消息聊天 |
| `agents` | 列出可用智能体 |
| `use <id>` | 切换智能体 |
| `skills` | 列出技能 |
| `clear` | 清屏 |
| `exit` | 退出 |

## 常用操作流程

```
1. health           # 检查后端是否正常
2. create           # 创建会话
3. chat 你好        # 开始聊天
4. agents           # 查看有哪些智能体
5. use coder        # 切换到coder智能体
6. chat 帮我写个函数 # 让coder帮你写代码
```

## 常见问题

**Q: 连接失败怎么办？**
A: 确保后端服务器已启动 (步骤3)

**Q: 报错 "连接被拒绝"？**
A: 检查端口16888是否被占用

**Q: 中文显示乱码？**
A: 使用 `chcp 65001` 切换到UTF-8编码