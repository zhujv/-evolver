"""HybridSearch - 混合搜索（向量语义+关键词FTS5）"""

import logging
from typing import List, Dict
from .sqlite_store import SQLiteMemoryStore
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class HybridSearch:
    """混合搜索 - 向量语义搜索 + SQLite FTS5关键词搜索"""

    def __init__(self, sqlite_store: SQLiteMemoryStore, vector_store: VectorStore = None):
        self._sqlite = sqlite_store
        self._vector = vector_store

    def search(self, query: str, top_k: int = 5, mode: str = "hybrid") -> List[Dict]:
        if not isinstance(query, str) or not query.strip():
            return []

        safe_top_k = max(1, min(int(top_k or 5), 20))

        if mode == "vector" and self._vector and self._vector.is_available():
            return self._vector_search(query, safe_top_k)
        elif mode == "keyword":
            return self._keyword_search(query, safe_top_k)
        else:
            return self._hybrid_search(query, safe_top_k)

    def _hybrid_search(self, query: str, top_k: int) -> List[Dict]:
        keyword_results = self._keyword_search(query, top_k)
        vector_results = []

        if self._vector and self._vector.is_available():
            vector_results = self._vector_search(query, top_k)

        if not vector_results:
            return keyword_results[:top_k]

        if not keyword_results:
            return vector_results[:top_k]

        merged = {}
        for i, r in enumerate(keyword_results):
            key = r.get("content", "")[:100]
            score = (top_k - i) / top_k * 0.6
            if key in merged:
                merged[key]["score"] += score
            else:
                merged[key] = {**r, "score": score, "source": "keyword"}

        for i, r in enumerate(vector_results):
            key = r.get("content", "")[:100]
            score = r.get("similarity", 0) * 0.4
            if key in merged:
                merged[key]["score"] += score
                merged[key]["source"] = "hybrid"
            else:
                merged[key] = {**r, "score": score, "source": "vector"}

        results = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)
        for r in results:
            r.pop("score", None)

        return results[:top_k]

    def _keyword_search(self, query: str, top_k: int) -> List[Dict]:
        return self._sqlite.recall(query, top_k)

    def _vector_search(self, query: str, top_k: int) -> List[Dict]:
        if not self._vector:
            return []
        results = self._vector.search(query, top_k)
        for r in results:
            r["type"] = "vector_match"
            r["search_mode"] = "semantic"
        return results
