# alter_db_learning.py
import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_learning_columns():
    """Добавляет столбцы test_words_count и memorize_words_count в таблицу users."""
    try:
        with db_manager.get_cursor() as cursor:
            # Проверяем наличие столбца test_words_count в таблице users
            cursor.execute("PRAGMA table_info(users)")
            result = cursor.fetchall()
            columns = [row[1] for row in result]
            
            if 'test_words_count' not in columns:
                # Добавляем столбец test_words_count, если его нет
                cursor.execute("ALTER TABLE users ADD COLUMN test_words_count INTEGER DEFAULT 5")
                logger.info("Столбец 'test_words_count' успешно добавлен.")
            else:
                logger.info("Столбец 'test_words_count' уже существует.")
                
            if 'memorize_words_count' not in columns:
                # Добавляем столбец memorize_words_count, если его нет
                cursor.execute("ALTER TABLE users ADD COLUMN memorize_words_count INTEGER DEFAULT 5")
                logger.info("Столбец 'memorize_words_count' успешно добавлен.")
            else:
                logger.info("Столбец 'memorize_words_count' уже существует.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении столбцов: {e}")

if __name__ == '__main__':
    add_learning_columns()