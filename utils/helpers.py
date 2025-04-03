import os
import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import LEVELS_DIR, REMINDER_START, DURATION_HOURS, DEFAULT_SETS
from database import crud

# Настройка логирования
logger = logging.getLogger(__name__)

# Кэш для ежедневных слов
daily_words_cache = {}

# Хранение уникальных слов предыдущего дня
previous_daily_words = {}

def reset_daily_words_cache(chat_id):
    """Сбрасывает кэш списка слов дня для данного пользователя."""
    try:
        if chat_id in daily_words_cache:
            del daily_words_cache[chat_id]
            logger.debug(f"Cache reset for user {chat_id}")
    except Exception as e:
        logger.error(f"Error resetting cache for user {chat_id}: {e}")

def load_words_for_set(level: str, chosen_set: str):
    """
    Загружает слова из файла для выбранного сета.
    Файл ищется по пути LEVELS_DIR/level/chosen_set.txt.
    """
    filename = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
    words = []
    
    try:
        if not os.path.exists(filename):
            logger.warning(f"Set file not found: {filename}")
            return words
            
        with open(filename, encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
        
        logger.debug(f"Loaded {len(words)} words from {filename}")
        return words
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return words
    except PermissionError:
        logger.error(f"Permission denied when accessing file: {filename}")
        return words
    except UnicodeDecodeError:
        logger.error(f"Unicode decode error in file: {filename}")
        try:
            # Попытка открыть файл с другой кодировкой
            with open(filename, encoding="cp1251") as f:
                words = [line.strip() for line in f if line.strip()]
            logger.info(f"Successfully loaded file with cp1251 encoding: {filename}")
            return words
        except Exception as e:
            logger.error(f"Failed to load file with alternative encoding: {e}")
            return words
    except Exception as e:
        logger.error(f"Error loading words from {filename}: {e}")
        return words

def compute_notification_times(total_count, first_time, duration_hours, tz="Europe/Moscow"):
    """Вычисляет времена отправки уведомлений."""
    try:
        base = datetime.strptime(first_time, "%H:%M").replace(tzinfo=ZoneInfo(tz))
        interval = timedelta(hours=duration_hours / total_count)
        times = [(base + n * interval).strftime("%H:%M") for n in range(total_count)]
        return times
    except ValueError as e:
        logger.error(f"Invalid time format '{first_time}': {e}")
        # Возвращаем равномерно распределенные времена как запасной вариант
        return [f"{int(i * 24 / total_count):02d}:00" for i in range(total_count)]
    except ZoneInfoNotFoundError as e:
        logger.error(f"Invalid timezone '{tz}': {e}")
        # Используем UTC как запасной вариант
        return compute_notification_times(total_count, first_time, duration_hours, "UTC")
    except Exception as e:
        logger.error(f"Error computing notification times: {e}")
        # Простой запасной вариант в случае ошибки
        return ["12:00"] * total_count

def extract_english(word_line: str) -> str:
    """Извлекает английскую часть из строки формата 'word - translation'."""
    try:
        if " - " in word_line:
            return word_line.split(" - ", 1)[0].strip()
        return word_line.strip()
    except Exception as e:
        logger.error(f"Error extracting English word from '{word_line}': {e}")
        return word_line.strip() if isinstance(word_line, str) else ""

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours, force_reset=False, chosen_set=None):
    """
    Генерирует или возвращает кэшированный список слов дня.
    """
    # Локальный импорт для избежания циклического импорта
    try:
        from handlers.settings import user_set_selection
    except ImportError as e:
        logger.error(f"Error importing user_set_selection: {e}")
        user_set_selection = {}

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        if force_reset:
            reset_daily_words_cache(chat_id)
            if chat_id in previous_daily_words:
                del previous_daily_words[chat_id]
        
        if chat_id in daily_words_cache:
            cached = daily_words_cache[chat_id]
            if (cached[0] == today and cached[3] == first_time and 
                cached[4] == duration_hours and cached[5] == words_count and cached[6] == repetitions):
                return cached[1], cached[2]
            reset_daily_words_cache(chat_id)

        # Определяем выбранный сет
        if chosen_set is None:
            chosen_set = user_set_selection.get(chat_id, DEFAULT_SETS.get(level))
        
        file_words = load_words_for_set(level, chosen_set)
        if not file_words:
            logger.warning(f"No words found for level {level}, set {chosen_set}")
            return None

        # Получаем выученные слова
        try:
            learned_raw = crud.get_learned_words(chat_id)
            learned_set = set(extract_english(item[0]) for item in learned_raw)
        except Exception as e:
            logger.error(f"Error getting learned words for user {chat_id}: {e}")
            learned_set = set()

        # Логика выбора слов
        try:
            if len(learned_set) >= len(file_words):
                if len(file_words) >= words_count:
                    unique_words = random.sample(file_words, words_count)
                else:
                    unique_words = file_words[:]
            else:
                available_words = [w for w in file_words if extract_english(w) not in learned_set]
                leftover = []
                if chat_id in previous_daily_words:
                    leftover = [w for w in previous_daily_words[chat_id] if extract_english(w) not in learned_set]
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
        except ValueError as e:
            logger.error(f"Error sampling words: {e}")
            # Запасной вариант: берём первые words_count слов или все доступные
            unique_words = file_words[:words_count] if len(file_words) >= words_count else file_words[:]
        
        # Создаем сообщения и времена
        try:
            messages_unique = ["🔹 " + word for word in unique_words]
            repeated_messages = messages_unique * repetitions
            total_notifications = len(unique_words) * repetitions
        except Exception as e:
            logger.error(f"Error creating messages: {e}")
            messages_unique = ["🔹 Error loading words"]
            repeated_messages = messages_unique * repetitions
            total_notifications = len(messages_unique) * repetitions

        # Получаем часовой пояс пользователя
        try:
            user = crud.get_user(chat_id)
            user_tz = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
        except Exception as e:
            logger.error(f"Error getting user timezone: {e}")
            user_tz = "Europe/Moscow"

        # Вычисляем времена уведомлений
        times = compute_notification_times(total_notifications, first_time, duration_hours, tz=user_tz)

        # Сохраняем в кэш
        daily_words_cache[chat_id] = (today, repeated_messages, times, first_time, duration_hours, words_count, repetitions, user_tz, unique_words)
        
        return repeated_messages, times
    except Exception as e:
        logger.error(f"Unhandled error in get_daily_words_for_user for chat_id {chat_id}: {e}")
        # Возвращаем минимальный набор данных в случае ошибки
        return ["🔹 Error loading daily words"], ["12:00"]