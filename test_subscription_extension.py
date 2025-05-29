# test_subscription_extension.py
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_subscription_extension():
    """Тестирует логику продления подписки."""
    print("=== Тестирование логики продления подписки ===")
    
    try:
        from database import crud
        from services.payment import PaymentService
        
        # Тестовый пользователь
        test_chat_id = 999999
        
        # Имитируем активную подписку (истекает через 30 дней)
        current_expiry = datetime.now() + timedelta(days=30)
        crud.update_user_subscription(test_chat_id, "premium", current_expiry.isoformat(), "test_payment_1")
        
        print(f"✅ Создана тестовая подписка до: {current_expiry.strftime('%Y-%m-%d %H:%M')}")
        
        # Тестируем продление на 3 месяца
        new_expiry_str = PaymentService.calculate_subscription_expiry(3, test_chat_id)
        new_expiry = datetime.fromisoformat(new_expiry_str)
        
        print(f"📅 После продления на 3 месяца: {new_expiry.strftime('%Y-%m-%d %H:%M')}")
        
        # Проверяем, что добавилось именно 90 дней
        expected_expiry = current_expiry + timedelta(days=90)
        days_difference = abs((new_expiry - expected_expiry).days)
        
        if days_difference <= 1:  # Допускаем погрешность в 1 день
            print(f"✅ Продление работает корректно! Добавлено ~90 дней")
            total_days = (new_expiry - datetime.now()).days
            print(f"💎 Общий срок действия подписки: {total_days} дней")
        else:
            print(f"❌ Ошибка в расчете! Ожидалось: {expected_expiry}, получено: {new_expiry}")
        
        # Очищаем тестовые данные
        crud.update_user_subscription(test_chat_id, "free")
        print(f"🧹 Тестовые данные очищены")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_subscription_extension()