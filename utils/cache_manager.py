# utils/cache_manager.py
import threading
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

class CacheManager:
    """
    Класс для безопасного управления кэшем с поддержкой блокировок,
    автоматического истечения срока действия и логирования.
    """
    def __init__(self, expiry_time: int = 86400):  # По умолчанию 24 часа
        self._cache: Dict[int, Tuple[float, Any]] = {}  # {key: (expiry_timestamp, value)}
        self._lock = threading.RLock()
        self._expiry_time = expiry_time
        self.logger = logging.getLogger('cache_manager')
        
    def get(self, key: int) -> Optional[Any]:
        """Получение значения из кэша с проверкой срока годности"""
        with self._lock:
            if key not in self._cache:
                return None
            
            timestamp, value = self._cache[key]
            current_time = time.time()
            
            # Проверка срока годности записи
            if current_time > timestamp:
                self.logger.info(f"Cache expired for key {key}")
                del self._cache[key]
                return None
                
            return value
            
    def set(self, key: int, value: Any, custom_expiry: Optional[int] = None) -> None:
        """Установка значения в кэш с опциональным пользовательским сроком годности"""
        with self._lock:
            expiry = custom_expiry if custom_expiry is not None else self._expiry_time
            expiry_timestamp = time.time() + expiry
            self._cache[key] = (expiry_timestamp, value)
            self.logger.debug(f"Cache set for key {key} with expiry {expiry} seconds")
            
    def delete(self, key: int) -> bool:
        """Удаление записи из кэша"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.logger.debug(f"Cache deleted for key {key}")
                return True
            return False
            
    def clear(self) -> None:
        """Очистка всего кэша"""
        with self._lock:
            self._cache.clear()
            self.logger.info("Cache cleared completely")
            
    def get_all_keys(self) -> list:
        """Получение списка всех ключей в кэше"""
        with self._lock:
            return list(self._cache.keys())
            
    def clean_expired(self) -> int:
        """Очистка истекших записей кэша, возвращает количество удаленных записей"""
        count = 0
        current_time = time.time()
        with self._lock:
            expired_keys = [k for k, (timestamp, _) in self._cache.items() if current_time > timestamp]
            for k in expired_keys:
                del self._cache[k]
                count += 1
        if count > 0:
            self.logger.info(f"Cleaned {count} expired cache entries")
        return count
            
    def has_key(self, key: int) -> bool:
        """Проверка наличия ключа в кэше с учетом срока годности"""
        with self._lock:
            if key not in self._cache:
                return False
                
            timestamp, _ = self._cache[key]
            if time.time() > timestamp:
                del self._cache[key]
                return False
                
            return True