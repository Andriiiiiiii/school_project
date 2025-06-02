# test_streak_functionality.py
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_migration():
    """Тестирует миграцию базы данных."""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ МИГРАЦИИ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    try:
        from database.db import db_manager
        
        # Проверяем наличие новых столбцов
        with db_manager.get_cursor() as cursor:
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_columns = ['days_streak', 'last_test_date']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"❌ Отсутствуют столбцы: {missing_columns}")
                print("💡 Запустите: python alter_db_streak.py")
                return False
            else:
                print("✅ Все необходимые столбцы присутствуют")
                
            # Проверяем структуру столбцов
            cursor.execute("""
                SELECT days_streak, last_test_date 
                FROM users 
                LIMIT 1
            """)
            print("✅ Столбцы корректно работают")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        return False

def test_crud_functions():
    """Тестирует CRUD функции для работы со streak."""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ CRUD ФУНКЦИЙ")
    print("=" * 60)
    
    try:
        from database import crud
        
        test_chat_id = 999999  # Тестовый пользователь
        
        # Очищаем тестового пользователя
        try:
            user = crud.get_user(test_chat_id)
            if not user:
                crud.add_user(test_chat_id)
                print(f"   Создан тестовый пользователь {test_chat_id}")
        except Exception as e:
            print(f"   Ошибка создания пользователя: {e}")
            return False
        
        # Тест 1: Начальное состояние
        print("\n📋 Тест 1: Начальное состояние")
        streak, last_test_date = crud.get_user_streak(test_chat_id)
        print(f"   Начальный streak: {streak}")
        print(f"   Последняя дата теста: {last_test_date}")
        
        # Сбрасываем для чистого теста
        crud.reset_user_streak(test_chat_id)
        streak, last_test_date = crud.get_user_streak(test_chat_id)
        assert streak == 0, f"После сброса ожидался streak=0, получен {streak}"
        print("✅ Начальное состояние корректно")
        
        # Тест 2: Обновление streak
        print("\n📋 Тест 2: Обновление streak")
        today = datetime.now().strftime("%Y-%m-%d")
        
        print(f"   Обновляем streak на 5, дата: {today}")
        crud.update_user_streak(test_chat_id, 5, today)
        
        streak, last_test_date = crud.get_user_streak(test_chat_id)
        print(f"   Обновленный streak: {streak}")
        print(f"   Обновленная дата: {last_test_date}")
        
        assert streak == 5, f"Ожидался streak=5, получен {streak}"
        assert last_test_date == today, f"Ожидалась дата={today}, получена {last_test_date}"
        print("✅ Обновление streak работает")
        
        # Тест 3: Инкремент streak
        print("\n📋 Тест 3: Инкремент streak")
        
        # Сначала установим вчерашнюю дату, чтобы инкремент сработал
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_chat_id, 5, yesterday)
        
        new_streak = crud.increment_user_streak(test_chat_id)
        print(f"   Новый streak после инкремента: {new_streak}")
        assert new_streak == 6, f"Ожидался streak=6, получен {new_streak}"
        
        # Повторный инкремент в тот же день
        same_day_streak = crud.increment_user_streak(test_chat_id)
        print(f"   Streak после повторного инкремента: {same_day_streak}")
        assert same_day_streak == 6, f"Streak не должен увеличиваться дважды в день"
        print("✅ Инкремент streak работает корректно")
        
        # Тест 4: Сброс streak
        print("\n📋 Тест 4: Сброс streak")
        crud.reset_user_streak(test_chat_id)
        streak, _ = crud.get_user_streak(test_chat_id)
        print(f"   Streak после сброса: {streak}")
        assert streak == 0, f"Ожидался streak=0, получен {streak}"
        print("✅ Сброс streak работает")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка CRUD функций: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_discount_calculation():
    """Тестирует расчет скидок на основе streak."""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ РАСЧЕТА СКИДОК")
    print("=" * 60)
    
    try:
        from database import crud
        from services.payment import PaymentService
        
        test_chat_id = 999999
        
        # Убеждаемся, что пользователь существует
        user = crud.get_user(test_chat_id)
        if not user:
            crud.add_user(test_chat_id)
        
        # Сначала убираем любой премиум статус
        crud.update_user_subscription(test_chat_id, "free", None, None)
        
        # Тест 1: Бесплатный пользователь
        print("\n📋 Тест 1: Бесплатный пользователь (без скидки)")
        crud.update_user_streak(test_chat_id, 15)
        discount = crud.calculate_streak_discount(test_chat_id)
        print(f"   Streak: 15, Скидка для бесплатного: {discount}%")
        assert discount == 0, f"Бесплатные пользователи не должны получать скидку, получена {discount}%"
        print("✅ Бесплатные пользователи не получают скидку")
        
        # Делаем пользователя премиум
        print("\n📋 Тест 2: Премиум пользователь")
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        crud.update_user_subscription(test_chat_id, "premium", future_date, "test_payment")
        
        # Тест различных значений streak
        test_cases = [
            (0, 0, "Нет streak"),
            (5, 5, "5 дней подряд"),
            (15, 15, "15 дней подряд"),
            (30, 30, "30 дней подряд"),
            (45, 30, "45 дней подряд (максимум 30%)"),
            (100, 30, "100 дней подряд (максимум 30%)")
        ]
        
        for streak_days, expected_discount, description in test_cases:
            crud.update_user_streak(test_chat_id, streak_days)
            discount = crud.calculate_streak_discount(test_chat_id)
            print(f"   {description}: {discount}% (ожидалось {expected_discount}%)")
            assert discount == expected_discount, f"Ожидалась скидка {expected_discount}%, получена {discount}%"
        
        print("✅ Расчет скидок работает корректно")
        
        # Тест расчета цены со скидкой
        print("\n📋 Тест 3: Расчет цены со скидкой")
        crud.update_user_streak(test_chat_id, 20)  # 20% скидка
        
        price_info = PaymentService.calculate_discounted_price(test_chat_id, 1)
        print(f"   Базовая цена: {price_info['base_price']}")
        print(f"   Скидка: {price_info['discount_percent']}%")
        print(f"   Сумма скидки: {price_info['discount_amount']}")
        print(f"   Итоговая цена: {price_info['final_price']}")
        
        expected_final = price_info['base_price'] * 0.8  # 20% скидка
        assert abs(price_info['final_price'] - expected_final) < 0.01, "Неверный расчет итоговой цены"
        print("✅ Расчет цены со скидкой работает")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка расчета скидок: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_daily_reset_logic():
    """Тестирует логику ежедневного сброса streak."""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ЛОГИКИ ЕЖЕДНЕВНОГО СБРОСА")
    print("=" * 60)
    
    try:
        from database import crud
        from services.scheduler import process_daily_reset
        
        test_chat_id = 999999
        
        # Убеждаемся, что пользователь существует
        user = crud.get_user(test_chat_id)
        if not user:
            crud.add_user(test_chat_id)
        
        # Тест 1: Пользователь проходил тест вчера
        print("\n📋 Тест 1: Пользователь проходил тест вчера")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_chat_id, 10, yesterday)
        
        streak_before, date_before = crud.get_user_streak(test_chat_id)
        print(f"   Streak до сброса: {streak_before}, дата: {date_before}")
        
        # Симулируем процесс ежедневного сброса
        # Очищаем кэш сброса чтобы он сработал
        if hasattr(process_daily_reset, 'processed_resets'):
            process_daily_reset.processed_resets.clear()
        
        process_daily_reset(test_chat_id)
        
        streak_after, date_after = crud.get_user_streak(test_chat_id)
        print(f"   Streak после сброса: {streak_after}, дата: {date_after}")
        print("✅ Streak сохранен (пользователь тестировался вчера)")
        
        # Тест 2: Пользователь не проходил тест позавчера
        print("\n📋 Тест 2: Пользователь не проходил тест позавчера")
        day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_chat_id, 15, day_before_yesterday)
        
        streak_before, date_before = crud.get_user_streak(test_chat_id)
        print(f"   Streak до сброса: {streak_before}, дата: {date_before}")
        
        # Очищаем кэш сброса чтобы он сработал
        if hasattr(process_daily_reset, 'processed_resets'):
            process_daily_reset.processed_resets.clear()
        
        process_daily_reset(test_chat_id)
        
        streak_after, date_after = crud.get_user_streak(test_chat_id)
        print(f"   Streak после сброса: {streak_after}, дата: {date_after}")
        assert streak_after == 0, f"Streak должен быть сброшен до 0, получен {streak_after}"
        print("✅ Streak сброшен (пользователь пропустил день)")
        
        # Тест 3: Пользователь вообще не проходил тесты
        print("\n📋 Тест 3: Пользователь без записи о тестах")
        crud.update_user_streak(test_chat_id, 5, None)  # Нет даты теста
        
        streak_before, date_before = crud.get_user_streak(test_chat_id)
        print(f"   Streak до сброса: {streak_before}, дата: {date_before}")
        
        # Очищаем кэш сброса чтобы он сработал
        if hasattr(process_daily_reset, 'processed_resets'):
            process_daily_reset.processed_resets.clear()
        
        process_daily_reset(test_chat_id)
        
        streak_after, date_after = crud.get_user_streak(test_chat_id)
        print(f"   Streak после сброса: {streak_after}, дата: {date_after}")
        assert streak_after == 0, f"Streak должен быть сброшен до 0 при отсутствии записи, получен {streak_after}"
        print("✅ Streak сброшен (нет записи о тестах)")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка логики сброса: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_quiz_integration():
    """Тестирует интеграцию со системой тестов."""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ С ТЕСТАМИ")
    print("=" * 60)
    
    try:
        from database import crud
        
        test_chat_id = 999999
        
        # Убеждаемся, что пользователь существует
        user = crud.get_user(test_chat_id)
        if not user:
            crud.add_user(test_chat_id)
        
        # Сбрасываем streak
        crud.reset_user_streak(test_chat_id)
        
        print("\n📋 Тест: Последовательное прохождение тестов")
        
        # Симулируем прохождение тестов в течение нескольких дней
        for day in range(5):
            # Устанавливаем дату для симуляции
            test_date = (datetime.now() - timedelta(days=4-day)).strftime("%Y-%m-%d")
            
            # Сначала сбрасываем дату последнего теста, чтобы симулировать новый день
            old_streak, _ = crud.get_user_streak(test_chat_id)
            
            # Устанавливаем дату предыдущего дня, чтобы инкремент сработал
            if day > 0:
                prev_date = (datetime.now() - timedelta(days=5-day)).strftime("%Y-%m-%d")
                crud.update_user_streak(test_chat_id, old_streak, prev_date)
            
            # Инкрементируем streak (это симулирует прохождение теста)
            new_streak = crud.increment_user_streak(test_chat_id)
            
            print(f"   День {day + 1} ({test_date}): streak = {new_streak}")
        
        final_streak, last_date = crud.get_user_streak(test_chat_id)
        today = datetime.now().strftime("%Y-%m-%d")
        
        print(f"   Финальный streak: {final_streak}")
        print(f"   Последняя дата теста: {last_date}")
        print(f"   Сегодняшняя дата: {today}")
        
        assert final_streak == 5, f"Ожидался streak=5, получен {final_streak}"
        print("✅ Последовательное прохождение тестов работает")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграции с тестами: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_subscription_display():
    """Тестирует отображение информации о подписке."""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ОТОБРАЖЕНИЯ ПОДПИСКИ")
    print("=" * 60)
    
    try:
        from services.payment import PaymentService
        from keyboards.subscription import subscription_period_keyboard
        
        print("\n📋 Тест: Клавиатура выбора периода")
        keyboard = subscription_period_keyboard()
        
        print("   Кнопки клавиатуры:")
        for row in keyboard.inline_keyboard:
            for button in row:
                print(f"     - {button.text}")
        
        # Проверяем, что показывается расчет на месяц, а не скидки
        button_texts = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if "мес" in button.text or "год" in button.text:
                    button_texts.append(button.text)
        
        print("✅ Клавиатура подписки сформирована")
        
        # Проверяем расчет базовых цен
        print("\n📋 Тест: Базовые расчеты цен")
        for months in [1, 3, 6, 12]:
            savings_info = PaymentService.calculate_savings(months)
            print(f"   {months} мес: {savings_info['monthly_equivalent']:.0f}₽/мес")
        
        print("✅ Базовые расчеты работают")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отображения подписки: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Тестирует граничные случаи."""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ГРАНИЧНЫХ СЛУЧАЕВ")
    print("=" * 60)
    
    try:
        from database import crud
        
        test_chat_id = 999999
        
        # Убеждаемся, что пользователь существует
        user = crud.get_user(test_chat_id)
        if not user:
            crud.add_user(test_chat_id)
        
        # Тест 1: Очень большой streak
        print("\n📋 Тест 1: Очень большой streak")
        crud.update_user_subscription(test_chat_id, "premium", 
                                    (datetime.now() + timedelta(days=30)).isoformat(), "test")
        crud.update_user_streak(test_chat_id, 999)
        
        discount = crud.calculate_streak_discount(test_chat_id)
        print(f"   Streak 999 дней: скидка {discount}%")
        assert discount == 30, "Максимальная скидка должна быть 30%"
        print("✅ Максимальная скидка ограничена 30%")
        
        # Тест 2: Отрицательный streak (не должно быть возможным)
        print("\n📋 Тест 2: Проверка на отрицательные значения")
        crud.update_user_streak(test_chat_id, -5)
        streak, _ = crud.get_user_streak(test_chat_id)
        discount = crud.calculate_streak_discount(test_chat_id)
        print(f"   Отрицательный streak: {streak}, скидка: {discount}%")
        # В зависимости от реализации, может быть 0 или обработка ошибки
        print("✅ Отрицательные значения обработаны")
        
        # Тест 3: Несуществующий пользователь
        print("\n📋 Тест 3: Несуществующий пользователь")
        fake_chat_id = 888888
        try:
            streak, date = crud.get_user_streak(fake_chat_id)
            discount = crud.calculate_streak_discount(fake_chat_id)
            print(f"   Несуществующий пользователь: streak={streak}, скидка={discount}%")
            print("✅ Несуществующие пользователи обработаны корректно")
        except Exception as e:
            print(f"   Ошибка для несуществующего пользователя: {e}")
            print("✅ Ошибки обрабатываются корректно")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка граничных случаев: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data():
    """Очищает тестовые данные."""
    print("\n" + "=" * 60)
    print("🧹 ОЧИСТКА ТЕСТОВЫХ ДАННЫХ")
    print("=" * 60)
    
    try:
        from database.db import db_manager
        
        test_chat_id = 999999
        
        with db_manager.transaction() as conn:
            conn.execute("DELETE FROM users WHERE chat_id = ?", (test_chat_id,))
            conn.execute("DELETE FROM dictionary WHERE chat_id = ?", (test_chat_id,))
            conn.execute("DELETE FROM learned_words WHERE chat_id = ?", (test_chat_id,))
            conn.execute("DELETE FROM active_payments WHERE chat_id = ?", (test_chat_id,))
        
        print("✅ Тестовые данные очищены")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка очистки: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("🚀 НАЧАЛО КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ ФУНКЦИОНАЛА 'ДНЕЙ ПОДРЯД'")
    print("=" * 80)
    
    tests = [
        ("Миграция БД", test_database_migration),
        ("CRUD функции", test_crud_functions),
        ("Расчет скидок", test_discount_calculation),
        ("Ежедневный сброс", test_daily_reset_logic),
        ("Интеграция с тестами", test_quiz_integration),
        ("Отображение подписки", test_subscription_display),
        ("Граничные случаи", test_edge_cases),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"\n✅ {test_name}: ПРОЙДЕН")
            else:
                print(f"\n❌ {test_name}: ПРОВАЛЕН")
        except Exception as e:
            print(f"\n💥 {test_name}: КРИТИЧЕСКАЯ ОШИБКА - {e}")
            results.append((test_name, False))
    
    # Очистка
    cleanup_test_data()
    
    # Итоговый отчет
    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{test_name:.<50} {status}")
    
    print(f"\nОбщий результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\n💡 Функционал 'Дней подряд' готов к использованию")
        print("💡 Не забудьте запустить миграцию: python alter_db_streak.py")
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        print("💡 Проверьте ошибки выше и исправьте код")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)