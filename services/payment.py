# services/payment.py
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, SUBSCRIPTION_PRICES

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
        Создает платеж для подписки через ЮKassa.
        
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
                
            # Получаем цену для указанного периода
            price = SUBSCRIPTION_PRICES.get(months)
            if not price:
                logger.error(f"Invalid subscription period: {months} months")
                return None
                
            logger.info(f"Creating payment for user {chat_id}, period: {months} months, amount: {price}")
            
            # Определяем описание периода
            period_description = {
                1: "1 месяц",
                3: "3 месяца", 
                6: "6 месяцев",
                12: "12 месяцев"
            }.get(months, f"{months} месяцев")
            
            payment = Payment.create({
                "amount": {
                    "value": f"{price:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/your_bot_name"  # Замените на имя вашего бота
                },
                "capture": True,
                "description": f"Premium подписка на {period_description} для пользователя {chat_id}",
                "receipt": {
                    "customer": {
                        "email": "noreply@yourdomain.com"  # Замените на ваш email
                    },
                    "items": [
                        {
                            "description": f"Premium подписка на {period_description}",
                            "quantity": "1.00",
                            "amount": {
                                "value": f"{price:.2f}",
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
                    "subscription_months": str(months)
                }
            }, uuid.uuid4())
            
            logger.info(f"Payment created successfully for user {chat_id}: {payment.id}")
            
            return {
                "payment_id": payment.id,
                "confirmation_url": payment.confirmation.confirmation_url,
                "status": payment.status,
                "amount": payment.amount.value,
                "months": months,
                "description": f"Premium на {period_description}"
            }
            
        except Exception as e:
            logger.error(f"Error creating payment for user {chat_id}: {e}")
            logger.error(f"Payment details - months: {months}, chat_id: {chat_id}")
            return None
    
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
                            logger.info(f"Extending existing subscription for user {chat_id}: current expiry {expires_at}, adding {months} months")
                            days = months * 30
                            new_expiry = current_expiry + timedelta(days=days)
                            return new_expiry.isoformat()
                        else:
                            logger.info(f"Existing subscription expired for user {chat_id}, starting new subscription from now")
                    except ValueError as e:
                        logger.error(f"Invalid expiry date format for user {chat_id}: {e}")
            
            # Если нет активной подписки или не передан chat_id, считаем от текущей даты
            days = months * 30
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
        Вычисляет экономию при покупке длительной подписки.
        
        Args:
            months: Количество месяцев
            
        Returns:
            Словарь с информацией об экономии
        """
        if months == 1:
            return {"savings": 0, "savings_percent": 0}
            
        monthly_price = SUBSCRIPTION_PRICES[1]
        actual_price = SUBSCRIPTION_PRICES.get(months, monthly_price * months)
        full_price = monthly_price * months
        
        savings = full_price - actual_price
        savings_percent = (savings / full_price) * 100 if full_price > 0 else 0
        
        return {
            "savings": savings,
            "savings_percent": round(savings_percent),
            "monthly_equivalent": round(actual_price / months, 2)
        }