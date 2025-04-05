# handlers/dictionary.py
from aiogram import types, Dispatcher, Bot
from keyboards.submenus import dictionary_menu_keyboard
from database import crud
from functools import partial
from utils.visual_helpers import format_dictionary_message

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

def register_dictionary_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        partial(handle_dictionary, bot=bot),
        lambda c: c.data == "menu:dictionary"
    )