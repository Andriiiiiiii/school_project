# keyboards/main_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📖 Получить слово дня", callback_data="menu:get_word"),
        InlineKeyboardButton("🔧 Настройки", callback_data="menu:settings"),
        InlineKeyboardButton("📚 Мой словарь", callback_data="menu:my_dictionary"),
        InlineKeyboardButton("📝 Викторина", callback_data="menu:quiz"),
        InlineKeyboardButton("❓ Помощь", callback_data="menu:help"),
        InlineKeyboardButton("📝 Тест уровня", callback_data="menu:test")
    )
    return keyboard

