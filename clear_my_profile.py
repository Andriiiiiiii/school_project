#pathtofile/clear_my_profile.py
from database.db import conn, cursor

def clear_my_profile(chat_id):
    cursor.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM dictionary WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM learned_words WHERE chat_id = ?", (chat_id,))
    conn.commit()
    print(f"Профиль пользователя с chat_id {chat_id} успешно удалён.")

if __name__ == '__main__':
    # Замените YOUR_CHAT_ID на ваш фактический chat_id (число)
    my_chat_id = 380675615 
    clear_my_profile(my_chat_id)
