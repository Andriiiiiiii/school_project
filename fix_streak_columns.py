# fix_streak_columns.py
"""
Исправляет структуру БД для корректной работы streak функционала
"""

import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_streak_columns():
    """Добавляет недостающие столбцы для streak функционала."""
    try:
        with db_manager.get_cursor() as cursor:
            # Проверяем структуру таблицы users
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            logger.info("Текущие столбцы в таблице users:")
            for col in columns:
                logger.info(f"  {col[1]} - {col[2]} (default: {col[4]})")
        
        # Добавляем недостающие столбцы
        with db_manager.transaction() as conn:
            if 'days_streak' not in column_names:
                conn.execute("ALTER TABLE users ADD COLUMN days_streak INTEGER DEFAULT 0")
                logger.info("Добавлен столбец 'days_streak'")
            else:
                logger.info("Столбец 'days_streak' уже существует")
                
            if 'last_test_date' not in column_names:
                conn.execute("ALTER TABLE users ADD COLUMN last_test_date TEXT DEFAULT NULL")
                logger.info("Добавлен столбец 'last_test_date'")
            else:
                logger.info("Столбец 'last_test_date' уже существует")
        
        # Проверяем итоговую структуру
        with db_manager.get_cursor() as cursor:
            cursor.execute("PRAGMA table_info(users)")
            final_columns = cursor.fetchall()
            final_column_names = [col[1] for col in final_columns]
            
            required_columns = ['days_streak', 'last_test_date']
            missing_columns = [col for col in required_columns if col not in final_column_names]
            
            if missing_columns:
                logger.error(f"Не удалось добавить столбцы: {missing_columns}")
                return False
            else:
                logger.info("✅ Все необходимые столбцы присутствуют")
                return True
                
    except Exception as e:
        logger.error(f"Ошибка при исправлении столбцов: {e}")
        return False

if __name__ == '__main__':
    success = fix_streak_columns()
    if success:
        print("✅ Структура БД исправлена успешно")
    else:
        print("❌ Ошибка при исправлении структуры БД")