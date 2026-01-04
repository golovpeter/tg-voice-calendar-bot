import json
import logging
from typing import Optional

import redis

from config import REDIS_URL

logger = logging.getLogger(__name__)


class Storage:
    """Redis хранилище для токенов пользователей"""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        logger.info("✅ Redis подключен")
    
    def _key(self, user_id: int) -> str:
        """Формируем ключ для токена пользователя"""
        return f"user:{user_id}:token"
    
    # ============= Методы для токенов =============
    
    def save_token(self, user_id: int, token_data: dict) -> bool:
        """Сохранить OAuth токен пользователя"""
        try:
            self.redis.set(self._key(user_id), json.dumps(token_data))
            logger.info(f"🔐 Токен пользователя {user_id} сохранён")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения токена: {e}")
            return False
    
    def get_token(self, user_id: int) -> Optional[dict]:
        """Получить OAuth токен пользователя"""
        try:
            data = self.redis.get(self._key(user_id))
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения токена: {e}")
            return None
    
    def delete_token(self, user_id: int) -> bool:
        """Удалить токен пользователя"""
        try:
            self.redis.delete(self._key(user_id))
            logger.info(f"🗑️ Токен пользователя {user_id} удалён")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления токена: {e}")
            return False
    
    def has_token(self, user_id: int) -> bool:
        """Проверить есть ли токен у пользователя"""
        return self.redis.exists(self._key(user_id)) > 0
    
    # ============= Методы для OAuth flows =============
    # Примечание: OAuth flows хранятся в памяти CalendarService, так как содержат
    # lambda функции, которые нельзя сериализовать через pickle


# Синглтон
storage = Storage()
