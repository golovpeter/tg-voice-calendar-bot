import asyncio

from bot import dp, bot


async def main():
    """Запуск бота"""
    print("🤖 Бот запущен...")
    print("📋 Используется GigaChat для распознавания речи и парсинга событий")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
