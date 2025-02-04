# handlers/settings.py
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.main_menu import main_menu_keyboard
from database import crud

# Отправка меню настроек
async def show_settings(chat_id: int, bot: Bot):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⏰ Утро", callback_data="set_time:morning"),
        InlineKeyboardButton("⏰ День", callback_data="set_time:day"),
        InlineKeyboardButton("⏰ Вечер", callback_data="set_time:evening"),
        InlineKeyboardButton("⏰ Отключить", callback_data="set_time:disable")
    )
    keyboard.add(InlineKeyboardButton("Назад", callback_data="menu:back"))
    await bot.send_message(chat_id, "Выберите время напоминаний:", reply_markup=keyboard)

# Callback-обработчик для установки времени
async def process_set_time(callback_query: types.CallbackQuery, bot: Bot):
    chat_id = callback_query.from_user.id
    option = callback_query.data.split(":")[1]
    # Пример: можно задать время в зависимости от выбора
    if option == "morning":
        time = "08:00"
    elif option == "day":
        time = "13:00"
    elif option == "evening":
        time = "18:00"
    elif option == "disable":
        time = "00:00"
    else:
        time = "09:00"
    crud.update_user_reminder_time(chat_id, time)
    await bot.send_message(chat_id, f"Время напоминаний установлено на {time}.", reply_markup=main_menu_keyboard())
    await callback_query.answer()

# Обёртки для регистрации обработчиков с правильным порядком аргументов
async def show_settings_callback(callback_query: types.CallbackQuery):
    await show_settings(callback_query.from_user.id, callback_query.bot)

async def process_set_time_callback(callback_query: types.CallbackQuery):
    await process_set_time(callback_query, callback_query.bot)

def register_settings_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(
        show_settings_callback,
        lambda c: c.data == "menu:settings"
    )
    dp.register_callback_query_handler(
        process_set_time_callback,
        lambda c: c.data.startswith("set_time:")
    )
