"""MemoryLayer - 记忆分层（短期/长期）"""

import time
import logging
from typing import List, Dict, Optional
from .sqlite_store import SQLiteMemoryStore
from .vector_store import VectorStore
from .hybrid_search import HybridSearch

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """短期记忆 - 当前会话上下文，自动过期"""

    def __init__(self, max_items: int = 50, ttl_seconds: int = 3600):
        self._items: List[Dict] = []
        self._max_items = max_items
        self._ttl = ttl_seconds

    def add(self, content: str, metadata: Dict = None) -> None:
        now = time.time()
        self._items.append({
            "content": content,
            "metadata": metadata or {},
            "created_at": now,
            "expires_at": now + self._ttl
        })
        self._cleanup()
        if len(self._items) > self._max_items:
            self._items = self._items[-self._max_items:]

    def recall(self, query: str = "", top_k: int = 10) -> List[Dict]:
        self._cleanup()
        if not query:
            return self._items[:top_k]

        query_lower = query.lower()
        scored = []
        for item in self._items:
            score = 0
            if query_lower in item["content"].lower():
                score += 1.0
            meta = item.get("metadata", {})
            if query_lower in str(meta).lower():
                score += 0.5
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def clear(self):
        self._items.clear()

    def _cleanup(self):
        now = time.time()
        self._items = [i for i in self._items if i.get("expires_at", 0) > now]


class LongTermMemory:
    """长期记忆 - 持久化存储，支持语义搜索"""

    def __init__(self, sqlite_store: SQLiteMemoryStore, vector_store: VectorStore = None):
        self._sqlite = sqlite_store
        self._vector = vector_store
        self._hybrid = HybridSearch(sqlite_store, vector_store)

    def save(
        self,
        content: str,
        memory_type: str = "success",
        metadata: Dict = None,
        ttl_days: int = 90,
        importance: int = 0,
        tags: list = None,
        scope_type: str = "project",
        scope_id: str = "default",
    ) -> bool:
        try:
            self._sqlite.add_memory(
                content,
                metadata,
                memory_type,
                ttl_days,
                scope_type=scope_type,
                scope_id=scope_id,
                importance=importance,
                tags=tags,
            )

            if self._vector and self._vector.is_available():
                self._vector.add(content, {
                    "type": memory_type,
                    "importance": importance,
                    "tags": tags,
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    **(metadata or {})
                })

            return True
        except Exception as e:
            logger.error(f"LongTermMemory save failed: {e}")
            return False

    def recall(self, query: str, top_k: int = 5, mode: str = "hybrid", scope_type: str = "project", scope_id: str = "default") -> List[Dict]:
        results = self._hybrid.search(query, top_k, mode)
        scoped = []
        for item in results:
            meta = item.get("metadata", {}) if isinstance(item, dict) else {}
            if meta.get("scope_type", scope_type) == scope_type and meta.get("scope_id", scope_id) == scope_id:
                scoped.append(item)
        return scoped if scoped else results

    def delete(self, memory_id: str) -> bool:
        return self._sqlite.delete_memory(memory_id)

    def cleanup(self):
        self._sqlite.cleanup_expired()


class MemoryLayer:
    """记忆分层管理 - 统一管理短期和长期记忆"""

    def __init__(self, sqlite_store: SQLiteMemoryStore, vector_store: VectorStore = None):
        self._short_term = ShortTermMemory()
        self._long_term = LongTermMemory(sqlite_store, vector_store)
        self._sqlite = sqlite_store
        self._vector = vector_store

    def save(self, content: str, memory_type: str = "success", metadata: Dict = None, ttl_days: int = 90, importance: int = 0, tags: list = None, scope_type: str = "project", scope_id: str = "default"):
        meta = {"type": memory_type, "importance": importance, "tags": tags, "scope_type": scope_type, "scope_id": scope_id, **(metadata or {})}
        self._short_term.add(content, meta)
        return self._long_term.save(content, memory_type, metadata, ttl_days, importance, tags, scope_type=scope_type, scope_id=scope_id)

    def recall(self, query: str, top_k: int = 5, mode: str = "hybrid", scope_type: str = "project", scope_id: str = "default") -> Dict:
        short_results = self._short_term.recall(query, top_k=3)
        long_results = self._long_term.recall(query, top_k, mode, scope_type=scope_type, scope_id=scope_id)

        return {
            "short_term": short_results,
            "long_term": long_results,
            "total": len(short_results) + len(long_results)
        }

    def clear_short_term(self):
        self._short_term.clear()

    def cleanup(self):
        self._long_term.cleanup()

    @property
    def short_term(self):
        return self._short_term

    @property
    def long_term(self):
        return self._long_term
