# handlers/subscription.py
import logging
from functools import partial

from aiogram import Bot, Dispatcher, types

from config import SUBSCRIPTION_PRICE
from database import crud
from keyboards.subscription import (
    subscription_menu_keyboard, 
    payment_keyboard, 
    subscription_status_keyboard,
    premium_info_keyboard
)
from services.payment import PaymentService
from utils.subscription_helpers import format_subscription_status, get_premium_sets_for_level

logger = logging.getLogger(__name__)

# Словарь для хранения активных платежей
active_payments = {}

async def show_subscription_menu(callback: types.CallbackQuery, bot: Bot):
    """Показывает главное меню подписки."""
    await callback.message.edit_text(
        "💎 *Premium подписка*\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=subscription_menu_keyboard()
    )
    await callback.answer()

async def show_premium_info(callback: types.CallbackQuery, bot: Bot):
    """Показывает информацию о Premium подписке."""
    info_text = (
        "💎 *Premium подписка*\n\n"
        "🎯 *Что дает Premium:*\n"
        "• Доступ ко всем наборам слов\n"
        "• Специальные тематические наборы\n"
        "• Продвинутые наборы для каждого уровня\n"
        "• Регулярные обновления с новыми словами\n\n"
        "📚 *Доступные наборы:*\n"
        "• A1: Путешествия, Еда, Семья, Работа...\n"
        "• A2: Здоровье, Спорт, Хобби, Покупки...\n"
        "• B1: Бизнес, Технологии, Культура...\n"
        "• B2: Наука, Искусство, Политика...\n"
        "• C1: Профессиональная лексика, Академический английский...\n"
        "• C2: Идиомы, Сложные конструкции, Литературный язык...\n\n"
        f"💰 *Стоимость:* {SUBSCRIPTION_PRICE:.0f} руб/месяц\n\n"
        "🔒 *Без Premium* доступны только наборы \"Basic 1\" и \"Basic 2\" для каждого уровня."
    )
    
    await callback.message.edit_text(
        info_text,
        parse_mode="Markdown",
        reply_markup=premium_info_keyboard()
    )
    await callback.answer()

async def start_payment(callback: types.CallbackQuery, bot: Bot):
    """Начинает процесс оплаты Premium подписки."""
    chat_id = callback.from_user.id
    
    try:
        # Создаем платеж через ЮKassa
        payment_data = PaymentService.create_subscription_payment(chat_id)
        
        if not payment_data:
            await callback.message.edit_text(
                "❌ *Ошибка создания платежа*\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
                parse_mode="Markdown",
                reply_markup=subscription_menu_keyboard()
            )
            await callback.answer("Ошибка создания платежа", show_alert=True)
            return
        
        # Сохраняем информацию о платеже
        active_payments[chat_id] = {
            "payment_id": payment_data["payment_id"],
            "amount": payment_data["amount"],
            "created_at": payment_data.get("created_at")
        }
        
        await callback.message.edit_text(
            f"💳 *Оплата Premium подписки*\n\n"
            f"💰 Сумма: {payment_data['amount']} руб\n"
            f"📅 Срок: 30 дней\n\n"
            f"Нажмите кнопку \"Оплатить\" для перехода к оплате.\n"
            f"После оплаты нажмите \"Проверить оплату\".",
            parse_mode="Markdown",
            reply_markup=payment_keyboard(payment_data["confirmation_url"])
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error starting payment for user {chat_id}: {e}")
        await callback.message.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Не удалось создать платеж. Попробуйте позже.",
            parse_mode="Markdown",
            reply_markup=subscription_menu_keyboard()
        )
        await callback.answer("Ошибка создания платежа", show_alert=True)

async def check_payment_status(callback: types.CallbackQuery, bot: Bot):
    """Проверяет статус платежа."""
    chat_id = callback.from_user.id
    
    if chat_id not in active_payments:
        await callback.answer("Активных платежей не найдено", show_alert=True)
        return
    
    try:
        payment_id = active_payments[chat_id]["payment_id"]
        payment_status = PaymentService.check_payment_status(payment_id)
        
        if not payment_status:
            await callback.answer("Ошибка проверки статуса платежа", show_alert=True)
            return
        
        if payment_status["status"] == "succeeded" and payment_status["paid"]:
            # Платеж успешен - активируем подписку
            expiry_date = PaymentService.calculate_subscription_expiry()
            crud.update_user_subscription(
                chat_id, 
                "premium", 
                expiry_date, 
                payment_id
            )
            
            # Удаляем из активных платежей
            del active_payments[chat_id]
            
            await callback.message.edit_text(
                "🎉 *Платеж успешно завершен!*\n\n"
                "💎 Premium подписка активирована на 30 дней!\n\n"
                "Теперь у вас есть доступ ко всем наборам слов. "
                "Перейдите в Настройки → Наборы слов, чтобы выбрать новые наборы для изучения.",
                parse_mode="Markdown",
                reply_markup=subscription_menu_keyboard()
            )
            await callback.answer("Premium активирован! 🎉")
            
        elif payment_status["status"] == "pending":
            await callback.answer("Платеж в обработке. Попробуйте через несколько минут.", show_alert=True)
            
        elif payment_status["status"] == "canceled":
            await callback.answer("Платеж отменен", show_alert=True)
            del active_payments[chat_id]
            
        else:
            await callback.answer(f"Статус платежа: {payment_status['status']}", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error checking payment status for user {chat_id}: {e}")
        await callback.answer("Ошибка проверки статуса платежа", show_alert=True)

async def show_subscription_status(callback: types.CallbackQuery, bot: Bot):
    """Показывает текущий статус подписки пользователя."""
    chat_id = callback.from_user.id
    
    try:
        status_text = format_subscription_status(chat_id)
        is_premium = crud.is_user_premium(chat_id)
        
        # Добавляем информацию о доступных наборах
        if is_premium:
            status_text += "\n\n📚 *Доступные наборы:* Все наборы всех уровней"
        else:
            status_text += "\n\n📚 *Доступные наборы:* Только Basic 1 и Basic 2 для каждого уровня"
            
            # Показываем примеры премиум наборов
            user = crud.get_user(chat_id)
            if user:
                level = user[1]
                premium_sets = get_premium_sets_for_level(level)
                if premium_sets:
                    status_text += f"\n\n🔒 *Премиум наборы уровня {level}:*\n"
                    for i, set_name in enumerate(premium_sets[:3]):  # Показываем первые 3
                        status_text += f"• {set_name}\n"
                    if len(premium_sets) > 3:
                        status_text += f"• ... и еще {len(premium_sets) - 3} наборов"
        
        await callback.message.edit_text(
            status_text,
            parse_mode="Markdown",
            reply_markup=subscription_status_keyboard(is_premium)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing subscription status for user {chat_id}: {e}")
        await callback.message.edit_text(
            "❌ *Ошибка получения статуса*\n\n"
            "Попробуйте позже.",
            parse_mode="Markdown",
            reply_markup=subscription_menu_keyboard()
        )
        await callback.answer("Ошибка получения статуса", show_alert=True)

def register_subscription_handlers(dp: Dispatcher, bot: Bot):
    """Регистрирует обработчики для подписки."""
    
    # Главное меню подписки
    dp.register_callback_query_handler(
        partial(show_subscription_menu, bot=bot),
        lambda c: c.data == "menu:subscription"
    )
    
    dp.register_callback_query_handler(
        partial(show_subscription_menu, bot=bot),
        lambda c: c.data == "subscription:menu"
    )
    
    # Информация о Premium
    dp.register_callback_query_handler(
        partial(show_premium_info, bot=bot),
        lambda c: c.data == "subscription:info"
    )
    
    # Покупка подписки
    dp.register_callback_query_handler(
        partial(start_payment, bot=bot),
        lambda c: c.data == "subscription:buy"
    )
    
    # Проверка статуса платежа
    dp.register_callback_query_handler(
        partial(check_payment_status, bot=bot),
        lambda c: c.data == "subscription:check_payment"
    )
    
    # Статус подписки
    dp.register_callback_query_handler(
        partial(show_subscription_status, bot=bot),
        lambda c: c.data == "subscription:status"
    )