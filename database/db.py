# database/db.py
import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from config import DB_PATH, PRODUCTION_MODE

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Оптимизированный менеджер базы данных для продакшена.
    """
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
            
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._conn_pool = {}
        self._conn_pool_lock = threading.RLock()
        
        # Создаем основное соединение для обратной совместимости
        self.conn = self._create_connection()
        self.cursor = self.conn.cursor()
        
        # Инициализируем БД
        self.init_db()
        logger.info("База данных инициализирована")
    
    def _create_connection(self):
        """Создает оптимизированное соединение с базой данных для продакшена."""
        connection = sqlite3.connect(
            DB_PATH, 
            check_same_thread=False,
            timeout=30.0  # Увеличен timeout для продакшена
        )
        
        # Оптимизированные настройки для продакшена
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA cache_size=-64000")  # 64MB кэш
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        
        connection.isolation_level = None
        connection.row_factory = sqlite3.Row
        return connection
        
    def get_connection(self):
        """Получает соединение из пула."""
        current_thread = threading.current_thread().ident
        with self._conn_pool_lock:
            if current_thread not in self._conn_pool:
                self._conn_pool[current_thread] = self._create_connection()
            return self._conn_pool[current_thread]
    
    @contextmanager
    def get_cursor(self):
        """Контекстный менеджер для получения курсора."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute(self, sql, params=None, commit=False):
        """
        Выполняет SQL-запрос с оптимизированной обработкой ошибок.
        """
        if params is None:
            params = ()
            
        conn = self.get_connection()
        max_attempts = 3  # Уменьшено для продакшена
        attempt = 0
        
        while attempt < max_attempts:
            try:
                with self._lock:
                    cursor = conn.cursor()
                    cursor.execute(sql, params)
                    if commit:
                        conn.commit()
                    return cursor
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) or "busy" in str(e):
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error("БД заблокирована после %d попыток", max_attempts)
                        raise
                    # Экспоненциальная задержка
                    backoff = 0.1 * (2 ** attempt)
                    if not PRODUCTION_MODE:
                        logger.warning("БД заблокирована, повтор через %.2fs (%d/%d)", 
                                     backoff, attempt, max_attempts)
                    time.sleep(backoff)
                else:
                    logger.error("Ошибка SQL: %s", e)
                    raise
            except Exception as e:
                logger.error("Неожиданная ошибка БД: %s", e)
                raise
    
    @contextmanager
    def transaction(self):
        """Контекстный менеджер для транзакций."""
        conn = self.get_connection()
        conn.execute("BEGIN")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Транзакция отменена: %s", e)
            raise
    
    def init_db(self):
        """Инициализирует базу данных с оптимизированными таблицами."""
        try:
            # Таблица пользователей
            self.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    level TEXT DEFAULT 'A1',
                    words_per_day INTEGER DEFAULT 5,
                    notifications INTEGER DEFAULT 10,
                    reminder_time TEXT DEFAULT '09:00',
                    timezone TEXT DEFAULT 'Europe/Moscow',
                    chosen_set TEXT DEFAULT '',
                    test_words_count INTEGER DEFAULT 5,
                    memorize_words_count INTEGER DEFAULT 5,
                    subscription_status TEXT DEFAULT 'free',
                    subscription_expires_at TEXT DEFAULT NULL,
                    subscription_payment_id TEXT DEFAULT NULL
                )
            ''', commit=True)
            
            # Таблица словаря (используется меньше)
            self.execute('''
                CREATE TABLE IF NOT EXISTS dictionary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    word TEXT,
                    translation TEXT,
                    transcription TEXT,
                    example TEXT,
                    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
                )
            ''', commit=True)
            
            # Таблица выученных слов (основная)
            self.execute('''
                CREATE TABLE IF NOT EXISTS learned_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    word TEXT,
                    translation TEXT,
                    learned_date TEXT,
                    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
                )
            ''', commit=True)
            
            # Таблица активных платежей
            self.execute('''
                CREATE TABLE IF NOT EXISTS active_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    payment_id TEXT NOT NULL UNIQUE,
                    amount REAL NOT NULL,
                    months INTEGER NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    processed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
                )
            ''', commit=True)
            
            # Создаем индексы для оптимизации запросов
            self._create_indexes()
            
        except Exception as e:
            logger.error("Ошибка инициализации БД: %s", e)
            raise
    
    def _create_indexes(self):
        """Создает индексы для оптимизации запросов."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_learned_words_chat_id ON learned_words(chat_id)",
            "CREATE INDEX IF NOT EXISTS idx_learned_words_word ON learned_words(word)",
            "CREATE INDEX IF NOT EXISTS idx_active_payments_chat_id ON active_payments(chat_id)",
            "CREATE INDEX IF NOT EXISTS idx_active_payments_processed ON active_payments(processed)",
            "CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_status, subscription_expires_at)"
        ]
        
        for index_sql in indexes:
            try:
                self.execute(index_sql, commit=True)
            except Exception as e:
                if not PRODUCTION_MODE:
                    logger.warning("Не удалось создать индекс: %s", e)
    
    def optimize_db(self):
        """Оптимизирует базу данных (вызывать периодически)."""
        try:
            self.execute("VACUUM", commit=True)
            self.execute("ANALYZE", commit=True)
            if not PRODUCTION_MODE:
                logger.info("База данных оптимизирована")
        except Exception as e:
            logger.error("Ошибка оптимизации БД: %s", e)
    
    def get_stats(self):
        """Возвращает статистику использования БД."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users")
                users_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM learned_words")
                words_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM active_payments WHERE processed = FALSE")
                pending_payments = cursor.fetchone()[0]
                
                return {
                    'users': users_count,
                    'learned_words': words_count,
                    'pending_payments': pending_payments
                }
        except Exception as e:
            logger.error("Ошибка получения статистики БД: %s", e)
            return {}
    
    def close_all(self):
        """Закрывает все соединения с базой данных."""
        with self._conn_pool_lock:
            for conn in self._conn_pool.values():
                try:
                    conn.close()
                except:
                    pass
            self._conn_pool.clear()
            try:
                self.conn.close()
            except:
                pass

# Создаем глобальный экземпляр
db_manager = DatabaseManager()

# Для обратной совместимости
conn = db_manager.conn
cursor = db_manager.cursor

def init_db():
    """Функция инициализации БД для обратной совместимости."""
    db_manager.init_db()