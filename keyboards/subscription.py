# keyboards/subscription.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def subscription_menu_keyboard():
    """Создает клавиатуру главного меню подписки."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💎 Оформить Premium", callback_data="subscription:buy"),
        InlineKeyboardButton("📊 Мой статус", callback_data="subscription:status"),
        InlineKeyboardButton("ℹ️ О Premium", callback_data="subscription:info"),
        InlineKeyboardButton("🔙 Назад", callback_data="menu:back")
    )
    return keyboard

def payment_keyboard(payment_url: str):
    """Создает клавиатуру с кнопкой оплаты."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=payment_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data="subscription:check_payment"),
        InlineKeyboardButton("🔙 Назад", callback_data="subscription:menu")
    )
    return keyboard

def subscription_status_keyboard(is_premium: bool = False):
    """Создает клавиатуру для страницы статуса подписки."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    if not is_premium:
        keyboard.add(InlineKeyboardButton("💎 Оформить Premium", callback_data="subscription:buy"))
    else:
        keyboard.add(InlineKeyboardButton("🔄 Продлить Premium", callback_data="subscription:buy"))
    
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="subscription:menu")
    )
    return keyboard

def premium_info_keyboard():
    """Создает клавиатуру для информации о Premium."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💎 Оформить Premium", callback_data="subscription:buy"),
        InlineKeyboardButton("🔙 Назад", callback_data="subscription:menu")
    )
    return keyboard