import os
import sys
import uuid
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from .run_agent import AIAgent
from .agent_profiles import get_agent_profile, list_agent_profiles
from .session_store import SessionStore
from ..memory.sqlite_store import SQLiteMemoryStore
from ..memory.vector_store import VectorStore
from ..memory.hybrid_search import HybridSearch
from ..memory.memory_layer import MemoryLayer
from ..memory.privacy_filter import PrivacyFilter
from ..skills.skill_manager import SkillManager
from ..mcp.client import MCPClient
from ..mcp.server import MCPServer
from ..tools.mcp_tools import MCPTools
from ..config.loader import ConfigLoader
from ..runtime_env import effective_http_host

logger = logging.getLogger(__name__)

_EVOLVER_PROXY_ENV_KEYS = ('EVOLVER_PROXY_TYPE', 'EVOLVER_API_BASE', 'EVOLVER_API_KEY', 'EVOLVER_MAIN_MODEL')


def _sync_evolver_proxy_env_from_provider(provider: str, pdata: Dict) -> None:
    """让进程内 EVOLVER_* 与磁盘上的供应商块一致，避免「验证连接」曾写入的 endpoint 长期覆盖后续路由。"""
    os.environ['EVOLVER_PROXY_TYPE'] = (provider or 'openai').strip().lower()
    if pdata.get('endpoint'):
        os.environ['EVOLVER_API_BASE'] = str(pdata['endpoint']).strip()
    else:
        os.environ.pop('EVOLVER_API_BASE', None)
    if pdata.get('api_key'):
        os.environ['EVOLVER_API_KEY'] = str(pdata['api_key']).strip()
    else:
        os.environ.pop('EVOLVER_API_KEY', None)
    if pdata.get('model_name'):
        os.environ['EVOLVER_MAIN_MODEL'] = str(pdata['model_name']).strip()
    else:
        os.environ.pop('EVOLVER_MAIN_MODEL', None)


def _local_fs_root_path() -> Optional[Path]:
    """若设置 EVOLVER_LOCAL_FS_ROOT，则本地文件类 RPC 仅能访问该目录下内容。"""
    raw = os.environ.get('EVOLVER_LOCAL_FS_ROOT', '').strip()
    if not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError:
        return None


def _reject_bad_path_string(path_str: str) -> Optional[str]:
    if not path_str or not isinstance(path_str, str):
        return '路径无效'
    if len(path_str) > 8192:
        return '路径过长'
    if '\x00' in path_str:
        return '路径包含非法字符'
    return None


def _ensure_under_optional_root(real: Path) -> Optional[str]:
    root = _local_fs_root_path()
    if root is None:
        return None
    try:
        real.relative_to(root)
    except ValueError:
        return '路径不在 EVOLVER_LOCAL_FS_ROOT 允许的范围内'
    return None


def _resolve_local_dir(path_str: str) -> Tuple[Optional[Path], Optional[str]]:
    """用于 list_local_files：目标必须是已存在目录。"""
    bad = _reject_bad_path_string(path_str)
    if bad:
        return None, bad
    try:
        p = Path(path_str).expanduser()
        if not path_str.strip():
            p = Path.cwd()
        real = p.resolve()
    except (OSError, RuntimeError) as e:
        return None, f'路径解析失败: {e}'
    if not real.exists() or not real.is_dir():
        return None, '目录不存在或不是文件夹'
    err = _ensure_under_optional_root(real)
    if err:
        return None, err
    return real, None


def _resolve_local_file(path_str: str) -> Tuple[Optional[Path], Optional[str]]:
    """用于 read_local_file：目标必须是已存在文件。"""
    bad = _reject_bad_path_string(path_str)
    if bad:
        return None, bad
    try:
        real = Path(path_str).expanduser().resolve()
    except (OSError, RuntimeError) as e:
        return None, f'路径解析失败: {e}'
    if not real.exists() or not real.is_file():
        return None, '文件不存在或不是普通文件'
    err = _ensure_under_optional_root(real)
    if err:
        return None, err
    return real, None


def _effective_listen_host() -> str:
    """与 evolver.server.HTTP_HOST 同源（runtime_env.effective_http_host），仅做小写便于比较。"""
    return effective_http_host().lower()


def _exec_shell_enabled() -> bool:
    """显式 0/false 关闭；显式 1 开启；未设置时：仅 HTTP 监听本机回环则默认开启（方便本地 python -m evolver.server），否则关闭。"""
    raw = os.environ.get('EVOLVER_ALLOW_EXEC_SHELL', '').strip().lower()
    if raw in ('0', 'false', 'no', 'off'):
        return False
    if raw in ('1', 'true', 'yes', 'on'):
        return True
    host = _effective_listen_host()
    return host in ('127.0.0.1', 'localhost', '::1')


def _agent_ndjson(location: str, message: str, data: dict, hypothesis_id: str = 'H-exec-shell') -> None:
    """历史占位：调试用 NDJSON 已移除，调用方无需改动。"""
    return


class AgentManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
        return cls._instance

    def _init(self):
        self._config = ConfigLoader().load()
        self._memory = SQLiteMemoryStore()
        self._privacy_filter = PrivacyFilter()
        self._skills = SkillManager()
        self._session_store = SessionStore()
        self._sessions: Dict[str, AIAgent] = {}
        self._sessions_lock = threading.Lock()
        self._max_message_length = 20000

        self._vector_store = VectorStore(
            db_path=self._config.get('memory', {}).get('vector_db', '~/.evolver/vector_db')
        )
        self._memory_layer = MemoryLayer(self._memory, self._vector_store)

        self._mcp_client = MCPClient()
        self._mcp_server = MCPServer()
        self._mcp_tools = MCPTools(self._mcp_client)
        self._skills.set_tool_registry(None)
        self._skills.set_tool_registry(self._mcp_tools)
        self._active_project_id = self._config.get('project', {}).get('active_project_id', 'default')
        self._projects: Dict[str, Dict] = {
            self._active_project_id: {
                'project_id': self._active_project_id,
                'name': self._active_project_id,
                'description': 'default project',
                'metadata': {},
            }
        }
        self._self_evolution_history: Dict[str, List[Dict]] = {self._active_project_id: []}
        self._failure_history: Dict[str, List[Dict]] = {self._active_project_id: []}
        self._work_items: Dict[str, List[Dict]] = {self._active_project_id: []}

        mcp_config = self._config.get('mcp', {})
        if mcp_config.get('enabled') and mcp_config.get('servers'):
            for server_id, server_conf in mcp_config['servers'].items():
                if server_conf.get('enabled'):
                    self._mcp_tools.connect_server(
                        server_id,
                        server_conf.get('command', ''),
                        server_conf.get('args', []),
                        server_conf.get('env')
                    )

        logger.info('AgentManager initialized with Skill/Memory/MCP')

    def _ensure_project_state(self, project_id: Optional[str] = None) -> str:
        pid = project_id or self._active_project_id or 'default'
        if pid not in self._projects:
            self._projects[pid] = {
                'project_id': pid,
                'name': pid,
                'description': '',
                'metadata': {},
            }
        self._self_evolution_history.setdefault(pid, [])
        self._failure_history.setdefault(pid, [])
        self._work_items.setdefault(pid, [])
        return pid

    def create_project(self, name: str, description: str = '', metadata: Dict = None) -> Dict:
        project_id = (name or '').strip()
        if not project_id:
            return {'success': False, 'error': 'invalid project name'}
        self._ensure_project_state(project_id)
        self._projects[project_id] = {
            'project_id': project_id,
            'name': project_id,
            'description': description or '',
            'metadata': metadata or {},
        }
        return {'success': True, 'project_id': project_id}

    def list_projects(self) -> List[Dict]:
        return list(self._projects.values())

    def set_active_project(self, project_id: str) -> Dict:
        pid = self._ensure_project_state(project_id)
        self._active_project_id = pid
        return {'success': True, 'active_project_id': pid}

    def get_active_project(self) -> Dict:
        pid = self._ensure_project_state(self._active_project_id)
        return {'project_id': pid, 'project': self._projects.get(pid, {})}

    def chat(self, session_id: str, message: str, agent_id: str = "default", model: str = None, project_id: str = None) -> Dict:
        if not isinstance(message, str):
            return {'final_response': '错误: message 必须是字符串', 'messages': []}
        if len(message) > self._max_message_length:
            return {'final_response': f'错误: message 过长，最�?{self._max_message_length} 字符', 'messages': []}

        project_id = self._ensure_project_state(project_id)
        with self._sessions_lock:
            agent = self._sessions.get(session_id)
            if not agent:
                agent = self._load_or_create_session(session_id)

        try:
            active_agent = get_agent_profile(agent_id)
            filtered_message = self._privacy_filter.sanitize_llm_input(message)

            search_mode = self._config.get('memory', {}).get('search_mode', 'hybrid')
            context = self._memory_layer.recall(filtered_message, mode=search_mode)
            if not isinstance(context, dict):
                context = {}
            if model:
                agent.model = model
                context["requested_model"] = model
            context["active_agent"] = active_agent

            result = agent.run_conversation(
                filtered_message,
                context=context,
                skills=self._skills.get_relevant(
                    filtered_message,
                    agent_focus=active_agent.get("focus", "")
                ),
            )

            if result.get('final_response'):
                result['final_response'] = self._privacy_filter.sanitize_llm_output(result['final_response'])
            else:
                self._failure_history[project_id].append({
                    'project_id': project_id,
                    'session_id': session_id,
                    'agent_id': agent_id,
                    'model': model,
                    'message': filtered_message,
                    'reason': 'empty_final_response',
                    'timestamp': time.time(),
                })

            with self._sessions_lock:
                if session_id in self._sessions:
                    self._session_store.save(session_id, agent)

            return result
        except Exception as e:
            logger.error(f'Chat error: {e}')
            self._failure_history[project_id].append({
                'project_id': project_id,
                'session_id': session_id,
                'agent_id': agent_id,
                'model': model,
                'message': filtered_message if 'filtered_message' in locals() else message,
                'reason': str(e),
                'timestamp': time.time(),
            })
            return {'final_response': f'错误: {str(e)}', 'messages': []}

    def list_agents(self) -> List[Dict]:
        return list_agent_profiles()

    def interrupt(self, session_id: str, message: str = None):
        with self._sessions_lock:
            agent = self._sessions.get(session_id)
            if agent:
                agent.interrupt(message)
                logger.info(f'Session {session_id} interrupted')

    def _load_or_create_session(self, session_id: str) -> AIAgent:
        saved = self._session_store.load(session_id)
        if saved:
            logger.info(f'Loaded session {session_id} from disk')
            agent = AIAgent(model=saved.get('model'))
            agent.messages = saved.get('messages', [])
            agent.context = saved.get('context', {})
            agent.iteration_count = saved.get('iteration_count', 0)
            agent.operation_history = saved.get('operation_history', [])
            agent.token_usage = saved.get('token_usage', 0)
            agent.max_context_size = saved.get('max_context_size', 10)
            agent.max_iterations = saved.get('max_iterations', 5)
            agent.max_same_file_operations = saved.get('max_same_file_operations', 3)
            agent.max_same_command_executions = saved.get('max_same_command_executions', 2)
            agent.max_memory_usage = saved.get('max_memory_usage', 512)
            agent.current_memory_usage = 0
        else:
            default_model = self._config.get('model', {}).get('default', 'claude-sonnet-4-20250514')
            agent = AIAgent(model=default_model)
            logger.info(f'Created new session {session_id}')

        self._sessions[session_id] = agent
        return agent

    def _create_session(self, session_id: str) -> AIAgent:
        default_model = self._config.get('model', {}).get('default', 'claude-sonnet-4-20250514')
        agent = AIAgent(model=default_model)
        if 'max_iterations' in self._config.get('model', {}):
            agent.max_iterations = self._config['model']['max_iterations']
        if 'max_memory_usage' in self._config:
            agent.max_memory_usage = self._config['max_memory_usage']
        self._sessions[session_id] = agent
        self._session_store.save(session_id, agent)
        return agent

    def create_session(self, config: Optional[Dict] = None) -> str:
        session_id = str(uuid.uuid4())
        with self._sessions_lock:
            self._create_session(session_id)
        return session_id

    def delete_session(self, session_id: str):
        with self._sessions_lock:
            self._sessions.pop(session_id, None)
        self._session_store.delete(session_id)
        logger.info(f'Session {session_id} deleted')

    def list_sessions(self) -> List[Dict]:
        return self._session_store.list_sessions()

    def get_session_history(self, session_id: str) -> Dict:
        """获取会话历史记录"""
        try:
            saved = self._session_store.load(session_id)
            if saved:
                return {
                    'session_id': session_id,
                    'model': saved.get('model'),
                    'messages': saved.get('messages', []),
                    'created_at': saved.get('created_at', int(time.time())),
                    'updated_at': saved.get('updated_at', int(time.time()))
                }
            return {'session_id': session_id, 'messages': []}
        except Exception as e:
            logger.error(f'Failed to get session history: {e}')
            return {'session_id': session_id, 'messages': []}

    def list_skills(self) -> List:
        return self._skills.list_skills()

    def save_skill(self, skill: Dict) -> Dict:
        return self._skills.save_skill(skill)

    def approve_skill(self, skill_id: str) -> Dict:
        return self._skills.approve_skill(skill_id)

    def reject_skill(self, skill_id: str, reason: str = "") -> Dict:
        return self._skills.reject_skill(skill_id, reason)

    def get_pending_approvals(self) -> List[Dict]:
        return self._skills.get_pending_approvals()

    def list_pending_approvals(self) -> List[Dict]:
        return self._skills.get_pending_approvals()

    def execute_skill(self, skill_name: str, context: Dict = None) -> Dict:
        return self._skills.execute_skill(skill_name, context or {})

    def list_projects_workflow(self) -> Dict:
        return {
            'active_project_id': self._active_project_id,
            'projects': self.list_projects(),
            'work_items': self.list_work_items(scope_id=self._active_project_id),
            'failures': self.get_recent_failures(scope_id=self._active_project_id),
        }

    def recall_memory(self, query: str, top_k: int = 5) -> List:
        return self._memory.recall(query, top_k)

    def save_memory(self, content: str, memory_type: str = "success", metadata: Dict = None, scope_type: str = "project", scope_id: str = None) -> Dict:
        sid = scope_id or self._active_project_id
        try:
            result = self._memory_layer.save(content, memory_type, metadata, scope_type=scope_type, scope_id=sid)
            return {'success': True, 'scope_id': sid}
        except Exception as e:
            logger.error(f'Save memory error: {e}')
            return {'success': False, 'error': str(e)}

    def search_memory(self, query: str, top_k: int = 5, mode: str = "hybrid", scope_type: str = "project", scope_id: str = None) -> Dict:
        sid = scope_id or self._active_project_id
        return self._memory_layer.recall(query, top_k, mode, scope_type=scope_type, scope_id=sid)

    def self_evolve(self, goal: str, signals: Dict = None, scope_type: str = "project", scope_id: str = None) -> Dict:
        signals = signals or {}
        scope_id = scope_id or self._active_project_id
        scope_id = self._ensure_project_state(scope_id)
        goal_lower = (goal or "").lower()
        recent_failures = self._failure_history[scope_id][-10:]

        improvement_candidates = []

        if any(keyword in goal_lower for keyword in ["skill", "技能", "审批"]):
            improvement_candidates.append({
                "area": "skills",
                "action": "strengthen_skill_approval_and_discovery",
                "priority": 5,
                "reason": "技能系统是中期目标重点，适合先优化创建、审批、发现流程"
            })

        if any(keyword in goal_lower for keyword in ["memory", "记忆", "搜索", "检索"]):
            improvement_candidates.append({
                "area": "memory",
                "action": "upgrade_memory_search_pipeline",
                "priority": 5,
                "reason": "记忆系统需要从 SQLite 升级到向量混合检索，以提升召回质量"
            })

        if any(keyword in goal_lower for keyword in ["mcp", "protocol", "context"]):
            improvement_candidates.append({
                "area": "mcp",
                "action": "expand_mcp_registry_and_health_checks",
                "priority": 4,
                "reason": "MCP 集成需要完善连接、列举、调用与健康检查能力"
            })

        if recent_failures:
            improvement_candidates.insert(0, {
                "area": "feedback",
                "action": "analyze_recent_failures_and_close_the_loop",
                "priority": 5,
                "reason": f"最近捕获到 {len(recent_failures)} 条失败记录，应优先将其转为改进项"
            })

        if not improvement_candidates:
            improvement_candidates.append({
                "area": "core",
                "action": "capture_feedback_and_generate_next_iteration",
                "priority": 3,
                "reason": "先将用户反馈沉淀为下一轮优化计划"
            })

        snapshot = {
            "goal": goal,
            "signals": signals,
            "recommendations": improvement_candidates,
            "timestamp": time.time()
        }
        self._self_evolution_history[scope_id].append(snapshot)
        for rec in improvement_candidates:
            self._work_items[scope_id].append({
                "id": str(uuid.uuid4()),
                "title": f"[{rec['area']}] {rec['action']}",
                "area": rec["area"],
                "action": rec["action"],
                "priority": rec["priority"],
                "reason": rec["reason"],
                "status": "pending",
                "created_at": snapshot["timestamp"],
                "source_goal": goal,
            })
        return {
            "success": True,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "goal": goal,
            "recommendations": improvement_candidates,
            "work_items": self._work_items[scope_id][-len(improvement_candidates):],
            "history_size": len(self._self_evolution_history[scope_id]),
            "recent_failures": recent_failures,
        }

    def get_self_evolution_history(self, scope_type: str = "project", scope_id: str = None) -> List[Dict]:
        sid = self._ensure_project_state(scope_id)
        return list(self._self_evolution_history[sid])

    def get_recent_failures(self, scope_type: str = "project", scope_id: str = None, limit: int = 20) -> List[Dict]:
        sid = self._ensure_project_state(scope_id)
        return self._failure_history[sid][-limit:]

    def list_work_items(self, scope_type: str = "project", scope_id: str = None, status: str = None) -> List[Dict]:
        sid = self._ensure_project_state(scope_id)
        items = list(self._work_items[sid])
        if status:
            items = [item for item in items if item.get("status") == status]
        return items

    def update_work_item(self, item_id: str, status: str) -> Dict:
        allowed = {"pending", "in_progress", "done", "cancelled"}
        if status not in allowed:
            return {"success": False, "error": "invalid status"}
        for project_id, items in self._work_items.items():
            for item in items:
                if item.get("id") == item_id:
                    item["status"] = status
                    item["updated_at"] = time.time()
                    return {"success": True, "work_item": item, "scope_id": project_id}
        return {"success": False, "error": "work item not found"}

    def record_failure(self, scope_type: str, scope_id: str, payload: Dict) -> Dict:
        sid = self._ensure_project_state(scope_id)
        item = {
            'id': str(uuid.uuid4()),
            'scope_type': scope_type,
            'scope_id': sid,
            **(payload or {}),
            'timestamp': time.time(),
        }
        self._failure_history[sid].append(item)
        return {'success': True, 'failure': item}

    def list_mcp_servers(self) -> List[Dict]:
        return self._mcp_tools.list_servers()

    def connect_mcp_server(self, server_id: str, command: str, args: List[str] = None, env: Dict = None) -> Dict:
        return self._mcp_tools.connect_server(server_id, command, args, env)

    def disconnect_mcp_server(self, server_id: str) -> bool:
        return self._mcp_tools.disconnect_server(server_id)

    def list_mcp_tools(self) -> List[Dict]:
        return self._mcp_tools.list_mcp_tools()

    def call_mcp_tool(self, tool_name: str, parameters: Dict = None) -> Dict:
        return self._mcp_tools.execute_mcp_tool(tool_name, parameters or {})

    def update_api_config(self, config: Dict) -> Dict:
        """更新API配置"""
        try:
            from ..config.loader import ConfigLoader
            loader = ConfigLoader()
            current_config = loader.load()
            
            # 更新API配置
            if 'api' not in current_config:
                current_config['api'] = {}
            
            if 'providers' not in current_config['api']:
                current_config['api']['providers'] = {}
            
            # 保存API配置
            for provider, provider_config in config.items():
                current_config['api']['providers'][provider] = provider_config

            keys = [k for k in config.keys() if isinstance(config.get(k), dict)]
            if keys:
                preferred = keys[0]
                current_config['api']['preferred_provider'] = preferred
                pdata = current_config['api']['providers'].get(preferred, {})
                _sync_evolver_proxy_env_from_provider(preferred, pdata)
                logger.info('API preferred provider set to %r (matches UI save)', preferred)

            loader.save(current_config)
            logger.info(f'API config updated: {list(config.keys())}')
            return {'success': True, 'message': 'API配置已更新'}
        except Exception as e:
            logger.error(f'Failed to update API config: {e}')
            return {'success': False, 'error': str(e)}

    def validate_api_config(self, config: Dict = None) -> Dict:
        """验证API配置"""
        from ..providers.router import ModelRouter
        saved_env: Optional[Dict[str, Optional[str]]] = None
        try:
            if config:
                saved_env = {k: os.environ.get(k) for k in _EVOLVER_PROXY_ENV_KEYS}
                keys = [k for k, v in config.items() if isinstance(v, dict)]
                if keys:
                    pdata = config[keys[0]]
                    if isinstance(pdata, dict):
                        _sync_evolver_proxy_env_from_provider(keys[0], pdata)
                router = ModelRouter()
            else:
                router = ModelRouter()

            result = router.validate_api_config()
            logger.info(f'API config validation result: {result}')
            return result
        except Exception as e:
            logger.error(f'Failed to validate API config: {e}')
            return {
                'valid': False,
                'errors': [f'验证过程出错: {str(e)}'],
                'warnings': []
            }
        finally:
            if saved_env is not None:
                for k in _EVOLVER_PROXY_ENV_KEYS:
                    v = saved_env.get(k)
                    if v is not None:
                        os.environ[k] = v
                    else:
                        os.environ.pop(k, None)

    def list_local_files(self, path: str = "") -> List[Dict]:
        """列出本地文件和目录"""
        try:
            import stat

            effective = (path or "").strip() or os.getcwd()
            dir_path, err = _resolve_local_dir(effective)
            if err or dir_path is None:
                logger.warning('list_local_files rejected: %s', err)
                return []

            path_str = str(dir_path)
            files = []
            for item in os.listdir(path_str):
                item_path = os.path.join(path_str, item)
                try:
                    item_stat = os.stat(item_path)
                    is_directory = stat.S_ISDIR(item_stat.st_mode)
                    files.append({
                        'name': item,
                        'path': item_path,
                        'isDirectory': is_directory
                    })
                except Exception as e:
                    logger.warning(f'Error accessing {item_path}: {e}')

            files.sort(key=lambda x: (not x['isDirectory'], x['name']))
            logger.info(f'Listed {len(files)} items in {path_str}')
            return files
        except Exception as e:
            logger.error(f'Failed to list local files: {e}')
            return []

    def select_directory(self) -> Dict:
        """弹出原生文件选择对话框，让用户选择目录"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            # 创建隐藏的Tk窗口
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # 弹出目录选择对话框
            selected_path = filedialog.askdirectory(title="选择目录")
            
            # 销毁窗口
            root.destroy()
            
            if selected_path:
                logger.info(f'Directory selected: {selected_path}')
                return {'path': selected_path, 'cancelled': False}
            else:
                logger.info('Directory selection cancelled')
                return {'path': None, 'cancelled': True}
        except Exception as e:
            logger.error(f'Failed to select directory: {e}')
            return {'path': None, 'cancelled': True}

    def read_local_file(self, path: str) -> Dict:
        """读取本地文件内容"""
        try:
            max_size = 10 * 1024 * 1024  # 10MB
            fp, err = _resolve_local_file(path)
            if err or fp is None:
                return {'content': f'读取被拒绝: {err or "unknown"}'}
            if fp.stat().st_size > max_size:
                return {'content': f'文件过大，超过 {max_size / 1024 / 1024}MB 限制'}

            with fp.open('r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            logger.info(f'Read file: {fp}')
            return {'content': content}
        except Exception as e:
            logger.error(f'Failed to read local file: {e}')
            return {'content': f'读取文件失败: {str(e)}'}

    def exec_shell(self, command: str) -> Dict:
        """在本地执行一条 shell 命令；工作目录固定为当前进程 cwd。是否允许由 _exec_shell_enabled() 决定。"""
        import subprocess

        eh = _effective_listen_host()
        try:
            if not _exec_shell_enabled():
                _agent_ndjson(
                    'manager.py:exec_shell',
                    'blocked',
                    {
                        'effective_listen_host': eh,
                        'env_http': os.environ.get('EVOLVER_HTTP_HOST', ''),
                        'env_allow': os.environ.get('EVOLVER_ALLOW_EXEC_SHELL', ''),
                    },
                )
                return {
                    'ok': False,
                    'error': (
                        f'exec_shell 已禁用：解析到的监听地址为 {eh!r}（与 evolver.runtime_env.effective_http_host 一致）。'
                        '若仅本机使用请设 EVOLVER_HTTP_HOST=127.0.0.1；'
                        '若需监听 0.0.0.0，请另设 EVOLVER_ALLOW_EXEC_SHELL=1。'
                        '完全关闭本机 shell 可设 EVOLVER_ALLOW_EXEC_SHELL=0。'
                    ),
                    'diagnostic': {'effective_listen_host': eh, 'raw_http_host': os.environ.get('EVOLVER_HTTP_HOST', '')},
                }
            if not command or not str(command).strip():
                return {'ok': False, 'error': '命令为空'}
            if len(command) > 32768:
                return {'ok': False, 'error': '命令过长'}
            work = os.getcwd()
            proc = subprocess.run(
                command,
                shell=True,
                cwd=work,
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8',
                errors='replace',
            )
            out = (proc.stdout or '')[-8000:]
            err = (proc.stderr or '')[-8000:]
            _agent_ndjson(
                'manager.py:exec_shell',
                'completed',
                {'returncode': proc.returncode, 'cwd': work, 'cmd_len': len(command), 'effective_listen_host': eh},
            )
            return {
                'ok': True,
                'returncode': proc.returncode,
                'stdout': out,
                'stderr': err,
            }
        except subprocess.TimeoutExpired:
            _agent_ndjson('manager.py:exec_shell', 'timeout', {'effective_listen_host': eh})
            return {'ok': False, 'error': '命令超时（>120s）'}
        except Exception as e:
            logger.error(f'exec_shell failed: {e}')
            _agent_ndjson('manager.py:exec_shell', 'exception', {'error': str(e), 'effective_listen_host': eh})
            return {'ok': False, 'error': str(e)}
