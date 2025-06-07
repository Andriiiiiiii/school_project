# debug_streak_system.py
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_database_structure():
    """Проверяет структуру БД для системы streak."""
    print("🔍 ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    try:
        from database.db import db_manager
        
        with db_manager.get_cursor() as cursor:
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            
            print("📋 Структура таблицы users:")
            for col in columns:
                print(f"   {col[1]} - {col[2]} (default: {col[4]})")
            
            # Проверяем наличие нужных столбцов
            column_names = [col[1] for col in columns]
            required = ['days_streak', 'last_test_date']
            missing = [col for col in required if col not in column_names]
            
            if missing:
                print(f"❌ Отсутствуют столбцы: {missing}")
                return False
            else:
                print("✅ Все необходимые столбцы присутствуют")
                return True
                
    except Exception as e:
        print(f"❌ Ошибка проверки БД: {e}")
        return False

def test_crud_operations():
    """Тестирует CRUD операции для streak."""
    print("\n🧪 ТЕСТИРОВАНИЕ CRUD ОПЕРАЦИЙ")
    print("=" * 50)
    
    try:
        from database import crud
        
        # Тестовый пользователь
        test_id = 999999
        
        # Очищаем старые данные
        try:
            with crud.db_manager.transaction() as tx:
                tx.execute("DELETE FROM users WHERE chat_id = ?", (test_id,))
                tx.execute("DELETE FROM dictionary WHERE chat_id = ?", (test_id,))
                tx.execute("DELETE FROM learned_words WHERE chat_id = ?", (test_id,))
        except:
            pass
        
        # Создаем пользователя
        crud.add_user(test_id)
        print(f"✅ Создан тестовый пользователь {test_id}")
        
        # Тест 1: Начальный streak
        streak, date = crud.get_user_streak(test_id)
        print(f"📊 Начальный streak: {streak}, дата: {date}")
        assert streak == 0, f"Начальный streak должен быть 0, получен {streak}"
        
        # Тест 2: Первый инкремент
        new_streak = crud.increment_user_streak(test_id)
        print(f"📈 После первого инкремента: {new_streak}")
        assert new_streak == 1, f"После инкремента должно быть 1, получено {new_streak}"
        
        # Тест 3: Повторный инкремент в тот же день
        repeat_streak = crud.increment_user_streak(test_id)
        print(f"🔄 После повторного инкремента: {repeat_streak}")
        assert repeat_streak == 1, f"Повторный инкремент должен остаться 1, получено {repeat_streak}"
        
        # Тест 4: Проверка даты
        final_streak, final_date = crud.get_user_streak(test_id)
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"📅 Финальное состояние: streak={final_streak}, дата={final_date}")
        assert final_date == today, f"Дата должна быть {today}, получена {final_date}"
        
        # Тест 5: Сброс streak
        crud.reset_user_streak(test_id)
        reset_streak, reset_date = crud.get_user_streak(test_id)
        print(f"🔄 После сброса: streak={reset_streak}, дата={reset_date}")
        assert reset_streak == 0, f"После сброса должно быть 0, получено {reset_streak}"
        
        print("✅ Все CRUD операции работают корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в CRUD операциях: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_subscription_discounts():
    """Тестирует систему скидок для подписки."""
    print("\n💰 ТЕСТИРОВАНИЕ СИСТЕМЫ СКИДОК")
    print("=" * 50)
    
    try:
        from database import crud
        from services.payment import PaymentService
        
        test_id = 999999
        
        # Создаем пользователя если нужно
        try:
            crud.add_user(test_id)
        except:
            pass
        
        # Тест скидки для бесплатного пользователя
        crud.update_user_streak(test_id, 15, datetime.now().strftime("%Y-%m-%d"))
        discount_free = crud.calculate_streak_discount(test_id)
        print(f"🆓 Скидка для бесплатного пользователя (streak=15): {discount_free}%")
        assert discount_free == 0, f"Бесплатные пользователи не должны получать скидку"
        
        # Делаем премиум
        future = (datetime.now() + timedelta(days=30)).isoformat()
        crud.update_user_subscription(test_id, "premium", future, "test")
        
        # Тест скидки для премиум пользователя
        discount_15 = crud.calculate_streak_discount(test_id)
        print(f"💎 Скидка для премиум пользователя (streak=15): {discount_15}%")
        assert discount_15 == 15, f"Скидка должна быть 15%, получена {discount_15}%"
        
        # Тест максимальной скидки
        crud.update_user_streak(test_id, 35, datetime.now().strftime("%Y-%m-%d"))
        discount_35 = crud.calculate_streak_discount(test_id)
        print(f"💎 Скидка для премиум пользователя (streak=35): {discount_35}%")
        assert discount_35 == 30, f"Максимальная скидка должна быть 30%, получена {discount_35}%"
        
        # Тест расчета цен
        price_info = PaymentService.calculate_discounted_price(test_id, 1)
        print(f"💸 Расчет цены: базовая={price_info['base_price']}, финальная={price_info['final_price']}, скидка={price_info['discount_percent']}%")
        
        # Очистка
        crud.update_user_subscription(test_id, "free")
        crud.reset_user_streak(test_id)
        
        print("✅ Система скидок работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в системе скидок: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_midnight_reset_logic():
    """Тестирует логику сброса в полночь."""
    print("\n🌙 ТЕСТИРОВАНИЕ ЛОГИКИ ПОЛУНОЧНОГО СБРОСА")
    print("=" * 50)
    
    try:
        from database import crud
        from services.scheduler import process_daily_reset
        
        test_id = 999999
        
        # Создаем пользователя если нужно
        try:
            crud.add_user(test_id)
        except:
            pass
        
        # Устанавливаем streak на вчерашнюю дату
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_id, 5, yesterday)
        
        print(f"📅 Установлен streak=5 на дату {yesterday}")
        
        # Симулируем полуночный сброс
        process_daily_reset(test_id)
        
        # Проверяем результат
        new_streak, new_date = crud.get_user_streak(test_id)
        print(f"🌅 После полуночного сброса: streak={new_streak}, дата={new_date}")
        
        # Streak не должен сброситься, так как тест был вчера
        assert new_streak == 5, f"Streak не должен сброситься при тесте вчера"
        
        # Тестируем сброс при пропуске дня
        day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        crud.update_user_streak(test_id, 7, day_before_yesterday)
        
        print(f"📅 Установлен streak=7 на дату {day_before_yesterday} (позавчера)")
        
        # Симулируем полуночный сброс
        process_daily_reset(test_id)
        
        # Проверяем результат
        reset_streak, reset_date = crud.get_user_streak(test_id)
        print(f"🌅 После полуночного сброса: streak={reset_streak}, дата={reset_date}")
        
        # Streak должен сброситься, так как тест был позавчера
        assert reset_streak == 0, f"Streak должен сброситься при пропуске дня"
        
        print("✅ Логика полуночного сброса работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в логике полуночного сброса: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_scheduler_status():
    """Проверяет статус планировщика."""
    print("\n⏰ ПРОВЕРКА ПЛАНИРОВЩИКА")
    print("=" * 50)
    
    try:
        # Проверяем конфигурацию
        from config import PRODUCTION_MODE, SERVER_TIMEZONE
        print(f"🔧 Режим: {'PRODUCTION' if PRODUCTION_MODE else 'DEVELOPMENT'}")
        print(f"🌍 Серверный часовой пояс: {SERVER_TIMEZONE}")
        
        # Проверяем доступность функций планировщика
        from services.scheduler import process_daily_reset, scheduler_job
        print("✅ Функции планировщика доступны")
        
        # Проверяем текущее время
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        now_server = datetime.now(tz=ZoneInfo(SERVER_TIMEZONE))
        print(f"🕒 Текущее серверное время: {now_server.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Проверяем пример пользовательского времени
        moscow_time = now_server.astimezone(ZoneInfo("Europe/Moscow"))
        print(f"🕒 Время в Москве: {moscow_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки планировщика: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция диагностики."""
    print("🚀 ДИАГНОСТИКА СИСТЕМЫ ДНЕЙ ПОДРЯД")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Проверка 1: Структура БД
    if not check_database_structure():
        all_tests_passed = False
        print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Проблемы со структурой БД")
        print("   Запустите: python fix_streak_db.py")
        return False
    
    # Проверка 2: CRUD операции
    if not test_crud_operations():
        all_tests_passed = False
        print("\n❌ ОШИБКА: Проблемы с CRUD операциями")
    
    # Проверка 3: Система скидок
    if not test_subscription_discounts():
        all_tests_passed = False
        print("\n❌ ОШИБКА: Проблемы с системой скидок")
    
    # Проверка 4: Логика полуночного сброса
    if not test_midnight_reset_logic():
        all_tests_passed = False
        print("\n❌ ОШИБКА: Проблемы с логикой полуночного сброса")
    
    # Проверка 5: Планировщик
    if not check_scheduler_status():
        all_tests_passed = False
        print("\n❌ ОШИБКА: Проблемы с планировщиком")
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система дней подряд работает корректно.")
        print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("   1. Убедитесь что бот перезапущен после исправлений")
        print("   2. Проверьте логи бота на ошибки")
        print("   3. Протестируйте прохождение теста дня")
    else:
        print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ! Система дней подряд требует исправления.")
        print("\n📋 РЕКОМЕНДАЦИИ:")
        print("   1. Запустите: python fix_streak_db.py")
        print("   2. Примените исправления к handlers/quiz.py")
        print("   3. Примените исправления к services/scheduler.py")
        print("   4. Перезапустите бота")
    
    return all_tests_passed

if __name__ == "__main__":
    main()