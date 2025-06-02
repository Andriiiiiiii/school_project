# alter_db_daily_streak.py
import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_daily_streak_columns():
    """Добавляет столбцы для отслеживания дней подряд в таблицу users."""
    try:
        with db_manager.get_cursor() as cursor:
            # Проверяем наличие столбцов в таблице users
            cursor.execute("PRAGMA table_info(users)")
            result = cursor.fetchall()
            columns = [row[1] for row in result]
            
            if 'daily_streak' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_streak INTEGER DEFAULT 0")
                logger.info("Столбец 'daily_streak' успешно добавлен.")
            else:
                logger.info("Столбец 'daily_streak' уже существует.")
                
            if 'last_test_date' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN last_test_date TEXT DEFAULT NULL")
                logger.info("Столбец 'last_test_date' успешно добавлен.")
            else:
                logger.info("Столбец 'last_test_date' уже существует.")
                
        # Зафиксируем изменения
        with db_manager.transaction() as conn:
            conn.execute("SELECT 1")  # Простой запрос для подтверждения транзакции
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении столбцов: {e}")

if __name__ == '__main__':
    add_daily_streak_columns()