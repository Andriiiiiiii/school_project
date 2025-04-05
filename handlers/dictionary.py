# Updated dictionary handlers in handlers/dictionary.py

from aiogram import types, Dispatcher, Bot
from keyboards.submenus import dictionary_menu_keyboard, clear_dictionary_confirm_keyboard
from database import crud
from functools import partial
from utils.visual_helpers import format_dictionary_message
from utils.sticker_helper import get_clean_sticker

async def handle_dictionary(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Мой словарь". Показывает выученные слова с улучшенным форматированием.
    """
    chat_id = callback.from_user.id
    learned = crud.get_learned_words(chat_id)
    
    if not learned:
        await bot.send_message(
            chat_id, 
            "📚 *Ваш словарь пуст*\n\nПройдите квизы, чтобы добавить слова в свой словарь!",
            parse_mode="Markdown",
            reply_markup=dictionary_menu_keyboard()
        )
    else:
        # Используем визуальный помощник для форматирования словаря
        formatted_message = format_dictionary_message(learned)
        
        await bot.send_message(
            chat_id, 
            formatted_message,
            parse_mode="Markdown", 
            reply_markup=dictionary_menu_keyboard()
        )
    
    await callback.answer()

async def handle_clear_dictionary_confirm(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик подтверждения очистки словаря. Показывает диалог подтверждения.
    """
    chat_id = callback.from_user.id
    
    await bot.send_message(
        chat_id,
        "⚠️ *Вы уверены, что хотите очистить весь словарь?*\n\n"
        "Это действие удалит все выученные слова и не может быть отменено.",
        parse_mode="Markdown",
        reply_markup=clear_dictionary_confirm_keyboard()
    )
    
    await callback.answer()

async def handle_clear_dictionary_confirmed(callback: types.CallbackQuery, bot: Bot):
    """Обработчик положительного подтверждения очистки словаря."""
    chat_id = callback.from_user.id
    
    try:
        # Очищаем словарь пользователя
        crud.clear_learned_words_for_user(chat_id)
        
        # Отправляем стикер после очистки словаря
        sticker_id = get_clean_sticker()  # Используем стикер повышения уровня
        if sticker_id:
            await bot.send_sticker(chat_id, sticker_id)
        
        await bot.send_message(
            chat_id,
            "✅ Ваш словарь успешно очищен.",
            parse_mode="Markdown",
            reply_markup=dictionary_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error clearing dictionary for user {chat_id}: {e}")
        await bot.send_message(
            chat_id,
            "❌ Произошла ошибка при очистке словаря. Пожалуйста, попробуйте позже.",
            parse_mode="Markdown",
            reply_markup=dictionary_menu_keyboard()
        )
    
    await callback.answer()

async def handle_clear_dictionary_cancelled(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик отмены очистки словаря. Возвращает к просмотру словаря.
    """
    chat_id = callback.from_user.id
    
    await handle_dictionary(callback, bot)
    await callback.answer("Очистка словаря отменена")

def register_dictionary_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        partial(handle_dictionary, bot=bot),
        lambda c: c.data == "menu:dictionary"
    )
    dp.register_callback_query_handler(
        partial(handle_clear_dictionary_confirm, bot=bot),
        lambda c: c.data == "dictionary:clear_confirm"
    )
    dp.register_callback_query_handler(
        partial(handle_clear_dictionary_confirmed, bot=bot),
        lambda c: c.data == "dictionary:clear_confirmed"
    )
    dp.register_callback_query_handler(
        partial(handle_clear_dictionary_cancelled, bot=bot),
        lambda c: c.data == "dictionary:clear_cancel"
    )