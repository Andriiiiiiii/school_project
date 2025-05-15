# keyboards/main_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📌 Слова дня", callback_data="menu:words_day"),
        InlineKeyboardButton("🏋️ Практика", callback_data="menu:learning")
    )
    keyboard.add(
        InlineKeyboardButton("📖 Мой словарь", callback_data="menu:dictionary"),
        InlineKeyboardButton("🏠 Персонализация", callback_data="menu:settings")
    )
    keyboard.add(
        InlineKeyboardButton("📝 Тест дня", callback_data="quiz:start"),
        InlineKeyboardButton("ℹ️ Справка", callback_data="menu:help")
    )
    return keyboard
