#pathtofile/handlers/dictionary.py
from aiogram import types, Dispatcher, Bot
from keyboards.submenus import dictionary_menu_keyboard
from database import crud
from functools import partial

async def handle_dictionary(callback: types.CallbackQuery, bot: Bot):
    """
    Обработчик кнопки "Мой словарь". Теперь выводит выученные слова из таблицы learned_words,
    где каждая запись отображается в формате "• word — translation".
    """
    chat_id = callback.from_user.id
    learned = crud.get_learned_words(chat_id)
    if not learned:
        await bot.send_message(chat_id, "Ваш словарь пуст.", reply_markup=dictionary_menu_keyboard())
    else:
        text = "Ваш словарь (выученные слова):\n\n"
        # Ожидается, что get_learned_words возвращает список кортежей (word, translation)
        for word, translation in learned:
            text += f"• {word} — {translation}\n"
        await bot.send_message(chat_id, text, reply_markup=dictionary_menu_keyboard())
    await callback.answer()

def register_dictionary_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        partial(handle_dictionary, bot=bot),
        lambda c: c.data == "menu:dictionary"
    )
