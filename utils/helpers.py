import os
import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import LEVELS_DIR, REMINDER_START, DURATION_HOURS, DEFAULT_SETS
from database import crud
from utils.cache_manager import CacheManager

# Создаем экземпляр менеджера кэша с истечением срока действия 24 часа
daily_words_manager = CacheManager(expiry_time=86400)  # 24 часа в секундах

# Кэш для хранения слов предыдущего дня
previous_daily_words_manager = CacheManager(expiry_time=172800)  # 48 часов

# Настраиваем логирование
logger = logging.getLogger(__name__)

def reset_daily_words_cache(chat_id):
    """Сбрасывает кэш списка слов дня для данного пользователя."""
    daily_words_manager.delete(chat_id)
    logger.debug(f"Daily words cache reset for user {chat_id}")

def load_words_for_set(level: str, chosen_set: str):
    """
    Загружает слова из файла для выбранного сета.
    Файл ищется по пути LEVELS_DIR/level/chosen_set.txt.
    """
    filename = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
    if not os.path.exists(filename):
        logger.warning(f"Set file not found: {filename}")
        return []
        
    try:
        with open(filename, encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
        logger.debug(f"Loaded {len(words)} words from {filename}")
        return words
    except Exception as e:
        logger.error(f"Error loading words from {filename}: {e}")
        return []

def compute_notification_times(total_count, first_time, duration_hours, tz="Europe/Moscow"):
    try:
        base = datetime.strptime(first_time, "%H:%M").replace(tzinfo=ZoneInfo(tz))
        interval = timedelta(hours=duration_hours / total_count)
        times = [(base + n * interval).strftime("%H:%M") for n in range(total_count)]
        return times
    except Exception as e:
        logger.error(f"Error computing notification times: {e}")
        # Fallback to evenly distributed times
        try:
            hours_per_notification = duration_hours / total_count
            return [f"{int(hours_per_notification * n):02d}:00" for n in range(total_count)]
        except:
            logger.critical("Critical error in computing notification times")
            return ["12:00"] * total_count

def extract_english(word_line: str) -> str:
    """Извлекает английскую часть из строки формата 'word - translation'. Если разделитель не найден – возвращает всю строку."""
    if " - " in word_line:
        return word_line.split(" - ", 1)[0].strip()
    return word_line.strip()

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours, force_reset=False, chosen_set=None):
    """
    Генерирует или возвращает кэшированный список слов дня с учетом следующих правил.
    Если chosen_set не задан, берется выбранный пользователем сет из глобального словаря,
    а если пользователь не выбирал – используется основной набор из DEFAULT_SETS.
    """
    # Локальный импорт для избежания циклического импорта
    from handlers.settings import user_set_selection

    today = datetime.now().strftime("%Y-%m-%d")
    
    if force_reset:
        reset_daily_words_cache(chat_id)
        previous_daily_words_manager.delete(chat_id)
    
    # Проверка наличия кэшированных данных
    cached_data = daily_words_manager.get(chat_id)
    if cached_data:
        cached_today, repeated_messages, times, cached_first_time, cached_duration_hours, cached_words_count, cached_repetitions, user_tz, unique_words = cached_data
        
        # Проверяем актуальность кэша
        if (cached_today == today and cached_first_time == first_time and 
            cached_duration_hours == duration_hours and cached_words_count == words_count and 
            cached_repetitions == repetitions):
            logger.debug(f"Using cached daily words for user {chat_id}")
            return repeated_messages, times
        
        # Если кэш не актуален - сбрасываем его
        reset_daily_words_cache(chat_id)
        logger.debug(f"Cache invalidated for user {chat_id}: settings changed")

    # Определяем выбранный сет: если не передан, пробуем получить из глобального словаря, иначе основной из DEFAULT_SETS
    if chosen_set is None:
        chosen_set = user_set_selection.get(chat_id, DEFAULT_SETS.get(level))
    
    file_words = load_words_for_set(level, chosen_set)
    if not file_words:
        logger.warning(f"No words found for level {level}, set {chosen_set}")
        return None

    try:
        learned_raw = crud.get_learned_words(chat_id)
        learned_set = set(extract_english(item[0]) for item in learned_raw)

        # Логика выбора слов для изучения
        if len(learned_set) >= len(file_words):
            if len(file_words) >= words_count:
                unique_words = random.sample(file_words, words_count)
            else:
                unique_words = file_words[:]
        else:
            available_words = [w for w in file_words if extract_english(w) not in learned_set]
            
            # Получаем слова предыдущего дня из кэша
            previous_words = previous_daily_words_manager.get(chat_id) or []
            leftover = [w for w in previous_words if extract_english(w) not in learned_set]
            
            if len(leftover) >= words_count:
                unique_words = random.sample(leftover, words_count)
            else:
                needed_new = words_count - len(leftover)
                candidates = [w for w in available_words if w not in leftover]
                if len(candidates) >= needed_new:
                    new_words = random.sample(candidates, needed_new)
                else:
                    new_words = candidates
                unique_words = leftover + new_words
        
        messages_unique = ["🔹 " + word for word in unique_words]
        repeated_messages = messages_unique * repetitions
        total_notifications = len(unique_words) * repetitions

        user = crud.get_user(chat_id)
        user_tz = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
        times = compute_notification_times(total_notifications, first_time, duration_hours, tz=user_tz)

        # Сохраняем в кэш
        cache_data = (today, repeated_messages, times, first_time, duration_hours, words_count, repetitions, user_tz, unique_words)
        daily_words_manager.set(chat_id, cache_data)
        logger.debug(f"Daily words generated and cached for user {chat_id}")
        
        return repeated_messages, times
    except Exception as e:
        logger.error(f"Error generating daily words for user {chat_id}: {e}")
        return None