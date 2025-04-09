# database/crud.py
import logging
from database.db import conn, cursor, db_manager
from config import DEFAULT_WORDS_PER_DAY, DEFAULT_REPETITIONS, REMINDER_DEFAULT

# Настройка логирования
logger = logging.getLogger(__name__)

def add_user(chat_id: int):
    """Добавляет нового пользователя в базу данных, если он еще не существует."""
    try:
        # Проверяем существование пользователя
        cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        if cursor.fetchone() is None:
            # Берем базовый сет для начального уровня A1
            from config import DEFAULT_SETS
            default_set = DEFAULT_SETS.get("A1", "")
            
            # notifications используется для количества повторений
            with db_manager.transaction() as tx_conn:
                tx_conn.execute(
                    "INSERT INTO users (chat_id, level, words_per_day, notifications, reminder_time, timezone, chosen_set) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (chat_id, 'A1', DEFAULT_WORDS_PER_DAY, DEFAULT_REPETITIONS, REMINDER_DEFAULT, "Europe/Moscow", default_set)
                )
            logger.info(f"Added new user with chat_id: {chat_id} with default set: {default_set}")
    except Exception as e:
        logger.error(f"Error adding user {chat_id}: {e}")
        raise

def get_user(chat_id: int):
    """Получает информацию о пользователе по его chat_id."""
    try:
        cursor.execute(
            "SELECT chat_id, level, words_per_day, notifications, reminder_time, timezone, chosen_set FROM users WHERE chat_id = ?", 
            (chat_id,)
        )
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting user {chat_id}: {e}")
        return None

def get_all_users():
    """Получает список всех пользователей."""
    try:
        cursor.execute("SELECT chat_id, level, words_per_day, notifications, reminder_time, timezone FROM users")
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []

def update_user_level(chat_id: int, level: str):
    """Обновляет уровень пользователя."""
    try:
        cursor.execute("UPDATE users SET level = ? WHERE chat_id = ?", (level, chat_id))
        conn.commit()
        logger.debug(f"Updated level to {level} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating level for user {chat_id}: {e}")
        raise

def update_user_words_per_day(chat_id: int, count: int):
    """Обновляет количество слов в день для пользователя."""
    try:
        cursor.execute("UPDATE users SET words_per_day = ? WHERE chat_id = ?", (count, chat_id))
        conn.commit()
        logger.debug(f"Updated words_per_day to {count} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating words_per_day for user {chat_id}: {e}")
        raise

def update_user_notifications(chat_id: int, count: int):
    """Обновляет количество уведомлений для пользователя."""
    try:
        cursor.execute("UPDATE users SET notifications = ? WHERE chat_id = ?", (count, chat_id))
        conn.commit()
        logger.debug(f"Updated notifications to {count} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating notifications for user {chat_id}: {e}")
        raise

def update_user_reminder_time(chat_id: int, time: str):
    """Обновляет время напоминания для пользователя."""
    try:
        cursor.execute("UPDATE users SET reminder_time = ? WHERE chat_id = ?", (time, chat_id))
        conn.commit()
        logger.debug(f"Updated reminder_time to {time} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating reminder_time for user {chat_id}: {e}")
        raise

def update_user_timezone(chat_id: int, timezone: str):
    """Обновляет часовой пояс пользователя."""
    try:
        cursor.execute("UPDATE users SET timezone = ? WHERE chat_id = ?", (timezone, chat_id))
        conn.commit()
        logger.debug(f"Updated timezone to {timezone} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating timezone for user {chat_id}: {e}")
        raise

def add_word_to_dictionary(chat_id: int, word_data: dict):
    """Добавляет слово в словарь пользователя."""
    try:
        cursor.execute(
            """
            INSERT INTO dictionary (chat_id, word, translation, transcription, example)
            VALUES (?, ?, ?, ?, ?)
            """, 
            (chat_id, word_data.get('word'), word_data.get('translation', ''), 
             word_data.get('transcription', ''), word_data.get('example', ''))
        )
        conn.commit()
        logger.debug(f"Added word '{word_data.get('word')}' to dictionary for user {chat_id}")
    except Exception as e:
        logger.error(f"Error adding word to dictionary for user {chat_id}: {e}")
        raise

def get_user_dictionary(chat_id: int, limit: int = 10, offset: int = 0):
    """Получает словарь пользователя с пагинацией."""
    try:
        cursor.execute(
            "SELECT word, translation, transcription, example FROM dictionary WHERE chat_id = ? ORDER BY id DESC LIMIT ? OFFSET ?", 
            (chat_id, limit, offset)
        )
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting dictionary for user {chat_id}: {e}")
        return []

def add_learned_word(chat_id: int, word: str, translation: str, learned_date: str):
    """Добавляет выученное слово в список пользователя."""
    try:
        # Транзакция для обеспечения атомарности операции
        with db_manager.transaction() as tx_conn:
            tx_cursor = tx_conn.cursor()
            # Проверяем, не добавлено ли это слово уже
            tx_cursor.execute(
                "SELECT COUNT(*) FROM learned_words WHERE chat_id = ? AND word = ?", 
                (chat_id, word)
            )
            count = tx_cursor.fetchone()[0]
            # Если слово не найдено, добавляем его
            if count == 0:
                tx_cursor.execute(
                    "INSERT INTO learned_words (chat_id, word, translation, learned_date) VALUES (?, ?, ?, ?)", 
                    (chat_id, word, translation, learned_date)
                )
                logger.debug(f"Added learned word '{word}' for user {chat_id}")
    except Exception as e:
        logger.error(f"Error adding learned word for user {chat_id}: {e}")
        raise

# В файле database/crud.py исправляем функцию get_learned_words

def get_learned_words(chat_id: int):
    """
    Возвращает список выученных слов для пользователя.
    Возвращаются кортежи (word, translation).
    Исправленная версия с дополнительной защитой от ошибок и логированием.
    """
    try:
        # Используем здесь явную блокировку для избежания конфликтов при чтении
        # Это особенно важно на серверах с несколькими процессами
        with db_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT word, translation FROM learned_words WHERE chat_id = ?", 
                (chat_id,)
            )
            result = cursor.fetchall()
            logger.debug(f"Retrieved {len(result)} learned words for user {chat_id}")
            return result
    except sqlite3.Error as sql_error:
        logger.error(f"SQLite error getting learned words for user {chat_id}: {sql_error}")
        # В случае ошибки базы данных возвращаем пустой список
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting learned words for user {chat_id}: {e}")
        return []

def clear_learned_words_for_user(chat_id: int):
    """Очищает таблицу выученных слов для указанного пользователя."""
    try:
        cursor.execute("DELETE FROM learned_words WHERE chat_id = ?", (chat_id,))
        conn.commit()
        logger.info(f"Cleared learned words for user {chat_id}")
    except Exception as e:
        logger.error(f"Error clearing learned words for user {chat_id}: {e}")
        raise

def update_user_chosen_set(chat_id: int, set_name: str):
    """Обновляет выбранный набор слов для пользователя."""
    try:
        cursor.execute("UPDATE users SET chosen_set = ? WHERE chat_id = ?", (set_name, chat_id))
        conn.commit()
        logger.debug(f"Updated chosen_set to '{set_name}' for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating chosen_set for user {chat_id}: {e}")
        raise

def update_user_test_words_count(chat_id: int, count: int):
    """Обновляет количество слов для теста."""
    try:
        with db_manager.transaction() as conn:
            conn.execute("UPDATE users SET test_words_count = ? WHERE chat_id = ?", (count, chat_id))
        logger.info(f"Updated test_words_count to {count} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating test_words_count for user {chat_id}: {e}")
        raise

def update_user_memorize_words_count(chat_id: int, count: int):
    """Обновляет количество слов для заучивания."""
    try:
        with db_manager.transaction() as conn:
            conn.execute("UPDATE users SET memorize_words_count = ? WHERE chat_id = ?", (count, chat_id))
        logger.info(f"Updated memorize_words_count to {count} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating memorize_words_count for user {chat_id}: {e}")
        raise