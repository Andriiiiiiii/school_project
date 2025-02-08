# database/db.py
import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            level TEXT DEFAULT 'A1',
            words_per_day INTEGER DEFAULT 5,
            notifications INTEGER DEFAULT 10,
            reminder_time TEXT DEFAULT '09:00'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            word TEXT,
            translation TEXT,
            transcription TEXT,
            example TEXT
        )
    ''')
    conn.commit()

init_db()
