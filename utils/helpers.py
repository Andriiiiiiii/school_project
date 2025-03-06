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

# Хранение уникальных слов предыдущего дня (как они записаны в файле): ключ – chat_id, значение – список строк
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

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours, force_reset=False):
    """
    Генерирует или возвращает кэшированный список слов дня с учетом следующих правил:
    
    1. Если пользователь ещё не изучил все слова из уровня, из файла исключаются слова, уже присутствующие в "моем словаре". 
       Для сравнения используется только английская часть (извлекается через extract_english).
    2. Если после фильтрации остается меньше слов, чем задано (например, требуется 8, а осталось 4),
       итоговый список состоит только из оставшихся уникальных слов.
    3. Если пользователь изучил все слова из уровня, выбор происходит случайно из всего файла.
    4. При генерации нового списка (при смене дня или изменении настроек) учитывается остаток предыдущего дня:
       - Если в previous_daily_words для данного chat_id есть невыученные слова, они включаются в новый список,
         а затем дополняются новыми уникальными словами до требуемого количества.
    5. Если force_reset=True (например, при изменении настроек), то сбрасываются кэш и предыдущий остаток.
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

    file_words = load_words_for_level(level)
    if not file_words:
        return None

    learned_raw = crud.get_learned_words(chat_id)
    # Извлекаем английские части для уже изученных слов
    learned_set = set(extract_english(item[0]) for item in learned_raw)

    if len(learned_set) >= len(file_words):
        # Если пользователь изучил все слова из файла, не фильтруем
        if len(file_words) >= words_count:
            unique_words = random.sample(file_words, words_count)
        else:
            unique_words = file_words[:]  # все слова
    else:
        # Формируем список доступных для изучения слов:
        available_words = [w for w in file_words if extract_english(w) not in learned_set]
        leftover = []
        if chat_id in previous_daily_words:
            # Используем остаток предыдущего дня (уже сохранённые строки) и фильтруем их по изученным словам
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
            # Если итоговое число уникальных слов меньше, чем words_count, список остается короче.
    
    # Формируем сообщения с префиксом
    messages_unique = ["🔹 " + word for word in unique_words]
    repeated_messages = messages_unique * repetitions
    total_notifications = len(unique_words) * repetitions

    user = crud.get_user(chat_id)
    user_tz = user[5] if user and len(user) > 5 and user[5] else "Europe/Moscow"
    times = compute_notification_times(total_notifications, first_time, duration_hours, tz=user_tz)

    # Сохраняем в кэш вместе с уникальными словами
    daily_words_cache[chat_id] = (today, repeated_messages, times, first_time, duration_hours, words_count, repetitions, user_tz, unique_words)
    return repeated_messages, times
