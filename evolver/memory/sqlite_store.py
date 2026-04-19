"""SQLiteMemoryStore - MVP记忆存储：SQLite + FTS5"""

import sqlite3
import json
import re
from datetime import datetime
import uuid
import os
from .privacy_filter import PrivacyFilter


class SQLiteMemoryStore:
    """MVP记忆存储：SQLite + FTS5全文索引"""

    def __init__(self, db_path: str = "~/.evolver/memories.db"):
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
        self._privacy_filter = PrivacyFilter()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    scope_type TEXT NOT NULL DEFAULT 'project',
                    scope_id TEXT NOT NULL DEFAULT 'default',
                    content TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'success',
                    metadata TEXT,
                    created_at INTEGER,
                    expires_at INTEGER,
                    importance INTEGER DEFAULT 0,
                    tags TEXT
                )
            """)
            self._migrate_db(db)
            db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(content, tags, content=memories, content_rowid=rowid)
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, tags) 
                    VALUES (new.rowid, new.content, new.tags);
                END
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, tags) 
                    VALUES('delete', old.rowid, old.content, old.tags);
                END
            """)

    def _migrate_db(self, db):
        """数据库迁移：添加缺失的列"""
        cursor = db.execute("PRAGMA table_info(memories)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        migrations = [
            ("scope_type", "TEXT NOT NULL DEFAULT 'project'"),
            ("scope_id", "TEXT NOT NULL DEFAULT 'default'"),
            ("importance", "INTEGER DEFAULT 0"),
            ("tags", "TEXT"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing_columns:
                db.execute(f"ALTER TABLE memories ADD COLUMN {col_name} {col_def}")
                db.commit()

    def add_memory(self, content: str, metadata: dict = None,
                   memory_type: str = "success", ttl_days: int = 30,
                   scope_type: str = "project", scope_id: str = "default",
                   importance: int = 0, tags: list = None):
        """添加记忆"""
        now = int(datetime.now().timestamp())
        expires = now + (ttl_days * 86400) if ttl_days else None
        
        # 过滤敏感数据
        sanitized_content = self._privacy_filter.sanitize(content)
        
        # 处理标签
        tags_str = json.dumps(tags) if tags else None
        
        # 记录数据操作
        self._privacy_filter.log_action("add_memory", {
            "memory_id": str(uuid.uuid4()),
            "memory_type": memory_type,
            "content_length": len(content),
            "importance": importance,
            "tags": tags
        })
        
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), scope_type, scope_id, sanitized_content, memory_type,
                 json.dumps(metadata or {}), now, expires, importance, tags_str)
            )
            db.commit()

    def recall(self, query: str, top_k: int = 5, scope_type: str = "project", scope_id: str = "default") -> list:
        """混合搜索：FTS5 + 关键词匹配"""
        results = []
        if not isinstance(query, str) or not query.strip():
            return results
        safe_top_k = max(1, min(int(top_k or 5), 20))
        
        with sqlite3.connect(self.db_path) as db:
            fts_ok = False
            fts_query = self._sanitize_fts_query(query.strip())
            if fts_query:
                try:
                    cursor = db.execute("""
                        SELECT m.id, m.content, m.memory_type, m.metadata, m.created_at, m.importance, m.tags
                        FROM memories m
                        JOIN memories_fts f ON m.rowid = f.rowid
                        WHERE memories_fts MATCH ? AND m.scope_type = ? AND m.scope_id = ?
                        ORDER BY m.importance DESC, rank
                        LIMIT ?
                    """, (fts_query, scope_type, scope_id, safe_top_k))
                    results = self._fetch_results(cursor)
                    fts_ok = True
                except sqlite3.OperationalError:
                    fts_ok = False
            
            if not fts_ok or len(results) < safe_top_k:
                keywords = query.lower().split()
                if keywords:
                    cursor = db.execute("""
                        SELECT id, content, memory_type, metadata, created_at, importance, tags
                        FROM memories
                        WHERE scope_type = ? AND scope_id = ? AND content LIKE ?
                        ORDER BY importance DESC, created_at DESC
                        LIMIT ?
                    """, (scope_type, scope_id, f"%{'%'.join(keywords[:3])}%", safe_top_k))
                    results = self._deduplicate(results, self._fetch_results(cursor))
        
        return results[:safe_top_k]

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        """清理FTS5查询字符串，移除特殊字符"""
        tokens = re.findall(r'[a-zA-Z0-9\u4e00-\u9fff]+', query)
        if not tokens:
            return ""
        return " OR ".join(tokens)

    def _fetch_results(self, cursor) -> list:
        results = []
        for r in cursor.fetchall():
            try:
                metadata = json.loads(r[3]) if r[3] else {}
            except json.JSONDecodeError:
                metadata = {}
            try:
                tags = json.loads(r[6]) if r[6] else []
            except json.JSONDecodeError:
                tags = []
            results.append({
                "id": r[0],
                "content": r[1],
                "type": r[2],
                "metadata": metadata,
                "created_at": r[4],
                "importance": r[5] if len(r) > 5 else 0,
                "tags": tags
            })
        return results

    def _deduplicate(self, existing: list, new: list) -> list:
        """去重"""
        ids = {r["id"] for r in existing}
        return existing + [r for r in new if r["id"] not in ids]

    def cleanup_expired(self):
        """清理过期记忆"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM memories WHERE expires_at < ?", (now,))

    def delete_memory(self, memory_id: str):
        """删除记忆"""
        # 记录数据操作
        self._privacy_filter.log_action("delete_memory", {
            "memory_id": memory_id,
            "method": "secure_delete"
        })
        
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return db.rowcount > 0
