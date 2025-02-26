# clear_learned_words.py
from database.db import conn, cursor

def clear_learned_words():
    cursor.execute("DELETE FROM learned_words")
    conn.commit()
    print("Таблица learned_words очищена.")

if __name__ == '__main__':
    clear_learned_words()
