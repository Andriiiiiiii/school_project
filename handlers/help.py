# handlers/help.py
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.main_menu import main_menu_keyboard

# Отправка главного меню помощи
async def show_help_menu(chat_id: int, bot: Bot):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("ℹ️ О боте", callback_data="help:about"),
        InlineKeyboardButton("📜 Список команд", callback_data="help:commands"),
        InlineKeyboardButton("✉️ Обратная связь", callback_data="help:feedback"),
        InlineKeyboardButton("Назад", callback_data="menu:back")
    )
    await bot.send_message(chat_id, "Выберите, что хотите узнать:", reply_markup=keyboard)

# Callback обработчики для каждого пункта помощи
async def process_help_about(callback_query: types.CallbackQuery, bot: Bot):
    await bot.send_message(callback_query.from_user.id,
                           "О боте:\nЭтот бот помогает изучать английские слова, проводить викторины, тестировать уровень и т.д.")
    await callback_query.answer()

async def process_help_commands(callback_query: types.CallbackQuery, bot: Bot):
    await bot.send_message(callback_query.from_user.id,
                           "Список команд:\n/start - Запуск бота\n/help - Помощь\n/settings - Настройки\n/dictionary - Мой словарь\n/quiz - Викторина\n/test - Тест уровня")
    await callback_query.answer()

async def process_help_feedback(callback_query: types.CallbackQuery, bot: Bot):
    await bot.send_message(callback_query.from_user.id,
                           "Обратная связь:\nПишите: admin@example.com")
    await callback_query.answer()

def register_help_handlers(dp: Dispatcher, bot: Bot):
    dp.register_callback_query_handler(lambda c: c.data == "menu:help", lambda c: show_help_menu(c.from_user.id, bot))
    dp.register_callback_query_handler(lambda c: c.data == "help:about", lambda c: process_help_about(c, bot))
    dp.register_callback_query_handler(lambda c: c.data == "help:commands", lambda c: process_help_commands(c, bot))
    dp.register_callback_query_handler(lambda c: c.data == "help:feedback", lambda c: process_help_feedback(c, bot))
