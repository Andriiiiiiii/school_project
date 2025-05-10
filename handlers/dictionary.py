# handlers/dictionary.py
"""
Обработчики «Мой словарь»:
 • Просмотр списка выученных слов
 • Подтверждение очистки
 • Очистка словаря
 • Отмена очистки
"""

import logging
from functools import partial

from aiogram import Bot, Dispatcher, types

from database import crud
from keyboards.submenus import dictionary_menu_keyboard, clear_dictionary_confirm_keyboard
from keyboards.reply_keyboards import get_main_menu_keyboard
from utils.sticker_helper import send_sticker_with_menu, get_clean_sticker
from utils.visual_helpers import format_dictionary_message

logger = logging.getLogger(__name__)


async def show_dictionary(callback: types.CallbackQuery, bot: Bot):
    """Показывает выученные слова или сообщение о пустом словаре."""
    chat_id = callback.from_user.id
    learned = crud.get_learned_words(chat_id)

    if not learned:
        text = (
            "📚 *Ваш словарь пуст*\n\n"
            "Пройдите квизы, чтобы добавить слова в свой словарь!"
        )
    else:
        text = format_dictionary_message(learned)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=dictionary_menu_keyboard()
    )
    await callback.answer()


async def confirm_clear(callback: types.CallbackQuery, bot: Bot):
    """Запрашивает подтверждение очистки словаря."""
    await callback.message.edit_text(
        "⚠️ *Вы уверены, что хотите очистить весь словарь?*\n\n"
        "Это действие удалит все выученные слова и не может быть отменено.",
        parse_mode="Markdown",
        reply_markup=clear_dictionary_confirm_keyboard()
    )
    await callback.answer()


async def clear_dictionary(callback: types.CallbackQuery, bot: Bot):
    """Очищает словарь пользователя и показывает главное меню."""
    chat_id = callback.from_user.id
    try:
        crud.clear_learned_words_for_user(chat_id)
        # Стикер + меню
        await send_sticker_with_menu(chat_id, bot, get_clean_sticker())
        await bot.send_message(
            chat_id,
            "Словарь успешно очищен.",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        logger.error("Error clearing dictionary for user %s: %s", chat_id, e)
        # Возвращаем пользователя к просмотру словаря с ошибкой
        await callback.message.edit_text(
            "❌ Произошла ошибка при очистке словаря. Пожалуйста, попробуйте позже.",
            parse_mode="Markdown",
            reply_markup=dictionary_menu_keyboard()
        )
    await callback.answer()


async def cancel_clear(callback: types.CallbackQuery, bot: Bot):
    """Отменяет очистку и возвращает к просмотру словаря."""
    await show_dictionary(callback, bot)
    await callback.answer("Очистка словаря отменена")


def register_dictionary_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        partial(show_dictionary, bot=bot),
        lambda c: c.data == "menu:dictionary"
    )
    dp.register_callback_query_handler(
        partial(confirm_clear, bot=bot),
        lambda c: c.data == "dictionary:clear_confirm"
    )
    dp.register_callback_query_handler(
        partial(clear_dictionary, bot=bot),
        lambda c: c.data == "dictionary:clear_confirmed"
    )
    dp.register_callback_query_handler(
        partial(cancel_clear, bot=bot),
        lambda c: c.data == "dictionary:clear_cancel"
    )
