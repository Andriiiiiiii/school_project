# handlers/subscription.py
import logging
from functools import partial

from aiogram import Bot, Dispatcher, types

from config import SUBSCRIPTION_PRICES
from database import crud
from keyboards.subscription import (
    subscription_menu_keyboard, 
    subscription_period_keyboard,
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
        "🔒 *Без Premium* доступны только наборы \"Basic 1\" и \"Basic 2\" для каждого уровня."
    )
    
    await callback.message.edit_text(
        info_text,
        parse_mode="Markdown",
        reply_markup=premium_info_keyboard()
    )
    await callback.answer()

async def show_subscription_plans(callback: types.CallbackQuery, bot: Bot):
    """Показывает планы подписки с ценами."""
    plans_text = (
        "💎 *Выберите план Premium подписки*\n\n"
        "📊 *Доступные планы:*\n\n"
    )
    
    # Добавляем информацию о каждом плане
    for months, price in SUBSCRIPTION_PRICES.items():
        savings_info = PaymentService.calculate_savings(months)
        
        if months == 1:
            plans_text += f"🗓 *1 месяц* - {price:.0f}₽\n"
        elif months == 3:
            savings = savings_info['savings']
            plans_text += f"🗓 *3 месяца* - {price:.0f}₽\n"
            plans_text += f"   💰 Экономия: {savings:.0f}₽ ({savings_info['savings_percent']}%)\n"
        elif months == 6:
            savings = savings_info['savings']
            plans_text += f"🗓 *6 месяцев* - {price:.0f}₽\n"
            plans_text += f"   💰 Экономия: {savings:.0f}₽ ({savings_info['savings_percent']}%)\n"
        elif months == 12:
            savings = savings_info['savings']
            plans_text += f"🗓 *1 год* - {price:.0f}₽\n"
            plans_text += f"   💰 Экономия: {savings:.0f}₽ ({savings_info['savings_percent']}%)\n"
            plans_text += f"   ⭐ *Самый выгодный план!*\n"
        
        plans_text += "\n"
    
    plans_text += "Выберите подходящий план:"
    
    await callback.message.edit_text(
        plans_text,
        parse_mode="Markdown",
        reply_markup=subscription_period_keyboard()
    )
    await callback.answer()

async def start_payment(callback: types.CallbackQuery, bot: Bot):
    """Начинает процесс оплаты Premium подписки."""
    # Извлекаем количество месяцев из callback_data
    try:
        months = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        months = 1
    
    chat_id = callback.from_user.id
    
    try:
        # Создаем платеж через ЮKassa
        payment_data = PaymentService.create_subscription_payment(chat_id, months)
        
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
            "months": months,
            "description": payment_data["description"]
        }
        
        # Проверяем, есть ли активная подписка
        current_status, current_expires, _ = crud.get_user_subscription_status(chat_id)
        is_extension = (current_status == 'premium' and current_expires and 
                       datetime.fromisoformat(current_expires) > datetime.now())
        
        # Форматируем описание периода
        period_text = {
            1: "1 месяц",
            3: "3 месяца",
            6: "6 месяцев", 
            12: "12 месяцев"
        }.get(months, f"{months} месяцев")
        
        # Формируем сообщение в зависимости от того, продление это или новая подписка
        if is_extension:
            current_days = (datetime.fromisoformat(current_expires) - datetime.now()).days
            message_text = (
                f"💳 *Продление Premium подписки*\n\n"
                f"📅 Добавляемый период: {period_text}\n"
                f"💰 Сумма: {payment_data['amount']} руб\n"
                f"⏰ Текущая подписка действует еще {current_days} дней\n\n"
                f"После оплаты подписка будет продлена на {period_text}.\n"
                f"Нажмите кнопку \"Оплатить\" для перехода к оплате."
            )
        else:
            message_text = (
                f"💳 *Оплата Premium подписки*\n\n"
                f"📅 Период: {period_text}\n"
                f"💰 Сумма: {payment_data['amount']} руб\n\n"
                f"Нажмите кнопку \"Оплатить\" для перехода к оплате.\n"
                f"После оплаты нажмите \"Проверить оплату\"."
            )
        
        await callback.message.edit_text(
            message_text,
            parse_mode="Markdown",
            reply_markup=payment_keyboard(payment_data["confirmation_url"], months)
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
    
    # Извлекаем количество месяцев из callback_data
    try:
        months = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        months = 1
    
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
            # Платеж успешен - активируем/продлеваем подписку
            
            # Получаем информацию о текущей подписке
            current_status, current_expires, _ = crud.get_user_subscription_status(chat_id)
            is_extension = (current_status == 'premium' and current_expires and 
                          datetime.fromisoformat(current_expires) > datetime.now())
            
            # Вычисляем новую дату окончания с учетом существующей подписки
            expiry_date = PaymentService.calculate_subscription_expiry(months, chat_id)
            crud.update_user_subscription(
                chat_id, 
                "premium", 
                expiry_date, 
                payment_id
            )
            
            # Удаляем из активных платежей
            del active_payments[chat_id]
            
            period_text = {
                1: "1 месяц",
                3: "3 месяца",
                6: "6 месяцев",
                12: "12 месяцев"
            }.get(months, f"{months} месяцев")
            
            # Формируем сообщение в зависимости от того, продление это или новая подписка
            if is_extension:
                # Вычисляем общий срок действия
                new_expiry = datetime.fromisoformat(expiry_date)
                total_days = (new_expiry - datetime.now()).days
                
                success_message = (
                    f"🎉 *Подписка успешно продлена!*\n\n"
                    f"💎 Добавлен период: {period_text}\n"
                    f"⏰ Общий срок действия: {total_days} дней\n\n"
                    f"Ваша Premium подписка была продлена. "
                    f"Вы по-прежнему имеете доступ ко всем наборам слов."
                )
            else:
                success_message = (
                    f"🎉 *Платеж успешно завершен!*\n\n"
                    f"💎 Premium подписка активирована на {period_text}!\n\n"
                    f"Теперь у вас есть доступ ко всем наборам слов. "
                    f"Перейдите в Настройки → Наборы слов, чтобы выбрать новые наборы для изучения."
                )
            
            await callback.message.edit_text(
                success_message,
                parse_mode="Markdown",
                reply_markup=subscription_menu_keyboard()
            )
            
            if is_extension:
                await callback.answer("Подписка продлена! 🎉")
            else:
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
    
    # Выбор плана подписки
    dp.register_callback_query_handler(
        partial(show_subscription_plans, bot=bot),
        lambda c: c.data == "subscription:choose_period"
    )
    
    # Покупка подписки (с указанием периода)
    dp.register_callback_query_handler(
        partial(start_payment, bot=bot),
        lambda c: c.data.startswith("subscription:buy:")
    )
    
    # Проверка статуса платежа (с указанием периода) 
    dp.register_callback_query_handler(
        partial(check_payment_status, bot=bot),
        lambda c: c.data.startswith("subscription:check_payment:")
    )
    
    # Статус подписки
    dp.register_callback_query_handler(
        partial(show_subscription_status, bot=bot),
        lambda c: c.data == "subscription:status"
    )