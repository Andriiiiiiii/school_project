# handlers/help.py
from aiogram import types, Dispatcher, Bot
from keyboards.submenus import help_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from functools import partial

async def show_help_callback(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    await bot.send_message(chat_id, "Выберите пункт помощи:", reply_markup=help_menu_keyboard())
    await callback.answer()

async def process_help_about_callback(callback: types.CallbackQuery, bot: Bot):
    await bot.send_message(callback.from_user.id,
                           "О боте:\nЭтот бот помогает изучать английские слова, тестировать уровень знаний, проводить викторины и организовывать обучение.")
    await callback.answer()

async def process_help_commands_callback(callback: types.CallbackQuery, bot: Bot):
    await bot.send_message(callback.from_user.id,
                           "Список команд:\n/start, /help, /settings, /dictionary, /quiz, /test")
    await callback.answer()

async def process_help_feedback_callback(callback: types.CallbackQuery, bot: Bot):
    await bot.send_message(callback.from_user.id,
                           "Обратная связь: напишите администратору на admin@example.com")
    await callback.answer()

def register_help_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        partial(show_help_callback, bot=bot),
        lambda c: c.data == "menu:help"
    )
    dp.register_callback_query_handler(
        partial(process_help_about_callback, bot=bot),
        lambda c: c.data == "help:about"
    )
    dp.register_callback_query_handler(
        partial(process_help_commands_callback, bot=bot),
        lambda c: c.data == "help:commands"
    )
    dp.register_callback_query_handler(
        partial(process_help_feedback_callback, bot=bot),
        lambda c: c.data == "help:feedback"
    )
