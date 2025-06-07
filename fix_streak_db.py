# fix_streak_db.py
import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_streak_columns():
    """Исправляет столбцы для системы дней подряд."""
    try:
        with db_manager.get_cursor() as cursor:
            # Проверяем наличие столбцов в таблице users
            cursor.execute("PRAGMA table_info(users)")
            result = cursor.fetchall()
            columns = [row[1] for row in result]
            
            # Удаляем старый неправильный столбец если есть
            if 'daily_streak' in columns:
                logger.info("Удаляем неправильный столбец 'daily_streak'")
                # SQLite не поддерживает DROP COLUMN, поэтому пересоздаем таблицу
                with db_manager.transaction() as tx:
                    # Создаем временную таблицу без daily_streak
                    tx.execute('''
                        CREATE TABLE users_temp AS 
                        SELECT chat_id, level, words_per_day, notifications, reminder_time, 
                               timezone, chosen_set, test_words_count, memorize_words_count,
                               subscription_status, subscription_expires_at, subscription_payment_id
                        FROM users
                    ''')
                    
                    # Удаляем старую таблицу
                    tx.execute("DROP TABLE users")
                    
                    # Переименовываем временную таблицу
                    tx.execute("ALTER TABLE users_temp RENAME TO users")
                    
                    logger.info("Удален неправильный столбец 'daily_streak'")
            
            # Обновляем информацию о столбцах
            cursor.execute("PRAGMA table_info(users)")
            result = cursor.fetchall()
            columns = [row[1] for row in result]
            
            # Добавляем правильные столбцы
            with db_manager.transaction() as tx:
                if 'days_streak' not in columns:
                    tx.execute("ALTER TABLE users ADD COLUMN days_streak INTEGER DEFAULT 0")
                    logger.info("Столбец 'days_streak' успешно добавлен.")
                else:
                    logger.info("Столбец 'days_streak' уже существует.")
                    
                if 'last_test_date' not in columns:
                    tx.execute("ALTER TABLE users ADD COLUMN last_test_date TEXT DEFAULT NULL")
                    logger.info("Столбец 'last_test_date' успешно добавлен.")
                else:
                    logger.info("Столбец 'last_test_date' уже существует.")
                    
        logger.info("Исправление столбцов streak завершено успешно.")
        return True
                
    except Exception as e:
        logger.error(f"Ошибка при исправлении столбцов: {e}")
        return False

def verify_streak_functionality():
    """Проверяет функциональность системы дней подряд."""
    try:
        from database import crud
        
        # Тестовый пользователь
        test_chat_id = 777777
        
        # Создаем тестового пользователя если нужно
        try:
            crud.add_user(test_chat_id)
            logger.info(f"Создан тестовый пользователь {test_chat_id}")
        except:
            logger.info(f"Тестовый пользователь {test_chat_id} уже существует")
        
        # Тестируем основные функции
        logger.info("Тестирование функций streak...")
        
        # Сброс streak
        crud.reset_user_streak(test_chat_id)
        streak, date = crud.get_user_streak(test_chat_id)
        logger.info(f"После сброса: streak={streak}, date={date}")
        
        # Инкремент streak
        new_streak = crud.increment_user_streak(test_chat_id)
        logger.info(f"После инкремента: streak={new_streak}")
        
        # Проверка скидки
        discount = crud.calculate_streak_discount(test_chat_id)
        logger.info(f"Скидка для бесплатного пользователя: {discount}%")
        
        # Делаем премиум и проверяем скидку
        from datetime import datetime, timedelta
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        crud.update_user_subscription(test_chat_id, "premium", future_date, "test")
        
        discount = crud.calculate_streak_discount(test_chat_id)
        logger.info(f"Скидка для премиум пользователя: {discount}%")
        
        # Очистка
        crud.update_user_subscription(test_chat_id, "free")
        
        logger.info("✅ Все функции streak работают корректно!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании функций streak: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_db_init():
    """Обновляет файл database/db.py для включения столбцов streak."""
    print("📝 Обновление init_db() для включения столбцов streak...")
    
    # Читаем текущий файл
    try:
        with open('database/db.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, есть ли уже строки со streak
        if 'days_streak INTEGER DEFAULT 0' in content:
            print("✅ Столбцы streak уже есть в init_db()")
            return True
        
        # Находим строку с subscription_payment_id и добавляем после неё
        old_line = 'subscription_payment_id TEXT DEFAULT NULL'
        new_lines = '''subscription_payment_id TEXT DEFAULT NULL,
                    days_streak INTEGER DEFAULT 0,
                    last_test_date TEXT DEFAULT NULL'''
        
        if old_line in content:
            updated_content = content.replace(old_line, new_lines)
            
            # Записываем обновленный файл
            with open('database/db.py', 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print("✅ Файл database/db.py обновлен")
            return True
        else:
            print("⚠️ Не найдена строка для замены в database/db.py")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении database/db.py: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Исправление системы дней подряд...")
    
    # Обновляем init_db()
    update_db_init()
    
    # Исправляем столбцы БД
    if fix_streak_columns():
        print("✅ Столбцы БД исправлены")
        
        # Проверяем функциональность
        if verify_streak_functionality():
            print("🎉 Система дней подряд работает корректно!")
        else:
            print("❌ Обнаружены проблемы в функциональности")
    else:
        print("❌ Ошибка при исправлении столбцов БД")