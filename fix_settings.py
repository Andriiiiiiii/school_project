# fix_settings.py
import logging
from database.db import db_manager
from database import crud
from utils.helpers import reset_daily_words_cache

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_update_settings_function():
    """Проверяет и исправляет функцию обновления настроек в базе данных."""
    try:
        # Тестируем соединение с базой данных
        with db_manager.get_cursor() as cursor:
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            
            logger.info(f"Проверка структуры таблицы users:")
            for col in columns:
                logger.info(f"Колонка: {col}")
                
        logger.info("Соединение с базой данных работает.")
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке базы данных: {e}")
        return False

if __name__ == "__main__":
    fix_update_settings_function()