"""MemoryTools - 记忆工具"""

from ..memory.sqlite_store import SQLiteMemoryStore


class MemoryTools:
    """记忆工具"""

    def __init__(self):
        self._memory_store = SQLiteMemoryStore()

    def save(self, key: str, value: any) -> dict:
        """保存记忆"""
        try:
            if not isinstance(key, str) or not key.strip():
                return {"error": "key 不能为空"}
            content = f"{key.strip()}: {value}"
            self._memory_store.add_memory(content, metadata={"key": key.strip()})
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def recall(self, query: str) -> dict:
        """检索记忆"""
        try:
            if not isinstance(query, str) or not query.strip():
                return {"error": "query 不能为空"}
            results = self._memory_store.recall(query.strip())
            return {"results": results}
        except Exception as e:
            return {"error": str(e)}
