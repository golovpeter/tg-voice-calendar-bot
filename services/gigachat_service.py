import json
import logging
from datetime import datetime
from typing import Optional

from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage

from config import (
    AUTHORIZATION_KEY,
    GIGACHAT_MODEL,
    TRANSCRIPTION_PROMPT,
    EVENT_EXTRACTION_PROMPT,
)

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GigaChatService:
    """Сервис для работы с GigaChat API"""
    
    def __init__(self):
        self.giga = GigaChat(
            credentials=AUTHORIZATION_KEY,
            verify_ssl_certs=False,
            model=GIGACHAT_MODEL
        )
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """Расшифровка аудио файла"""
        logger.info(f"🎤 Начинаю расшифровку аудио: {audio_file_path}")
        
        # 1. Загружаем файл в GigaChat
        with open(audio_file_path, "rb") as f:
            uploaded_file = self.giga.upload_file(f, purpose="general")
        
        file_id = uploaded_file.id_
        logger.info(f"📤 Файл загружен, ID: {file_id}")
        
        # Логируем информацию о загруженном файле
        upload_info = {
            "id": uploaded_file.id_,
            "filename": uploaded_file.filename,
            "bytes": uploaded_file.bytes_,
            "purpose": uploaded_file.purpose,
        }
        logger.debug(f"📋 Upload response: {json.dumps(upload_info, ensure_ascii=False, indent=2)}")
        
        try:
            # 2. Отправляем запрос с прикрепленным файлом
            messages = [
                SystemMessage(content=TRANSCRIPTION_PROMPT),
                HumanMessage(
                    content="Расшифруй этот аудиофайл",
                    additional_kwargs={"attachments": [file_id]}
                )
            ]
            
            logger.debug(f"📨 Отправляю запрос на расшифровку с file_id: {file_id}")
            response = self.giga.invoke(messages)
            
            # Логируем полный ответ API
            response_info = {
                "content": response.content,
                "type": response.type,
                "response_metadata": response.response_metadata if hasattr(response, "response_metadata") else None,
            }
            logger.info(f"📥 Transcription API response: {json.dumps(response_info, ensure_ascii=False, indent=2)}")
            
            return response.content
            
        finally:
            # 3. Удаляем файл после обработки
            self._delete_file(file_id)
    
    def parse_event(self, text: str) -> Optional[dict]:
        """Извлечение данных события из текста"""
        today = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"🔍 Парсинг события из текста: {text[:100]}...")
        
        messages = [
            SystemMessage(content=EVENT_EXTRACTION_PROMPT.format(today=today)),
            HumanMessage(content=text)
        ]
        
        response = self.giga.invoke(messages)
        
        # Логируем ответ API для парсинга события
        response_info = {
            "content": response.content,
            "type": response.type,
        }
        logger.info(f"📥 Event parsing API response: {json.dumps(response_info, ensure_ascii=False, indent=2)}")
        
        parsed = self._extract_json(response.content)
        if parsed:
            logger.debug(f"📋 Parsed event data: {json.dumps(parsed, ensure_ascii=False, indent=2)}")
        else:
            logger.debug("📋 Parsed event data: None")
        
        return parsed
    
    def _extract_json(self, text: str) -> Optional[dict]:
        """Извлечение JSON из текста ответа"""
        try:
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
        return None
    
    def _delete_file(self, file_id: str) -> None:
        """Удаление файла из GigaChat"""
        try:
            self.giga._client.delete_file(file_id)
            logger.info(f"🗑️ Файл {file_id} удален")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить файл: {e}")


# Синглтон для использования в хэндлерах
gigachat_service = GigaChatService()
