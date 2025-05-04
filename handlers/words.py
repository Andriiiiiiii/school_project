# handlers/words.py
from aiogram import types, Dispatcher, Bot
from database import crud
from keyboards.submenus import words_day_keyboard
from utils.helpers import get_daily_words_for_user, reset_daily_words_cache
from utils.helpers import get_user_settings
from utils.visual_helpers import format_daily_words_message
from config import REMINDER_START, DURATION_HOURS
import os
from config import LEVELS_DIR, DEFAULT_SETS
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

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

    # Проверка на необходимость смены сета
    if result is None:
        await callback.message.edit_text(
            f"⚠️ Нет слов для уровня {user[1]}.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    elif len(result) == 3 and result[0] is None and result[1] is None:
        # Нужно подтверждение смены сета
        default_set = result[2]
        # Создаем клавиатуру для подтверждения
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ Да, сменить", callback_data=f"confirm_set_change:{default_set}"),
            types.InlineKeyboardButton("❌ Нет, отмена", callback_data="menu:back")
        )
        
        # Получаем текущий выбранный сет для отображения
        current_set = None
        if len(user) > 6 and user[6]:
            current_set = user[6]
        else:
            try:
                from handlers.settings import user_set_selection
                current_set = user_set_selection.get(chat_id)
            except ImportError:
                pass
        
        if not current_set:
            current_set = "не выбран"
        
        await callback.message.edit_text(
            f"⚠️ *Внимание! Смена сета приведет к полному сбросу прогресса.*\n\n"
            f"Текущий сет: *{current_set}*\n"
            f"Текущий уровень: *{user[1]}*\n\n"
            f"Выбранный сет не соответствует текущему уровню. "
            f"Хотите сменить его на базовый сет *{default_set}* для уровня {user[1]}?\n\n"
            f"При смене сета ваш словарь будет полностью очищен. Вы уверены?",
            parse_mode="Markdown",
            reply_markup=keyboard
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

async def handle_confirm_set_change(callback: types.CallbackQuery, bot: Bot):
    """Обработчик подтверждения смены сета на базовый для нового уровня."""
    chat_id = callback.from_user.id
    
    try:
        _, default_set = callback.data.split(":", 1)
        
        # Получаем информацию о пользователе
        user = crud.get_user(chat_id)
        if not user:
            await callback.answer("Профиль не найден. Используйте /start.", show_alert=True)
            return
            
        level = user[1]
        
        # Очищаем словарь пользователя
        try:
            crud.clear_learned_words_for_user(chat_id)
            logger.info(f"Словарь очищен для пользователя {chat_id} при смене сета")
        except Exception as e:
            logger.error(f"Ошибка при очистке словаря: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при очистке словаря. Пожалуйста, попробуйте позже.",
                reply_markup=words_day_keyboard()
            )
            await callback.answer()
            return
        
        # Обновляем выбранный сет в базе данных и кэше
        try:
            crud.update_user_chosen_set(chat_id, default_set)
            from handlers.settings import user_set_selection
            user_set_selection[chat_id] = default_set
            reset_daily_words_cache(chat_id)
            logger.info(f"Сет изменен на '{default_set}' для пользователя {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении сета: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при обновлении сета. Пожалуйста, попробуйте позже.",
                reply_markup=words_day_keyboard()
            )
            await callback.answer()
            return
        
        # Получаем слова для нового сета
        words_per_day, repetitions_per_word = get_user_settings(chat_id)
        result = get_daily_words_for_user(
            chat_id, level, words_per_day, repetitions_per_word,
            first_time=REMINDER_START, duration_hours=DURATION_HOURS
        )
        
        if result is None:
            await callback.message.edit_text(
                f"⚠️ Не удалось получить слова для уровня {level} и сета {default_set}.",
                parse_mode="Markdown",
                reply_markup=words_day_keyboard()
            )
            await callback.answer()
            return
            
        messages, times = result
        
        # Отправляем стикер для смены сета
        from utils.sticker_helper import get_clean_sticker
        sticker_id = get_clean_sticker()
        if sticker_id:
            await bot.send_sticker(chat_id, sticker_id)
        
        # Используем визуальный помощник для форматирования сообщения
        formatted_message = format_daily_words_message(messages, times)
        
        await callback.message.edit_text(
            f"✅ Сет успешно изменен на '{default_set}'.\n⚠️ Словарь очищен.\n\n" + formatted_message,
            parse_mode="Markdown", 
            reply_markup=words_day_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении смены сета: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=words_day_keyboard()
        )
    
    await callback.answer()

def register_words_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: send_words_day_schedule(c, bot),
        lambda c: c.data == "menu:words_day"
    )
    dp.register_callback_query_handler(
        lambda c: handle_confirm_set_change(c, bot),
        lambda c: c.data and c.data.startswith("confirm_set_change:")
    )