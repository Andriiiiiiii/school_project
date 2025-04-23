# handlers/words.py
from aiogram import types, Dispatcher, Bot
from database import crud
from keyboards.submenus import words_day_keyboard
from utils.helpers import get_daily_words_for_user
from utils.helpers import get_user_settings
from utils.visual_helpers import format_daily_words_message
from config import REMINDER_START, DURATION_HOURS
import os
from config import LEVELS_DIR, DEFAULT_SETS


async def send_words_day_schedule(callback: types.CallbackQuery, bot: Bot):
    """Обработчик кнопки 'Слова дня'."""
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    
    if not user:
        await callback.message.edit_text(
            "⚠️ Профиль не найден. Пожалуйста, используйте /start для создания профиля.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    # Получаем количество слов и повторений из настроек
    words_per_day, repetitions_per_word = get_user_settings(chat_id)
    
    # Дальше идет логика для создания списка "Слов дня" с учетом новых параметров
    result = get_daily_words_for_user(
        chat_id, user[1], words_per_day, repetitions_per_word,
        first_time=REMINDER_START, duration_hours=DURATION_HOURS
    )

    if result is None:
        await callback.message.edit_text(
            f"⚠️ Нет слов для уровня {user[1]}.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    messages, times = result

    # Используем визуальный помощник для форматирования сообщения
    formatted_message = format_daily_words_message(messages, times)
    
    await callback.message.edit_text(
        formatted_message,
        parse_mode="Markdown", 
        reply_markup=words_day_keyboard()
    )
    
    await callback.answer()

def register_words_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: send_words_day_schedule(c, bot),
        lambda c: c.data == "menu:words_day"
    )