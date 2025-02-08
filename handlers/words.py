# handlers/words.py
import random
from aiogram import types, Dispatcher, Bot
from keyboards.submenus import words_day_keyboard
from utils.helpers import load_words_for_level
from database import crud
from functools import partial

async def send_words_day(chat_id: int, bot: Bot):
    user = crud.get_user(chat_id)
    if not user:
        await bot.send_message(chat_id, "Пользователь не найден.")
        return
    level = user[1]  # например, 'A1'
    words = load_words_for_level(level)
    if not words:
        await bot.send_message(chat_id, f"Слова для уровня {level} не найдены.")
        return

    words_to_send = words[:10]
    messages = []
    for w in words_to_send:
        msg = (f"Слово: {w}\n"
               f"Перевод: (пример перевода)\n"
               f"Транскрипция: (пример транскрипции)\n"
               f"Пример использования: (пример предложения)")
        messages.append(msg)
    full_text = "\n\n".join(messages)
    await bot.send_message(chat_id, full_text, reply_markup=words_day_keyboard())

async def handle_words_day(callback: types.CallbackQuery, bot: Bot):
    await send_words_day(callback.from_user.id, bot)
    await callback.answer()

async def handle_add_word(callback: types.CallbackQuery, bot: Bot):
    try:
        _, word = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
    chat_id = callback.from_user.id
    crud.add_word_to_dictionary(chat_id, {"word": word})
    await bot.send_message(chat_id, f"Слово '{word}' добавлено в ваш словарь!")
    await callback.answer()

def register_words_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        partial(handle_words_day, bot=bot),
        lambda c: c.data == "menu:words_day"
    )
    dp.register_callback_query_handler(
        partial(handle_add_word, bot=bot),
        lambda c: c.data and c.data.startswith("add_word:")
    )
