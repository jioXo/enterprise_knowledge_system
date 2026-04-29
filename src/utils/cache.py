import pickle
import hashlib
import json
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
import redis
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.redis_client = None
        self.default_timeout = 3600  # 默认1小时
        self._init_redis()

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            if settings.REDIS_URL:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                # 测试连接
                self.redis_client.ping()
                logger.info("Redis connection established")
            else:
                logger.warning("Redis URL not configured, using in-memory cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            if self.redis_client:
                # Redis缓存
                value = self.redis_client.get(key)
                if value:
                    try:
                        return pickle.loads(value)
                    except (pickle.PickleError, EOFError):
                        # 如果pickle失败，尝试JSON
                        try:
                            return json.loads(value.decode('utf-8'))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            return None
                return None
            else:
                # 内存缓存（简化版，实际应该使用lru_cache）
                return self._get_from_memory(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            if self.redis_client:
                # Redis缓存
                if timeout is None:
                    timeout = self.default_timeout

                # 先尝试pickle，再尝试JSON
                try:
                    serialized_value = pickle.dumps(value)
                    self.redis_client.setex(key, timeout, serialized_value)
                except (pickle.PickleError, TypeError):
                    # 如果无法pickle，转换为JSON
                    if isinstance(value, (dict, list, str, int, float, bool)):
                        serialized_value = json.dumps(value).encode('utf-8')
                        self.redis_client.setex(key, timeout, serialized_value)
                    else:
                        logger.warning(f"Cannot cache non-serializable value for key: {key}")
                        return False
            else:
                # 内存缓存
                self._set_to_memory(key, value, timeout)

            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self._delete_from_memory(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            if self.redis_client:
                return self.redis_client.exists(key) > 0
            else:
                return self._exists_in_memory(key)
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """批量删除匹配模式的缓存"""
        try:
            if self.redis_client:
                # Redis支持模式删除
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # 内存缓存不支持模式删除
                return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0

    def get_or_set(self, key: str, func: Callable, timeout: Optional[int] = None) -> Any:
        """获取缓存，如果不存在则执行函数并缓存结果"""
        value = self.get(key)
        if value is None:
            value = func()
            if value is not None:
                self.set(key, value, timeout)
        return value

    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 构建键名
        key_parts = [prefix]

        # 添加参数
        if args:
            key_parts.extend(str(arg) for arg in args)

        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend(f"{k}:{v}" for k, v in sorted_kwargs)

        # 生成哈希键
        full_key = ":".join(key_parts)
        return hashlib.md5(full_key.encode('utf-8')).hexdigest()

    def _get_from_memory(self, key: str) -> Optional[Any]:
        """内存缓存获取（简化版）"""
        # 这里应该实现真正的内存缓存
        # 例如使用lru_cache或者内存字典
        pass

    def _set_to_memory(self, key: str, value: Any, timeout: int):
        """内存缓存设置（简化版）"""
        pass

    def _delete_from_memory(self, key: str):
        """内存缓存删除（简化版）"""
        pass

    def _exists_in_memory(self, key: str) -> bool:
        """内存缓存检查（简化版）"""
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            if self.redis_client:
                info = self.redis_client.info()
                return {
                    "type": "redis",
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            else:
                return {
                    "type": "memory",
                    "note": "In-memory cache is being used"
                }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


# 全局缓存管理器实例
cache_manager = CacheManager()