# test_yookassa.py
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_yookassa_config():
    """Тестирует конфигурацию ЮKassa с разными периодами."""
    print("=== Тестирование конфигурации ЮKassa с разными планами ===")
    
    # Проверяем переменные окружения
    shop_id = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    
    print(f"SHOP_ID: {shop_id}")
    print(f"SECRET_KEY: {secret_key[:20]}... (обрезан)" if secret_key else "SECRET_KEY: None")
    
    if not shop_id or not secret_key:
        print("❌ Ошибка: переменные окружения не загружены!")
        return False
    
    # Тестируем инициализацию ЮKassa
    try:
        from yookassa import Configuration
        Configuration.account_id = str(shop_id)
        Configuration.secret_key = str(secret_key)
        print("✅ ЮKassa конфигурация успешно установлена")
        
        # Тестируем создание платежей для разных периодов
        from services.payment import PaymentService
        from config import SUBSCRIPTION_PRICES
        
        print(f"\n📊 Доступные планы подписки:")
        for months, price in SUBSCRIPTION_PRICES.items():
            print(f"  {months} мес. - {price}₽")
        
        # Тестируем создание платежа для каждого периода
        for months in [1, 3, 6, 12]:
            print(f"\n🧪 Тестирование платежа на {months} мес...")
            result = PaymentService.create_subscription_payment(12345, months)
            
            if result:
                print(f"✅ Платеж на {months} мес. создан успешно!")
                print(f"   Payment ID: {result['payment_id']}")
                print(f"   Amount: {result['amount']}₽")
                print(f"   Description: {result['description']}")
            else:
                print(f"❌ Ошибка создания платежа на {months} мес.")
                return False
        
        print("\n🎉 Все тесты пройдены успешно!")
        return True
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    success = test_yookassa_config()
    if success:
        print("\n🎉 Все тесты пройдены успешно!")
        print("\n💡 Теперь можно тестировать подписку в боте:")
        print("   1. Запустите бота")
        print("   2. Перейдите в Персонализация → Подписка")
        print("   3. Выберите период подписки")
        print("   4. Протестируйте оплату")
    else:
        print("\n❌ Есть проблемы с конфигурацией")