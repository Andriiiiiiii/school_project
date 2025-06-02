# handlers/subscription.py
import logging
from datetime import datetime
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
from aiogram.utils.exceptions import MessageNotModified

logger = logging.getLogger(__name__)

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
    """Показывает планы подписки с ценами и скидками."""
    chat_id = callback.from_user.id
    
    # Получаем информацию о скидке пользователя
    try:
        from database.crud import get_user_streak, is_user_premium
        streak, _ = get_user_streak(chat_id)
        is_premium = is_user_premium(chat_id)
        
        # Рассчитываем скидку только для премиум пользователей
        if is_premium and streak > 0:
            discount_percent = min(30, streak)  # Максимум 30%
        else:
            discount_percent = 0
    except Exception as e:
        logger.error(f"Error getting user discount info: {e}")
        discount_percent = 0
        streak = 0
    
    plans_text = "💎 <b>Выберите план Premium подписки</b>\n\n"
    
    # Добавляем информацию о скидке, если она есть
    if discount_percent > 0:
        plans_text += f"🔥 <b>Ваша скидка: {discount_percent}% (за {streak} дней подряд)</b>\n\n"
    
    plans_text += "📊 <b>Доступные планы:</b>\n\n"
    
    # Добавляем информацию о каждом плане с учетом скидки
    for months, base_price in SUBSCRIPTION_PRICES.items():
        # Рассчитываем цену со скидкой
        if discount_percent > 0:
            discount_amount = base_price * (discount_percent / 100)
            final_price = base_price - discount_amount
        else:
            final_price = base_price
            
        if months == 1:
            if discount_percent > 0:
                plans_text += f"🗓 <b>1 месяц</b>\n"
                plans_text += f"   <s>{base_price:.0f}₽</s> → <b>{final_price:.0f}₽</b>\n\n"
            else:
                plans_text += f"🗓 <b>1 месяц</b> - {base_price:.0f}₽\n\n"
        elif months == 3:
            monthly_equivalent = final_price / months
            if discount_percent > 0:
                plans_text += f"🗓 <b>3 месяца</b>\n"
                plans_text += f"   <s>{base_price:.0f}₽</s> → <b>{final_price:.0f}₽</b> ({monthly_equivalent:.0f}₽/мес)\n\n"
            else:
                plans_text += f"🗓 <b>3 месяца</b> - {base_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)\n\n"
        elif months == 6:
            monthly_equivalent = final_price / months
            if discount_percent > 0:
                plans_text += f"🗓 <b>6 месяцев</b>\n"
                plans_text += f"   <s>{base_price:.0f}₽</s> → <b>{final_price:.0f}₽</b> ({monthly_equivalent:.0f}₽/мес)\n\n"
            else:
                plans_text += f"🗓 <b>6 месяцев</b> - {base_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)\n\n"
        elif months == 12:
            monthly_equivalent = final_price / months
            if discount_percent > 0:
                plans_text += f"🗓 <b>1 год</b>\n"
                plans_text += f"   <s>{base_price:.0f}₽</s> → <b>{final_price:.0f}₽</b> ({monthly_equivalent:.0f}₽/мес)\n"
                plans_text += f"   ⭐ <b>Самый выгодный план!</b>\n\n"
            else:
                plans_text += f"🗓 <b>1 год</b> - {base_price:.0f}₽ ({monthly_equivalent:.0f}₽/мес)\n"
                plans_text += f"   ⭐ <b>Самый выгодный план!</b>\n\n"
    
    if discount_percent == 0:
        plans_text += "💡 <b>Совет:</b> Проходите тесты дня подряд, чтобы получать скидки!\n\n"
    
    plans_text += "Выберите подходящий план:"
    
    try:
        await callback.message.edit_text(
            plans_text,
            parse_mode="HTML",  # Изменили на HTML
            reply_markup=subscription_period_keyboard(chat_id)
        )
    except MessageNotModified:
        pass
    except Exception as e:
        logger.error(f"Error editing subscription plans message: {e}")
        await bot.send_message(
            chat_id,
            plans_text,
            parse_mode="HTML",  # Изменили на HTML
            reply_markup=subscription_period_keyboard(chat_id)
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
        # Сначала проверяем и обрабатываем любые активные платежи пользователя
        await PaymentService.check_and_process_user_payments(chat_id, bot)
        
        # Получаем информацию о цене с учетом скидки
        price_info = PaymentService.calculate_discounted_price(chat_id, months)
        
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
        
        # Сохраняем платеж в базу данных
        PaymentService.save_active_payment(
            chat_id=chat_id,
            payment_id=payment_data["payment_id"],
            amount=float(payment_data["amount"]),
            months=months,
            description=payment_data["description"]
        )
        
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
            message_text = f"💳 *Продление Premium подписки*\n\n"
        else:
            message_text = f"💳 *Оплата Premium подписки*\n\n"
            
        message_text += f"📅 Период: {period_text}\n"
        
        # Добавляем информацию о цене и скидке
        if price_info["has_discount"]:
            message_text += f"💰 Базовая цена: <s>{price_info['base_price']:.0f} руб</s>\n"
            message_text += f"🔥 Скидка ({price_info['discount_percent']}%): -{price_info['discount_amount']:.0f} руб\n"
            message_text += f"💸 К оплате: <b>{price_info['final_price']:.0f} руб</b>\n\n"
            
            # И измените parse_mode на HTML:
            await callback.message.edit_text(
                message_text,
                parse_mode="HTML",
                reply_markup=payment_keyboard(payment_data["confirmation_url"], months)
            )
            
            # Получаем информацию о streak
            try:
                streak, _ = crud.get_user_streak(chat_id)
                message_text += f"🎯 Ваша серия: {streak} дней подряд\n\n"
            except Exception:
                pass
        else:
            message_text += f"💰 Сумма: {price_info['final_price']:.0f} руб\n\n"
        
        if is_extension:
            message_text += f"⏰ Текущая подписка действует еще {current_days} дней\n\n"
            message_text += f"После оплаты подписка будет продлена автоматически.\n"
        
        message_text += f"Нажмите кнопку \"Оплатить\" для перехода к оплате.\n\n"
        message_text += f"ℹ️ *Подписка активируется автоматически после оплаты*"
        
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
    """Проверяет статус платежа вручную."""
    chat_id = callback.from_user.id
    
    # Извлекаем количество месяцев из callback_data
    try:
        months = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        months = 1
    
    try:
        # Проверяем и обрабатываем все активные платежи пользователя
        processed_count = await PaymentService.check_and_process_user_payments(chat_id, bot)
        
        if processed_count > 0:
            await callback.answer("Платеж обработан успешно! 🎉")
        else:
            await callback.message.edit_text(
                "🔄 *Проверка платежа*\n\n"
                "Платеж не найден или еще обрабатывается.\n"
                "Попробуйте через несколько минут или обратитесь в поддержку.",
                parse_mode="Markdown",
                reply_markup=subscription_menu_keyboard()
            )
            await callback.answer("Активных платежей не найдено")
        
    except Exception as e:
        logger.error(f"Error checking payment status for user {chat_id}: {e}")
        await callback.answer("Ошибка проверки статуса платежа", show_alert=True)

async def show_subscription_status(callback: types.CallbackQuery, bot: Bot):
    """Показывает текущий статус подписки пользователя."""
    chat_id = callback.from_user.id
    
    try:
        # Сначала проверяем активные платежи
        await PaymentService.check_and_process_user_payments(chat_id, bot)
        
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