# alter_db_subscription.py
import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_subscription_columns():
    """Добавляет столбцы для подписки в таблицу users."""
    try:
        with db_manager.get_cursor() as cursor:
            # Проверяем наличие столбцов в таблице users
            cursor.execute("PRAGMA table_info(users)")
            result = cursor.fetchall()
            columns = [row[1] for row in result]
            
            if 'subscription_status' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'free'")
                logger.info("Столбец 'subscription_status' успешно добавлен.")
            else:
                logger.info("Столбец 'subscription_status' уже существует.")
                
            if 'subscription_expires_at' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN subscription_expires_at TEXT DEFAULT NULL")
                logger.info("Столбец 'subscription_expires_at' успешно добавлен.")
            else:
                logger.info("Столбец 'subscription_expires_at' уже существует.")
                
            if 'subscription_payment_id' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN subscription_payment_id TEXT DEFAULT NULL")
                logger.info("Столбец 'subscription_payment_id' успешно добавлен.")
            else:
                logger.info("Столбец 'subscription_payment_id' уже существует.")
                
    except Exception as e:
        logger.error(f"Ошибка при добавлении столбцов: {e}")

if __name__ == '__main__':
    add_subscription_columns()