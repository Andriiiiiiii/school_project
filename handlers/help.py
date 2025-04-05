# handlers/help.py
from aiogram import types, Dispatcher, Bot
from keyboards.submenus import help_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from functools import partial

async def show_help_callback(callback: types.CallbackQuery, bot: Bot):
    await callback.message.edit_text("Выберите пункт помощи:", reply_markup=help_menu_keyboard())
    await callback.answer()

async def process_help_about_callback(callback: types.CallbackQuery, bot: Bot):
    await callback.message.edit_text(
        "О боте:\nЭтот бот помогает изучать английские слова, тестировать уровень знаний, проводить викторины и организовывать обучение.",
        reply_markup=help_menu_keyboard()  # Добавляем клавиатуру для возврата
    )
    await callback.answer()

async def process_help_commands_callback(callback: types.CallbackQuery, bot: Bot):
    await callback.message.edit_text(
        "Список команд:\n/start - Перезапуск\n/menu - Главное меню\n/mode - Выбрать нейросеть\n/profile - Профиль пользователя\n/pay - Купить подписку\n/reset - Сброс контекста\n/help - Справка и помощь",
        reply_markup=help_menu_keyboard()  # Добавляем клавиатуру для возврата
    )
    await callback.answer()

async def process_help_feedback_callback(callback: types.CallbackQuery, bot: Bot):
    await callback.message.edit_text(
        "Обратная связь: напишите администратору на admin@example.com",
        reply_markup=help_menu_keyboard()  # Добавляем клавиатуру для возврата
    )
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
