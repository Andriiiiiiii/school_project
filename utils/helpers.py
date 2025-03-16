# utils/helpers.py
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import LEVELS_DIR, REMINDER_START, DURATION_HOURS
from database import crud

# Кэш для ежедневных слов: ключ – chat_id, значение – 
# (today, repeated_messages, times, first_time, duration_hours, words_count, repetitions, user_tz, unique_words)
daily_words_cache = {}

# Хранение уникальных слов предыдущего дня: ключ – chat_id, значение – список строк
previous_daily_words = {}

def reset_daily_words_cache(chat_id):
    """Сбрасывает кэш списка слов дня для данного пользователя."""
    if chat_id in daily_words_cache:
        del daily_words_cache[chat_id]

def load_words_for_level(level: str):
    filename = os.path.join(LEVELS_DIR, f"{level}.txt")
    if not os.path.exists(filename):
        return []
    with open(filename, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    return words

def compute_notification_times(total_count, first_time, duration_hours, tz="Europe/Moscow"):
    base = datetime.strptime(first_time, "%H:%M").replace(tzinfo=ZoneInfo(tz))
    interval = timedelta(hours=duration_hours / total_count)
    times = [(base + n * interval).strftime("%H:%M") for n in range(total_count)]
    return times

def extract_english(word_line: str) -> str:
    """Извлекает английскую часть из строки формата 'word - translation'. Если разделитель не найден – возвращает всю строку."""
    if " - " in word_line:
        return word_line.split(" - ", 1)[0].strip()
    return word_line.strip()

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours, force_reset=False, selected_set=None):
    """
    Генерирует или возвращает кэшированный список слов дня с учетом следующих правил:
    
    Если selected_set передан, то слова загружаются из файла:
        LEVELS_DIR/level/selected_set.txt
    Иначе слова загружаются из файла LEVELS_DIR/level.txt.
    
    Остальная логика (исключение уже изученных слов, использование остатка предыдущего дня и т.д.) остаётся прежней.
    """
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
    
    if selected_set:
        filename = os.path.join(LEVELS_DIR, level, f"{selected_set}.txt")
        if not os.path.exists(filename):
            return None
        with open(filename, encoding="utf-8") as f:
            file_words = [line.strip() for line in f if line.strip()]
    else:
        file_words = load_words_for_level(level)
    
    if not file_words:
        return None

    learned_raw = crud.get_learned_words(chat_id)
    learned_set = set(extract_english(item[0]) for item in learned_raw)

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
    
    messages_unique = ["🔹 " + word for word in unique_words]
    repeated_messages = messages_unique * repetitions
    total_notifications = len(unique_words) * repetitions

    user = crud.get_user(chat_id)
    user_tz = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
    times = compute_notification_times(total_notifications, first_time, duration_hours, tz=user_tz)
    
    daily_words_cache[chat_id] = (today, repeated_messages, times, first_time, duration_hours, words_count, repetitions, user_tz, unique_words)
    return repeated_messages, times
