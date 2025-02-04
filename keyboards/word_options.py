# keyboards/word_options.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def word_options_keyboard(word: str):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔊 Послушать", callback_data=f"pronounce:{word}"),
        InlineKeyboardButton("📚 Добавить в словарь", callback_data=f"add:{word}")
    )
    return keyboard
