# alter_db.py
from database.db import conn, cursor

def add_timezone_column():
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow'")
        conn.commit()
        print("Столбец 'timezone' успешно добавлен.")
    except Exception as e:
        print("Ошибка при добавлении столбца:", e)

if __name__ == '__main__':
    add_timezone_column()
