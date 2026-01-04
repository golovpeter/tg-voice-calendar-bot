import os
from pathlib import Path

# Загружаем .env файл если он существует
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv не установлен, это нормально
    pass

# ============= КОНФИГУРАЦИЯ =============

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "❌ TELEGRAM_BOT_TOKEN не установлен!\n"
        "Установите переменную окружения:\n"
        "  export TELEGRAM_BOT_TOKEN='your_token'\n"
        "Или создайте файл .env с содержимым:\n"
        "  TELEGRAM_BOT_TOKEN=your_token"
    )

AUTHORIZATION_KEY = os.getenv("GIGACHAT_AUTH_KEY")
if not AUTHORIZATION_KEY:
    raise ValueError(
        "❌ GIGACHAT_AUTH_KEY не установлен!\n"
        "Установите переменную окружения:\n"
        "  export GIGACHAT_AUTH_KEY='your_key'\n"
        "Или создайте файл .env с содержимым:\n"
        "  GIGACHAT_AUTH_KEY=your_key"
    )

GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-2-Pro")

# ============= GOOGLE CALENDAR =============
GOOGLE_CREDENTIALS_FILE = "credentials.json"

# ============= REDIS =============
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ============= ПРОМПТЫ =============

TRANSCRIPTION_PROMPT = """Расшифруй аудиофайл и верни только текст, который был сказан. 
Без комментариев, только расшифровка речи."""

EVENT_EXTRACTION_PROMPT = """Ты помощник для создания событий в календаре. 
Из сообщения пользователя извлеки информацию о событии и верни JSON в формате:
{{
    "title": "название события",
    "date": "YYYY-MM-DD",
    "time_start": "HH:MM",
    "time_end": "HH:MM",
    "description": "описание события (опционально)",
    "color": "цвет события (опционально)"
}}

Если какая-то информация не указана, используй разумные значения по умолчанию:
- Если не указана дата - используй сегодняшнюю
- Если не указано время окончания - добавь 1 час к началу
- Если не указано время - используй 10:00
- Если не указан цвет - НЕ добавляй поле color в JSON

Доступные цвета: красный, синий, зеленый, желтый, оранжевый, розовый, фиолетовый, голубой, серый, сиреневый.
Если пользователь указал цвет (например: "с красным цветом", "красное событие", "пометь красным") - добавь его в поле color.

Сегодняшняя дата: {today}

ВАЖНО: Верни ТОЛЬКО JSON без дополнительного текста.
"""
