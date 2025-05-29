# create_payments_table.py
import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_payments_table():
    """Создает таблицу для хранения активных платежей."""
    try:
        with db_manager.transaction() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS active_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    payment_id TEXT NOT NULL UNIQUE,
                    amount REAL NOT NULL,
                    months INTEGER NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')
        logger.info("Таблица active_payments создана успешно.")
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы active_payments: {e}")

if __name__ == '__main__':
    create_payments_table()