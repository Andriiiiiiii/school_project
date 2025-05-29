# utils/helpers.py

import os
import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import LEVELS_DIR, REMINDER_START, DURATION_HOURS, DEFAULT_SETS, PRODUCTION_MODE
from database import crud
from utils.visual_helpers import extract_english

logger = logging.getLogger(__name__)

# Оптимизированные кэши
daily_words_cache = {}
previous_daily_words = {}

# Кэш файлов со словами (новый для продакшена)
_words_file_cache = {}
_cache_max_age = 3600  # 1 час

def get_user_settings(chat_id):
    """Получает настройки пользователя (оптимизированная версия)."""
    try:
        user = crud.get_user(chat_id)
        if user:
            return (user[2], user[3])  # words_per_day, repetitions_per_word
        return (5, 3)  # Значения по умолчанию
    except Exception as e:
        logger.error("Ошибка получения настроек пользователя %s: %s", chat_id, e)
        return (5, 3)

def reset_daily_words_cache(chat_id):
    """Сброс кэша слов дня для пользователя."""
    try:
        if chat_id in daily_words_cache:
            del daily_words_cache[chat_id]
            if not PRODUCTION_MODE:
                logger.info("Кэш слов дня сброшен для пользователя %s", chat_id)
    except Exception as e:
        logger.error("Ошибка сброса кэша для пользователя %s: %s", chat_id, e)

def load_words_for_set(level: str, chosen_set: str):
    """
    Загружает слова из файла с кэшированием для продакшена.
    """
    if not level or not chosen_set:
        return []
        
    cache_key = f"{level}_{chosen_set}"
    current_time = datetime.now().timestamp()
    
    # Проверяем кэш файлов
    if cache_key in _words_file_cache:
        cached_data, cache_time = _words_file_cache[cache_key]
        if current_time - cache_time < _cache_max_age:
            return cached_data
    
    filename = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
    words = []
    
    try:
        if not os.path.exists(filename):
            if not PRODUCTION_MODE:
                logger.warning("Файл набора не найден: %s", filename)
            return words
            
        # Пробуем основные кодировки
        for encoding in ("utf-8", "cp1251"):
            try:
                with open(filename, encoding=encoding) as f:
                    words = [line.strip() for line in f if line.strip()]
                break
            except UnicodeDecodeError:
                continue
        
        # Кэшируем результат
        _words_file_cache[cache_key] = (words, current_time)
        
        # Ограничиваем размер кэша
        if len(_words_file_cache) > 50:
            oldest_key = min(_words_file_cache.keys(), 
                           key=lambda k: _words_file_cache[k][1])
            del _words_file_cache[oldest_key]
        
        if not PRODUCTION_MODE:
            logger.debug("Загружено %d слов из %s", len(words), filename)
        
        return words
        
    except Exception as e:
        logger.error("Ошибка загрузки слов из %s: %s", filename, e)
        return words

def compute_notification_times(total_count, first_time, duration_hours, tz="Europe/Moscow"):
    """
    Вычисляет времена уведомлений (оптимизированная версия).
    """
    try:
        if len(first_time.split(':')) == 2:
            first_time = f"{first_time}:00"
            
        base_time = datetime.strptime(first_time, "%H:%M:%S")
        
        if total_count <= 1:
            return [base_time.strftime("%H:%M")]
            
        interval_seconds = (duration_hours * 3600) / (total_count - 1) if total_count > 1 else 0
        
        times = []
        for i in range(total_count):
            notification_time = base_time + timedelta(seconds=i * interval_seconds)
            times.append(notification_time.strftime("%H:%M"))
            
        return times
        
    except Exception as e:
        logger.error("Ошибка вычисления времени уведомлений: %s", e)
        return [f"{int(i * 24 / total_count):02d}:00" for i in range(total_count)]

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours, 
                           force_reset=False, chosen_set=None):
    """
    Генерирует список слов дня (оптимизированная версия для продакшена).
    """
    # Локальные импорты для избежания циклических зависимостей
    try:
        from handlers.settings import user_set_selection
    except ImportError:
        user_set_selection = {}

    try:
        from utils.subscription_helpers import is_set_available_for_user
    except ImportError:
        def is_set_available_for_user(chat_id, set_name):
            return True

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Принудительный сброс кэша
        if force_reset:
            if chat_id in daily_words_cache:
                del daily_words_cache[chat_id]
            if chat_id in previous_daily_words:
                del previous_daily_words[chat_id]
        
        # Проверка кэша
        if chat_id in daily_words_cache and not force_reset:
            cached = daily_words_cache[chat_id]
            if (cached[0] == today and cached[3] == first_time and 
                cached[4] == duration_hours and cached[5] == words_count and cached[6] == repetitions):
                return cached[1], cached[2]
            reset_daily_words_cache(chat_id)

        # Определение выбранного набора
        if chosen_set is None:
            chosen_set = user_set_selection.get(chat_id, DEFAULT_SETS.get(level))
        
        # Проверка доступности набора
        if not is_set_available_for_user(chat_id, chosen_set):
            try:
                from utils.subscription_helpers import get_available_sets_for_user
                available_sets = get_available_sets_for_user(chat_id, level)
                if available_sets:
                    chosen_set = available_sets[0]
                else:
                    return None
            except ImportError:
                chosen_set = DEFAULT_SETS.get(level)
                if not chosen_set:
                    return None

        # Проверка соответствия уровня и набора
        default_set = DEFAULT_SETS.get(level)
        set_level_mismatch = False
        
        for prefix in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            if chosen_set and chosen_set.startswith(prefix) and prefix != level:
                set_level_mismatch = True
                break
        
        set_file_path = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
        if not os.path.exists(set_file_path) or set_level_mismatch:
            if default_set:
                default_set_path = os.path.join(LEVELS_DIR, level, f"{default_set}.txt")
                if os.path.exists(default_set_path):
                    return None, None, default_set
                else:
                    return None
            else:
                return None

        # Загрузка слов из набора
        file_words = load_words_for_set(level, chosen_set)
        if not file_words:
            return None

        # Получение выученных слов
        try:
            learned_raw = crud.get_learned_words(chat_id)
            learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
        except Exception as e:
            logger.error("Ошибка получения выученных слов для пользователя %s: %s", chat_id, e)
            learned_set = set()

        # Определение доступных слов
        available_words = []
        for word in file_words:
            eng_word = extract_english(word).lower()
            if eng_word not in learned_set:
                available_words.append(word)
        
        # Получение невыученных слов из предыдущего дня
        leftover_words = []
        if chat_id in previous_daily_words:
            for word in previous_daily_words[chat_id]:
                eng_word = extract_english(word).lower()
                if eng_word not in learned_set:
                    leftover_words.append(word)
        
        total_available = len(available_words) + len(leftover_words)
        min_words_threshold = min(3, words_count // 2)
        
        # Определение режима повторения
        is_revision_mode = (total_available == 0) or (total_available < min_words_threshold and len(file_words) > 0)
        
        unique_words = []
        prefix_message = ""
        
        if is_revision_mode:
            prefix_message = "🎓 Поздравляем! Вы выучили все слова в этом наборе. Вот некоторые для повторения:\n\n"
            
            if len(file_words) <= words_count:
                unique_words = file_words.copy()
            else:
                unique_words = random.sample(file_words, words_count)
        else:
            # Сначала добавляем слова из предыдущего дня
            if leftover_words:
                if len(leftover_words) <= words_count:
                    unique_words.extend(leftover_words)
                else:
                    unique_words.extend(random.sample(leftover_words, words_count))
            
            # Затем добавляем новые слова
            if len(unique_words) < words_count:
                words_needed = words_count - len(unique_words)
                remaining_available = [w for w in available_words if w not in unique_words]
                
                if remaining_available:
                    if len(remaining_available) <= words_needed:
                        unique_words.extend(remaining_available)
                    else:
                        unique_words.extend(random.sample(remaining_available, words_needed))
            
            # Проверка недостатка слов
            if len(unique_words) < words_count:
                total_unique = len(set([extract_english(w).lower() for w in (available_words + leftover_words)]))
                
                if total_unique > 0:
                    prefix_message = f"⚠️ Осталось всего {total_unique} невыученных слов в этом наборе!\n\n"
                else:
                    prefix_message = "🎓 Поздравляем! Вы выучили все слова в этом наборе.\n\n"
        
        # Создание сообщений
        try:
            if prefix_message:
                messages_unique = [prefix_message] + ["🔹 " + word for word in unique_words]
            else:
                messages_unique = ["🔹 " + word for word in unique_words]
                
            repeated_messages = []
            for _ in range(repetitions):
                repeated_messages.extend(messages_unique)
                
            total_notifications = len(repeated_messages)
        except Exception as e:
            logger.error("Ошибка создания сообщений: %s", e)
            messages_unique = ["🔹 Ошибка загрузки слов"]
            repeated_messages = messages_unique * repetitions
            total_notifications = len(repeated_messages)

        # Получение часового пояса пользователя
        try:
            user = crud.get_user(chat_id)
            user_tz = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
        except Exception:
            user_tz = "Europe/Moscow"

        # Вычисление времен уведомлений
        times = compute_notification_times(total_notifications, first_time, duration_hours, tz=user_tz)

        # Сохранение в кэш
        daily_words_cache[chat_id] = (today, repeated_messages, times, first_time, duration_hours, 
                                    words_count, repetitions, user_tz, unique_words, is_revision_mode)
        
        return repeated_messages, times
        
    except Exception as e:
        logger.error("Критическая ошибка в get_daily_words_for_user для пользователя %s: %s", chat_id, e)
        return ["🔹 Ошибка загрузки слов дня"], ["12:00"]

def cleanup_caches():
    """Очистка старых данных из кэшей (для продакшена)."""
    try:
        # Очистка кэша файлов
        current_time = datetime.now().timestamp()
        expired_keys = [
            key for key, (_, cache_time) in _words_file_cache.items()
            if current_time - cache_time > _cache_max_age
        ]
        for key in expired_keys:
            del _words_file_cache[key]
        
        # Очистка кэша слов дня (оставляем только сегодняшние)
        today = datetime.now().strftime("%Y-%m-%d")
        expired_users = [
            chat_id for chat_id, cached_data in daily_words_cache.items()
            if cached_data[0] != today
        ]
        for chat_id in expired_users:
            del daily_words_cache[chat_id]
        
        if not PRODUCTION_MODE and (expired_keys or expired_users):
            logger.info("Очищены кэши: %d файлов, %d пользователей", 
                       len(expired_keys), len(expired_users))
                       
    except Exception as e:
        logger.error("Ошибка очистки кэшей: %s", e)