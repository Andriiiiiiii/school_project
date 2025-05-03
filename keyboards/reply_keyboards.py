# keyboards/reply_keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard():
    """Creates a simplified menu with just the start command."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("/start"))
    return keyboard

def get_remove_keyboard():
    """Убирает клавиатуру."""
    return ReplyKeyboardMarkup(resize_keyboard=True, remove_keyboard=True)