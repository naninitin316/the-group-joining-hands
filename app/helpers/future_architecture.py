"""
The Group of Joining Hands - Future Architecture Contracts
=============================================================
Future-Ready Abstractions for Caching (Redis), Realtime Transport (WebSockets),
and Asynchronous Job Queues (Background Workers).

IMPORTANT INVARIANT:
Zero external dependencies required today (no Redis, no Celery, no WebSocket server needed).
All interfaces have synchronous, zero-cost, memory/database fallbacks for the current system.
"""

import time
import threading
from typing import Any, Callable, Dict, Optional

# ==============================================================================
# 1. CACHE & STATE ABSTRACTION (Future Redis Readiness)
# ==============================================================================

class CacheBackend:
    """Interface for key-value caching, state storage, and rate-limiting."""
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
        
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        raise NotImplementedError
        
    def delete(self, key: str) -> bool:
        raise NotImplementedError
        
    def increment(self, key: str, delta: int = 1) -> int:
        raise NotImplementedError


class InMemoryCacheBackend(CacheBackend):
    """In-Memory fallback implementation. Used when Redis is not installed."""
    def __init__(self):
        self._store: Dict[str, tuple[Any, Optional[float]]] = {}
        self._lock = threading.Lock()
        
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            val, expiry = self._store[key]
            if expiry is not None and time.time() > expiry:
                del self._store[key]
                return None
            return val
            
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        with self._lock:
            expiry = (time.time() + ttl_seconds) if ttl_seconds else None
            self._store[key] = (value, expiry)
            return True
            
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False
            
    def increment(self, key: str, delta: int = 1) -> int:
        with self._lock:
            curr = self.get(key)
            new_val = (curr or 0) + delta
            self.set(key, new_val)
            return new_val


# Singleton Cache Instance (Can be dynamically replaced with RedisCacheBackend in future)
cache = InMemoryCacheBackend()


# ==============================================================================
# 2. REALTIME TRANSPORT ABSTRACTION (Future WebSockets Readiness)
# ==============================================================================

class RealtimeEventDispatcher:
    """
    Interface for publishing realtime events (message.new, typing.start, notification.new).
    Currently logs and delivers locally; in future seamlessly connects to WebSocket hubs.
    """
    def __init__(self):
        self._subscribers: Dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, payload: dict):
        """Dispatches event to local handlers or WebSocket clients when enabled."""
        if event_type in self._subscribers:
            for cb in self._subscribers[event_type]:
                try:
                    cb(payload)
                except Exception:
                    pass

# Singleton Realtime Dispatcher
realtime = RealtimeEventDispatcher()


# ==============================================================================
# 3. ASYNC TASK QUEUE ABSTRACTION (Future Background Workers Readiness)
# ==============================================================================

class JobQueue:
    """
    Interface for offloading heavy jobs (Image processing, Bulk notifications, Backups).
    Executes in lightweight worker thread locally today; ready for Celery/RQ in future.
    """
    def enqueue(self, task_name: str, task_fn: Callable, *args, **kwargs) -> str:
        # Run immediately in a non-blocking background daemon thread
        t = threading.Thread(target=task_fn, args=args, kwargs=kwargs, daemon=True)
        t.start()
        return f"job_{int(time.time()*1000)}"

# Singleton Job Queue Instance
job_queue = JobQueue()
