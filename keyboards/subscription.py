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

def subscription_period_keyboard(chat_id: int = None):
    """Создает клавиатуру выбора периода подписки с учетом скидок пользователя."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Получаем информацию о скидке пользователя
    discount_percent = 0
    if chat_id:
        try:
            from database.crud import get_user_streak, is_user_premium
            streak, _ = get_user_streak(chat_id)
            is_premium = is_user_premium(chat_id)
            
            # Рассчитываем скидку только для премиум пользователей
            if is_premium and streak > 0:
                discount_percent = min(30, streak)  # Максимум 30%
        except Exception:
            discount_percent = 0
    
    # Добавляем кнопки с учетом скидки
    for months, base_price in SUBSCRIPTION_PRICES.items():
        # Рассчитываем цену со скидкой
        if discount_percent > 0:
            discount_amount = base_price * (discount_percent / 100)
            final_price = base_price - discount_amount
        else:
            final_price = base_price
            
        if months == 1:
            if discount_percent > 0:
                text = f"1 месяц - {final_price:.0f}₽ (скидка {discount_percent}%)"
            else:
                text = f"1 месяц - {final_price:.0f}₽"
        elif months == 3:
            monthly_equivalent = final_price / months
            if discount_percent > 0:
                text = f"3 мес. - {final_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес, скидка {discount_percent}%)"
            else:
                text = f"3 мес. - {final_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)"
        elif months == 6:
            monthly_equivalent = final_price / months
            if discount_percent > 0:
                text = f"6 мес. - {final_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес, скидка {discount_percent}%)"
            else:
                text = f"6 мес. - {final_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)"
        elif months == 12:
            monthly_equivalent = final_price / months
            if discount_percent > 0:
                text = f"12 мес. - {final_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес, скидка {discount_percent}%)"
            else:
                text = f"12 мес. - {final_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)"
        
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