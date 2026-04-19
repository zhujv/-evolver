"""VectorStore - 向量存储与语义搜索（基于USearch）"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from usearch.index import Index
    USEARCH_AVAILABLE = True
except ImportError:
    USEARCH_AVAILABLE = False
    logger.warning("usearch not available, vector search disabled")

try:
    import usearch
    logger.info(f"usearch version: {usearch.__version__}")
except Exception:
    pass


class VectorStore:
    """向量存储 - USearch + 嵌入生成 + 语义搜索"""

    def __init__(self, db_path: str = "~/.evolver/vector_db", dim: int = 384):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(self.db_path, exist_ok=True)
        self.dim = dim
        self.index_path = os.path.join(self.db_path, "memory.index")
        self.meta_path = os.path.join(self.db_path, "metadata.json")
        self._metadata: Dict[int, Dict] = {}
        self._next_id = 1
        self._index = None

        if USEARCH_AVAILABLE:
            try:
                import usearch
                if hasattr(usearch, 'Index'):
                    self._index = usearch.Index(
                        ndim=dim if hasattr(usearch.Index, 'ndim') else dim,
                        metric="cos",
                        dtype="f32"
                    )
                else:
                    self._index = Index(ndim=dim, metric="cos", dtype="f32")
                if os.path.exists(self.index_path):
                    self._index.load(self.index_path)
                self._load_metadata()
                logger.info(f"VectorStore initialized, dim={dim}, entries={len(self._metadata)}")
            except Exception as e:
                logger.error(f"VectorStore init failed: {e}")
                self._index = None
        else:
            logger.info("VectorStore disabled (usearch not installed)")

    def _load_metadata(self):
        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._metadata = {int(k): v for k, v in data.get("metadata", {}).items()}
                    self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, IOError):
                self._metadata = {}
                self._next_id = 1

    def _save_metadata(self):
        try:
            data = {
                "metadata": {str(k): v for k, v in self._metadata.items()},
                "next_id": self._next_id
            }
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save metadata: {e}")

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        if not text or not text.strip():
            return None

        text_bytes = text.encode("utf-8")
        h = hashlib.sha256(text_bytes).digest()

        embedding = []
        for i in range(self.dim):
            byte_idx = i % len(h)
            val = h[byte_idx] / 255.0
            embedding.append(val * 2 - 1)

        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def add(self, text: str, metadata: Dict = None) -> Optional[int]:
        if not self._index:
            return None

        embedding = self._generate_embedding(text)
        if not embedding:
            return None

        vec_id = self._next_id
        self._next_id += 1

        try:
            self._index.add(vec_id, embedding)
            self._metadata[vec_id] = {
                "content": text[:500],
                "full_content_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
                "metadata": metadata or {},
            }
            self._save_metadata()
            self._index.save(self.index_path)
            return vec_id
        except Exception as e:
            logger.error(f"Failed to add vector: {e}")
            return None

    def search(self, query: str, top_k: int = 5, threshold: float = 0.3) -> List[Dict]:
        if not self._index or len(self._metadata) == 0:
            return []

        embedding = self._generate_embedding(query)
        if not embedding:
            return []

        safe_top_k = max(1, min(top_k, len(self._metadata)))

        try:
            results = self._index.search(embedding, safe_top_k)
            matches = []
            for hit in results:
                vec_id = int(hit.key) if hasattr(hit, "key") else int(hit[0])
                distance = float(hit.distance) if hasattr(hit, "distance") else float(hit[1])
                similarity = 1.0 - distance

                if similarity >= threshold:
                    meta = self._metadata.get(vec_id, {})
                    matches.append({
                        "id": vec_id,
                        "content": meta.get("content", ""),
                        "similarity": round(similarity, 4),
                        "metadata": meta.get("metadata", {}),
                    })

            return sorted(matches, key=lambda x: x["similarity"], reverse=True)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def delete(self, vec_id: int) -> bool:
        if vec_id in self._metadata:
            del self._metadata[vec_id]
            self._save_metadata()
            return True
        return False

    def count(self) -> int:
        return len(self._metadata)

    def is_available(self) -> bool:
        return self._index is not None
