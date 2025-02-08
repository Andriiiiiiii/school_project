# keyboards/main_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📌 Слова дня", callback_data="menu:words_day"),
        InlineKeyboardButton("📌 Обучение", callback_data="menu:learning"),
        InlineKeyboardButton("📌 Мой словарь", callback_data="menu:dictionary"),
        InlineKeyboardButton("📌 Настройки", callback_data="menu:settings"),
        InlineKeyboardButton("📌 Помощь", callback_data="menu:help")
    )
    return keyboard
