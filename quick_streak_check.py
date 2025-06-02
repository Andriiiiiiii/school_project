# quick_streak_check.py
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def quick_check():
    """Быстрая проверка основного функционала."""
    print("⚡ БЫСТРАЯ ПРОВЕРКА STREAK ФУНКЦИОНАЛА")
    print("=" * 50)
    
    try:
        from database import crud
        from services.payment import PaymentService
        
        # Используем специальный тестовый ID
        test_id = 777777
        
        # Очищаем тестового пользователя если он есть
        try:
            with crud.db_manager.transaction() as tx:
                tx.execute("DELETE FROM users WHERE chat_id = ?", (test_id,))
                tx.execute("DELETE FROM dictionary WHERE chat_id = ?", (test_id,))
                tx.execute("DELETE FROM learned_words WHERE chat_id = ?", (test_id,))
        except:
            pass
        
        # Создаем тестового пользователя
        crud.add_user(test_id)
        print(f"   Создан тестовый пользователь {test_id}")
        
        print("1. Проверка CRUD операций...")
        
        # Убеждаемся что streak = 0
        crud.reset_user_streak(test_id)
        initial_streak, _ = crud.get_user_streak(test_id)
        print(f"   Начальный streak: {initial_streak}")
        
        # Тест CRUD
        streak1 = crud.increment_user_streak(test_id)
        print(f"   После первого инкремента: {streak1}")
        
        streak2 = crud.increment_user_streak(test_id)  # Повторно в тот же день
        print(f"   После второго инкремента: {streak2}")
        
        assert streak1 == 1, f"Первый инкремент должен дать 1, получен {streak1}"
        assert streak2 == 1, f"Повторный инкремент должен остаться 1, получен {streak2}"
        print("   ✅ CRUD операции работают")
        
        print("2. Проверка скидок...")
        
        # Сначала проверяем бесплатного пользователя
        crud.update_user_streak(test_id, 15)
        discount_free = crud.calculate_streak_discount(test_id)
        print(f"   Скидка для бесплатного пользователя (streak=15): {discount_free}%")
        assert discount_free == 0, f"Бесплатные пользователи не должны получать скидку, получена {discount_free}%"
        
        # Делаем премиум и проверяем скидки
        future = (datetime.now() + timedelta(days=30)).isoformat()
        crud.update_user_subscription(test_id, "premium", future, "test")
        
        discount15 = crud.calculate_streak_discount(test_id)
        print(f"   Скидка для премиум пользователя (streak=15): {discount15}%")
        
        crud.update_user_streak(test_id, 35)
        discount35 = crud.calculate_streak_discount(test_id)
        print(f"   Скидка для премиум пользователя (streak=35): {discount35}%")
        
        assert discount15 == 15, f"Скидка за 15 дней должна быть 15%, получена {discount15}%"
        assert discount35 == 30, f"Скидка за 35 дней должна быть 30%, получена {discount35}%"
        print("   ✅ Расчет скидок работает")
        
        print("3. Проверка цен...")
        
        # Устанавливаем streak 20
        crud.update_user_streak(test_id, 20)
        price_info = PaymentService.calculate_discounted_price(test_id, 1)
        assert price_info['has_discount'], "Должна быть скидка"
        assert price_info['discount_percent'] == 20, f"Неверный процент скидки: ожидалось 20%, получено {price_info['discount_percent']}%"
        print("   ✅ Расчет цен работает")
        
        # Очистка
        crud.update_user_subscription(test_id, "free")
        crud.reset_user_streak(test_id)
        
        print("\n🎉 ВСЕ ОСНОВНЫЕ ФУНКЦИИ РАБОТАЮТ!")
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_check()
    if not success:
        print("\n💡 Запустите полное тестирование: python test_streak_functionality.py")