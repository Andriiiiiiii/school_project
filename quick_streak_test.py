# quick_streak_test_fixed.py
"""
ИСПРАВЛЕННЫЙ БЫСТРЫЙ ТЕСТ ФУНКЦИОНАЛА ДНЕЙ ПОДРЯД
Проверяет основные функции за минимальное время с исправлениями
"""

import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def quick_test():
    """Быстрая проверка основного функционала дней подряд."""
    print("⚡ ИСПРАВЛЕННЫЙ БЫСТРЫЙ ТЕСТ ФУНКЦИОНАЛА ДНЕЙ ПОДРЯД")
    print("=" * 60)
    
    test_user_id = 777777
    test_premium_id = 777778
    
    try:
        from database import crud
        from services.payment import PaymentService
        from database.db import db_manager
        
        print("🔧 Настройка тестового окружения...")
        
        # Очистка
        with db_manager.transaction() as tx:
            for user_id in [test_user_id, test_premium_id]:
                tx.execute("DELETE FROM users WHERE chat_id = ?", (user_id,))
                tx.execute("DELETE FROM dictionary WHERE chat_id = ?", (user_id,))
                tx.execute("DELETE FROM learned_words WHERE chat_id = ?", (user_id,))
                tx.execute("DELETE FROM active_payments WHERE chat_id = ?", (user_id,))
        
        # Создание пользователей
        crud.add_user(test_user_id)
        crud.add_user(test_premium_id)
        
        # Делаем премиум
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        crud.update_user_subscription(test_premium_id, "premium", future_date, "test")
        
        print("✅ Тестовые пользователи созданы")
        
        # Тест 1: Проверка импорта datetime
        print("\n1️⃣ Тест импорта datetime...")
        try:
            # Пытаемся вызвать функцию, которая использует datetime
            initial_streak, initial_date = crud.get_user_streak(test_user_id)
            print(f"   ✅ Функции с datetime работают (начальный streak: {initial_streak})")
        except NameError as e:
            if "datetime" in str(e):
                print(f"   ❌ Ошибка импорта datetime: {e}")
                print("   💡 Запустите: python fix_datetime_import.py")
                return False
            else:
                raise e
        
        # Тест 2: Базовые операции
        print("\n2️⃣ Тест базовых операций...")
        
        # Начальное состояние
        streak, date = crud.get_user_streak(test_user_id)
        assert streak == 0 and date is None, f"Начальное состояние неверное: {streak}, {date}"
        print("   ✅ Начальное состояние корректно")
        
        # Первый инкремент
        new_streak = crud.increment_user_streak(test_user_id)
        assert new_streak == 1, f"Первый инкремент должен дать 1, получено {new_streak}"
        print("   ✅ Первый инкремент работает")
        
        # Повторный инкремент в тот же день
        repeat_streak = crud.increment_user_streak(test_user_id)
        assert repeat_streak == 1, f"Повторный инкремент должен остаться 1, получено {repeat_streak}"
        print("   ✅ Повторный инкремент в тот же день работает")
        
        # Тест 3: Логика последовательных дней
        print("\n3️⃣ Тест логики последовательных дней...")
        
        # Устанавливаем вчерашний день
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_user_id, 5, yesterday)
        
        # Инкремент сегодня
        streak_today = crud.increment_user_streak(test_user_id)
        assert streak_today == 6, f"Streak должен увеличиться с 5 до 6, получено {streak_today}"
        print("   ✅ Логика последовательных дней работает")
        
        # Тест 4: Сброс при пропуске
        print("\n4️⃣ Тест сброса при пропуске дня...")
        
        # Устанавливаем позавчерашний день
        day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_user_id, 10, day_before_yesterday)
        
        # Инкремент сегодня (должен сброситься)
        reset_streak = crud.increment_user_streak(test_user_id)
        assert reset_streak == 1, f"При пропуске дня streak должен сброситься на 1, получено {reset_streak}"
        print("   ✅ Сброс при пропуске работает")
        
        # Тест 5: Функция сброса
        print("\n5️⃣ Тест функции сброса...")
        
        # Устанавливаем streak и сбрасываем
        crud.update_user_streak(test_user_id, 15, "2025-06-01")
        crud.reset_user_streak(test_user_id)
        
        streak_after_reset, date_after_reset = crud.get_user_streak(test_user_id)
        assert streak_after_reset == 0, f"После сброса streak должен быть 0, получено {streak_after_reset}"
        assert date_after_reset is None, f"После сброса дата должна быть None, получено {date_after_reset}"
        print("   ✅ Функция сброса работает")
        
        # Тест 6: Скидки
        print("\n6️⃣ Тест расчета скидок...")
        
        # Бесплатный пользователь
        crud.update_user_streak(test_user_id, 15, datetime.now().strftime("%Y-%m-%d"))
        free_discount = crud.calculate_streak_discount(test_user_id)
        assert free_discount == 0, f"Бесплатный пользователь не должен получать скидку, получено {free_discount}"
        print("   ✅ Скидка для бесплатного пользователя = 0%")
        
        # Премиум пользователь
        crud.update_user_streak(test_premium_id, 20, datetime.now().strftime("%Y-%m-%d"))
        premium_discount = crud.calculate_streak_discount(test_premium_id)
        assert premium_discount == 20, f"Премиум пользователь должен получать скидку 20%, получено {premium_discount}"
        print("   ✅ Скидка для премиум пользователя = 20%")
        
        # Максимальная скидка
        crud.update_user_streak(test_premium_id, 50, datetime.now().strftime("%Y-%m-%d"))
        max_discount = crud.calculate_streak_discount(test_premium_id)
        assert max_discount == 30, f"Максимальная скидка должна быть 30%, получено {max_discount}"
        print("   ✅ Максимальная скидка = 30%")
        
        # Тест 7: Интеграция с платежами
        print("\n7️⃣ Тест интеграции с платежами...")
        
        # Цена без скидки
        crud.update_user_streak(test_premium_id, 0, None)
        price_no_discount = PaymentService.calculate_discounted_price(test_premium_id, 1)
        assert not price_no_discount['has_discount'], "При streak=0 не должно быть скидки"
        assert price_no_discount['final_price'] == 299.0, f"Базовая цена должна быть 299, получено {price_no_discount['final_price']}"
        print("   ✅ Цена без скидки = 299₽")
        
        # Цена со скидкой
        crud.update_user_streak(test_premium_id, 15, datetime.now().strftime("%Y-%m-%d"))
        price_with_discount = PaymentService.calculate_discounted_price(test_premium_id, 1)
        expected_price = round(299.0 * 0.85, 2)  # 15% скидка, округляем до 2 знаков
        actual_price = round(price_with_discount['final_price'], 2)
        
        assert price_with_discount['has_discount'], "При streak=15 должна быть скидка"
        assert actual_price == expected_price, f"Цена со скидкой должна быть {expected_price}₽, получено {actual_price}₽"
        print(f"   ✅ Цена со скидкой 15% = {actual_price}₽")
        
        # Очистка
        print("\n🧹 Очистка тестовых данных...")
        with db_manager.transaction() as tx:
            for user_id in [test_user_id, test_premium_id]:
                tx.execute("DELETE FROM users WHERE chat_id = ?", (user_id,))
                tx.execute("DELETE FROM dictionary WHERE chat_id = ?", (user_id,))
                tx.execute("DELETE FROM learned_words WHERE chat_id = ?", (user_id,))
                tx.execute("DELETE FROM active_payments WHERE chat_id = ?", (user_id,))
        
        print("✅ Тестовые данные очищены")
        
        print("\n" + "=" * 60)
        print("🎉 ВСЕ БЫСТРЫЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Функционал дней подряд работает корректно")
        print("✅ Импорт datetime исправлен")
        print("✅ Все базовые операции функционируют")
        print("✅ Система скидок работает правильно")
        print("=" * 60)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        return False
    except NameError as e:
        if "datetime" in str(e):
            print(f"\n❌ ОШИБКА ИМПОРТА DATETIME: {e}")
            print("💡 Решение: запустите 'python fix_datetime_import.py'")
        else:
            print(f"\n❌ ОШИБКА ИМПОРТА: {e}")
        return False
    except Exception as e:
        print(f"\n❌ НЕОЖИДАННАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_test()
    if success:
        print("\n💡 Для полного тестирования запустите:")
        print("   python test_streak_full_functionality.py")
        print("\n🚀 Система готова к работе!")
    else:
        print("\n💡 Сначала исправьте проблемы:")
        print("   1. python fix_datetime_import.py")
        print("   2. python quick_streak_test_fixed.py")
    
    sys.exit(0 if success else 1)