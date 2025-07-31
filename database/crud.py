"""
database/crud.py
Основные CRUD-операции с таблицами бота (SQLite).

"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable, List, Tuple
from datetime import datetime, timedelta  # ДОБАВЬТЕ ЭТУ СТРОКУ

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

# В файле database/crud.py добавить эти функции перед функциями update_user_test_words_count и update_user_memorize_words_count:

def update_user_subscription(chat_id: int, status: str, expires_at: str = None, payment_id: str = None):
    """Обновляет статус подписки пользователя."""
    try:
        with db_manager.transaction() as tx:
            if expires_at and payment_id:
                tx.execute(
                    """UPDATE users SET subscription_status = ?, subscription_expires_at = ?, 
                       subscription_payment_id = ? WHERE chat_id = ?""",
                    (status, expires_at, payment_id, chat_id)
                )
            elif expires_at:
                tx.execute(
                    "UPDATE users SET subscription_status = ?, subscription_expires_at = ? WHERE chat_id = ?",
                    (status, expires_at, chat_id)
                )
            else:
                tx.execute(
                    "UPDATE users SET subscription_status = ? WHERE chat_id = ?",
                    (status, chat_id)
                )
        logger.info(f"Updated subscription status={status} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating subscription for user {chat_id}: {e}")
        raise

def get_user_subscription_status(chat_id: int) -> tuple:
    """Возвращает статус подписки пользователя."""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute(
                """SELECT subscription_status, subscription_expires_at, subscription_payment_id 
                   FROM users WHERE chat_id = ?""", 
                (chat_id,)
            )
            result = cursor.fetchone()
            if result:
                return result[0] or 'free', result[1], result[2]
            return 'free', None, None
    except Exception as e:
        logger.error(f"Error getting subscription status for user {chat_id}: {e}")
        return 'free', None, None

def is_user_premium(chat_id: int) -> bool:
    """Проверяет, является ли пользователь премиум (активная подписка)."""
    try:
        status, expires_at, _ = get_user_subscription_status(chat_id)
        
        if status != 'premium':
            return False
            
        if not expires_at:
            return False
            
        # Проверяем, не истекла ли подписка
        from datetime import datetime, timedelta 
        expiry_date = datetime.fromisoformat(expires_at)
        return datetime.now() < expiry_date
        
    except Exception as e:
        logger.error(f"Error checking premium status for user {chat_id}: {e}")
        return False

def get_all_premium_users() -> list:
    """Возвращает список всех премиум пользователей с их данными подписки."""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute(
                """SELECT chat_id, subscription_status, subscription_expires_at, subscription_payment_id 
                   FROM users WHERE subscription_status = 'premium'"""
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting premium users: {e}")
        return []
        
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


def update_user_chosen_set(chat_id: int, chosen_set: str):
    """Обновляет выбранный набор пользователя."""
    from database.db import db_manager
    try:
        with db_manager.transaction() as tx:
            tx.execute(
                "UPDATE users SET chosen_set = ? WHERE chat_id = ?",
                (chosen_set, chat_id)
            )
        logger.info("Набор пользователя %s обновлен на %s", chat_id, chosen_set)
    except Exception as e:
        logger.error("Ошибка обновления набора пользователя %s: %s", chat_id, e)

def update_user_streak(chat_id: int, days_streak: int, last_test_date: str = None):
    """Обновляет количество дней подряд пользователя."""
    try:
        if days_streak < 0:
            days_streak = 0
            
        with db_manager.transaction() as tx:
            if last_test_date is not None:
                tx.execute(
                    "UPDATE users SET days_streak = ?, last_test_date = ? WHERE chat_id = ?",
                    (days_streak, last_test_date, chat_id)
                )
            else:
                # ИСПРАВЛЕНИЕ: правильно сбрасываем дату на NULL
                tx.execute(
                    "UPDATE users SET days_streak = ?, last_test_date = NULL WHERE chat_id = ?",
                    (days_streak, chat_id)
                )
                
        logger.info(f"Updated streak to {days_streak} for user {chat_id}")
    except Exception as e:
        logger.error(f"Error updating streak for user {chat_id}: {e}")
        raise

def get_user_streak(chat_id: int) -> tuple:
    """Возвращает количество дней подряд и дату последнего теста."""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute(
                "SELECT days_streak, last_test_date FROM users WHERE chat_id = ?", 
                (chat_id,)
            )
            result = cursor.fetchone()
            if result:
                # Валидация: streak не может быть отрицательным
                streak = max(0, result[0] or 0)
                date = result[1]
                logger.debug(f"Retrieved streak={streak}, date={date} for user {chat_id}")
                return streak, date
            else:
                logger.warning(f"User {chat_id} not found when getting streak")
                return 0, None
    except Exception as e:
        logger.error(f"Error getting streak for user {chat_id}: {e}")
        return 0, None

def increment_user_streak(chat_id: int) -> int:
    """Увеличивает количество дней подряд на 1 и обновляет дату последнего теста. ИСПРАВЛЕННАЯ версия с учетом часового пояса пользователя."""
    try:
        # ИСПРАВЛЕНИЕ: получаем часовой пояс пользователя
        try:
            user = get_user(chat_id)
            user_timezone = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
            from zoneinfo import ZoneInfo
            user_tz = ZoneInfo(user_timezone)
            today = datetime.now(tz=user_tz).strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Ошибка получения часового пояса для пользователя {chat_id}: {e}")
            today = datetime.now().strftime("%Y-%m-%d")
        
        current_streak, last_test_date = get_user_streak(chat_id)
        logger.debug(f"Current state for user {chat_id}: streak={current_streak}, last_date={last_test_date}, today={today}")
        
        # Проверяем, не проходил ли уже тест сегодня
        if last_test_date == today:
            logger.debug(f"User {chat_id} already took test today, keeping streak at {current_streak}")
            return current_streak  # Уже проходил тест сегодня
        
        # Проверяем, был ли пропуск дней
        try:
            yesterday = (datetime.now(tz=user_tz) - timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        if last_test_date is None:
            # Первый тест вообще
            new_streak = 1
        elif last_test_date == yesterday:
            # Тест был вчера - увеличиваем streak
            new_streak = current_streak + 1
        else:
            # Был пропуск - начинаем заново
            new_streak = 1
        
        logger.debug(f"Incrementing streak for user {chat_id}: {current_streak} -> {new_streak}")
        
        update_user_streak(chat_id, new_streak, today)
        
        # Проверяем что обновление прошло успешно
        verify_streak, verify_date = get_user_streak(chat_id)
        logger.debug(f"After update verification: streak={verify_streak}, date={verify_date}")
        
        return new_streak
        
    except Exception as e:
        logger.error(f"Error incrementing streak for user {chat_id}: {e}")
        return 0

def reset_user_streak(chat_id: int):
    """Сбрасывает количество дней подряд до 0."""
    try:
        logger.debug(f"Resetting streak for user {chat_id}")
        update_user_streak(chat_id, 0, None)  # ИСПРАВЛЕНИЕ: передаем None
        logger.info(f"Reset streak for user {chat_id}")
    except Exception as e:
        logger.error(f"Error resetting streak for user {chat_id}: {e}")

def calculate_streak_discount(chat_id: int) -> int:
    """Вычисляет скидку на подписку на основе количества дней подряд."""
    try:
        # Проверяем, есть ли у пользователя премиум подписка
        if not is_user_premium(chat_id):
            return 0  # Бесплатные пользователи не получают скидку
        
        streak, _ = get_user_streak(chat_id)
        
        # Валидация: streak не может быть отрицательным
        streak = max(0, streak)
        
        if streak <= 30:
            return streak  # Скидка равна количеству дней
        else:
            return 30  # Максимальная скидка 30%
            
    except Exception as e:
        logger.error(f"Error calculating streak discount for user {chat_id}: {e}")
        return 0

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
def generate_referral_code(chat_id: int) -> str:
    """Генерирует уникальный реферальный код для пользователя."""
    import hashlib
    import time
    raw_string = f"{chat_id}_{int(time.time())}"
    return hashlib.md5(raw_string.encode()).hexdigest()[:8].upper()

def set_user_referral_code(chat_id: int) -> str:
    """Устанавливает реферальный код пользователю, если его нет."""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT referral_code FROM users WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                return result[0]
                
        # Генерируем новый код
        referral_code = generate_referral_code(chat_id)
        
        with db_manager.transaction() as tx:
            tx.execute("UPDATE users SET referral_code = ? WHERE chat_id = ?", 
                      (referral_code, chat_id))
        
        logger.info(f"Generated referral code {referral_code} for user {chat_id}")
        return referral_code
        
    except Exception as e:
        logger.error(f"Error setting referral code for user {chat_id}: {e}")
        return generate_referral_code(chat_id)

def add_referral(referrer_id: int, referred_id: int) -> bool:
    """Добавляет реферал в систему."""
    try:
        with db_manager.transaction() as tx:
            # Проверяем, что пользователь еще не является рефералом
            cursor = tx.cursor()  # Получаем курсор от транзакции
            cursor.execute("SELECT id FROM referrals WHERE referred_id = ?", (referred_id,))
            if cursor.fetchone():
                return False  # Уже является чьим-то рефералом
                
            # Проверяем, что пользователь не реферит сам себя
            if referrer_id == referred_id:
                return False
                
            # Добавляем реферал
            from datetime import datetime
            cursor.execute('''
                INSERT INTO referrals (referrer_id, referred_id, created_at)
                VALUES (?, ?, ?)
            ''', (referrer_id, referred_id, datetime.now().isoformat()))
            
        logger.info(f"Added referral: {referrer_id} -> {referred_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding referral {referrer_id} -> {referred_id}: {e}")
        return False

def get_user_referrals(chat_id: int) -> list:
    """Получает список рефералов пользователя."""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute('''
                SELECT r.referred_id, r.created_at, u.chat_id
                FROM referrals r
                LEFT JOIN users u ON r.referred_id = u.chat_id  
                WHERE r.referrer_id = ?
                ORDER BY r.created_at DESC
            ''', (chat_id,))
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting referrals for user {chat_id}: {e}")
        return []

def count_user_referrals(chat_id: int) -> int:
    """Подсчитывает количество рефералов пользователя."""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (chat_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error counting referrals for user {chat_id}: {e}")
        return 0

def get_user_by_referral_code(referral_code: str) -> tuple:
    """Получает пользователя по реферальному коду."""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE referral_code = ?", (referral_code,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting user by referral code {referral_code}: {e}")
        return None

def create_referral_reward(user_id: int, reward_type: str, reward_value: int, referrals_count: int):
    """Создает награду за рефералы."""
    try:
        with db_manager.transaction() as tx:
            from datetime import datetime
            tx.execute('''
                INSERT INTO referral_rewards 
                (user_id, reward_type, reward_value, referrals_count, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, reward_type, reward_value, referrals_count, datetime.now().isoformat()))
        
        logger.info(f"Created referral reward for user {user_id}: {reward_type} {reward_value}")
        
    except Exception as e:
        logger.error(f"Error creating referral reward for user {user_id}: {e}")

def process_referral_rewards(user_id: int) -> bool:
    """Обрабатывает награды за рефералы и активирует подписку."""
    try:
        referrals_count = count_user_referrals(user_id)
        
        # Проверяем, достиг ли пользователь 5 рефералов и не получал ли уже награду
        if referrals_count >= 5:
            with db_manager.get_cursor() as cursor:
                cursor.execute('''
                    SELECT COUNT(*) FROM referral_rewards 
                    WHERE user_id = ? AND reward_type = 'subscription' AND processed = TRUE
                ''', (user_id,))
                
                already_rewarded = cursor.fetchone()[0] > 0
                
                if not already_rewarded:
                    # Создаем награду
                    create_referral_reward(user_id, 'subscription', 1, referrals_count)
                    
                    # Активируем подписку на месяц
                    from services.payment import PaymentService
                    expiry_date = PaymentService.calculate_subscription_expiry(1, user_id)
                    update_user_subscription(user_id, "premium", expiry_date, f"referral_reward_{int(datetime.now().timestamp())}")
                    
                    # Отмечаем награду как обработанную
                    with db_manager.transaction() as tx:
                        tx.execute('''
                            UPDATE referral_rewards 
                            SET processed = TRUE 
                            WHERE user_id = ? AND reward_type = 'subscription' AND processed = FALSE
                        ''', (user_id,))
                    
                    logger.info(f"Processed referral reward for user {user_id}: 1 month subscription")
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing referral rewards for user {user_id}: {e}")
        return False