import os
import asyncio
import tempfile

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot import bot, dp
from services import GigaChatService, calendar_service


gigachat_service = GigaChatService()


class AuthStates(StatesGroup):
    """Состояния для OAuth авторизации"""
    waiting_for_code = State()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Проверяем авторизацию в Google Calendar
    is_auth = calendar_service.is_user_authenticated(user_id)
    calendar_status = "✅ подключен" if is_auth else "❌ не подключен"
    
    # Формируем клавиатуру
    if is_auth:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Отключить Google Calendar", callback_data="disconnect")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Подключить Google Calendar", callback_data="connect")]
        ])
    
    await message.answer(
        f"👋 Привет, {first_name or 'друг'}!\n\n"
        "Я бот для добавления событий в Google Календарь.\n\n"
        f"📆 Google Calendar: {calendar_status}\n\n"
        "📝 Отправь мне голосовое сообщение с описанием события, например:\n"
        "\"Завтра в 15:00 встреча с командой\"\n"
        "\"Созвон в 10 утра с красным цветом\"\n\n"
        "🎨 Можешь указать цвет: красный, синий, зеленый, желтый, оранжевый, розовый, фиолетовый, голубой, серый.\n\n"
        "💡 Также можешь отправить текстовое сообщение.",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "connect")
async def callback_connect(callback: CallbackQuery, state: FSMContext):
    """Начало подключения Google Calendar"""
    user_id = callback.from_user.id
    
    auth_url = calendar_service.get_auth_url(user_id)
    if not auth_url:
        await callback.message.answer(
            "❌ Не удалось создать ссылку для авторизации.\n"
            "Проверьте настройку credentials.json"
        )
        await callback.answer()
        return
    
    await state.set_state(AuthStates.waiting_for_code)
    
    await callback.message.answer(
        "🔐 **Подключение Google Calendar**\n\n"
        "1. Перейди по ссылке ниже\n"
        "2. Войди в свой Google аккаунт\n"
        "3. Разреши доступ к календарю\n"
        "4. Скопируй код и отправь мне\n\n"
        f"🔗 [Открыть авторизацию]({auth_url})\n\n"
        "⏳ Жду код авторизации...",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await callback.answer()


@dp.callback_query(F.data == "disconnect")
async def callback_disconnect(callback: CallbackQuery):
    """Отключение Google Calendar"""
    user_id = callback.from_user.id
    calendar_service.disconnect(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Подключить Google Calendar", callback_data="connect")]
    ])
    
    await callback.message.answer(
        "✅ Google Calendar отключен.\n\n"
        "Ты можешь подключить его снова в любое время.",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.message(AuthStates.waiting_for_code)
async def process_auth_code(message: Message, state: FSMContext):
    """Обработка кода авторизации"""
    user_id = message.from_user.id
    auth_code = message.text.strip()
    
    status_msg = await message.answer("🔄 Проверяю код...")
    
    # Выполняем в executor чтобы не блокировать
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(
        None, calendar_service.complete_auth, user_id, auth_code
    )
    
    await status_msg.delete()
    
    if success:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Отключить Google Calendar", callback_data="disconnect")]
        ])
        
        await message.answer(
            "✅ Google Calendar успешно подключен!\n\n"
            "Теперь ты можешь отправлять голосовые и текстовые сообщения "
            "для создания событий в своём календаре.",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            "❌ Неверный код авторизации.\n\n"
            "Попробуй ещё раз или нажми /start для получения новой ссылки."
        )
    
    await state.clear()


@dp.message(F.voice)
async def handle_voice(message: Message, state: FSMContext):
    """Обработчик голосовых сообщений"""
    # Проверяем, не ждём ли мы код авторизации
    current_state = await state.get_state()
    if current_state == AuthStates.waiting_for_code:
        await message.answer("⚠️ Сначала отправь код авторизации или нажми /start для отмены.")
        return
    
    user_id = message.from_user.id
    status_msg = await message.answer("🎤 Принял голосовое, обрабатываю...")
    
    try:
        # Скачиваем голосовое сообщение
        voice = message.voice
        file = await bot.get_file(voice.file_id)
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
            await bot.download_file(file.file_path, tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            loop = asyncio.get_event_loop()
            # 1) Расшифровка
            transcribed_text = await loop.run_in_executor(
                None, gigachat_service.transcribe_audio, tmp_path
            )
            # 2) Парсинг события
            event_data = await loop.run_in_executor(
                None, gigachat_service.parse_event, transcribed_text
            )
            
            final_text = _build_response(
                user_id=user_id,
                transcribed_text=transcribed_text,
                event_data=event_data
            )
            
            await message.answer(final_text, parse_mode="Markdown")
            await status_msg.delete()
                
        finally:
            os.unlink(tmp_path)
            
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")


@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений"""
    if message.text.startswith("/"):
        return
    
    # Проверяем, не ждём ли мы код авторизации (обрабатывается в process_auth_code)
    current_state = await state.get_state()
    if current_state == AuthStates.waiting_for_code:
        return  # Уже обрабатывается в process_auth_code
    
    user_id = message.from_user.id
    status_msg = await message.answer("⚙️ Обрабатываю...")
    
    try:
        loop = asyncio.get_event_loop()
        event_data = await loop.run_in_executor(
            None, gigachat_service.parse_event, message.text
        )
        
        final_text = _build_response(
            user_id=user_id,
            transcribed_text=None,
            event_data=event_data
        )
        
        await message.answer(final_text, parse_mode="Markdown")
        await status_msg.delete()
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")


def _build_response(user_id: int, transcribed_text: str | None, event_data: dict | None) -> str:
    """Формирует итоговое сообщение одним блоком"""
    if not event_data:
        return "❌ Не удалось извлечь информацию о событии. Попробуй еще раз."
    
    # Капитализируем название события
    title = event_data.get('title', 'Без названия')
    if title:
        title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
    event_data['title'] = title
    
    parts = []
    if transcribed_text:
        parts.append(f"📝 Текст: \"{transcribed_text}\"")
    
    parts.append("📅 Событие:")
    parts.append(f"• Название: {title}")
    parts.append(f"• Дата: {event_data.get('date', 'Не указана')}")
    parts.append(f"• Время: {event_data.get('time_start', '?')} - {event_data.get('time_end', '?')}")
    if event_data.get('description'):
        parts.append(f"• Описание: {event_data['description']}")
    if event_data.get('color'):
        parts.append(f"• Цвет: {event_data['color']}")
    
    # Добавляем в Google Calendar (если пользователь авторизован)
    if calendar_service.is_user_authenticated(user_id):
        result = calendar_service.create_event(
            user_id=user_id,
            title=event_data.get('title', 'Событие'),
            date=event_data.get('date'),
            time_start=event_data.get('time_start', '10:00'),
            time_end=event_data.get('time_end', '11:00'),
            description=event_data.get('description'),
            color=event_data.get('color'),
        )
        if result:
            parts.append(f"✅ Добавлено в календарь: [ссылка]({result['link']})")
        else:
            parts.append("⚠️ Не удалось добавить в календарь.")
    else:
        parts.append("⚠️ Google Calendar не подключен. Нажми /start для подключения.")
    
    return "\n".join(parts)
