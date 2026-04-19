# Evolver - AI 编程助手技术规格

## 1. 项目概述

**项目名称**: Evolver
**项目类型**: 桌面应用程序 + CLI
**核心功能**: 可进化的 AI 编程助手，能主动完成复杂任务
**目标用户**: 开发者

### 核心特性
- **自我进化** - 从交互中学习，适配用户习惯（需人工确认）
- **主动执行** - 自主完成复杂任务，非仅辅助
- **双模型支持** - Claude 3.5 Sonnet + GPT-4o
- **桌面集成** - GUI + CLI 双模式

---

## 2. 技术架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────┐
│              UI 层 (Tauri + React)          │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │  Desktop UI │  │  Terminal TUI     │   │
│  └─────────────┘  └─────────────────────┘   │
│                    │                        │
│              JSON-RPC (stdin/stdout)        │
└────────────────────┼────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│           AgentManager (Python)               │
│  ┌─────────────────────────────────────┐   │
│  │  • 单例管理多会话                    │   │
│  • 状态持久化                          │   │
│  • 工具编排                          │   │
│  │  • 记忆管理                         │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│             工具层 (Python)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │文件工具  │ │执行工具  │ │搜索工具  │  │
│  │(沙箱)   │ │(白名单)  │ │        │  │
│  └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐                │
│  │记忆工具  │ │ MCP工具  │                │
│  │(向量化) │ │        │                │
│  └──────────┘ └──────────┘                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│          Provider 适配层 (Python)          │
│  ┌─────────────────────────────────────┐   │
│  │     统一工具调用格式转换             │   │
│  │  OpenAI格式 ↔ Anthropic格式 ↔ ...   │   │
│  └─────────────────────────────���───────┘   │
└─────────────────────────────────────────────┘
```

### 2.2 IPC 通信设计

**方案**: HTTP Server + Unix Socket 双模式（推荐Socket）

```python
# Python 后端 (server.py) - 强化版
import json
import time
import threading
import http.server
import socketserver
import os
import signal

THREAD_PORT = 16888
SOCKET_PATH = os.environ.get('EVOLVER_SOCKET', '/tmp/evolver.sock')

class AgentServer:
    def __init__(self, port: int = THREAD_PORT, socket_path: str = SOCKET_PATH):
        self.port = port
        self.socket_path = socket_path
        self.manager = AgentManager()
        self.running = True
        self._health_status = {
            'last_ping': time.time(),
            'uptime': 0,
            'start_time': time.time(),
            'request_count': 0,
        }

    def start_http(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                try:
                    request = json.loads(body)
                    response = self._handle_request(request)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # 禁用默认日志

        with socketserver.TCPServer(('', self.port), Handler) as httpd:
            httpd.serve_forever()

    def start_socket(self):
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        
        import socket
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.socket_path)
        os.chmod(self.socket_path, 0o600)
        server.listen(5)
        
        while self.running:
            conn, _ = server.accept()
            self._handle_connection(conn)

    def _handle_connection(self, conn):
        try:
            data = conn.recv(4)
            if len(data) < 4:
                return
            length = int.from_bytes(data, 'big')
            if length > 10 * 1024 * 1024:
                return
            
            body = b''
            while len(body) < length:
                chunk = conn.recv(length - len(body))
                if not chunk:
                    break
                body += chunk
            
            request = json.loads(body)
            response = self._handle_request(request)
            
            resp_data = json.dumps(response).encode()
            conn.sendall(len(resp_data).to_bytes(4, 'big'))
            conn.sendall(resp_data)
        finally:
            conn.close()

    def _handle_request(self, request: dict) -> dict:
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        self._health_status['request_count'] += 1
        
        handlers = {
            'chat': self.manager.chat,
            'create_session': self.manager.create_session,
            'interrupt': self.manager.interrupt,
            'get_skills': self.manager.list_skills,
            'save_skill': self.manager.save_skill,
            'get_memory': self.manager.recall_memory,
            'health': lambda: self._health_status,
            'restart': self._graceful_restart,
        }
        
        handler = handlers.get(method)
        try:
            result = handler(**params) if params else handler()
            return {'result': result, 'id': request_id}
        except Exception as e:
            return {'error': {'code': -32603, 'message': str(e)}, 'id': request_id}

    def _graceful_restart(self):
        self.running = False
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)

    def health_check(self) -> dict:
        return {
            'status': 'healthy' if self.running else 'stopped',
            'uptime': time.time() - self._health_status['start_time'],
            'requests': self._health_status['request_count'],
            'last_ping': time.time() - self._health_status['last_ping'],
        }

class HealthMonitor:
    def __init__(self, server: AgentServer, check_interval: int = 10):
        self.server = server
        self.check_interval = check_interval
        self._stop = threading.Event()
    
    def start(self):
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
    
    def _monitor_loop(self):
        while not self._stop.is_set():
            time.sleep(self.check_interval)
            health = self.server.health_check()
            
            if health['last_ping'] > 60:
                print(f'[Health] Unresponsive, restarting...')
                self.server._graceful_restart()
            
            if health['uptime'] > 3600:
                print(f'[Health] Rolling restart after 1h')
                self.server._graceful_restart()

import sys
if __name__ == '__main__':
    server = AgentServer()
    
    mode = os.environ.get('EVOLVER_IPC_MODE', 'socket')
    if mode == 'http':
        threading.Thread(target=server.start_http, daemon=True).start()
    else:
        threading.Thread(target=server.start_socket, daemon=True).start()
    
    HealthMonitor(server).start()
    print(f'[Evolver] Server started (mode: {mode})')
    
    while server.running:
        time.sleep(1)
```

```rust
// Rust 前端 (src/ipc.rs)
use serde::{Deserialize, Serialize};
use std::process::Command;

#[derive(Serialize, Deserialize)]
struct JsonRpcRequest {
    method: String,
    params: Option<serde_json::Value>,
    id: Option<u64>,
}

#[derive(Serialize, Deserialize)]
struct JsonRpcResponse {
    result: Option<serde_json::Value>,
    error: Option<JsonRpcError>,
    id: Option<u64>,
}

struct FrontendIpc {
    socket_path: String,
    http_port: u16,
    use_socket: bool,
}

impl FrontendIpc {
    fn new() -> Self {
        let socket_path = std::env::var('EVOLVER_SOCKET')
            .unwrap_or_else(|_| '/tmp/evolver.sock'.to_string());
        let http_port = std::env::var('EVOLVER_PORT')
            .unwrap_or_else(|_| '16888'.to_string())
            .parse()
            .unwrap_or(16888);
        
        Self {
            socket_path,
            http_port,
            use_socket: std::path::Path::new(&socket_path).exists(),
        }
    }

    fn call(&mut self, method: &str, params: Value) -> Result<Value, Error> {
        let req = JsonRpcRequest {
            method: method.to_string(),
            params: Some(params),
            id: Some(self.next_id()),
        };

        if self.use_socket {
            self.call_socket(req)
        } else {
            self.call_http(req)
        }
    }

    fn call_socket(&mut self, req: JsonRpcRequest) -> Result<Value, Error> {
        use std::io::{Read, Write};
        
        let mut stream = std::fs::File::create(&self.socket_path)?;
        let data = serde_json::to_string(&req)?;
        stream.write_all(&(data.len() as u32).to_be_bytes())?;
        stream.write_all(data.as_bytes())?;
        stream.flush()?;
        
        let mut response = [0u8; 4];
        stream.read_exact(&mut response)?;
        let length = u32::from_be_bytes(response) as usize;
        let mut buffer = vec![0u8; length];
        stream.read_exact(&mut buffer)?;
        
        let resp: JsonRpcResponse = serde_json::from_slice(&buffer)?;
        resp.result.ok_or(resp.error.into())
    }

    fn call_http(&mut self, req: JsonRpcRequest) -> Result<Value, Error> {
        let client = reqwest::blocking::Client::new();
        let url = format!(
            'http://localhost:{}/rpc',
            self.http_port
        );
        
        let response = client
            .post(&url)
            .json(&req)
            .send()?;
        
        let resp: JsonRpcResponse = response.json()?;
        resp.result.ok_or(resp.error.into())
    }

    fn health_check(&self) -> Result<serde_json::Value, Error> {
        let req = JsonRpcRequest {
            method: 'health'.to_string(),
            params: None,
            id: None,
        };
        
        if self.use_socket {
            self.call_socket(req)
        } else {
            self.call_http(req)
        }
    }
}

#[derive(Serialize, Deserialize)]
struct JsonRpcResponse {
    result: Option<serde_json::Value>,
    error: Option<JsonRpcError>,
    id: Option<u64>,
}

impl FrontendIpc {
    fn call(&mut self, method: &str, params: Value) -> Result<Value, Error> {
        let req = JsonRpcRequest {
            method: method.to_string(),
            params: Some(params),
            id: self.next_id(),
        };

        // 写入 stdin (长度前缀协议)
        let data = serde_json::to_string(&req)?;
        let length = (data.len() as u32).to_be_bytes();
        self.stdin.write_all(&length)?;
        self.stdin.write_all(data.as_bytes())?;
        self.stdin.flush()?;

        // 读取 stdout (长度前缀)
        let response = self.read_message()?;
        response.result.ok_or(response.error.into())
    }

    fn read_message(&mut self) -> Result<JsonRpcResponse, Error> {
        let mut header = [0u8; 4];
        self.stdout.read_exact(&mut header)?;
        let length = u32::from_be_bytes(header) as usize;
        let mut buffer = vec![0u8; length];
        self.stdout.read_exact(&mut buffer)?;
        Ok(serde_json::from_slice(&buffer)?)
    }

    // 主动推送 (Python → Rust)
    fn on_tool_progress(&mut self, tool: &str, progress: &str) {
        // 用于流式更新 UI
    }
}
```

### 2.3 AgentManager 单例设计

```python
# agent/manager.py
class AgentManager:
    """全局单例，管理所有会话"""

    _instance = None
    _sessions: dict[str, AIAgent] = {}
    _skills: SkillManager
    _memory: MemoryStore with VectorDB

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        # 初始化记忆存储 (MVP: SQLite + FTS5)
        self._memory = SQLiteMemoryStore()
        # 加载技能
        self._skills = SkillManager()
        # 初始化会话存储
        self._session_store = SessionStore()
        # Phase 1: 内存会话
        self._sessions: dict[str, AIAgent] = {}
        # Phase 2: 持久化会话 (见 2.5 节)

    def chat(self, session_id: str, message: str) -> ChatResult:
        """处理对话请求"""
        agent = self._sessions.get(session_id)
        if not agent:
            agent = self._create_session(session_id)

        # 注入记忆上下文
        context = self._memory.recall(message)

        return agent.run_conversation(
            message,
            context=context,
            skills=self._skills.get_relevant(message),
        )

    def interrupt(self, session_id: str, message: str = None):
        """中断会话"""
        agent = self._sessions.get(session_id)
        if agent:
            agent.interrupt(message)

    def _create_session(self, session_id: str) -> AIAgent:
        """创建新会话"""
        agent = AIAgent(model=self._config.default_model)
        self._sessions[session_id] = agent
        self._session_store.save(session_id, agent)  # 持久化
        return agent

    def _load_sessions(self) -> dict[str, AIAgent]:
        """加载所有会话"""
        return self._session_store.load_all_sessions()

### 2.4 AIAgent 最小实现 - 动态Token预算 + 迭代保护

```python
# agent/run_agent.py
import tiktoken

class AIAgent:
    def __init__(self, model: str):
        self.model = model
        self.messages: list[dict] = []
        self.context: dict = {}
        self.iteration_count: int = 0
        self.max_iterations = 50
        self.max_same_file_operations = 3
        self.max_same_command_executions = 2
        self.operation_history = []
        self.running_processes = []
        self._interrupted = False
        self._tokenizer = tiktoken.for_model(model) if model else None
        self.max_tokens = 100000
        self.warning_threshold = 0.8
        self._token_warning_sent = False

    def _estimate_tokens(self) -> int:
        if not self._tokenizer:
            return 0
        return sum(self._tokenizer.encode(str(m.get('content', ''))) for m in self.messages)

    def _should_continue(self) -> tuple[bool, str]:
        if self._interrupted:
            return False, '操作已被用户中断'
        if self.iteration_count >= self.max_iterations:
            return False, f'已达到最大迭代次数({self.max_iterations})'
        current_tokens = self._estimate_tokens()
        if current_tokens > self.max_tokens:
            return False, f'Token预算已用尽({current_tokens}/{self.max_tokens})'
        if current_tokens > self.max_tokens * self.warning_threshold and not self._token_warning_sent:
            self._token_warning_sent = True
            return True, f'[警告] Token使用已超过80%'
        duplicate_check = self._check_duplicate_operations()
        if duplicate_check:
            return False, f'检测到重复操作：{duplicate_check}'
        return True, ''

    def run_conversation(self, message: str, context: dict = None, skills: list = None) -> ChatResult:
        self.messages.append({'role': 'user', 'content': message})
        while True:
            should_continue, reason = self._should_continue()
            if not should_continue:
                return ChatResult(final_response=reason or '已达限制', messages=self.messages)
            response = self._call_llm(context, skills)
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    self.operation_history.append(tool_call)
                    result = self._execute_tool(tool_call)
                    self.messages.append(tool_call.result)
            else:
                return ChatResult(final_response=response.content, messages=self.messages, iterations=self.iteration_count)
            self.iteration_count += 1
        return ChatResult(final_response=f'已达限制({self.iteration_count}次)', messages=self.messages)
            if self._interrupted:
                return ChatResult(
                    final_response="操作已被用户中断",
                    messages=self.messages
                )
            
            duplicate_check = self._check_duplicate_operations()
            if duplicate_check:
                return ChatResult(
                    final_response=f"检测到重复操作：{duplicate_check}，已自动终止",
                    messages=self.messages
                )
            
            response = self._call_llm(context, skills)

            if response.tool_calls:
                for tool_call in response.tool_calls:
                    self.operation_history.append(tool_call)
                    result = self._execute_tool(tool_call)
                    self.messages.append(tool_call.result)
            else:
                return ChatResult(
                    final_response=response.content,
                    messages=self.messages,
                    iterations=self.iteration_count,
                )

            self.iteration_count += 1

        return ChatResult(final_response=f"已达到最大迭代次数({self.max_iterations})", messages=self.messages)

    def _check_duplicate_operations(self):
        file_operations = {}
        for op in self.operation_history:
            file = op.get("parameters", {}).get("path", "unknown")
            file_operations[file] = file_operations.get(file, 0) + 1
            if file_operations[file] >= self.max_same_file_operations:
                return f"文件 {file} 操作次数过多"
        
        command_executions = {}
        for op in self.operation_history:
            cmd = op.get("name", "unknown")
            command_executions[cmd] = command_executions.get(cmd, 0) + 1
            if command_executions[cmd] >= self.max_same_command_executions:
                return f"命令 {cmd} 执行次数过多"
        
        return None

    def interrupt(self, message: str = None):
        """中断当前执行"""
        self._interrupted = True
        for proc in self.running_processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        self.running_processes = []

    def _call_llm(self, context: dict, skills: list) -> LLMResponse:
        pass

    def _execute_tool(self, tool_call: dict) -> dict:
        pass
```

### 2.5 会话持久化 (Phase 2) - 禁用pickle + 版本兼容

```python
# agent/session_store.py
import msgpack
import sqlite3
import time

SESSION_VERSION = 1

class SessionStore:
    """SQLite 会话持久化 - 禁用pickle"""

    def __init__(self, db_path: str = "~/.evolver/sessions.db"):
        self.db_path = db_path
        with sqlite3.connect(db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    model TEXT,
                    created_at INTEGER,
                    updated_at INTEGER,
                    state BLOB
                )
            """)

    def save(self, session_id: str, agent: AIAgent):
        state = {
            "_version": SESSION_VERSION,
            "model": agent.model,
            "messages": agent.messages,
            "context": agent.context,
            "iteration_count": agent.iteration_count
        }
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?)",
                (session_id, agent.model, int(time.time()), int(time.time()), 
                 msgpack.dumps(state, use_bin_type=True))
            )

    def load(self, session_id: str):
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT model, state FROM sessions WHERE id = ?",
                (session_id,)).fetchone()
        if row:
            model, state_blob = row
            state = msgpack.loads(state_blob, raw=False)
            
            # 版本迁移
            version = state.get("_version", 0)
            if version < SESSION_VERSION:
                state = self._migrate(state, version)
            
            agent = AIAgent(model=model)
            agent.messages = state.get("messages", [])
            agent.context = state.get("context", {})
            agent.iteration_count = state.get("iteration_count", 0)
            return agent
        return None

    def _migrate(self, state: dict, from_version: int) -> dict:
        """版本迁移"""
        if from_version == 0:
            # v0 -> v1: 添加新增字段
            state["iteration_count"] = state.get("iteration_count", 0)
            state["_version"] = SESSION_VERSION
        return state
```

### 2.6 核心模块

```
evolver/
├── src/
│   ├── main.rs              # Tauri 入口
│   ├── lib.rs               # 库导出
│   ├── ipc.rs              # JSON-RPC 通信
│   └── ui/                 # React 组件
│
├── agent/                  # AI Agent 核心
│   ├── __init__.py
│   ├── manager.py          # AgentManager 单例 ★
│   ├── run_agent.py        # AIAgent 主循环
│   ├── prompt_builder.py # 提示词构建
│   └── context_compressor.py
│
├── tools/                  # 工具实现 (沙箱)
│   ├── registry.py        # 工具注册
│   ├── sandbox.py       # 技能沙箱 ★
│   ├── file_tools.py    # 文件操作
│   ├── bash_tool.py     # 命令执行 (白名单)
│   ├── search_tools.py
│   ├── memory_tools.py  # 记忆 (向量化)
│   └── mcp_tools.py
│
├── skills/                # 技能系统
│   ├── __init__.py
│   ├── skill_manager.py
│   ├── skill_sandbox.py  # 技能执行限制 ★
│   └── skill_store.py
│
├── memory/                # 记忆系统 (向量)
│   ├── __init__.py
│   ├── vector_store.py   # SQLite FTS5 / usearch
│   ├── short_term.py
│   ├── long_term.py
│   ├── privacy_filter.py # 敏感数据过滤 ★
│   └── session_db.py
│
├── providers/             # LLM 提供商
│   ├── __init__.py
│   ├── router.py        # 路由 + 格式转换 ★
│   ├── adapter.py      # 统一工具调用格式
│   ├── openrouter.py
│   ├── anthropic.py
│   └── openai.py
│
├── ui/                   # TUI 界面
│   ├── __init__.py
│   ├── cli.py
│   ├── display.py
│   └── input.py
│
└── config/
    ├── __init__.py
    ├── loader.py
    └── defaults.py
```

---

## 3. Provider 适配层 (关键)

### 3.1 统一工具调用格式

```python
# providers/adapter.py
from abc import ABC, abstractmethod
from typing import Any

class ModelAdapter(ABC):
    """模型适配器基类"""

    @abstractmethod
    def format_tools(self, tools: list[dict]) -> list[dict]:
        """将统一格式转为模型特定格式"""

    @abstractmethod
    def parse_tool_calls(self, response: Any) -> list[dict]:
        """从模型响应中提取工具调用"""

class OpenAIAdapter(ModelAdapter):
    def format_tools(self, tools):
        # OpenAI Function Calling 格式
        return [{"type": "function", "function": {...}} for t in tools]

    def parse_tool_calls(self, response):
        return [t.model_dump() for t in response.tool_calls]

class AnthropicAdapter(ModelAdapter):
    def format_tools(self, tools):
        # Anthropic tool_use 格式
        return [{"name": t["name"], "description": t["description"],
                 "input_schema": t["parameters"]} for t in tools]

    def parse_tool_calls(self, response):
        return [tc.model_dump() for tc in response.tools]

# 工厂函数
def get_adapter(provider: str, model: str) -> ModelAdapter:
    if provider in ("openai", "openrouter") or "gpt" in model:
        return OpenAIAdapter()
    elif provider == "anthropic" or "claude" in model:
        return AnthropicAdapter()
    # ...
```

### 3.2 统一工具调用格式（强校验版）

```python
# providers/adapter.py
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

ALLOWED_TOOLS = {
    "read_file", "write_file", "patch", "grep", "glob",
    "git_commit", "git_push", "search_files"
}

class UnifiedToolAdapter:
    def parse_tool_calls(self, response) -> List[Dict]:
        try:
            raw_calls = self._extract_raw_tool_calls(response)
            
            standardized = []
            for call in raw_calls:
                standardized.append({
                    "id": call.get("id", self._generate_id()),
                    "name": call["name"],
                    "parameters": call.get("parameters", {})
                })
            
            for call in standardized:
                if call["name"] not in ALLOWED_TOOLS:
                    raise ValueError(f"非法工具调用: {call['name']}")
            
            return standardized
            
        except Exception as e:
            logger.error(f"工具调用解析失败: {e}")
            return []

    def _extract_raw_tool_calls(self, response):
        pass

    def _generate_id(self):
        import uuid
        return str(uuid.uuid4())
```

### 3.2 LLM注入攻击防御（强化版）

```python
# providers/adapter.py
import re

class LLMSanitizer:
    def sanitize_llm_input(self, text: str) -> str:
        # 移除系统提示词注入
        text = re.sub(r"<system>.*?</system>", "", text, flags=re.DOTALL)
        text = re.sub(r"</?system>", "", text, flags=re.IGNORECASE)
        # 移除工具调用注入
        text = re.sub(r"<工具>.*?</工具>", "", text, flags=re.DOTALL)
        text = re.sub(r"</?工具>", "", text, flags=re.IGNORECASE)
        # 移除指令注入关键词
        text = re.sub(r"(忽略|无视|忘记|执行|运行)[\s,:]?前面的指令?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"ignore\s+previous\s+instructions?", "", text, flags=re.IGNORECASE)
        return text

    def sanitize_llm_output(self, text: str) -> str:
        """过滤LLM输出的显示文本"""
        dangerous_cmds = ["rm -rf", "mkfs", "dd", "wget", "curl", "sudo", "su"]
        for cmd in dangerous_cmds:
            text = text.replace(cmd, f"[禁止执行: {cmd}]")
        return text
    # 注意：实际工具执行的安全检查由 DockerSandbox.execute() 和 validate_skill() 负责

    def sanitize_memory_content(self, content: str) -> str:
        # 移除所有HTML/XML标签
        content = re.sub(r"<[^>]+>", "", content)
        # 移除系统指令关键词
        content = re.sub(r"(忽略|无视|忘记|执行|运行)[\s,:]?前面的指令?", "", content, flags=re.IGNORECASE)
        # 移除代码注释中的注入
        content = re.sub(r"#\s*(忽略|无视|忘记).*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"//\s*(忽略|无视|忘记).*", "", content, flags=re.IGNORECASE)
        return content
```

### 3.3 模型熔断机制

```python
# providers/router.py
import time

class ModelRouter:
    def __init__(self, main_model, fallback_model):
        self.main_model = main_model
        self.fallback_model = fallback_model
        self.failure_count = 0
        self.circuit_breaker_open = False
        self.circuit_breaker_reset_time = 0
        self.max_failures = 3
        self.circuit_breaker_duration = 60

    def chat(self, messages, tools):
        if self.circuit_breaker_open:
            if time.time() < self.circuit_breaker_reset_time:
                return self.fallback_model.chat(messages, tools)
            else:
                self.circuit_breaker_open = False
                self.failure_count = 0
        
        try:
            result = self.main_model.chat(messages, tools)
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.max_failures:
                self.circuit_breaker_open = True
                self.circuit_breaker_reset_time = time.time() + self.circuit_breaker_duration
            return self.fallback_model.chat(messages, tools)
```

---

## 4. 技能沙箱 (安全关键)

### 4.1 Docker沙箱隔离（强化版）

```python
# tools/sandbox.py
import docker
import os
import re

class DockerSandbox:
    def __init__(self):
        self.client = docker.from_env()
        self.image = "python:3.11-slim"
        self.denied_patterns = [
            r"rm\s+-rf", r"mkfs", r"dd\s+if", r"wget", r"curl",
            r"sudo", r"su\s", r"chmod\s+777", r"chown",
            r"/etc/passwd", r"/etc/shadow", r"~/.ssh",
            r"eval\s+", r"exec\s+", r"source\s+.*\.sh"
        ]
        self.allowed_commands = {
            "git": ["status", "add", "commit", "push", "pull", "log", "diff", "checkout"],
            "pip": ["install", "list", "show", "uninstall"],
            "python": ["-m", "-c", "-u"],
            "npm": ["install", "run", "test"],
            "node": ["-e", "-p"],
        }

    def execute(self, command: str) -> dict:
        command = command.strip()
        
        # 全字符串匹配检查
        for pattern in self.denied_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise PermissionError(f"禁止执行高危命令: {pattern}")
        
        # 检查允许的命令白名单
        cmd_parts = command.split()
        if cmd_parts:
            base_cmd = cmd_parts[0]
            if base_cmd in self.allowed_commands:
                if len(cmd_parts) > 1:
                    sub_cmd = cmd_parts[1]
                    if sub_cmd not in self.allowed_commands[base_cmd]:
                        raise PermissionError(f"不允许的子命令: {sub_cmd}")
            elif base_cmd not in ["bash", "cat", "ls", "grep", "find", "echo", "pwd", "cd"]:
                raise PermissionError(f"不允许的命令: {base_cmd}")
        
        # 检查挂载路径安全
        workspace_path = os.getcwd()
        if os.path.exists("/workspace"):
            workspace_path = "/workspace"
        
        # 以非root用户运行容器
        try:
            container = self.client.containers.run(
                self.image,
                command=f"bash -c '{command}'",
                volumes={
                    workspace_path: {"bind": "/workspace", "mode": "ro"}
                },
                working_dir="/workspace",
                network_disabled=True,
                mem_limit="256m",
                cpu_period=100000,
                cpu_quota=25000,
                user="1000:1000",
                cap_drop=["ALL"],
                read_only=True,
                detach=True
            )
            result = container.wait(timeout=30)
            output = container.logs().decode("utf-8", errors="replace")
            container.remove()
            return {"exit_code": result["StatusCode"], "output": output}
        except docker.errors.DockerNotFound:
            return self._fallback_execute(command)

def _fallback_execute(self, command: str) -> dict:
        import subprocess
        import re

        SAFE_COMMANDS = {
            'git': {
                'status': ['git', 'status'],
                'diff': ['git', 'diff', '--stat'],
                'diff HEAD': ['git', 'diff', 'HEAD'],
                'log': ['git', 'log', '--oneline', '-10'],
                'log --oneline': ['git', 'log', '--oneline', '-10'],
                'log -5': ['git', 'log', '--oneline', '-5'],
                'branch': ['git', 'branch', '-a'],
                'branch -a': ['git', 'branch', '-a'],
                'remote -v': ['git', 'remote', '-v'],
                'show': ['git', 'show', '--stat'],
                'status -s': ['git', 'status', '-s'],
            },
            'ls': {
                'ls': ['ls'],
                'ls -la': ['ls', '-la'],
                'ls -l': ['ls', '-l'],
                'ls -R': ['ls', '-R'],
            },
            'find': {
                'find . -name': ['find', '.', '-name'],
                'find . -type f': ['find', '.', '-type', 'f'],
                'find . -type d': ['find', '.', '-type', 'd'],
            },
            'cat': {'cat': ['cat']},
            'pwd': {'pwd': ['pwd']},
            'head': {'head': ['head'], 'head -n': ['head', '-n']},
            'tail': {'tail': ['tail'], 'tail -n': ['tail', '-n']},
            'wc': {'wc -l': ['wc', '-l'], 'wc -w': ['wc', '-w']},
            'file': {'file': ['file']},
            'which': {'which': ['which']},
            'env': {'env': ['env']},
        }

        BLOCKED_PATTERNS = [
            r'rm?\b', r'del\b', r'mkfs\b', r'dd\b',
            r'sudo\b', r'su\b', r'chmod\b', r'chown\b',
            r'>', r'>>', r'eval', r'exec', r'source',
            r'&&', r'\\|\\|', r';', r'`',
            r'wget\b', r'curl\b', r'nc\b', r'bash\b',
        ]

        cmd_original = command.strip()

        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, cmd_original, re.IGNORECASE):
                raise PermissionError(f'禁止执行: 包含危险模式 {pattern}')

        for base, subcmds in SAFE_COMMANDS.items():
            for key, cmd_list in subcmds.items():
                if cmd_original.startswith(key):
                    try:
                        result = subprocess.run(
                            cmd_list,
                            capture_output=True,
                            text=True,
                            timeout=15,
                            cwd=os.getcwd()
                        )
                        return {
                            'exit_code': result.returncode,
                            'output': result.stdout + result.stderr,
                            'fallback': True,
                            'mode': 'safe_only'
                        }
                    except subprocess.TimeoutExpired:
                        return {'exit_code': 124, 'output': '命令超时', 'fallback': True}
                    except Exception as e:
                        return {'exit_code': 1, 'output': str(e), 'fallback': True}

        raise RuntimeError(f'Docker不可用，该命令不允许在降级模式执行。允许命令: git status/diff/log/branch, ls, find . -name, cat, pwd, head, tail, wc, file, which, env')
```

### 4.2 Docker环境检测

```python
# tools/docker_check.py
def check_docker_available() -> bool:
    """检测Docker是否可用"""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except:
        return False
```

### 4.2 审批工作流

```python
# Rust 前端审批
fn request_approval(action: &SkillAction) -> bool {
    let message = format!(
        "技能 '{}' 尝试执行: {}\n\n命令: {}\n\n是否允许?",
        action.name, action.tool, action.command
    );

    // 显示确认对话框
    dialog::confirm(message)
}
```

---

## 5. 记忆存储 (MVP: SQLite + FTS5)

### 5.1 MVP阶段：SQLite + FTS5

```python
# memory/sqlite_store.py
import sqlite3
import json
import re
from datetime import datetime

class SQLiteMemoryStore:
    """MVP记忆存储：SQLite + FTS5全文索引"""

    def __init__(self, db_path: str = "~/.evolver/memories.db"):
        self.db_path = db_path
        with sqlite3.connect(db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'success',
                    metadata TEXT,
                    created_at INTEGER,
                    expires_at INTEGER
                )
            """)
            db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(content, content=memories, content_rowid=rowid)
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content) 
                    VALUES (new.rowid, new.content);
                END
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content) 
                    VALUES('delete', old.rowid, old.content);
                END
            """)

    def add_memory(self, content: str, metadata: dict = None, 
                   memory_type: str = "success", ttl_days: int = 30):
        """添加记忆"""
        import uuid
        now = int(datetime.now().timestamp())
        expires = now + (ttl_days * 86400) if ttl_days else None
        
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), content, memory_type, 
                 json.dumps(metadata or {}), now, expires)
            )

    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        """混合搜索：FTS5 + 关键词匹配"""
        results = []
        
        with sqlite3.connect(self.db_path) as db:
            # FTS5全文检索
            cursor = db.execute("""
                SELECT m.id, m.content, m.memory_type, m.metadata, m.created_at
                FROM memories m
                JOIN memories_fts f ON m.rowid = f.rowid
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, top_k))
            results = self._fetch_results(cursor)
            
            # 关键词备选搜索
            if len(results) < top_k:
                keywords = query.lower().split()
                cursor = db.execute("""
                    SELECT id, content, memory_type, metadata, created_at
                    FROM memories
                    WHERE content LIKE ?
                    LIMIT ?
                """, (f"%{'%'.join(keywords[:3])}%", top_k))
                results = self._deduplicate(results, self._fetch_results(cursor))
        
        return results[:top_k]

    def _fetch_results(self, cursor) -> list:
        return [
            {"id": r[0], "content": r[1], "type": r[2], 
             "metadata": json.loads(r[3]), "created_at": r[4]}
            for r in cursor.fetchall()
        ]

    def _deduplicate(self, existing: list, new: list) -> list:
        ids = {r["id"] for r in existing}
        return existing + [r for r in new if r["id"] not in ids]

    def cleanup_expired(self):
        """清理过期记忆"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM memories WHERE expires_at < ?", (now,))
```

### 5.2 Phase3：轻量向量库（usearch）

```python
# memory/vector_store.py
class USearchMemoryStore:
    """Phase3轻量向量库"""
    
    def __init__(self):
        try:
            import usearch
            self.index = usearch.Index(ndim=128, metric="cos")
            self.initialized = True
        except ImportError:
            self.initialized = False

    def add(self, content: str, embedding: list):
        if self.initialized:
            self.index.add(np.array(embedding))

    def search(self, query: str, top_k: int = 5) -> list:
        if not self.initialized:
            return []
        # ...
```
            {"content": doc, "metadata": meta}
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ]

    def _get_collection(self, memory_type: str):
        return {
            "success": self.memories,
            "failure": self.memories,
            "preference": self.preferences,
            "skill": self.skills,
        }.get(memory_type, self.memories)
```

### 5.2 索引策略

```python
# MVP 阶段: 混合搜索
class HybridSearch:
    """向量 + 关键词混合搜索"""

    def search(self, query: str) -> list[dict]:
        # 1. 向量检索
        vector_results = self.vector_store.recall(query)

        # 2. 关键词匹配 (备用)
        if not vector_results:
            keyword_results = self._keyword_match(query)

        # 3. 排序合并
        return self._rank_results(vector_results, keyword_results)
```

---

## 6. 敏感数据过滤 (安全强化版)

### 6.1 多层过滤 + 加密 + 审计

```python
# memory/privacy_filter.py
import json
import re
import hashlib
from datetime import datetime
from cryptography.fernet import Fernet

class PrivacyFilter:
    """敏感数据过滤器 - 强化版"""

    BUILTIN_PATTERNS = [
        (r"api[_-]?key[=:]?\s*[\"']?[\w-]+[\"']?", "[API_KEY]"),
        (r"password[=:]?\s*[\"'][^ \"']+[\"']?", "[PASSWORD]"),
        (r"token[=:]?\s*[\"']?[\w-]+[\"']?", "[TOKEN]"),
        (r"sk[-]?[\w]{20,}", "[SECRET_KEY]"),
        (r"Bearer\s+[\w-]+", "Bearer [TOKEN]"),
        (r"ghp_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),
    ]

    def __init__(self, encryption_key: str = None):
        self.custom_patterns: list[tuple[str, str]] = []
        self.encryption_key = encryption_key
        self.fernet = Fernet(encryption_key.encode()) if encryption_key else None
        self.audit_log_path = "~/.evolver/privacy_audit.log"

    def add_pattern(self, pattern: str, replacement: str = "[FILTERED]"):
        self.custom_patterns.append((pattern, replacement))

    def sanitize(self, text: str) -> str:
        result = text
        for pattern, replacement in self.BUILTIN_PATTERNS + self.custom_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def sanitize_log(self, text: str) -> str:
        """日志专用过滤"""
        return self.sanitize(text)

    def encrypt_save(self, data: dict) -> bytes:
        """AES-256加密存储"""
        if self.fernet:
            serialized = json.dumps(data)
            return self.fernet.encrypt(serialized.encode())
        return json.dumps(data).encode()

    def decrypt_load(self, data: bytes) -> dict:
        """解密加载"""
        if self.fernet:
            return json.loads(self.fernet.decrypt(data).decode())
        return json.loads(data)

    def log_action(self, action: str, details: dict):
        """数据操作审计"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        }
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def delete_data(self, data_id: str):
        """安全删除数据"""
        self.log_action("delete_data", {"data_id": data_id, "method": "secure_delete"})
        # 实际删除逻辑
```

### 6.2 配置

```yaml
# config.yaml
privacy:
  filter_enabled: true
  encrypt_memories: false  # 可选加密
  
  patterns:
    - pattern: "MY_SECRET=.*"
      replace: "[MY_SECRET]"
    - pattern: "DB_PASSWORD=.*"
      replace: "[DB_PASSWORD]"
```

---

## 7. 内存管理

### 7.1 前端清理

```typescript
// React 组件卸载时清理
useEffect(() => {
  return () => {
    // 清理事件监听
    ipc.removeListener("tool_progress", handleProgress);
    ipc.removeListener("agent_error", handleError);
    
    // 清理定时器
    clearInterval(heartbeatTimer);
    clearTimeout(timeoutTimer);
    
    // 释放大对象
    setResponseChunks(null);
  };
}, []);
```

### 7.2 后端内存监控

```python
# 定期清理
class MemoryMonitor:
    """内存监控"""

    def __init__(self, max_memory_mb: int = 512):
        self.max_memory = max_memory_mb * 1024 * 1024

    def check(self):
        import psutil
        process = psutil.Process()
        memory = process.memory_info().rss

        if memory > self.max_memory:
            # 触发 GC
            import gc
            gc.collect()

            # 压缩上下文
            for agent in self._sessions.values():
                agent.compress_context()
```

---

## 8. 数据流

### 8.1 消息流程

```
用户输入 (React UI)
   ↓
Tauri Command (invoke)
   ↓
IPC → JSON-RPC (stdin)
   ↓
AgentManager.chat()
   ├─ 检索记忆 (向量)
   ├─ 检索技能 (匹配)
   ├─ 构建提示词
   ├─ Provider 适配器
   ├─ LLM 调用
   └─ 执行工具 (沙箱)
   ↓
IPC ← JSON-RPC (stdout)
   ↓
React 状态更新
   ↓
渲染结果
```

### 8.2 主动推送

```
Python 执行工具
   ↓
emit("tool_progress", {...})
   ↓
IPC → JSON-RPC (stdout)
   ↓
Tauri Event
   ↓
React onToolProgress
   ↓
更新 UI
```

---

## 9. 核心接口

### 9.1 AgentManager 接口

```python
class AgentManager:
    def chat(self, session_id: str, message: str) -> ChatResult:
        """处理对话"""

    def create_session(self, config: dict = None) -> str:
        """创建新会话"""

    def interrupt(self, session_id: str, message: str = None):
        """中断会话"""

    def save_skill(self, skill: dict) -> bool:
        """保存技能"""

    def recall_memory(self, query: str, top_k: int = 5) -> list[dict]:
        """检索记忆"""
```

### 9.2 Provider 接口

```python
class Provider:
    def chat(self, messages: list[dict], tools: list[dict]) -> Response:
        """发送消息"""

    def format_tools(self, tools: list[dict]) -> list[dict]:
        """格式化工具"""

    def parse_tool_calls(self, response: Response) -> list[dict]:
        """解析工具调用"""
```

---

## 10. 技术栈

### 10.1 后端 (Python)

```toml
[project]
dependencies = [
    "openai>=1.0.0",
    "anthropic>=0.18.0",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
    "prompt-toolkit>=3.0.0",
    "sqlite-utils>=3.35.0",
    "pyyaml>=6.0.0",
    "python-dotenv>=1.0.0",
    "msgpack>=1.0.0",            # 会话序列化
    "usearch>=0.6.0",           # Phase3轻量向量库
    "cryptography>=41.0.0",     # AES-256加密
    "tiktoken>=0.5.0",        # Token 计数
    "docker>=6.0.0",            # Docker沙箱
]
```

### 10.2 前端 (Tauri + React)

```toml
[dependencies]
tauri = { version = "2", features = ["devtools"] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[dependencies.react]
react = "^18"
react-dom = "^18"
```

### 10.3 构建

```bash
# 开发
cargo tauri dev

# 构建
cargo tauri build

# Python 打包
uv build --wheel
uv build --sdist
```

### 10.4 工程维护

```bash
# 每周依赖漏洞扫描
pip-audit

# YAML配置校验
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 运行单元测试
pytest tests/ -v
```

---

## 11. 配置

### 11.1 用户配置

```yaml
# ~/.evolver/config.yaml
model:
  provider: "openrouter"
  default: "anthropic/claude-sonnet-4-20250514"
  fallback:
    - "openai/gpt-4o"

tools:
  enabled:
    - "file"
    - "bash"
    - "search"
    - "memory"
  disabled: []

memory:
  enabled: true
  auto_save: true
  vector_db: "~/.evolver/vector_db"  # 向量库路径

privacy:
  filter_enabled: true
  encrypt_memories: false

ui:
  theme: "default"
  colorful: true

evolution:
  enabled: true
  auto_learn: false  # 禁止自动保存任何记忆
  auto_create_skills: false
  confirm_before_save: true  # 所有学习必须弹窗确认
  audit_log: true  # 开启进化审计日志
  max_confidence_auto_apply: 0.95  # 仅>95%置信度可自动应用
  skill_approval_required: true
```

### 11.2 环境变量

```bash
# API Keys
OPENROUTER_API_KEY=sk-...
OPENAI_API_KEY=sk-...

# 配置
EVOLVER_HOME=~/.evolver
EVOLVER_MODEL=claude-sonnet-4-20250514
EVOLVER_MAX_ITERATIONS=90
```

---

## 12. 里程碑

### Phase 1: MVP
- [ ] JSON-RPC IPC 通信
- [ ] AgentManager 单例
- [ ] 基础文件工具
- [ ] CLI 界面
- [ ] 单模型支持

### Phase 2: 扩展
- [ ] Provider 适配层
- [ ] 向量数据库集成
- [ ] 桌面 GUI
- [ ] 多模型路由
- [ ] 记忆系统

### Phase 3: 进化
- [ ] 技能沙箱
- [ ] 敏感数据过滤
- [ ] 自我学习
- [ ] MCP 集成

### Phase 4: 优化
- [ ] 内存监控
- [ ] 加密存储
- [ ] 性能优化

---

## 12. 最终验证清单

- [ ] 所有命令执行通过Docker沙箱隔离
- [ ] 已删除所有pickle序列化代码
- [ ] 已关闭全自动进化，所有学习需人工确认
- [ ] 仅保留Claude和GPT两个模型
- [ ] 已实现三重迭代限制+全局中断
- [ ] 所有高危操作需弹窗审批
- [ ] 敏感数据已过滤+本地加密
- [ ] 已开启进化审计日志

---

版本: 0.2
日期: 2026-04-14