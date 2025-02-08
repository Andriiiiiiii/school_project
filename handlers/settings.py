# handlers/settings.py
from aiogram import types, Dispatcher, Bot
from keyboards.submenus import settings_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from database import crud
from functools import partial

async def show_settings_callback(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    await bot.send_message(chat_id, "Настройки бота:", reply_markup=settings_menu_keyboard())
    await callback.answer()

async def process_settings_choice_callback(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    try:
        _, option = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return

    if option == "level":
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        for lvl in levels:
            keyboard.add(types.InlineKeyboardButton(lvl, callback_data=f"set_level:{lvl}"))
        await bot.send_message(chat_id, "Выберите уровень:", reply_markup=keyboard)
    elif option == "words":
        await bot.send_message(chat_id, "Введите количество слов в день:")
    elif option == "notifications":
        await bot.send_message(chat_id, "Введите количество уведомлений в день:")
    await callback.answer()

async def process_set_level_callback(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.from_user.id
    try:
        _, level = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Неверный формат данных.", show_alert=True)
        return
    crud.update_user_level(chat_id, level)
    await bot.send_message(chat_id, f"Уровень установлен на {level}.", reply_markup=main_menu_keyboard())
    await callback.answer()

def register_settings_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        partial(show_settings_callback, bot=bot),
        lambda c: c.data == "menu:settings"
    )
    dp.register_callback_query_handler(
        partial(process_settings_choice_callback, bot=bot),
        lambda c: c.data and c.data.startswith("settings:")
    )
    dp.register_callback_query_handler(
        partial(process_set_level_callback, bot=bot),
        lambda c: c.data and c.data.startswith("set_level:")
    )
