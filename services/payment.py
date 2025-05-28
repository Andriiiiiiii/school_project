# services/payment.py
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, SUBSCRIPTION_PRICE

logger = logging.getLogger(__name__)

# Настройка ЮKassa
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY
else:
    logger.warning("ЮKassa credentials not configured")

class PaymentService:
    @staticmethod
    def create_subscription_payment(chat_id: int, price: float = None) -> Optional[Dict[str, Any]]:
        """
        Создает платеж для подписки через ЮKassa.
        
        Args:
            chat_id: ID пользователя
            price: Цена подписки (по умолчанию из config)
            
        Returns:
            Словарь с данными платежа или None в случае ошибки
        """
        try:
            if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
                logger.error("ЮKassa credentials not configured")
                return None
                
            if price is None:
                price = SUBSCRIPTION_PRICE
                
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
                "description": f"Подписка Premium для пользователя {chat_id}",
                "metadata": {
                    "chat_id": str(chat_id),
                    "subscription_type": "monthly"
                }
            }, uuid.uuid4())
            
            logger.info(f"Payment created for user {chat_id}: {payment.id}")
            
            return {
                "payment_id": payment.id,
                "confirmation_url": payment.confirmation.confirmation_url,
                "status": payment.status,
                "amount": payment.amount.value
            }
            
        except Exception as e:
            logger.error(f"Error creating payment for user {chat_id}: {e}")
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
            if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
                logger.error("ЮKassa credentials not configured")
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
            
            logger.info(f"Webhook received: event={event}, payment_id={payment_id}, status={status}")
            
            if event == "payment.succeeded" and status == "succeeded" and chat_id:
                return {
                    "chat_id": int(chat_id),
                    "payment_id": payment_id,
                    "status": status,
                    "amount": payment_data.get("amount", {}).get("value"),
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
    def calculate_subscription_expiry() -> str:
        """
        Вычисляет дату окончания подписки (через месяц от текущей даты).
        
        Returns:
            Дата в формате ISO string
        """
        expiry_date = datetime.now() + timedelta(days=30)  # 30 дней подписки
        return expiry_date.isoformat()