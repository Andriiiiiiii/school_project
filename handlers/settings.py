# handlers/settings.py
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import main_menu_keyboard
from database import crud

async def send_settings_menu(chat_id: int, bot: Bot):
    keyboard = InlineKeyboardMarkup(row_width=2)
    topics = ['business', 'IT', 'travel', 'movies']
    buttons = [InlineKeyboardButton(text=t.capitalize(), callback_data=f"topic:{t}") for t in topics]
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("Установить время рассылки", callback_data="settime"))
    keyboard.add(InlineKeyboardButton("Назад", callback_data="menu:help"))
    await bot.send_message(chat_id, "Настройки:", reply_markup=keyboard)

async def process_set_time(callback_query: types.CallbackQuery, bot: Bot):
    chat_id = callback_query.from_user.id
    await bot.send_message(chat_id, "Введите время для получения слова дня в формате HH:MM (например, 09:00):")
    await callback_query.answer()

async def process_topic_selection(callback_query: types.CallbackQuery, bot: Bot):
    topic = callback_query.data.split(":")[1]
    chat_id = callback_query.from_user.id
    crud.update_user_topic(chat_id, topic)
    await bot.send_message(chat_id, f"Тема успешно изменена на {topic.capitalize()}.", reply_markup=main_menu_keyboard())
    await callback_query.answer()

def register_settings_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(lambda c: c.data == "settime", lambda c: process_set_time(c, bot))
    dp.register_callback_query_handler(lambda c: c.data.startswith("topic:"), lambda c: process_topic_selection(c, bot))
