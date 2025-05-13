"""
database/crud.py
Основные CRUD-операции с таблицами бота (SQLite).

"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable, List, Tuple

from database.db import conn, cursor, db_manager     # существующая инфраструктура
from config import (
    DEFAULT_WORDS_PER_DAY,
    DEFAULT_REPETITIONS,
    REMINDER_DEFAULT,
    DEFAULT_SETS,
    DB_PATH,
)

logger = logging.getLogger(__name__)

# ───────────────────────── вспомогательные утилиты ──────────────────────────
def _exec(query: str, params: Iterable[Any] | None = None) -> List[Tuple]:
    """Выполнить запрос с открытием короткого соединения (для составных функций)."""
    with sqlite3.connect(DB_PATH) as _con:
        cur = _con.execute(query, params or [])
        result = cur.fetchall()
    return result


# ───────────────────────── базовые (существовавшие) функции ─────────────────
def update_user_words_and_repetitions(chat_id, words_per_day, repetitions_per_word):
    try:
        with db_manager.transaction() as tx:
            tx.execute(
                "UPDATE users SET words_per_day = ?, notifications = ? WHERE chat_id = ?",
                (words_per_day, repetitions_per_word, chat_id),
            )
        logger.info(
            f"Updated words_per_day={words_per_day}, notifications={repetitions_per_word} "
            f"for user {chat_id}"
        )
        return True
    except Exception as e:
        logger.error(f"Error updating settings for user {chat_id}: {e}")
        return False


def add_user(chat_id: int):
    try:
        cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        if cursor.fetchone() is None:
            default_set = DEFAULT_SETS.get("A1", "")
            with db_manager.transaction() as tx:
                tx.execute(
                    """
                    INSERT INTO users
                    (chat_id, level, words_per_day, notifications,
                     reminder_time, timezone, chosen_set)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chat_id,
                        "A1",
                        DEFAULT_WORDS_PER_DAY,
                        DEFAULT_REPETITIONS,
                        REMINDER_DEFAULT,
                        "Europe/Moscow",
                        default_set,
                    ),
                )
            logger.info("Added new user %s with default set %s", chat_id, default_set)
    except Exception as e:
        logger.error(f"Error adding user {chat_id}: {e}")
        raise


def get_user(chat_id: int):
    try:
        cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting user {chat_id}: {e}")
        return None


def get_all_users():
    try:
        cursor.execute(
            "SELECT chat_id, level, words_per_day, notifications, reminder_time, timezone "
            "FROM users"
        )
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []


# ───────────────────────── новые «короткие» сеттеры ─────────────────────────
def set_test_words(chat_id: int, count: int) -> None:
    """Сохраняет количество слов для режима «тест по словарю» (col test_words_count)."""
    try:
        with db_manager.transaction() as tx:
            tx.execute(
                "UPDATE users SET test_words_count = ? WHERE chat_id = ?",
                (count, chat_id),
            )
        logger.info("set_test_words: chat=%s → %d", chat_id, count)
    except Exception as e:
        logger.error(f"set_test_words error (user {chat_id}): {e}")
        raise


def set_memorize_words(chat_id: int, count: int) -> None:
    """Сохраняет количество слов для «заучивания сета» (col memorize_words_count)."""
    try:
        with db_manager.transaction() as tx:
            tx.execute(
                "UPDATE users SET memorize_words_count = ? WHERE chat_id = ?",
                (count, chat_id),
            )
        logger.info("set_memorize_words: chat=%s → %d", chat_id, count)
    except Exception as e:
        logger.error(f"set_memorize_words error (user {chat_id}): {e}")
        raise


def update_user_field(chat_id: int, field_idx: int, value: Any) -> None:
    """
    Универсальный Fallback: обновляет users-поле по его порядковому индексу.
    Используется handlers/learning.py, если не нашёлся специализированный сеттер.
    """
    try:
        cols = _exec("PRAGMA table_info(users)")
        if field_idx < 0 or field_idx >= len(cols):
            raise IndexError(f"users table has only {len(cols)} columns")
        col_name = cols[field_idx][1]  # (cid, name, type, …)
        with db_manager.transaction() as tx:
            tx.execute(f"UPDATE users SET {col_name} = ? WHERE chat_id = ?", (value, chat_id))
        logger.info(
            "update_user_field: chat=%s col=%s(idx=%d) → %s",
            chat_id,
            col_name,
            field_idx,
            value,
        )
    except Exception as e:
        logger.error(f"update_user_field error (user {chat_id}): {e}")
        raise


# ───────────────────────── остальные прежние функции ───────────────────────
def update_user_level(chat_id: int, level: str):
    try:
        cursor.execute("UPDATE users SET level = ? WHERE chat_id = ?", (level, chat_id))
        conn.commit()
        logger.debug("Updated level=%s for user %s", level, chat_id)
    except Exception as e:
        logger.error(f"Error updating level for user {chat_id}: {e}")
        raise


def update_user_words_per_day(chat_id: int, count: int):
    try:
        cursor.execute("UPDATE users SET words_per_day = ? WHERE chat_id = ?", (count, chat_id))
        conn.commit()
        logger.debug("Updated words_per_day=%d for user %s", count, chat_id)
    except Exception as e:
        logger.error(f"Error updating words_per_day for user {chat_id}: {e}")
        raise


def update_user_notifications(chat_id: int, count: int):
    try:
        cursor.execute("UPDATE users SET notifications = ? WHERE chat_id = ?", (count, chat_id))
        conn.commit()
        logger.debug("Updated notifications=%d for user %s", count, chat_id)
    except Exception as e:
        logger.error(f"Error updating notifications for user {chat_id}: {e}")
        raise


def update_user_reminder_time(chat_id: int, time: str):
    try:
        cursor.execute("UPDATE users SET reminder_time = ? WHERE chat_id = ?", (time, chat_id))
        conn.commit()
        logger.debug("Updated reminder_time=%s for user %s", time, chat_id)
    except Exception as e:
        logger.error(f"Error updating reminder_time for user {chat_id}: {e}")
        raise


def update_user_timezone(chat_id: int, timezone: str):
    try:
        cursor.execute("UPDATE users SET timezone = ? WHERE chat_id = ?", (timezone, chat_id))
        conn.commit()
        logger.debug("Updated timezone=%s for user %s", timezone, chat_id)
    except Exception as e:
        logger.error(f"Error updating timezone for user {chat_id}: {e}")
        raise


def add_word_to_dictionary(chat_id: int, word_data: dict):
    try:
        cursor.execute(
            """
            INSERT INTO dictionary (chat_id, word, translation, transcription, example)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                word_data.get("word"),
                word_data.get("translation", ""),
                word_data.get("transcription", ""),
                word_data.get("example", ""),
            ),
        )
        conn.commit()
        logger.debug("Added word '%s' for user %s", word_data.get("word"), chat_id)
    except Exception as e:
        logger.error(f"Error adding word to dictionary for user {chat_id}: {e}")
        raise


def get_user_dictionary(chat_id: int, limit: int = 10, offset: int = 0):
    try:
        cursor.execute(
            """
            SELECT word, translation, transcription, example
            FROM dictionary WHERE chat_id = ?
            ORDER BY id DESC LIMIT ? OFFSET ?
            """,
            (chat_id, limit, offset),
        )
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting dictionary for user {chat_id}: {e}")
        return []


def add_learned_word(chat_id: int, word: str, translation: str, learned_date: str):
    try:
        with db_manager.transaction() as tx:
            tx_cur = tx.cursor()
            tx_cur.execute(
                "SELECT COUNT(*) FROM learned_words WHERE chat_id = ? AND word = ?",
                (chat_id, word),
            )
            if tx_cur.fetchone()[0] == 0:
                tx_cur.execute(
                    """
                    INSERT INTO learned_words (chat_id, word, translation, learned_date)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, word, translation, learned_date),
                )
                logger.debug("Added learned word '%s' for user %s", word, chat_id)
    except Exception as e:
        logger.error(f"Error adding learned word for user {chat_id}: {e}")
        raise


def get_learned_words(chat_id: int):
    try:
        with db_manager.get_cursor() as cur:
            cur.execute(
                "SELECT word, translation FROM learned_words WHERE chat_id = ?", (chat_id,)
            )
            res = cur.fetchall()
            logger.debug("Retrieved %d learned words for user %s", len(res), chat_id)
            return res
    except sqlite3.Error as sql_error:
        logger.error(f"SQLite error getting learned words for user {chat_id}: {sql_error}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting learned words for user {chat_id}: {e}")
        return []


def clear_learned_words_for_user(chat_id: int):
    try:
        cursor.execute("DELETE FROM learned_words WHERE chat_id = ?", (chat_id,))
        conn.commit()
        logger.info("Cleared learned words for user %s", chat_id)
    except Exception as e:
        logger.error(f"Error clearing learned words for user {chat_id}: {e}")
        raise


def update_user_chosen_set(chat_id: int, set_name: str):
    try:
        cursor.execute("UPDATE users SET chosen_set = ? WHERE chat_id = ?", (set_name, chat_id))
        conn.commit()
        logger.debug("Updated chosen_set='%s' for user %s", set_name, chat_id)
    except Exception as e:
        logger.error(f"Error updating chosen_set for user {chat_id}: {e}")
        raise


def update_user_test_words_count(chat_id: int, count: int):
    try:
        with db_manager.transaction() as tx:
            tx.execute(
                "UPDATE users SET test_words_count = ? WHERE chat_id = ?",
                (count, chat_id),
            )
        logger.info("Updated test_words_count=%d for user %s", count, chat_id)
    except Exception as e:
        logger.error(f"Error updating test_words_count for user {chat_id}: {e}")
        raise


def update_user_memorize_words_count(chat_id: int, count: int):
    try:
        with db_manager.transaction() as tx:
            tx.execute(
                "UPDATE users SET memorize_words_count = ? WHERE chat_id = ?",
                (count, chat_id),
            )
        logger.info("Updated memorize_words_count=%d for user %s", count, chat_id)
    except Exception as e:
        logger.error(f"Error updating memorize_words_count for user {chat_id}: {e}")
        raise
