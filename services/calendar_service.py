import json
import logging
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GOOGLE_CREDENTIALS_FILE
from services.storage import storage

logger = logging.getLogger(__name__)

# Права доступа к календарю
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Маппинг цветов на colorId Google Calendar
# https://developers.google.com/calendar/api/v3/reference/colors
COLOR_MAP = {
    # Русские названия
    "лавандовый": "1", "сиреневый": "1", "лаванда": "1",
    "серо-зеленый": "2", "шалфей": "2", "серо-зелёный": "2",
    "фиолетовый": "3", "виноград": "3", "пурпурный": "3",
    "розовый": "4", "фламинго": "4",
    "желтый": "5", "жёлтый": "5", "банан": "5", "банановый": "5",
    "оранжевый": "6", "мандарин": "6", "мандариновый": "6",
    "голубой": "7", "бирюзовый": "7", "павлин": "7", "циан": "7",
    "серый": "8", "графит": "8", "графитовый": "8",
    "синий": "9", "черника": "9", "темно-синий": "9", "тёмно-синий": "9",
    "зеленый": "10", "зелёный": "10", "базилик": "10",
    "красный": "11", "томат": "11", "томатный": "11", "алый": "11",
    # Английские названия
    "lavender": "1", "sage": "2", "grape": "3", "flamingo": "4",
    "banana": "5", "tangerine": "6", "peacock": "7", "graphite": "8",
    "blueberry": "9", "basil": "10", "tomato": "11",
    "red": "11", "blue": "9", "green": "10", "yellow": "5", 
    "orange": "6", "pink": "4", "purple": "3", "gray": "8", "grey": "8",
}


class CalendarService:
    """Сервис для работы с Google Calendar API (многопользовательский)"""
    
    def __init__(self):
        # Кэш сервисов для пользователей
        self._services: dict[int, any] = {}
        # Pending flows для OAuth
        self._pending_flows: dict[int, any] = {}
    
    def _get_credentials(self, user_id: int) -> Optional[Credentials]:
        """Получить credentials из хранилища"""
        token_data = storage.get_token(user_id)
        if not token_data:
            return None
        
        try:
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            return creds
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки credentials: {e}")
            return None
    
    def _save_credentials(self, user_id: int, creds: Credentials) -> bool:
        """Сохранить credentials в хранилище"""
        try:
            token_data = json.loads(creds.to_json())
            return storage.save_token(user_id, token_data)
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения credentials: {e}")
            return False
    
    def get_service(self, user_id: int):
        """Получить Google Calendar service для пользователя"""
        # Проверяем кэш
        if user_id in self._services:
            return self._services[user_id]
        
        # Пытаемся получить credentials
        creds = self._get_credentials(user_id)
        if not creds:
            return None
        
        try:
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    logger.info(f"🔄 Обновляю токен для пользователя {user_id}...")
                    creds.refresh(Request())
                    # Сохраняем обновленный токен
                    self._save_credentials(user_id, creds)
                else:
                    logger.warning(f"⚠️ Токен пользователя {user_id} невалиден")
                    return None
            
            service = build("calendar", "v3", credentials=creds)
            self._services[user_id] = service
            logger.info(f"✅ Google Calendar подключен для пользователя {user_id}")
            return service
            
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации пользователя {user_id}: {e}")
            # Если токен невалиден, удаляем его
            storage.delete_token(user_id)
            return None
    
    def is_user_authenticated(self, user_id: int) -> bool:
        """Проверка авторизации пользователя"""
        return self.get_service(user_id) is not None
    
    def get_auth_url(self, user_id: int) -> Optional[str]:
        """Получить URL для авторизации пользователя"""
        import os
        if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
            logger.error(f"❌ Файл {GOOGLE_CREDENTIALS_FILE} не найден!")
            return None
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CREDENTIALS_FILE, 
                SCOPES,
                redirect_uri="urn:ietf:wg:oauth:2.0:oob"  # Для ручного ввода кода
            )
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            # Сохраняем flow для последующего обмена кода
            self._pending_flows[user_id] = flow
            return auth_url
        except Exception as e:
            logger.error(f"❌ Ошибка создания auth URL: {e}")
            return None
    
    def complete_auth(self, user_id: int, auth_code: str) -> bool:
        """Завершить авторизацию с полученным кодом"""
        flow = self._pending_flows.get(user_id)
        
        if not flow:
            logger.error(f"❌ Нет pending flow для пользователя {user_id}")
            return False
        
        try:
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            # Сохраняем токен в SQLite
            if not self._save_credentials(user_id, creds):
                return False
            
            logger.info(f"✅ Пользователь {user_id} успешно авторизован")
            
            # Очищаем pending flow
            del self._pending_flows[user_id]
            
            # Убираем из кэша чтобы пересоздать сервис
            if user_id in self._services:
                del self._services[user_id]
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка завершения авторизации: {e}")
            return False
    
    def disconnect(self, user_id: int):
        """Отключить пользователя от Google Calendar"""
        storage.delete_token(user_id)
        if user_id in self._services:
            del self._services[user_id]
        logger.info(f"🔓 Пользователь {user_id} отключен от Google Calendar")
    
    def create_event(
        self,
        user_id: int,
        title: str,
        date: str,
        time_start: str,
        time_end: str,
        description: Optional[str] = None,
        timezone: str = "Europe/Moscow",
        color: Optional[str] = None
    ) -> Optional[dict]:
        """
        Создание события в Google Calendar пользователя
        
        Args:
            user_id: ID пользователя Telegram
            title: Название события
            date: Дата в формате YYYY-MM-DD
            time_start: Время начала HH:MM
            time_end: Время окончания HH:MM
            description: Описание события
            timezone: Часовой пояс
            color: Название цвета (русское или английское)
        
        Returns:
            dict с информацией о созданном событии или None при ошибке
        """
        service = self.get_service(user_id)
        if not service:
            logger.error(f"❌ Google Calendar не подключен для пользователя {user_id}")
            return None
        
        # Проверяем и корректируем время окончания
        if time_end <= time_start:
            # Добавляем 1 час к времени начала
            try:
                start_h, start_m = map(int, time_start.split(':'))
                end_h = start_h + 1
                if end_h >= 24:
                    end_h = 23
                    start_m = 59
                time_end = f"{end_h:02d}:{start_m:02d}"
                logger.info(f"⏰ Скорректировано время окончания: {time_end}")
            except ValueError:
                time_end = "11:00"  # fallback
        
        # Формируем datetime строки
        start_datetime = f"{date}T{time_start}:00"
        end_datetime = f"{date}T{time_end}:00"
        
        event_body = {
            "summary": title,
            "start": {
                "dateTime": start_datetime,
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_datetime,
                "timeZone": timezone,
            },
        }
        
        if description:
            event_body["description"] = description
        
        # Добавляем цвет если указан
        if color:
            color_id = COLOR_MAP.get(color.lower())
            if color_id:
                event_body["colorId"] = color_id
                logger.info(f"🎨 Установлен цвет: {color} (colorId={color_id})")
        
        logger.info(f"📅 Создаю событие для {user_id}: {title} на {date} {time_start}-{time_end}")
        logger.debug(f"📋 Event body: {event_body}")
        
        try:
            event = service.events().insert(
                calendarId="primary",
                body=event_body
            ).execute()
            
            logger.info(f"✅ Событие создано: {event.get('htmlLink')}")
            return {
                "id": event.get("id"),
                "link": event.get("htmlLink"),
                "summary": event.get("summary"),
                "start": event.get("start"),
                "end": event.get("end"),
            }
            
        except HttpError as error:
            logger.error(f"❌ Ошибка Google Calendar API: {error}")
            return None


# Синглтон
calendar_service = CalendarService()
