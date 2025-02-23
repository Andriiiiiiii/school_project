import os
import random
from datetime import datetime, timedelta
from config import LEVELS_DIR, REMINDER_START, DURATION_HOURS
from database import crud

# Кэш для ежедневных слов: ключ – chat_id, значение – (дата, messages, times, first_time, duration_hours, words_count, repetitions)
daily_words_cache = {}
# Постоянное хранилище для уже сохранённых наборов за сегодняшний день
daily_words_storage = {}

def load_words_for_level(level: str):
    filename = os.path.join(LEVELS_DIR, f"{level}.txt")
    if not os.path.exists(filename):
        return []
    with open(filename, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    return words

def compute_notification_times(total_count, first_time, duration_hours):
    """
    Вычисляет список из total_count времён уведомлений, начиная с first_time и равномерно распределяя
    интервал duration_hours между уведомлениями.
    Формат времени: "%H:%M".
    """
    base = datetime.strptime(first_time, "%H:%M")
    interval = timedelta(hours=duration_hours / total_count)
    times = [(base + n * interval).strftime("%H:%M") for n in range(total_count)]
    print(f"[DEBUG] compute_notification_times: total_count={total_count}, first_time={first_time}, duration_hours={duration_hours}")
    print(f"[DEBUG] Computed times: {times}")
    return times

def get_daily_words_for_user(chat_id, level, words_count, repetitions, first_time, duration_hours):
    """
    Если для данного chat_id уже сохранён окончательный набор слов на сегодняшний день
    (в daily_words_storage) с теми же параметрами, возвращает его.
    Иначе, если в кэше уже есть сгенерированный набор за сегодня с такими же параметрами,
    возвращает его. Если параметры не совпадают, удаляет старую запись и генерирует новый набор.
    
    Генерирует новый набор слов (исключая уже выученные), повторяет его repetitions раз,
    вычисляет времена уведомлений для общего числа уведомлений (words_count * repetitions)
    и сохраняет результат в кэш.
    
    Возвращает кортеж (repeated_messages, times) или None, если слов нет.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Сначала проверяем постоянное хранилище – если набор уже зафиксирован, возвращаем его.
    if chat_id in daily_words_storage:
        stored_date, messages, times, stored_first_time, stored_duration, stored_count, stored_reps = daily_words_storage[chat_id]
        if (stored_date == today and stored_first_time == first_time and 
            stored_duration == duration_hours and stored_count == words_count and stored_reps == repetitions):
            return messages, times

    # Если нет, проверяем кэш
    if chat_id in daily_words_cache:
        cached_date, messages, times, cached_first_time, cached_duration, cached_count, cached_reps = daily_words_cache[chat_id]
        if (cached_date == today and cached_first_time == first_time and 
            cached_duration == duration_hours and cached_count == words_count and cached_reps == repetitions):
            return messages, times
        else:
            del daily_words_cache[chat_id]

    words = load_words_for_level(level)
    if not words:
        return None

    # Исключаем уже выученные слова для данного пользователя
    learned = set(crud.get_learned_words(chat_id))
    available_words = [w for w in words if w not in learned]
    if not available_words:
        available_words = words

    if len(available_words) >= words_count:
        selected_words = random.sample(available_words, words_count)
    else:
        selected_words = random.choices(available_words, k=words_count)
    
    unique_messages = [f"🔹 {word}" for word in selected_words]
    repeated_messages = unique_messages * repetitions
    total_count = words_count * repetitions
    times = compute_notification_times(total_count, first_time, duration_hours)
    
    daily_words_cache[chat_id] = (today, repeated_messages, times, first_time, duration_hours, words_count, repetitions)
    return repeated_messages, times
