# clear_learned_words.py
import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_learned_words():
    """Очищает все записи из таблицы learned_words."""
    try:
        with db_manager.transaction() as conn:
            conn.execute("DELETE FROM learned_words")
        logger.info("Таблица learned_words очищена.")
    except Exception as e:
        logger.error(f"Ошибка при очистке таблицы: {e}")

if __name__ == '__main__':
    clear_learned_words()