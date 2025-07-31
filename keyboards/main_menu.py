# keyboards/main_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard(chat_id: int = None):
    """Создает главное меню с кнопкой рефералов."""
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
        InlineKeyboardButton("👥 Пригласи друзей", callback_data="menu:referrals")
    )
    keyboard.add(
        InlineKeyboardButton("ℹ️ Справка", callback_data="menu:help")
    )
    return keyboard