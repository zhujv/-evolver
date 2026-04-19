"""Performance optimization utilities for Evolver"""

import time
import json
import logging
import threading
import hashlib
from collections import OrderedDict
from typing import Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU cache implementation"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._hits += 1
                self._cache.move_to_end(key)
                return self._cache[key]['value']
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = 300):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 4)
            }


class RequestCache:
    """Cache for expensive request operations"""

    def __init__(self, max_size: int = 500, default_ttl: int = 3600):
        self.cache = LRUCache(max_size)
        self.default_ttl = default_ttl

    def _make_key(self, method: str, params: dict) -> str:
        param_str = json.dumps(params, sort_keys=True)
        key_str = f"{method}:{param_str}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def get(self, method: str, params: dict) -> Optional[Any]:
        key = self._make_key(method, params)
        return self.cache.get(key)

    def set(self, method: str, params: dict, value: Any, ttl: Optional[int] = None):
        key = self._make_key(method, params)
        self.cache.set(key, value, ttl or self.default_ttl)

    def invalidate(self, method: str, params: dict):
        key = self._make_key(method, params)
        with self.cache._lock:
            if key in self.cache._cache:
                del self.cache._cache[key]

    def stats(self) -> dict:
        return self.cache.stats()


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, max_calls: int = 120, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str = "default") -> bool:
        with self._lock:
            now = time.time()
            if key not in self._buckets:
                self._buckets[key] = []

            self._buckets[key] = [
                t for t in self._buckets[key]
                if now - t < self.period
            ]

            if len(self._buckets[key]) < self.max_calls:
                self._buckets[key].append(now)
                return True
            return False

    def wait_time(self, key: str = "default") -> float:
        with self._lock:
            if key not in self._buckets or not self._buckets[key]:
                return 0

            now = time.time()
            recent = [t for t in self._buckets[key] if now - t < self.period]

            if len(recent) < self.max_calls:
                return 0

            oldest = min(recent)
            return max(0, self.period - (now - oldest))


class MemoryMonitor:
    """Monitor memory usage and trigger cleanup when needed"""

    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self._cleanup_callbacks = []
        self._lock = threading.Lock()
        self._last_check = 0
        self._check_interval = 60

    def register_cleanup(self, callback: Callable):
        self._cleanup_callbacks.append(callback)

    def check_memory(self) -> dict:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        status = {
            'rss_mb': round(memory_mb, 2),
            'max_mb': self.max_memory_mb,
            'usage_percent': round(memory_mb / self.max_memory_mb * 100, 2),
            'vms_mb': round(memory_info.vms / 1024 / 1024, 2)
        }

        if memory_mb > self.max_memory_mb:
            logger.warning(f"Memory usage ({memory_mb}MB) exceeded limit ({self.max_memory_mb}MB)")
            self._trigger_cleanup()

        return status

    def _trigger_cleanup(self):
        with self._lock:
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Cleanup callback failed: {e}")


def cached(cache: RequestCache, ttl: int = 300):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            method = f"{func.__module__}.{func.__name__}"
            cached_result = cache.get(method, {'args': args, 'kwargs': kwargs})
            if cached_result is not None:
                return cached_result

            result = func(*args, **kwargs)
            cache.set(method, {'args': args, 'kwargs': kwargs}, result, ttl)
            return result
        return wrapper
    return decorator


class ConnectionPool:
    """Simple connection pool for HTTP clients"""

    def __init__(self, factory: Callable, max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self._pool = []
        self._lock = threading.Lock()
        self._created = 0

    def acquire(self) -> Any:
        with self._lock:
            while self._pool:
                client = self._pool.pop()
                return client

            if self._created < self.max_size:
                self._created += 1
                return self.factory()

            raise RuntimeError("Connection pool exhausted")

    def release(self, client: Any):
        with self._lock:
            if len(self._pool) < self.max_size:
                self._pool.append(client)


_global_cache = RequestCache(max_size=500, default_ttl=3600)
_global_rate_limiter = RateLimiter(max_calls=120, period=60)
_global_memory_monitor = MemoryMonitor(max_memory_mb=512)


def get_cache() -> RequestCache:
    return _global_cache


def get_rate_limiter() -> RateLimiter:
    return _global_rate_limiter


def get_memory_monitor() -> MemoryMonitor:
    return _global_memory_monitor
