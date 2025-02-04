# database/crud.py
from database.db import cursor, conn

def add_user(chat_id: int):
    cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (chat_id, topic, word_index, reminder_time, proficiency_level) VALUES (?, ?, ?, ?, ?)",
            (chat_id, 'business', 0, '09:00', 'A1')
        )
        conn.commit()

def get_user(chat_id: int):
    cursor.execute("SELECT chat_id, topic, word_index, reminder_time, proficiency_level FROM users WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone()

def update_user_topic(chat_id: int, topic: str):
    cursor.execute("UPDATE users SET topic = ?, word_index = ? WHERE chat_id = ?", (topic, 0, chat_id))
    conn.commit()

def update_user_word_index(chat_id: int, new_index: int):
    cursor.execute("UPDATE users SET word_index = ? WHERE chat_id = ?", (new_index, chat_id))
    conn.commit()

def update_user_reminder_time(chat_id: int, reminder_time: str):
    cursor.execute("UPDATE users SET reminder_time = ? WHERE chat_id = ?", (reminder_time, chat_id))
    conn.commit()

def get_user_proficiency(chat_id: int):
    cursor.execute("SELECT proficiency_level FROM users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def update_user_proficiency(chat_id: int, level: str):
    cursor.execute("UPDATE users SET proficiency_level = ? WHERE chat_id = ?", (level, chat_id))
    conn.commit()

def add_word_to_dictionary(chat_id: int, word_data: dict):
    cursor.execute("""
        INSERT INTO dictionary (chat_id, word, translation, transcription, example)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, word_data['word'], word_data.get('translation', ''), word_data.get('transcription', ''), word_data.get('example', '')))
    conn.commit()

def get_user_dictionary(chat_id: int):
    cursor.execute("SELECT word, translation, transcription, example FROM dictionary WHERE chat_id = ?", (chat_id,))
    return cursor.fetchall()
