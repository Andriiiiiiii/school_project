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
    Генерирует список слов дня (ОТЛАДОЧНАЯ ВЕРСИЯ для выявления проблем).
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
        
        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Запуск для пользователя {chat_id}, force_reset={force_reset}")
        
        # Принудительный сброс кэша
        if force_reset:
            if chat_id in daily_words_cache:
                del daily_words_cache[chat_id]
                if not PRODUCTION_MODE:
                    print(f"🔍 DEBUG: Кэш сброшен для пользователя {chat_id}")
        
        # Проверка кэша
        if chat_id in daily_words_cache and not force_reset:
            cached = daily_words_cache[chat_id]
            if (cached[0] == today and cached[3] == first_time and 
                cached[4] == duration_hours and cached[5] == words_count and cached[6] == repetitions):
                if not PRODUCTION_MODE:
                    print(f"🔍 DEBUG: Возвращаю из кэша для пользователя {chat_id}")
                return cached[1], cached[2]
            reset_daily_words_cache(chat_id)

        # Определение выбранного набора
        if chosen_set is None:
            chosen_set = user_set_selection.get(chat_id, DEFAULT_SETS.get(level))
        
        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Выбранный набор: {chosen_set}")

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

        # Загрузка всех слов из набора
        all_words_in_set = load_words_for_set(level, chosen_set)
        if not all_words_in_set:
            return None

        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Загружено {len(all_words_in_set)} слов из набора")

        # Получение выученных слов пользователя
        try:
            learned_words_raw = crud.get_learned_words(chat_id)
            learned_english_words = set()
            for word_data in learned_words_raw:
                english_word = extract_english(word_data[0]).lower()
                learned_english_words.add(english_word)
            
            if not PRODUCTION_MODE:
                print(f"🔍 DEBUG: Выучено слов: {len(learned_english_words)}")
                if learned_english_words:
                    print(f"🔍 DEBUG: Первые 5 выученных: {list(learned_english_words)[:5]}")
                    
        except Exception as e:
            logger.error("Ошибка получения выученных слов для пользователя %s: %s", chat_id, e)
            learned_english_words = set()

        # Находим ВСЕ невыученные слова в наборе
        all_unlearned_words = []
        for word in all_words_in_set:
            english_part = extract_english(word).lower()
            if english_part not in learned_english_words:
                all_unlearned_words.append(word)

        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Невыученных слов: {len(all_unlearned_words)}")

        # Получаем leftover слова из предыдущего дня (только те, что еще не выучены)
        leftover_words = []
        if chat_id in previous_daily_words:
            for word in previous_daily_words[chat_id]:
                english_part = extract_english(word).lower()
                # Leftover слово должно быть среди невыученных
                if english_part not in learned_english_words and word in all_unlearned_words:
                    leftover_words.append(word)

        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Leftover слов: {len(leftover_words)}")

        # Определяем режим работы
        total_unlearned = len(all_unlearned_words)
        
        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Всего невыученных слов: {total_unlearned}")
            print(f"🔍 DEBUG: Настройка words_count: {words_count}")
        
        # ИСПРАВЛЕННАЯ ЛОГИКА ОПРЕДЕЛЕНИЯ РЕЖИМОВ
        if total_unlearned == 0:
            # РЕЖИМ ПОВТОРЕНИЯ: все слова выучены
            is_revision_mode = True
            unique_words = random.sample(all_words_in_set, min(words_count, len(all_words_in_set)))
            prefix_message = "🎓 Поздравляем! Вы выучили все слова в этом наборе. Вот некоторые для повторения:"
            
            if not PRODUCTION_MODE:
                print(f"🔍 DEBUG: РЕЖИМ ПОВТОРЕНИЯ - {len(unique_words)} слов")
        else:
            # ОБЫЧНЫЙ РЕЖИМ или ФАЗА ОСТАТКОВ
            is_revision_mode = False
            unique_words = []
            
            # Сначала добавляем leftover слова
            unique_words.extend(leftover_words)
            
            # Затем добавляем новые невыученные слова
            remaining_slots = words_count - len(unique_words)
            new_unlearned_words = [w for w in all_unlearned_words if w not in leftover_words]
            
            if not PRODUCTION_MODE:
                print(f"🔍 DEBUG: Remaining slots: {remaining_slots}")
                print(f"🔍 DEBUG: Новых невыученных слов: {len(new_unlearned_words)}")
            
            # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: ограничиваем количество новых слов доступными
            if remaining_slots > 0 and new_unlearned_words:
                words_to_add = min(remaining_slots, len(new_unlearned_words))
                unique_words.extend(random.sample(new_unlearned_words, words_to_add))
                
                if not PRODUCTION_MODE:
                    print(f"🔍 DEBUG: Добавлено новых слов: {words_to_add}")
            
            # Определяем нужно ли предупреждение о фазе остатков
            actual_word_count = len(unique_words)
            if actual_word_count < words_count:
                # ФАЗА ОСТАТКОВ
                prefix_message = f"⚠️ Осталось всего {actual_word_count} невыученных слов в этом наборе!"
                if not PRODUCTION_MODE:
                    print(f"🔍 DEBUG: ФАЗА ОСТАТКОВ - {actual_word_count} слов")
            else:
                # ОБЫЧНАЯ ФАЗА
                prefix_message = ""
                if not PRODUCTION_MODE:
                    print(f"🔍 DEBUG: ОБЫЧНАЯ ФАЗА - {actual_word_count} слов")

        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Финальные уникальные слова: {len(unique_words)}")
            print(f"🔍 DEBUG: Режим повторения: {is_revision_mode}")
            print(f"🔍 DEBUG: Префикс: {prefix_message[:50] if prefix_message else 'Нет префикса'}")

        # Создаем сообщения для уведомлений
        messages_for_notifications = ["🔹 " + word for word in unique_words]
        
        # Добавляем префиксное сообщение в начало если есть
        if prefix_message:
            messages_for_notifications.insert(0, prefix_message)
        
        # Повторяем сообщения согласно настройке repetitions
        repeated_messages = []
        for rep in range(repetitions):
            repeated_messages.extend(messages_for_notifications)

        # Получение часового пояса пользователя
        try:
            user = crud.get_user(chat_id)
            user_tz = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
        except Exception:
            user_tz = "Europe/Moscow"

        # Вычисление времен уведомлений
        total_notifications = len(repeated_messages)
        times = compute_notification_times(total_notifications, first_time, duration_hours, tz=user_tz)

        # Сохранение в кэш
        daily_words_cache[chat_id] = (
            today,                     # 0: дата
            repeated_messages,         # 1: повторяющиеся сообщения
            times,                    # 2: времена
            first_time,               # 3: первое время
            duration_hours,           # 4: продолжительность
            words_count,              # 5: количество слов
            repetitions,              # 6: повторения
            user_tz,                  # 7: часовой пояс
            unique_words,             # 8: уникальные слова
            is_revision_mode,         # 9: режим повторения
            prefix_message            # 10: префиксное сообщение
        )
        
        if not PRODUCTION_MODE:
            print(f"🔍 DEBUG: Сохранено в кэш для пользователя {chat_id}")
        
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