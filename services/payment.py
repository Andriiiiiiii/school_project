# services/payment.py
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, SUBSCRIPTION_PRICES
from database.db import db_manager

logger = logging.getLogger(__name__)

# Инициализация ЮKassa с отладкой
def initialize_yookassa():
    """Инициализирует ЮKassa с проверкой конфигурации."""
    try:
        if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
            logger.error("ЮKassa credentials not configured properly")
            logger.error(f"SHOP_ID: {YOOKASSA_SHOP_ID}")
            logger.error(f"SECRET_KEY: {'***' if YOOKASSA_SECRET_KEY else 'None'}")
            return False
            
        # Конфигурация ЮKassa
        Configuration.account_id = str(YOOKASSA_SHOP_ID)
        Configuration.secret_key = str(YOOKASSA_SECRET_KEY)
        
        logger.info(f"ЮKassa initialized with shop_id: {YOOKASSA_SHOP_ID}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing ЮKassa: {e}")
        return False

# Инициализируем при импорте модуля
_is_initialized = initialize_yookassa()

class PaymentService:
    @staticmethod
    def create_subscription_payment(chat_id: int, months: int = 1) -> Optional[Dict[str, Any]]:
        """
        Создает платеж для подписки через ЮKassa с учетом скидки за дни подряд.
        
        Args:
            chat_id: ID пользователя
            months: Количество месяцев подписки (1, 3, 6, 12)
            
        Returns:
            Словарь с данными платежа или None в случае ошибки
        """
        try:
            if not _is_initialized:
                logger.error("ЮKassa not initialized")
                return None
                
            # Получаем цену с учетом скидки
            price_info = PaymentService.calculate_discounted_price(chat_id, months)
            final_price = price_info["final_price"]
            
            logger.info(f"Creating payment for user {chat_id}, period: {months} months, amount: {final_price}")
            
            # Определяем описание периода
            period_description = {
                1: "1 месяц",
                3: "3 месяца", 
                6: "6 месяцев",
                12: "12 месяцев"
            }.get(months, f"{months} месяцев")
            
            # Формируем описание с учетом скидки
            description = f"Premium подписка на {period_description} для пользователя {chat_id}"
            if price_info["has_discount"]:
                description += f" (скидка {price_info['discount_percent']}%)"
            
            payment = Payment.create({
                "amount": {
                    "value": f"{final_price:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/your_bot_name"  # Замените на имя вашего бота
                },
                "capture": True,
                "description": description,
                "receipt": {
                    "customer": {
                        "email": "noreply@yourdomain.com"  # Замените на ваш email
                    },
                    "items": [
                        {
                            "description": f"Premium подписка на {period_description}",
                            "quantity": "1.00",
                            "amount": {
                                "value": f"{final_price:.2f}",
                                "currency": "RUB"
                            },
                            "vat_code": "1",  # Без НДС
                            "payment_mode": "full_payment",
                            "payment_subject": "service"
                        }
                    ]
                },
                "metadata": {
                    "chat_id": str(chat_id),
                    "subscription_type": "premium",
                    "subscription_months": str(months),
                    "base_price": str(price_info["base_price"]),
                    "discount_percent": str(price_info["discount_percent"]),
                    "final_price": str(final_price)
                }
            }, uuid.uuid4())
            
            logger.info(f"Payment created successfully for user {chat_id}: {payment.id}")
            
            return {
                "payment_id": payment.id,
                "confirmation_url": payment.confirmation.confirmation_url,
                "status": payment.status,
                "amount": payment.amount.value,
                "months": months,
                "description": f"Premium на {period_description}",
                "price_info": price_info
            }
            
        except Exception as e:
            logger.error(f"Error creating payment for user {chat_id}: {e}")
            logger.error(f"Payment details - months: {months}, chat_id: {chat_id}")
            return None
    
    @staticmethod
    def save_active_payment(chat_id: int, payment_id: str, amount: float, months: int, description: str):
        """Сохраняет активный платеж в базу данных."""
        try:
            with db_manager.transaction() as conn:
                conn.execute('''
                    INSERT INTO active_payments 
                    (chat_id, payment_id, amount, months, description, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (chat_id, payment_id, amount, months, description, 
                      datetime.now().isoformat(), 'pending'))
            logger.info(f"Saved active payment {payment_id} for user {chat_id}")
        except Exception as e:
            logger.error(f"Error saving active payment: {e}")
    
    @staticmethod
    def get_active_payments(chat_id: int = None) -> List[Dict[str, Any]]:
        """Получает активные платежи из базы данных."""
        try:
            with db_manager.get_cursor() as cursor:
                if chat_id:
                    cursor.execute('''
                        SELECT * FROM active_payments 
                        WHERE chat_id = ? AND processed = FALSE
                        ORDER BY created_at DESC
                    ''', (chat_id,))
                else:
                    cursor.execute('''
                        SELECT * FROM active_payments 
                        WHERE processed = FALSE
                        ORDER BY created_at DESC
                    ''')
                
                rows = cursor.fetchall()
                payments = []
                for row in rows:
                    payments.append({
                        'id': row[0],
                        'chat_id': row[1],
                        'payment_id': row[2],
                        'amount': row[3],
                        'months': row[4],
                        'description': row[5],
                        'created_at': row[6],
                        'status': row[7],
                        'processed': row[8]
                    })
                return payments
        except Exception as e:
            logger.error(f"Error getting active payments: {e}")
            return []
    
    @staticmethod
    def mark_payment_processed(payment_id: str):
        """Отмечает платеж как обработанный."""
        try:
            with db_manager.transaction() as conn:
                conn.execute('''
                    UPDATE active_payments 
                    SET processed = TRUE, status = 'completed'
                    WHERE payment_id = ?
                ''', (payment_id,))
            logger.info(f"Marked payment {payment_id} as processed")
        except Exception as e:
            logger.error(f"Error marking payment as processed: {e}")
    
    @staticmethod
    def check_payment_status(payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Проверяет статус платежа.
        
        Args:
            payment_id: ID платежа
            
        Returns:
            Словарь со статусом платежа или None в случае ошибки
        """
        try:
            if not _is_initialized:
                logger.error("ЮKassa not initialized")
                return None
                
            payment = Payment.find_one(payment_id)
            
            return {
                "payment_id": payment.id,
                "status": payment.status,
                "paid": payment.paid,
                "amount": payment.amount.value,
                "created_at": payment.created_at,
                "metadata": payment.metadata
            }
            
        except Exception as e:
            logger.error(f"Error checking payment status {payment_id}: {e}")
            return None
    
    @staticmethod
    async def check_and_process_user_payments(chat_id: int, bot=None) -> int:
        """
        Проверяет и обрабатывает все активные платежи пользователя.
        
        Args:
            chat_id: ID пользователя
            bot: Экземпляр бота для отправки уведомлений
            
        Returns:
            Количество обработанных платежей
        """
        processed_count = 0
        
        try:
            active_payments = PaymentService.get_active_payments(chat_id)
            
            for payment_data in active_payments:
                payment_id = payment_data['payment_id']
                months = payment_data['months']
                
                # Проверяем статус в ЮKassa
                status = PaymentService.check_payment_status(payment_id)
                
                if status and status["status"] == "succeeded" and status["paid"]:
                    # Платеж успешен - активируем подписку
                    from database import crud
                    
                    # Вычисляем дату окончания подписки
                    expiry_date = PaymentService.calculate_subscription_expiry(months, chat_id)
                    
                    # Обновляем подписку пользователя
                    crud.update_user_subscription(chat_id, "premium", expiry_date, payment_id)
                    
                    # Отмечаем платеж как обработанный
                    PaymentService.mark_payment_processed(payment_id)
                    
                    processed_count += 1
                    
                    # Отправляем уведомление пользователю, если передан бот
                    if bot:
                        try:
                            # Определяем тип операции
                            current_status, current_expires, _ = crud.get_user_subscription_status(chat_id)
                            is_extension = (current_status == 'premium' and current_expires)
                            
                            period_text = {
                                1: "1 месяц",
                                3: "3 месяца",
                                6: "6 месяцев",
                                12: "12 месяцев"
                            }.get(months, f"{months} месяцев")
                            
                            if is_extension:
                                message = (
                                    f"🎉 *Подписка продлена!*\n\n"
                                    f"💎 Добавлен период: {period_text}\n"
                                    f"Ваш Premium доступ продлен автоматически!"
                                )
                            else:
                                message = (
                                    f"🎉 *Premium активирован!*\n\n"
                                    f"💎 Период: {period_text}\n"
                                    f"Теперь у вас есть доступ ко всем наборам слов!"
                                )
                            
                            await bot.send_message(chat_id, message, parse_mode="Markdown")
                            logger.info(f"Sent subscription notification to user {chat_id}")
                            
                        except Exception as e:
                            logger.error(f"Error sending notification to user {chat_id}: {e}")
                    
                    logger.info(f"Successfully processed payment {payment_id} for user {chat_id}")
                
                elif status and status["status"] == "canceled":
                    # Платеж отменен
                    PaymentService.mark_payment_processed(payment_id)
                    logger.info(f"Payment {payment_id} was canceled")
        
        except Exception as e:
            logger.error(f"Error processing payments for user {chat_id}: {e}")
        
        return processed_count
    
    @staticmethod
    async def check_all_active_payments(bot=None) -> int:
        """
        Проверяет все активные платежи в системе.
        Используется в планировщике для автоматической обработки.
        
        Args:
            bot: Экземпляр бота для отправки уведомлений
            
        Returns:
            Количество обработанных платежей
        """
        processed_count = 0
        
        try:
            active_payments = PaymentService.get_active_payments()
            logger.info(f"Checking {len(active_payments)} active payments")
            
            for payment_data in active_payments:
                chat_id = payment_data['chat_id']
                payment_id = payment_data['payment_id']
                months = payment_data['months']
                created_at = payment_data['created_at']
                
                # Проверяем возраст платежа - если старше 24 часов, помечаем как истекший
                try:
                    created_time = datetime.fromisoformat(created_at)
                    if datetime.now() - created_time > timedelta(hours=24):
                        PaymentService.mark_payment_processed(payment_id)
                        logger.info(f"Marked expired payment {payment_id} as processed")
                        continue
                except Exception as e:
                    logger.error(f"Error parsing payment date: {e}")
                
                # Проверяем статус в ЮKassa
                status = PaymentService.check_payment_status(payment_id)
                
                if status and status["status"] == "succeeded" and status["paid"]:
                    # Платеж успешен - активируем подписку
                    from database import crud
                    
                    try:
                        # Вычисляем дату окончания подписки
                        expiry_date = PaymentService.calculate_subscription_expiry(months, chat_id)
                        
                        # Обновляем подписку пользователя
                        crud.update_user_subscription(chat_id, "premium", expiry_date, payment_id)
                        
                        # Отмечаем платеж как обработанный
                        PaymentService.mark_payment_processed(payment_id)
                        
                        processed_count += 1
                        
                        # Отправляем уведомление пользователю
                        if bot:
                            try:
                                period_text = {
                                    1: "1 месяц",
                                    3: "3 месяца",
                                    6: "6 месяцев",
                                    12: "12 месяцев"
                                }.get(months, f"{months} месяцев")
                                
                                message = (
                                    f"🎉 *Premium активирован!*\n\n"
                                    f"💎 Ваша подписка на {period_text} успешно оплачена!\n"
                                    f"Теперь у вас есть доступ ко всем наборам слов.\n\n"
                                    f"Перейдите в Настройки → Наборы слов для выбора новых наборов."
                                )
                                
                                await bot.send_message(chat_id, message, parse_mode="Markdown")
                                logger.info(f"Sent auto-activation notification to user {chat_id}")
                                
                            except Exception as e:
                                logger.error(f"Error sending auto-notification to user {chat_id}: {e}")
                        
                        logger.info(f"Auto-processed payment {payment_id} for user {chat_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing payment {payment_id}: {e}")
                
                elif status and status["status"] == "canceled":
                    # Платеж отменен
                    PaymentService.mark_payment_processed(payment_id)
                    logger.info(f"Auto-marked canceled payment {payment_id} as processed")
        
        except Exception as e:
            logger.error(f"Error in check_all_active_payments: {e}")
        
        if processed_count > 0:
            logger.info(f"Auto-processed {processed_count} payments")
        
        return processed_count
    
    @staticmethod
    def process_webhook(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обрабатывает webhook от ЮKassa.
        
        Args:
            data: Данные webhook
            
        Returns:
            Обработанные данные или None в случае ошибки
        """
        try:
            event = data.get("event")
            payment_data = data.get("object")
            
            if not payment_data:
                logger.error("No payment data in webhook")
                return None
                
            payment_id = payment_data.get("id")
            status = payment_data.get("status")
            metadata = payment_data.get("metadata", {})
            chat_id = metadata.get("chat_id")
            months = int(metadata.get("subscription_months", 1))
            
            logger.info(f"Webhook received: event={event}, payment_id={payment_id}, status={status}, months={months}")
            
            if event == "payment.succeeded" and status == "succeeded" and chat_id:
                return {
                    "chat_id": int(chat_id),
                    "payment_id": payment_id,
                    "status": status,
                    "amount": payment_data.get("amount", {}).get("value"),
                    "months": months,
                    "success": True
                }
            
            return {
                "payment_id": payment_id,
                "status": status,
                "success": False
            }
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return None
    
    @staticmethod
    def calculate_subscription_expiry(months: int = 1, chat_id: int = None) -> str:
        """
        Вычисляет дату окончания подписки с учетом существующей активной подписки.
        
        Args:
            months: Количество месяцев подписки
            chat_id: ID пользователя (для проверки существующей подписки)
            
        Returns:
            Дата в формате ISO string
        """
        try:
            # Избегаем циклического импорта
            from database import crud
            
            # Правильное соответствие месяцев к дням
            month_to_days = {
                1: 30,    # 1 месяц = 30 дней
                3: 90,    # 3 месяца = 90 дней  
                6: 180,   # 6 месяцев = 180 дней
                12: 365   # 12 месяцев = 365 дней (1 год)
            }
            
            days = month_to_days.get(months, months * 30)
            
            logger.info(f"Calculating expiry: {months} months = {days} days")
            
            # Если передан chat_id, проверяем существующую подписку
            if chat_id:
                status, expires_at, _ = crud.get_user_subscription_status(chat_id)
                
                # Если есть активная премиум подписка, продлеваем от даты окончания
                if status == 'premium' and expires_at:
                    try:
                        current_expiry = datetime.fromisoformat(expires_at)
                        now = datetime.now()
                        
                        # Если подписка еще активна, добавляем новый период к существующему сроку
                        if current_expiry > now:
                            logger.info(f"Extending existing subscription for user {chat_id}: current expiry {expires_at}, adding {days} days")
                            new_expiry = current_expiry + timedelta(days=days)
                            return new_expiry.isoformat()
                        else:
                            logger.info(f"Existing subscription expired for user {chat_id}, starting new subscription from now")
                    except ValueError as e:
                        logger.error(f"Invalid expiry date format for user {chat_id}: {e}")
            
            # Если нет активной подписки или не передан chat_id, считаем от текущей даты
            expiry_date = datetime.now() + timedelta(days=days)
            logger.info(f"Creating new subscription: {months} months ({days} days) from now")
            return expiry_date.isoformat()
            
        except Exception as e:
            logger.error(f"Error calculating subscription expiry: {e}")
            # Fallback к базовому расчету
            days = months * 30
            expiry_date = datetime.now() + timedelta(days=days)
            return expiry_date.isoformat()
    
    @staticmethod
    def get_subscription_prices() -> Dict[int, float]:
        """Возвращает словарь с ценами подписки."""
        return SUBSCRIPTION_PRICES.copy()
    
    @staticmethod
    def calculate_savings(months: int) -> Dict[str, Any]:
        """
        Вычисляет информацию о ценах без скидок (базовый расчет).
        
        Args:
            months: Количество месяцев
            
        Returns:
            Словарь с информацией о ценах
        """
        monthly_price = SUBSCRIPTION_PRICES[1]
        actual_price = SUBSCRIPTION_PRICES.get(months, monthly_price * months)
        full_price = monthly_price * months
        
        savings = full_price - actual_price
        savings_percent = (savings / full_price) * 100 if full_price > 0 else 0
        
        return {
            "monthly_equivalent": round(actual_price / months, 2),
            "base_price": actual_price,
            "savings": savings,
            "savings_percent": round(savings_percent),
            "full_price": full_price
        }

    @staticmethod
    def calculate_discounted_price(chat_id: int, months: int) -> dict:
        """
        Вычисляет цену со скидкой на основе дней подряд.
        
        Args:
            chat_id: ID пользователя
            months: Количество месяцев подписки
            
        Returns:
            Словарь с информацией о цене и скидке
        """
        try:
            from database import crud
            
            base_price = SUBSCRIPTION_PRICES.get(months, 299.00)
            discount_percent = crud.calculate_streak_discount(chat_id)
            
            # Валидация скидки
            discount_percent = max(0, min(30, discount_percent))
            
            if discount_percent > 0:
                discount_amount = base_price * (discount_percent / 100)
                final_price = base_price - discount_amount
            else:
                discount_amount = 0
                final_price = base_price
            
            return {
                "base_price": base_price,
                "discount_percent": discount_percent,
                "discount_amount": discount_amount,
                "final_price": final_price,
                "has_discount": discount_percent > 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating discounted price for user {chat_id}: {e}")
            return {
                "base_price": SUBSCRIPTION_PRICES.get(months, 299.00),
                "discount_percent": 0,
                "discount_amount": 0,
                "final_price": SUBSCRIPTION_PRICES.get(months, 299.00),
                "has_discount": False
            }