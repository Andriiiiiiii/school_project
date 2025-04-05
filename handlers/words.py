# handlers/words.py
from aiogram import types, Dispatcher, Bot
from database import crud
from keyboards.submenus import words_day_keyboard
from utils.helpers import get_daily_words_for_user
from utils.visual_helpers import format_daily_words_message
from config import REMINDER_START, DURATION_HOURS

async def send_words_day_schedule(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Слова дня". Возвращает набор слов на сегодня с улучшенным форматированием.
    """
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    
    if not user:
        await bot.send_message(
            chat_id, 
            "⚠️ Профиль не найден. Пожалуйста, используйте /start для создания профиля.",
            parse_mode="Markdown"
        )
        return
    
    result = get_daily_words_for_user(
        chat_id, user[1], user[2], user[3],
        first_time=REMINDER_START, duration_hours=DURATION_HOURS
    )
    
    if result is None:
        await bot.send_message(
            chat_id, 
            f"⚠️ Нет слов для уровня {user[1]}.",
            parse_mode="Markdown"
        )
        return
    
    messages, times = result
    
    # Используем визуальный помощник для форматирования сообщения
    formatted_message = format_daily_words_message(messages, times)
    
    await bot.send_message(
        chat_id, 
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