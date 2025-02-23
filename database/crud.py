from database.db import cursor, conn
from config import DEFAULT_WORDS_PER_DAY, DEFAULT_REPETITIONS, REMINDER_DEFAULT

def add_user(chat_id: int):
    cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
    if cursor.fetchone() is None:
        # notifications теперь используется для количества повторений
        cursor.execute(
            "INSERT INTO users (chat_id, level, words_per_day, notifications, reminder_time) VALUES (?, ?, ?, ?, ?)",
            (chat_id, 'A1', DEFAULT_WORDS_PER_DAY, DEFAULT_REPETITIONS, REMINDER_DEFAULT)
        )
        conn.commit()

def get_user(chat_id: int):
    cursor.execute("SELECT chat_id, level, words_per_day, notifications, reminder_time FROM users WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone()

def get_all_users():
    cursor.execute("SELECT chat_id, level, words_per_day, notifications, reminder_time FROM users")
    return cursor.fetchall()

def update_user_level(chat_id: int, level: str):
    cursor.execute("UPDATE users SET level = ? WHERE chat_id = ?", (level, chat_id))
    conn.commit()

def update_user_words_per_day(chat_id: int, count: int):
    cursor.execute("UPDATE users SET words_per_day = ? WHERE chat_id = ?", (count, chat_id))
    conn.commit()

def update_user_notifications(chat_id: int, count: int):
    cursor.execute("UPDATE users SET notifications = ? WHERE chat_id = ?", (count, chat_id))
    conn.commit()

def update_user_reminder_time(chat_id: int, time: str):
    cursor.execute("UPDATE users SET reminder_time = ? WHERE chat_id = ?", (time, chat_id))
    conn.commit()

def add_word_to_dictionary(chat_id: int, word_data: dict):
    cursor.execute("""
        INSERT INTO dictionary (chat_id, word, translation, transcription, example)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, word_data.get('word'), word_data.get('translation', ''), word_data.get('transcription', ''), word_data.get('example', '')))
    conn.commit()

def get_user_dictionary(chat_id: int, limit: int = 10, offset: int = 0):
    cursor.execute("SELECT word, translation, transcription, example FROM dictionary WHERE chat_id = ? ORDER BY id DESC LIMIT ? OFFSET ?", (chat_id, limit, offset))
    return cursor.fetchall()

def add_learned_word(chat_id: int, word: str, learned_date: str):
    cursor.execute("INSERT INTO learned_words (chat_id, word, learned_date) VALUES (?, ?, ?)", (chat_id, word, learned_date))
    conn.commit()

def get_learned_words(chat_id: int):
    cursor.execute("SELECT word FROM learned_words WHERE chat_id = ?", (chat_id,))
    return [row[0] for row in cursor.fetchall()]
