# keyboards/subscription.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SUBSCRIPTION_PRICES

def subscription_menu_keyboard():
    """Создает клавиатуру главного меню подписки."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💎 Оформить Premium", callback_data="subscription:choose_period"),
        InlineKeyboardButton("📊 Мой статус", callback_data="subscription:status"),
        InlineKeyboardButton("ℹ️ О Premium", callback_data="subscription:info"),
        InlineKeyboardButton("🔙 Назад", callback_data="menu:back")
    )
    return keyboard

def subscription_period_keyboard():
    """Создает клавиатуру выбора периода подписки."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Добавляем кнопки без лишних расчетов
    for months, price in SUBSCRIPTION_PRICES.items():
        if months == 1:
            text = f"1 месяц - {price:.0f}₽"
        elif months == 3:
            monthly_equivalent = price / months
            text = f"3 мес. - {price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)"
        elif months == 6:
            monthly_equivalent = price / months
            text = f"6 мес. - {price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)"
        elif months == 12:
            monthly_equivalent = price / months
            text = f"12 мес. - {price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)"
        
        keyboard.add(InlineKeyboardButton(text, callback_data=f"subscription:buy:{months}"))
    
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="subscription:menu"))
    return keyboard

def payment_keyboard(payment_url: str, months: int):
    """Создает клавиатуру с кнопкой оплаты."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=payment_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"subscription:check_payment:{months}"),
        InlineKeyboardButton("🔙 Назад", callback_data="subscription:choose_period")
    )
    return keyboard

def subscription_status_keyboard(is_premium: bool = False):
    """Создает клавиатуру для страницы статуса подписки."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    if not is_premium:
        keyboard.add(InlineKeyboardButton("💎 Оформить Premium", callback_data="subscription:choose_period"))
    else:
        keyboard.add(InlineKeyboardButton("🔄 Продлить Premium", callback_data="subscription:choose_period"))
    
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="subscription:menu")
    )
    return keyboard

def premium_info_keyboard():
    """Создает клавиатуру для информации о Premium."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💎 Выбрать план", callback_data="subscription:choose_period"),
        InlineKeyboardButton("🔙 Назад", callback_data="subscription:menu")
    )
    return keyboard