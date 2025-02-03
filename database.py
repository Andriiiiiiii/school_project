# database.py
import sqlite3

# Подключаемся к базе (файл bot.db создастся автоматически)
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    """
    Создаёт таблицы для пользователей и их словаря,
    если они ещё не существуют.
    Добавлены колонки reminder_time и proficiency_level.
    """
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            topic TEXT DEFAULT 'business',
            word_index INTEGER DEFAULT 0,
            reminder_time TEXT DEFAULT '09:00',
            proficiency_level TEXT DEFAULT 'A1'
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

init_db()  # Инициализируем базу данных

# Функции для работы с данными пользователей
def add_user(chat_id: int):
    """Добавляет нового пользователя, если его ещё нет в базе."""
    cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (chat_id, topic, word_index, reminder_time, proficiency_level) VALUES (?, ?, ?, ?, ?)",
            (chat_id, 'business', 0, '09:00', 'A1')
        )
        conn.commit()

def get_user(chat_id: int):
    """
    Возвращает данные пользователя: (chat_id, topic, word_index, reminder_time, proficiency_level).
    Если пользователь не найден, возвращается None.
    """
    cursor.execute("SELECT chat_id, topic, word_index, reminder_time, proficiency_level FROM users WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone()

def update_user_topic(chat_id: int, topic: str):
    """Обновляет тему пользователя и сбрасывает счётчик слов."""
    cursor.execute("UPDATE users SET topic = ?, word_index = ? WHERE chat_id = ?", (topic, 0, chat_id))
    conn.commit()

def update_user_word_index(chat_id: int, new_index: int):
    """Обновляет индекс текущего слова для пользователя."""
    cursor.execute("UPDATE users SET word_index = ? WHERE chat_id = ?", (new_index, chat_id))
    conn.commit()

def update_user_reminder_time(chat_id: int, reminder_time: str):
    """Обновляет время рассылки слова дня для пользователя."""
    cursor.execute("UPDATE users SET reminder_time = ? WHERE chat_id = ?", (reminder_time, chat_id))
    conn.commit()

def get_user_proficiency(chat_id: int):
    """Возвращает уровень владения языка пользователя."""
    cursor.execute("SELECT proficiency_level FROM users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def update_user_proficiency(chat_id: int, level: str):
    """Обновляет уровень владения языка пользователя."""
    cursor.execute("UPDATE users SET proficiency_level = ? WHERE chat_id = ?", (level, chat_id))
    conn.commit()

def add_word_to_dictionary(chat_id: int, word_data: dict):
    """Добавляет слово в личный словарь пользователя."""
    cursor.execute("""
        INSERT INTO dictionary (chat_id, word, translation, transcription, example)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, word_data['word'], word_data.get('translation', ''), word_data.get('transcription', ''), word_data.get('example', '')))
    conn.commit()

def get_user_dictionary(chat_id: int):
    """Возвращает список слов, добавленных в личный словарь пользователя."""
    cursor.execute("SELECT word, translation, transcription, example FROM dictionary WHERE chat_id = ?", (chat_id,))
    return cursor.fetchall()

# Список доступных тем (старый функционал)
TOPICS = ['business', 'IT', 'travel', 'movies']

# Встроенный словарь слов для каждой темы (старый функционал)
words_data = {
    'business': [
        {
            'word': 'profit',
            'translation': 'прибыль',
            'transcription': '/ˈprɒfɪt/',
            'example': 'The company made a huge profit last year.'
        },
        # ... другие слова ...
    ],
    'IT': [
        # ...
    ],
    'travel': [
        # ...
    ],
    'movies': [
        # ...
    ]
}
