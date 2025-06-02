# debug_streak_db.py
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_database():
    """Отлаживает структуру и данные БД."""
    try:
        from database.db import db_manager
        from database import crud
        
        print("🔍 ОТЛАДКА СТРУКТУРЫ БАЗЫ ДАННЫХ")
        print("=" * 50)
        
        # Проверяем структуру таблицы users
        with db_manager.get_cursor() as cursor:
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            
            print("📋 Структура таблицы users:")
            for col in columns:
                print(f"   {col[1]} - {col[2]} (default: {col[4]})")
            
            # Проверяем есть ли нужные столбцы
            column_names = [col[1] for col in columns]
            required = ['days_streak', 'last_test_date']
            missing = [col for col in required if col not in column_names]
            
            if missing:
                print(f"❌ Отсутствуют столбцы: {missing}")
                return False
            else:
                print("✅ Все необходимые столбцы присутствуют")
        
        # Тестируем базовые операции
        test_id = 888888
        print(f"\n🧪 Тестирование с пользователем {test_id}")
        
        # Создаем тестового пользователя если нужно
        try:
            crud.add_user(test_id)
            print(f"   Создан тестовый пользователь {test_id}")
        except:
            print(f"   Пользователь {test_id} уже существует")
        
        # Проверяем начальное состояние
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT chat_id, days_streak, last_test_date FROM users WHERE chat_id = ?", (test_id,))
            result = cursor.fetchone()
            if result:
                print(f"   Начальное состояние: chat_id={result[0]}, streak={result[1]}, date={result[2]}")
            else:
                print(f"   ❌ Пользователь {test_id} не найден в БД")
                return False
        
        # Тестируем обновление напрямую через SQL
        print("\n🔧 Тестирование прямого SQL обновления...")
        with db_manager.transaction() as tx:
            tx.execute("UPDATE users SET days_streak = ?, last_test_date = ? WHERE chat_id = ?", 
                      (10, "2025-06-03", test_id))
        
        # Проверяем результат
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT days_streak, last_test_date FROM users WHERE chat_id = ?", (test_id,))
            result = cursor.fetchone()
            if result:
                print(f"   После SQL обновления: streak={result[0]}, date={result[1]}")
                if result[0] == 10 and result[1] == "2025-06-03":
                    print("   ✅ Прямое SQL обновление работает")
                else:
                    print("   ❌ Прямое SQL обновление не работает")
                    return False
            else:
                print("   ❌ Не удалось получить результат после обновления")
                return False
        
        # Тестируем CRUD функции
        print("\n🔧 Тестирование CRUD функций...")
        crud.update_user_streak(test_id, 15, "2025-06-04")
        
        streak, date = crud.get_user_streak(test_id)
        print(f"   После CRUD обновления: streak={streak}, date={date}")
        
        if streak == 15 and date == "2025-06-04":
            print("   ✅ CRUD функции работают")
        else:
            print("   ❌ CRUD функции не работают")
            return False
        
        # Очистка
        with db_manager.transaction() as tx:
            tx.execute("DELETE FROM users WHERE chat_id = ?", (test_id,))
        
        print("\n🎉 Все тесты БД пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отладки БД: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_database()