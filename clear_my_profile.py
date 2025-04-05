# clear_my_profile.py
import logging
from database.db import db_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_my_profile(chat_id):
    """Удаляет все данные пользователя из всех таблиц."""
    try:
        # Используем транзакцию для обеспечения консистентности данных
        with db_manager.transaction() as conn:
            conn.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
            conn.execute("DELETE FROM dictionary WHERE chat_id = ?", (chat_id,))
            conn.execute("DELETE FROM learned_words WHERE chat_id = ?", (chat_id,))
        logger.info(f"Профиль пользователя с chat_id {chat_id} успешно удалён.")
    except Exception as e:
        logger.error(f"Ошибка при удалении профиля пользователя: {e}")

if __name__ == '__main__':
    # Замените YOUR_CHAT_ID на ваш фактический chat_id (число)
    my_chat_id = 380675615 
    clear_my_profile(my_chat_id)