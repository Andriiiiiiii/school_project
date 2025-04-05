# handlers/words.py
from aiogram import types, Dispatcher, Bot
from database import crud
from keyboards.submenus import words_day_keyboard
from utils.helpers import get_daily_words_for_user
from utils.visual_helpers import format_daily_words_message
from config import REMINDER_START, DURATION_HOURS
import os
from config import LEVELS_DIR, DEFAULT_SETS


async def send_words_day_schedule(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Слова дня". Возвращает набор слов на сегодня с улучшенным форматированием.
    Исправлено: редактирует существующее сообщение вместо отправки нового.
    """
    chat_id = callback.from_user.id
    user = crud.get_user(chat_id)
    
    if not user:
        await callback.message.edit_text(
            "⚠️ Профиль не найден. Пожалуйста, используйте /start для создания профиля.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Проверяем соответствие сета уровню
    from handlers.settings import user_set_selection
    current_set = user_set_selection.get(chat_id)
    if not current_set and len(user) > 6:
        current_set = user[6]
    
    # Проверяем существование файла сета для текущего уровня
    level = user[1]
    if current_set:
        set_file_path = os.path.join(LEVELS_DIR, level, f"{current_set}.txt")
        if not os.path.exists(set_file_path):
            # Сет не соответствует уровню, пробуем установить базовый
            default_set = DEFAULT_SETS.get(level)
            if default_set:
                default_set_path = os.path.join(LEVELS_DIR, level, f"{default_set}.txt")
                if os.path.exists(default_set_path):
                    # Обновляем сет
                    crud.update_user_chosen_set(chat_id, default_set)
                    user_set_selection[chat_id] = default_set
                    reset_daily_words_cache(chat_id)
                    await callback.message.edit_text(
                        f"⚠️ Выбранный ранее сет '{current_set}' не соответствует вашему текущему уровню {level}.\n\n"
                        f"Автоматически установлен базовый сет '{default_set}' для уровня {level}.\n\n"
                        f"Нажмите 'Слова дня' еще раз для просмотра слов.",
                        parse_mode="Markdown",
                        reply_markup=words_day_keyboard()
                    )
                    await callback.answer()
                    return
    
    result = get_daily_words_for_user(
        chat_id, user[1], user[2], user[3],
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