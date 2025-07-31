# keyboards/referrals.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def referral_menu_keyboard():
    """Создает клавиатуру для меню рефералов."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📤 Поделиться ссылкой", callback_data="referrals:share"),
        InlineKeyboardButton("📊 Мои приглашения", callback_data="referrals:history"),
        InlineKeyboardButton("🔙 Назад", callback_data="menu:back")
    )
    return keyboard