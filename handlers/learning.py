# handlers/learning.py
import random
from aiogram import types, Dispatcher, Bot
from keyboards.submenus import learning_menu_keyboard
from utils.helpers import load_words_for_level
from database import crud
from functools import partial

async def start_learning_test(chat_id: int, bot: Bot):
    user = crud.get_user(chat_id)
    if not user:
        return
    level = user[1]
    words = load_words_for_level(level)
    if not words:
        await bot.send_message(chat_id, f"Нет слов для уровня {level}.")
        return
    selected = random.sample(words, min(15, len(words)))
    text = "Тест уровня знаний:\nВыберите правильный перевод для следующих слов:\n" + "\n".join(selected)
    await bot.send_message(chat_id, text, reply_markup=learning_menu_keyboard())

async def learning_placeholder(callback: types.CallbackQuery, bot: Bot):
    await bot.send_message(callback.from_user.id, "Эта функция в разработке.", reply_markup=learning_menu_keyboard())
    await callback.answer()

async def handle_learning_menu(callback: types.CallbackQuery, bot: Bot):
    await bot.send_message(callback.from_user.id, "Выберите режим обучения:", reply_markup=learning_menu_keyboard())
    await callback.answer()

async def handle_learning_test(callback: types.CallbackQuery, bot: Bot):
    await start_learning_test(callback.from_user.id, bot)
    await callback.answer()

def register_learning_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        lambda c: handle_learning_menu(c, bot),
        lambda c: c.data == "menu:learning"
    )
    dp.register_callback_query_handler(
        lambda c: handle_learning_test(c, bot),
        lambda c: c.data == "learning:test"
    )
    dp.register_callback_query_handler(
        lambda c: learning_placeholder(c, bot),
        lambda c: c.data in ["learning:quiz", "learning:memorize"]
    )


