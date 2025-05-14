# utils/helpers.py

import os
import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import LEVELS_DIR, REMINDER_START, DURATION_HOURS, DEFAULT_SETS
from database import crud  # Добавляем глобальный импорт
from utils.visual_helpers import extract_english  # Импортируем из правильного модуля

# Настройка логирования
logger = logging.getLogger(__name__)

# Кэш для ежедневных слов
daily_words_cache = {}

# Хранение уникальных слов предыдущего дня
previous_daily_words = {}

def get_user_settings(chat_id):
    """Получает настройки пользователя для слов и повторений из базы данных."""
    try:
        from database import crud
        
        # Получаем пользователя напрямую из базы данных
        user = crud.get_user(chat_id)
        if user:
            # Используем прямой доступ к полям
            words_per_day = user[2]
            repetitions_per_word = user[3]
            return (words_per_day, repetitions_per_word)
        else:
            # Значения по умолчанию, если пользователь не найден
            return (5, 3)
    except Exception as e:
        logger.error(f"Error fetching user settings: {e}")
        return (5, 3)  # По умолчанию 5 слов и 3 повторения

def reset_daily_words_cache(chat_id):
    """
    Resets the daily words cache for a user.
    Improved with better logging and error handling.
    """
    try:
        if chat_id in daily_words_cache:
            logger.info(f"Resetting daily words cache for user {chat_id}")
            
            # Log data for debugging
            entry = daily_words_cache[chat_id]
            if len(entry) > 9:
                is_revision = entry[9]
                logger.debug(f"User {chat_id} was in revision mode: {is_revision}")
            
            # Remove from cache
            del daily_words_cache[chat_id]
            
            # Verify deletion
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
    """
    Вычисляет времена отправки уведомлений равномерно распределенных в заданном интервале.
    
    Args:
        total_count: Общее количество уведомлений
        first_time: Время начала в формате "HH:MM"
        duration_hours: Продолжительность интервала в часах
        tz: Часовой пояс пользователя
        
    Returns:
        Список времен в формате ["HH:MM", ...]
    """
    try:
        # Проверяем формат времени и добавляем секунды если их нет
        if len(first_time.split(':')) == 2:
            first_time = f"{first_time}:00"
            
        # Создаем объект datetime для базового времени
        base_time = datetime.strptime(first_time, "%H:%M:%S")
        
        # Если всего 1 уведомление, возвращаем только начальное время
        if total_count <= 1:
            return [base_time.strftime("%H:%M")]
            
        # Вычисляем интервал между уведомлениями (в секундах)
        interval_seconds = (duration_hours * 3600) / (total_count - 1) if total_count > 1 else 0
        
        # Создаем список времен
        times = []
        for i in range(total_count):
            # Добавляем интервал к базовому времени
            notification_time = base_time + timedelta(seconds=i * interval_seconds)
            # Форматируем время
            times.append(notification_time.strftime("%H:%M"))
            
        return times
    except ValueError as e:
        logger.error(f"Invalid time format '{first_time}': {e}")
        # Возвращаем равномерно распределенные времена как запасной вариант
        return [f"{int(i * 24 / total_count):02d}:00" for i in range(total_count)]
    except Exception as e:
        logger.error(f"Error computing notification times: {e}")
        # Простой запасной вариант в случае ошибки
        return ["12:00"] * total_count

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours, force_reset=False, chosen_set=None):
    """
    Генерирует или возвращает кэшированный список слов дня.
    Улучшенная версия с более понятной логикой выбора слов и режимом повторения.
    
    Возвращает:
    - tuple (messages, times) - список сообщений для отправки и времена отправки
    - None в случае ошибки
    - tuple (None, None, default_set) если требуется подтверждение для смены сета
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
            if chat_id in daily_words_cache:
                logger.info(f"Force reset daily words cache for user {chat_id}")
                del daily_words_cache[chat_id]
            if chat_id in previous_daily_words:
                logger.info(f"Force reset previous daily words for user {chat_id}")
                del previous_daily_words[chat_id]
        
        # Проверка кэша - возвращаем если данные актуальны
        if chat_id in daily_words_cache and not force_reset:
            cached = daily_words_cache[chat_id]
            if (cached[0] == today and cached[3] == first_time and 
                cached[4] == duration_hours and cached[5] == words_count and cached[6] == repetitions):
                return cached[1], cached[2]
            reset_daily_words_cache(chat_id)

        # Определяем выбранный сет слов
        if chosen_set is None:
            chosen_set = user_set_selection.get(chat_id, DEFAULT_SETS.get(level))
        
        # Получаем базовый сет для текущего уровня
        default_set = DEFAULT_SETS.get(level)
        
        # Проверяем несоответствие между сетом и уровнем
        set_level_mismatch = False
        
        # Если в имени сета есть префикс уровня (A1, A2, B1, B2, C1, C2)
        for prefix in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            if chosen_set and chosen_set.startswith(prefix) and prefix != level:
                set_level_mismatch = True
                logger.info(f"Выбранный сет '{chosen_set}' не соответствует текущему уровню '{level}'")
                break
        
        # Проверяем существование файла сета для конкретного уровня
        set_file_path = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
        if not os.path.exists(set_file_path) or set_level_mismatch:
            logger.warning(f"Сет '{chosen_set}' не существует для уровня {level} или не соответствует уровню. Путь: {set_file_path}")
            
            # Если у нас есть базовый сет для текущего уровня, предлагаем его
            if default_set:
                default_set_path = os.path.join(LEVELS_DIR, level, f"{default_set}.txt")
                if os.path.exists(default_set_path):
                    # Возвращаем специальное значение для запроса подтверждения
                    return None, None, default_set
                else:
                    logger.error(f"Базовый сет '{default_set}' не существует для уровня {level}. Путь: {default_set_path}")
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
            # Всегда используем extract_english для унификации формата и приведения к нижнему регистру
            learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
        except Exception as e:
            logger.error(f"Error getting learned words for user {chat_id}: {e}")
            learned_set = set()

        # Определяем невыученные слова из файла
        available_words = []
        for word in file_words:
            eng_word = extract_english(word).lower()
            if eng_word not in learned_set:
                available_words.append(word)
        
        # Получаем невыученные слова из предыдущего дня
        leftover_words = []
        if chat_id in previous_daily_words:
            for word in previous_daily_words[chat_id]:
                eng_word = extract_english(word).lower()
                if eng_word not in learned_set:
                    leftover_words.append(word)
        
        # Определяем общее количество доступных невыученных слов
        total_available = len(available_words) + len(leftover_words)
        
        # Минимальный порог невыученных слов - если меньше, переходим в режим повторения
        min_words_threshold = min(3, words_count // 2)  # Минимальный порог невыученных слов
        
        # Определяем, нужен ли режим повторения (все или почти все слова выучены)
        is_revision_mode = (total_available == 0) or (total_available < min_words_threshold and len(file_words) > 0)
        
        # Инициализируем переменные
        unique_words = []
        prefix_message = ""
        
        if is_revision_mode:
            # Режим повторения - все слова уже выучены
            logger.info(f"Режим повторения активирован для пользователя {chat_id}. Доступно слов: {total_available}")
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
                # Убираем дубликаты для точного подсчета
                total_unique = len(set([extract_english(w).lower() for w in (available_words + leftover_words)]))
                
                if total_unique > 0:
                    prefix_message = f"⚠️ Осталось всего {total_unique} невыученных слов в этом наборе!\n\n"
                else:
                    prefix_message = "🎓 Поздравляем! Вы выучили все слова в этом наборе.\n\n"
        
        # Создаем сообщения для отправки
        try:
            if prefix_message:
                messages_unique = [prefix_message] + ["🔹 " + word for word in unique_words]
            else:
                messages_unique = ["🔹 " + word for word in unique_words]
                
            # Создаем список сообщений с повторениями
            repeated_messages = []
            
            # Добавляем уникальные слова repetitions раз
            for _ in range(repetitions):
                repeated_messages.extend(messages_unique)
                
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

        # Вычисляем времена уведомлений равномерно в промежутке времени
        times = compute_notification_times(total_notifications, first_time, duration_hours, tz=user_tz)

        # Сохраняем в кэш с добавлением флага режима повторения
        daily_words_cache[chat_id] = (today, repeated_messages, times, first_time, duration_hours, 
                                    words_count, repetitions, user_tz, unique_words, is_revision_mode)
        
        return repeated_messages, times
    except Exception as e:
        logger.error(f"Unhandled error in get_daily_words_for_user for chat_id {chat_id}: {e}")
        # Возвращаем минимальный набор данных в случае ошибки
        return ["🔹 Error loading daily words"], ["12:00"]