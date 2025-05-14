# clear_all_profiles.py
import logging
import sys
from database.db import db_manager
from utils.helpers import daily_words_cache, previous_daily_words, reset_daily_words_cache
from database import crud
import importlib

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_all_profiles(confirm=False):
    """Удаляет все данные всех пользователей из всех таблиц и очищает все кэши."""
    if not confirm:
        logger.warning("ВНИМАНИЕ! Эта операция удалит все профили пользователей и не может быть отменена.")
        response = input("Вы уверены, что хотите продолжить? (y/n): ")
        if response.lower() != 'y':
            logger.info("Операция отменена.")
            return
    
    try:
        # Получаем всех пользователей перед удалением
        try:
            all_users = crud.get_all_users()
            user_count = len(all_users)
            logger.info(f"Найдено пользователей: {user_count}")
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            all_users = []
            user_count = 0
        
        # Очистка кэшей
        logger.info("Очистка кэшей...")
        
        # Очистка daily_words_cache
        users_in_cache = list(daily_words_cache.keys())
        for user_id in users_in_cache:
            reset_daily_words_cache(user_id)
        daily_words_cache.clear()
        
        # Очистка previous_daily_words
        previous_daily_words.clear()
        
        # Очистка кэша user_set_selection в handlers.settings
        try:
            # Dynamically import to avoid circular imports
            settings_module = importlib.import_module('handlers.settings')
            if hasattr(settings_module, 'user_set_selection'):
                settings_module.user_set_selection.clear()
                logger.info("Кэш user_set_selection очищен.")
                
            if hasattr(settings_module, 'set_index_cache'):
                settings_module.set_index_cache.clear()
                logger.info("Кэш set_index_cache очищен.")
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша settings: {e}")

        # Очистка кэша в quiz
        try:
            quiz_module = importlib.import_module('handlers.quiz')
            if hasattr(quiz_module, 'quiz_states'):
                quiz_module.quiz_states.clear()
            if hasattr(quiz_module, 'poll_to_user'):
                quiz_module.poll_to_user.clear()
            if hasattr(quiz_module, 'poll_to_index'):
                quiz_module.poll_to_index.clear()
            if hasattr(quiz_module, 'nav_messages'):
                quiz_module.nav_messages.clear()
            logger.info("Кэш quiz очищен.")
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша quiz: {e}")
        
        # Очистка кэша в learning
        try:
            learning_module = importlib.import_module('handlers.learning')
            if hasattr(learning_module, 'states'):
                learning_module.states.clear()
            if hasattr(learning_module, 'lpoll2user'):
                learning_module.lpoll2user.clear()
            if hasattr(learning_module, 'lpoll2idx'):
                learning_module.lpoll2idx.clear()
            if hasattr(learning_module, 'lnav_msgs'):
                learning_module.lnav_msgs.clear()
            logger.info("Кэш learning очищен.")
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша learning: {e}")
            
        # Очистка кэша в scheduler
        try:
            scheduler_module = importlib.import_module('services.scheduler')
            if hasattr(scheduler_module, 'quiz_reminder_sent'):
                scheduler_module.quiz_reminder_sent.clear()
            if hasattr(scheduler_module, 'user_cache'):
                scheduler_module.user_cache.clear()
            scheduler_module.last_cache_update = 0
            logger.info("Кэш scheduler очищен.")
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша scheduler: {e}")
            
        # Используем транзакцию для удаления всех данных
        with db_manager.transaction() as conn:
            # Удаляем все данные из таблиц
            conn.execute("DELETE FROM learned_words")
            conn.execute("DELETE FROM dictionary")
            conn.execute("DELETE FROM users")
            
            # Проверка результатов удаления
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            users_left = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM dictionary")
            dictionary_left = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM learned_words")
            learned_left = cursor.fetchone()[0]
            
        logger.info(f"Удалено пользователей: {user_count}")
        logger.info(f"Осталось записей - users: {users_left}, dictionary: {dictionary_left}, learned_words: {learned_left}")
        logger.info("Все данные пользователей успешно удалены.")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при очистке данных пользователей: {e}")
        return False

if __name__ == '__main__':
    # Добавим параметр командной строки для автоматического подтверждения
    force = len(sys.argv) > 1 and sys.argv[1] == "--force"
    
    result = clear_all_profiles(confirm=force)
    if result:
        print("Успешно! Все профили и кэши очищены.")
    else:
        print("Произошла ошибка при очистке профилей. Проверьте логи.")