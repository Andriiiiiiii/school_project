# database/db.py
import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from config import DB_PATH

# Настройка логирования
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Класс для безопасной работы с базой данных SQLite в многопоточной среде.
    Имитирует интерфейс прямого подключения SQLite, но с дополнительной защитой.
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
        self._last_conn_id = 0
        
        # Создаем основное соединение, которое будет доступно через атрибуты conn и cursor
        # для обратной совместимости со старым кодом
        self.conn = self._create_connection()
        self.cursor = self.conn.cursor()
        
        # Инициализируем БД
        self.init_db()
        logger.info("Database initialized successfully")
    
    def _create_connection(self):
        """Создает и настраивает новое соединение с базой данных."""
        connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        # Настройки для улучшения конкурентности и производительности
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.isolation_level = None  # Автоматически управляем транзакциями
        connection.row_factory = sqlite3.Row  # Чтобы получать результаты в виде словаря
        return connection
        
    def get_connection(self):
        """Получает соединение из пула или создает новое."""
        current_thread = threading.current_thread().ident
        with self._conn_pool_lock:
            if current_thread not in self._conn_pool:
                # Создаем новое соединение для текущего потока
                self._conn_pool[current_thread] = self._create_connection()
            return self._conn_pool[current_thread]
    
    @contextmanager
    def get_cursor(self):
        """Контекстный менеджер для безопасного получения курсора."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute(self, sql, params=None, commit=False):
        """
        Выполняет SQL-запрос с обработкой блокировок и ошибок.
        Безопасно работает в многопоточной среде.
        """
        if params is None:
            params = ()
            
        conn = self.get_connection()
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                with self._lock:  # Блокируем доступ к БД на время выполнения запроса
                    cursor = conn.cursor()
                    cursor.execute(sql, params)
                    if commit:
                        conn.commit()
                    return cursor
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) or "busy" in str(e):
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Failed to execute after {max_attempts} attempts: {sql}")
                        raise
                    backoff = 0.1 * (2 ** attempt)  # Экспоненциальная задержка
                    logger.warning(f"Database locked, retrying in {backoff:.2f}s ({attempt}/{max_attempts})")
                    time.sleep(backoff)
                else:
                    logger.error(f"SQL error: {e} in query: {sql}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error: {e} in query: {sql}")
                raise
    
    @contextmanager
    def transaction(self):
        """Контекстный менеджер для транзакций с автоматическим откатом при ошибках."""
        conn = self.get_connection()
        conn.execute("BEGIN")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
    
    def init_db(self):
        """Инициализирует базу данных, создавая необходимые таблицы если они не существуют."""
        try:
            # Создаем таблицу пользователей
            self.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    level TEXT DEFAULT 'A1',
                    words_per_day INTEGER DEFAULT 5,
                    notifications INTEGER DEFAULT 10,
                    reminder_time TEXT DEFAULT '09:00',
                    timezone TEXT DEFAULT 'Europe/Moscow',
                    chosen_set TEXT DEFAULT ''
                )
            ''', commit=True)
            
            # Создаем таблицу словаря
            self.execute('''
                CREATE TABLE IF NOT EXISTS dictionary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    word TEXT,
                    translation TEXT,
                    transcription TEXT,
                    example TEXT
                )
            ''', commit=True)
            
            # Создаем таблицу выученных слов
            self.execute('''
                CREATE TABLE IF NOT EXISTS learned_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    word TEXT,
                    translation TEXT,
                    learned_date TEXT
                )
            ''', commit=True)
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
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

# Для обратной совместимости предоставляем доступ к conn и cursor через модуль
conn = db_manager.conn
cursor = db_manager.cursor

# Функция для инициализации БД, для обратной совместимости
def init_db():
    db_manager.init_db()