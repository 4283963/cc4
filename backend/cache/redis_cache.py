import json
import hashlib
import time
from typing import Optional, Dict, Any

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..config import Config


class ComputationCache:
    def __init__(self, host: str = None, port: int = None, db: int = None):
        self.host = host or Config.REDIS_HOST
        self.port = port or Config.REDIS_PORT
        self.db = db or Config.REDIS_DB
        self.ttl = Config.CACHE_TTL
        self._client = None
        self._fallback = {}
        self._fallback_timestamps = {}
    
    def _get_client(self):
        if self._client is None and REDIS_AVAILABLE:
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    decode_responses=True
                )
                self._client.ping()
            except Exception:
                self._client = None
        return self._client
    
    @property
    def redis_available(self) -> bool:
        return self._get_client() is not None
    
    def _make_key(self, prefix: str, data: Any) -> str:
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        hash_val = hashlib.md5(data_str.encode()).hexdigest()
        return f"cc4:{prefix}:{hash_val}"
    
    def set_result(self, key: str, result: Dict[str, Any], ttl: int = None):
        ttl = ttl or self.ttl
        client = self._get_client()
        
        if client:
            try:
                value = json.dumps(result)
                client.setex(key, ttl, value)
            except Exception:
                pass
        else:
            self._fallback[key] = result
            self._fallback_timestamps[key] = time.time() + ttl
    
    def get_result(self, key: str) -> Optional[Dict[str, Any]]:
        client = self._get_client()
        
        if client:
            try:
                value = client.get(key)
                if value:
                    return json.loads(value)
            except Exception:
                pass
        else:
            if key in self._fallback:
                if time.time() < self._fallback_timestamps.get(key, 0):
                    return self._fallback[key]
                else:
                    del self._fallback[key]
                    self._fallback_timestamps.pop(key, None)
        
        return None
    
    def set_task_status(self, task_id: str, status: str, progress: int = 0, 
                        result: Dict = None, ttl: int = None):
        ttl = ttl or self.ttl
        data = {
            'task_id': task_id,
            'status': status,
            'progress': progress,
            'result': result,
            'updated_at': time.time()
        }
        key = f"cc4:task:{task_id}"
        self.set_result(key, data, ttl)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        key = f"cc4:task:{task_id}"
        return self.get_result(key)
    
    def update_task_progress(self, task_id: str, progress: int):
        status = self.get_task_status(task_id)
        if status:
            status['progress'] = progress
            status['updated_at'] = time.time()
            key = f"cc4:task:{task_id}"
            self.set_result(key, status)
    
    def set_task_result(self, task_id: str, result: Dict):
        status = self.get_task_status(task_id) or {'task_id': task_id}
        status['status'] = 'completed'
        status['progress'] = 100
        status['result'] = result
        status['updated_at'] = time.time()
        key = f"cc4:task:{task_id}"
        self.set_result(key, status)
    
    def get_cached_result(self, params_dict: Dict) -> Optional[Dict]:
        key = self._make_key('result', params_dict)
        return self.get_result(key)
    
    def cache_result(self, params_dict: Dict, result: Dict, ttl: int = None):
        key = self._make_key('result', params_dict)
        self.set_result(key, result, ttl)
    
    def clear_all(self):
        client = self._get_client()
        if client:
            try:
                keys = client.keys("cc4:*")
                if keys:
                    client.delete(*keys)
            except Exception:
                pass
        self._fallback.clear()
        self._fallback_timestamps.clear()


_cache_instance = None


def get_cache() -> ComputationCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ComputationCache()
    return _cache_instance
