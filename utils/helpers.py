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
# Добавьте в utils/helpers.py улучшенную функцию сброса кэша

def reset_daily_words_cache(chat_id):
    """
    Сбрасывает кэш списка слов дня для данного пользователя.
    Улучшенная версия с более подробным логированием.
    """
    try:
        if chat_id in daily_words_cache:
            logger.info(f"Resetting daily words cache for user {chat_id}")
            # Сохраняем данные в лог для отладки
            entry = daily_words_cache[chat_id]
            if len(entry) > 9:
                is_revision = entry[9]
                logger.debug(f"User {chat_id} was in revision mode: {is_revision}")
            
            # Удаляем запись из кэша
            del daily_words_cache[chat_id]
            logger.debug(f"Cache reset for user {chat_id}")
            
            # Проверяем успешность удаления
            if chat_id not in daily_words_cache:
                logger.info(f"Cache successfully reset for user {chat_id}")
            else:
                logger.error(f"Failed to reset cache for user {chat_id}")
        else:
            logger.debug(f"No cache found for user {chat_id}, nothing to reset")
    except Exception as e:
        logger.error(f"Error resetting cache for user {chat_id}: {e}")

def load_words_for_set(level: str, chosen_set: str):
    """
    Загружает слова из файла для выбранного сета.
    Файл ищется по пути LEVELS_DIR/level/chosen_set.txt.
    """
    if not level or not chosen_set:
        logger.error(f"Неверные параметры: уровень={level}, сет={chosen_set}")
        return []
        
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
    except Exception as e:
        logger.error(f"Error computing notification times: {e}")
        # Простой запасной вариант в случае ошибки
        return ["12:00"] * total_count

# В файле utils/helpers.py исправляем функцию extract_english

def extract_english(word_line: str) -> str:
    """
    Извлекает английскую часть из строки формата 'word - translation'.
    Улучшенная версия для более надежной работы.
    """
    try:
        if not word_line or not isinstance(word_line, str):
            logger.error(f"Invalid input to extract_english: {word_line}")
            return ""
            
        # Стандартный формат 'word - translation'
        if " - " in word_line:
            return word_line.split(" - ", 1)[0].strip()
            
        # Альтернативный формат 'word – translation' (с длинным тире)
        if " – " in word_line:
            return word_line.split(" – ", 1)[0].strip()
            
        # Альтернативный формат 'word: translation'
        if ": " in word_line:
            return word_line.split(": ", 1)[0].strip()
            
        # Если строка начинается с emoji или специальных символов, удаляем их
        cleaned_line = word_line.strip()
        if cleaned_line and (cleaned_line[0] in ['🔹', '📌', '⏰', '⚠️', '🎓']):
            cleaned_line = cleaned_line[1:].strip()
            
        # Если разделитель не найден, возвращаем всю строку
        return cleaned_line
    except Exception as e:
        logger.error(f"Error extracting English word from '{word_line}': {e}")
        return word_line.strip() if isinstance(word_line, str) else ""

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours, force_reset=False, chosen_set=None):
    """
    Генерирует или возвращает кэшированный список слов дня.
    Улучшенная версия с более понятной логикой выбора слов и режимом повторения.
    
    Возвращает:
    - tuple (messages, times) - список сообщений для отправки и времена отправки
    - None в случае ошибки
    """
    # Локальный импорт для избежания циклического импорта
    try:
        from handlers.settings import user_set_selection
    except ImportError as e:
        logger.error(f"Error importing user_set_selection: {e}")
        user_set_selection = {}

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Принудительный сброс кэша если запрошено
        if force_reset:
            reset_daily_words_cache(chat_id)
            if chat_id in previous_daily_words:
                del previous_daily_words[chat_id]
        
        # Проверка кэша - возвращаем если данные актуальны
        if chat_id in daily_words_cache:
            cached = daily_words_cache[chat_id]
            if (cached[0] == today and cached[3] == first_time and 
                cached[4] == duration_hours and cached[5] == words_count and cached[6] == repetitions):
                return cached[1], cached[2]
            reset_daily_words_cache(chat_id)

        # Определяем выбранный сет слов
        if chosen_set is None:
            chosen_set = user_set_selection.get(chat_id, DEFAULT_SETS.get(level))
        
        # Проверяем существование файла сета для конкретного уровня
        set_file_path = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
        if not os.path.exists(set_file_path):
            logger.warning(f"Сет '{chosen_set}' не существует для уровня {level}. Путь: {set_file_path}")
            
            # Если файл не существует, пробуем установить базовый сет для текущего уровня
            default_set = DEFAULT_SETS.get(level)
            if default_set:
                default_set_path = os.path.join(LEVELS_DIR, level, f"{default_set}.txt")
                if os.path.exists(default_set_path):
                    # Обновляем выбранный сет в базе данных и кэше
                    try:
                        from database import crud
                        crud.update_user_chosen_set(chat_id, default_set)
                        user_set_selection[chat_id] = default_set
                        chosen_set = default_set
                        logger.info(f"Автоматически установлен базовый сет '{default_set}' для уровня {level} пользователю {chat_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении сета для пользователя {chat_id}: {e}")
                else:
                    logger.error(f"Базовый сет '{default_set}' тоже не существует для уровня {level}. Путь: {default_set_path}")
                    return None
            else:
                logger.error(f"Нет базового сета для уровня {level}")
                return None
        
        # Загружаем слова из выбранного сета
        file_words = load_words_for_set(level, chosen_set)
        if not file_words:
            logger.warning(f"No words found for level {level}, set {chosen_set}")
            return None

        # Получаем список уже выученных слов
        try:
            learned_raw = crud.get_learned_words(chat_id)
            # Всегда используем extract_english для унификации формата
            learned_set = set(extract_english(item[0]) for item in learned_raw)
        except Exception as e:
            logger.error(f"Error getting learned words for user {chat_id}: {e}")
            learned_set = set()

        # Определяем невыученные слова из файла
        available_words = []
        for word in file_words:
            eng_word = extract_english(word)
            if eng_word not in learned_set:
                available_words.append(word)
        
        # Получаем невыученные слова из предыдущего дня
        leftover_words = []
        if chat_id in previous_daily_words:
            for word in previous_daily_words[chat_id]:
                eng_word = extract_english(word)
                if eng_word not in learned_set:
                    leftover_words.append(word)
        
        # Определяем, в режиме повторения мы или нет
        is_revision_mode = len(available_words) == 0 and len(file_words) > 0
        
        unique_words = []
        prefix_message = ""
        
        if is_revision_mode:
            # Режим повторения - все слова уже выучены
            prefix_message = "🎓 Поздравляем! Вы выучили все слова в этом наборе. Вот некоторые для повторения:\n\n"
            # Выбираем случайные слова из всего набора для повторения
            if len(file_words) <= words_count:
                unique_words = file_words.copy()
            else:
                unique_words = random.sample(file_words, words_count)
        else:
            # Обычный режим - есть невыученные слова
            
            # 1. Сначала добавляем невыученные слова из предыдущего дня
            if leftover_words:
                if len(leftover_words) <= words_count:
                    unique_words.extend(leftover_words)
                else:
                    unique_words.extend(random.sample(leftover_words, words_count))
            
            # 2. Затем добавляем новые невыученные слова, если место еще осталось
            if len(unique_words) < words_count:
                words_needed = words_count - len(unique_words)
                remaining_available = [w for w in available_words if w not in unique_words]
                
                if remaining_available:
                    if len(remaining_available) <= words_needed:
                        unique_words.extend(remaining_available)
                    else:
                        unique_words.extend(random.sample(remaining_available, words_needed))
            
            # Проверяем, меньше ли слов, чем запрошено
            if len(unique_words) < words_count:
                # Если недостаточно слов, добавляем уведомление
                total_words = len(available_words) + len(leftover_words)
                # Убираем дубликаты
                total_unique = len(set([extract_english(w) for w in (available_words + leftover_words)]))
                
                if total_unique > 0:
                    prefix_message = f"⚠️ Осталось всего {total_unique} невыученных слов в этом наборе!\n\n"
                else:
                    # На всякий случай, хотя этот случай должен обрабатываться в is_revision_mode
                    prefix_message = "🎓 Поздравляем! Вы выучили все слова в этом наборе.\n\n"
        
        # Создаем сообщения для отправки
        try:
            if prefix_message:
                messages_unique = [prefix_message] + ["🔹 " + word for word in unique_words]
            else:
                messages_unique = ["🔹 " + word for word in unique_words]
                
            repeated_messages = messages_unique * repetitions
            total_notifications = len(repeated_messages)
        except Exception as e:
            logger.error(f"Error creating messages: {e}")
            messages_unique = ["🔹 Error loading words"]
            repeated_messages = messages_unique * repetitions
            total_notifications = len(repeated_messages)

        # Получаем часовой пояс пользователя
        try:
            user = crud.get_user(chat_id)
            user_tz = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
        except Exception as e:
            logger.error(f"Error getting user timezone: {e}")
            user_tz = "Europe/Moscow"

        # Вычисляем времена уведомлений
        times = compute_notification_times(total_notifications, first_time, duration_hours, tz=user_tz)

        # Сохраняем в кэш с добавлением флага режима повторения
        daily_words_cache[chat_id] = (today, repeated_messages, times, first_time, duration_hours, 
                                    words_count, repetitions, user_tz, unique_words, is_revision_mode)
        
        return repeated_messages, times
    except Exception as e:
        logger.error(f"Unhandled error in get_daily_words_for_user for chat_id {chat_id}: {e}")
        # Возвращаем минимальный набор данных в случае ошибки
        return ["🔹 Error loading daily words"], ["12:00"]