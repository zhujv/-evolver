import os
import sqlite3
import time
import json
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

try:
    import msgpack  # type: ignore
except ImportError:  # pragma: no cover
    msgpack = None

SESSION_VERSION = 1


class SessionStore:
    def __init__(self, db_path: str = '~/.evolver/sessions.db'):
        try:
            self.db_path = os.path.expanduser(db_path)
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            # 设置目录权限为0o700，只允许所有者访问
            if os.name != 'nt':  # 只在非Windows系统设置权限
                os.chmod(db_dir, 0o700)
            self._init_db()
            # 设置数据库文件权限为0o600，只允许所有者读写
            if os.name != 'nt' and os.path.exists(self.db_path):  # 只在非Windows系统设置权限
                os.chmod(self.db_path, 0o600)
        except Exception as e:
            # 如果无法创建数据库，使用内存数据库作为备选
            import tempfile
            temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            self.db_path = temp_db.name
            temp_db.close()
            self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    model TEXT,
                    created_at INTEGER,
                    updated_at INTEGER,
                    state BLOB
                )
            ''')
            db.execute('CREATE INDEX IF NOT EXISTS idx_updated ON sessions(updated_at)')
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=NORMAL')

    def save(self, session_id: str, agent: 'AIAgent'):
        # 构建会话状态，只包含必要的属性
        state = {
            '_version': SESSION_VERSION,
            'model': agent.model,
            'messages': agent.messages[:50],  # 限制消息数量，避免数据过大
            'context': agent.context,
            'iteration_count': agent.iteration_count,
            'operation_history': agent.operation_history[:20],  # 限制操作历史数量
            'token_usage': agent.token_usage,
            'max_context_size': agent.max_context_size,
            'max_iterations': agent.max_iterations,
            'max_same_file_operations': agent.max_same_file_operations,
            'max_same_command_executions': agent.max_same_command_executions,
            'max_memory_usage': agent.max_memory_usage,
        }
        
        # 清理会话状态中的敏感数据
        state['context'] = self._sanitize_context(state['context'])
        
        with sqlite3.connect(self.db_path) as db:
            now = int(time.time())
            if msgpack is not None:
                state_blob = msgpack.dumps(state, use_bin_type=True)
            else:
                state_blob = json.dumps(state, ensure_ascii=False).encode("utf-8")
            db.execute(
                'INSERT OR REPLACE INTO sessions (id, model, created_at, updated_at, state) VALUES (?, ?, ?, ?, ?)',
                (session_id, agent.model, now, now, state_blob)
            )
        logger.debug(f'Session {session_id} saved')

    def _sanitize_context(self, context: dict) -> dict:
        """清理上下文中的敏感数据"""
        if not isinstance(context, dict):
            return context
        
        sanitized = {}
        for key, value in context.items():
            if isinstance(value, str):
                # 对可能的敏感数据进行过滤
                if any(keyword in key.lower() for keyword in ['password', 'token', 'api', 'key', 'secret']):
                    sanitized[key] = '[FILTERED]'
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_context(value)
            else:
                sanitized[key] = value
        return sanitized

    def load(self, session_id: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                'SELECT model, state FROM sessions WHERE id = ?',
                (session_id,)
            ).fetchone()
        
        if row:
            model, state_blob = row
            try:
                state = None
                if msgpack is not None:
                    state = msgpack.loads(state_blob, raw=False)
                else:
                    if isinstance(state_blob, (bytes, bytearray)):
                        state = json.loads(state_blob.decode("utf-8", errors="replace"))
                    else:
                        state = json.loads(state_blob)
                version = state.get('_version', 0)
                if version < SESSION_VERSION:
                    state = self._migrate(state, version)
                return {
                    'model': model,
                    'messages': state.get('messages', []),
                    'context': state.get('context', {}),
                    'iteration_count': state.get('iteration_count', 0),
                    'operation_history': state.get('operation_history', []),
                    'token_usage': state.get('token_usage', 0),
                    'max_context_size': state.get('max_context_size', 10),
                    'max_iterations': state.get('max_iterations', 5),
                    'max_same_file_operations': state.get('max_same_file_operations', 3),
                    'max_same_command_executions': state.get('max_same_command_executions', 2),
                    'max_memory_usage': state.get('max_memory_usage', 512),
                }
            except Exception as e:
                logger.error(f'Failed to load session {session_id}: {e}')
        return None

    def _migrate(self, state: Dict, from_version: int) -> Dict:
        if from_version == 0:
            state['iteration_count'] = state.get('iteration_count', 0)
            state['operation_history'] = state.get('operation_history', [])
            state['token_usage'] = state.get('token_usage', 0)
            state['max_context_size'] = state.get('max_context_size', 10)
            state['max_iterations'] = state.get('max_iterations', 5)
            state['max_same_file_operations'] = state.get('max_same_file_operations', 3)
            state['max_same_command_executions'] = state.get('max_same_command_executions', 2)
            state['max_memory_usage'] = state.get('max_memory_usage', 512)
            state['_version'] = SESSION_VERSION
        return state

    def delete(self, session_id: str):
        with sqlite3.connect(self.db_path) as db:
            db.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        logger.debug(f'Session {session_id} deleted')

    def list_sessions(self) -> list:
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                'SELECT id, model, created_at, updated_at FROM sessions ORDER BY updated_at DESC'
            ).fetchall()
        return [
            {'id': r[0], 'model': r[1], 'created_at': r[2], 'updated_at': r[3]}
            for r in rows
        ]

    def cleanup_old(self, max_age_days: int = 30):
        cutoff = int(time.time()) - (max_age_days * 86400)
        with sqlite3.connect(self.db_path) as db:
            db.execute('DELETE FROM sessions WHERE updated_at < ?', (cutoff,))