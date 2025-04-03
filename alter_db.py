# alter_db.py
import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_timezone_column():
    """Добавляет столбец timezone в таблицу users, если он еще не существует."""
    try:
        with db_manager.get_cursor() as cursor:
            # Проверяем наличие столбца timezone в таблице users
            cursor.execute("PRAGMA table_info(users)")
            result = cursor.fetchall()
            columns = [row[1] for row in result]
            
            if 'timezone' not in columns:
                # Добавляем столбец timezone, если его нет
                cursor.execute("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow'")
                logger.info("Столбец 'timezone' успешно добавлен.")
            else:
                logger.info("Столбец 'timezone' уже существует.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении столбца: {e}")

if __name__ == '__main__':
    add_timezone_column()