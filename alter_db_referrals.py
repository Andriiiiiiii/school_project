# alter_db_referrals.py
import logging
from database.db import db_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_referral_system():
    """Добавляет реферальную систему к существующей БД."""
    try:
        with db_manager.transaction() as tx:
            # Проверяем наличие столбца referral_code в таблице users
            cursor = tx.cursor()
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'referral_code' not in columns:
                tx.execute("ALTER TABLE users ADD COLUMN referral_code TEXT UNIQUE")
                logger.info("Столбец 'referral_code' успешно добавлен.")
            else:
                logger.info("Столбец 'referral_code' уже существует.")
            
            # Создаем таблицу рефералов
            tx.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    rewarded BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (referrer_id) REFERENCES users (chat_id),
                    FOREIGN KEY (referred_id) REFERENCES users (chat_id),
                    UNIQUE(referred_id)
                )
            ''')
            logger.info("Таблица 'referrals' создана/проверена.")
            
            # Создаем таблицу наград за рефералы
            tx.execute('''
                CREATE TABLE IF NOT EXISTS referral_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reward_type TEXT NOT NULL,
                    reward_value INTEGER NOT NULL,
                    referrals_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    processed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (chat_id)
                )
            ''')
            logger.info("Таблица 'referral_rewards' создана/проверена.")
            
            # Создаем индексы
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)",
                "CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_id)", 
                "CREATE INDEX IF NOT EXISTS idx_referral_rewards_user ON referral_rewards(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)"
            ]
            
            for index_sql in indexes:
                try:
                    tx.execute(index_sql)
                except Exception as e:
                    logger.warning(f"Не удалось создать индекс: {e}")
            
            logger.info("Индексы для реферальной системы созданы.")
                
        logger.info("Реферальная система успешно добавлена к БД.")
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении реферальной системы: {e}")
        raise

if __name__ == '__main__':
    add_referral_system()