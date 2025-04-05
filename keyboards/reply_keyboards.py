# keyboards/reply_keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard():
    """Создает выдвигающееся меню с основными командами бота."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    
    keyboard.add(KeyboardButton("Перезапуск /start"))
    keyboard.add(KeyboardButton("Выбрать нейросеть /mode"))
    keyboard.add(KeyboardButton("Профиль пользователя /profile"))
    keyboard.add(KeyboardButton("Купить подписку /pay"))
    keyboard.add(KeyboardButton("Сброс контекста /reset"))
    keyboard.add(KeyboardButton("Закрыть меню"))
    
    return keyboard

def get_remove_keyboard():
    """Убирает клавиатуру."""
    return ReplyKeyboardMarkup(resize_keyboard=True, remove_keyboard=True)